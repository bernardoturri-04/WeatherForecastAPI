import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt
from flask import request, current_app

from extensions import db
from models import User, RequestLog

ITALY_TZ = ZoneInfo("Europe/Rome")


def to_italian_time_str(dt):
    """Converts a naive UTC datetime into a formatted Italian local time string (handles DST automatically)."""
    if dt is None:
        return None
    dt_utc = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_it = dt_utc.astimezone(ITALY_TZ)
    return dt_it.strftime("%d/%m/%Y %H:%M:%S")

# --- Password hashing ---

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_error_json(errorcode, message=""):
    return {"errorcode": errorcode, "message": message}, errorcode


def to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def get_placeid(placename=None):
    from models import Place
    from sqlalchemy import func

    if placename is not None:
        place = Place.query.filter(func.lower(Place.name) == func.lower(placename)).first()
        return place.id if place is not None else None
    return None

TOKEN_EXPIRATION_SECONDS = 24 * 60 * 60 


def generate_token(user):
    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(seconds=TOKEN_EXPIRATION_SECONDS)
    }
    return jwt.encode(payload, current_app.secret_key, algorithm="HS256")


def get_authenticated_user():
    """
    Reads the 'Authorization: Bearer <token>' header, if present, and returns (user, error_response).
    error_response is None if everything is fine. If the header is missing entirely,
    user is None and error_response is None too (the caller decides whether that's allowed,
    e.g. anonymous access to GET /api/forecast).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None, None

    if not auth_header.startswith("Bearer "):
        return None, create_error_json(401, "Invalid Authorization header. Expected format: 'Bearer <token>'.")

    token = auth_header[len("Bearer "):].strip()
    try:
        payload = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, create_error_json(401, "Token expired. Login again via POST /api/auth/login.")
    except jwt.InvalidTokenError:
        return None, create_error_json(401, "Invalid token.")

    user = User.query.filter_by(id=payload.get("user_id")).first()
    if user is None:
        return None, create_error_json(401, "Token refers to a user that no longer exists.")

    return user, None


def require_authenticated_user():
    """Like get_authenticated_user, but a valid token is mandatory. Returns (user, error_response)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None, create_error_json(
            401,
            "Missing Authorization header. Login via POST /api/auth/login to obtain a token, "
            "then send it as 'Authorization: Bearer <token>'."
        )
    return get_authenticated_user()


# --- Daily request limits ---
ANONYMOUS_DAILY_LIMIT = 2    
FREE_DAILY_LIMIT = 100       


def get_request_identifier(user):
    """Returns the string used to track daily usage: the user id if authenticated, otherwise the client IP."""
    if user is not None:
        return f"user:{user.id}"
    else:
        return f"ip:{request.remote_addr}"


def get_daily_limit(user):
    """Returns the daily request limit for this user, or None if unlimited (premium)."""
    if user is None:
        return ANONYMOUS_DAILY_LIMIT
    elif user.is_premium:
        return None
    else:
        return FREE_DAILY_LIMIT


def check_and_increment_usage(user):
    """
    Checks today's usage for this user/IP against their daily limit, and increments it if allowed.
    Returns a tuple (allowed: bool, count: int, limit: int|None).
    """
    identifier = get_request_identifier(user)
    limit = get_daily_limit(user)
    today = datetime.utcnow().date()

    log = RequestLog.query.filter_by(identifier=identifier, day=today).first()
    if log is None:
        log = RequestLog(identifier=identifier, day=today, count=0)
        db.session.add(log)

    if limit is not None and log.count >= limit:
        return False, log.count, limit

    log.count += 1
    db.session.commit()
    return True, log.count, limit
