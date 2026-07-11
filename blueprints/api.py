import json
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask.views import MethodView
from sqlalchemy import func, Table

from extensions import db
from models import Place, Condition, Forecast, User, SavedQuery
from helpers import (create_error_json, to_dict, hash_password, generate_token,
                      TOKEN_EXPIRATION_SECONDS, check_and_increment_usage,
                      get_authenticated_user, require_authenticated_user, to_italian_time_str)

api_bp = Blueprint('api', __name__, url_prefix='/api')


class AuthLoginAPI(MethodView):
    """POST /api/auth/login - authenticates with username+password and returns a JWT access token."""

    def post(self):
        data = request.get_json(silent=True) or {}
        username = request.form.get("username", data.get("username"))
        password = request.form.get("password", data.get("password"))

        if not username or not password:
            return create_error_json(400, "Missing required parameters 'username' and 'password'.")

        user = User.query.filter_by(username=username, hashed_pw=hash_password(password)).first()
        if user is None:
            return create_error_json(401, "Wrong username or password.")

        token = generate_token(user)
        role = "admin" if user.is_admin else ("premium" if user.is_premium else "free")
        return jsonify({
            "token": token,
            "token_type": "Bearer",
            "expires_in": TOKEN_EXPIRATION_SECONDS,
            "username": user.username,
            "role": role
        })


class ForecastAPI(MethodView):
    """
    GET is open to everyone (anonymous included) but rate-limited (see helpers.check_and_increment_usage);
    PUT/DELETE always require a valid Bearer token.
    """

    def get(self):
        user, error = get_authenticated_user()
        if error is not None:
            return error

        allowed, count, limit = check_and_increment_usage(user)
        if not allowed:
            if user is None:
                message = f"Daily limit of {limit} anonymous requests reached. Login and use a token for a higher limit."
            elif not user.is_premium:
                message = f"Daily limit of {limit} requests reached for your account. Upgrade to premium for unlimited requests."
            else:
                message = "Daily request limit reached."
            return create_error_json(429, message)

        if "placeid" in request.args:
            placeid = request.args["placeid"]
        elif "placename" in request.args:
            placename = request.args["placename"]
            place = Place.query.filter(func.lower(Place.name) == func.lower(placename)).first()
            if place is None:
                return create_error_json(400, "Place not found. Check the value or use another parameter to specify a place.")
            else:
                placeid = place.id
        else:
            return create_error_json(400, "Missing required parameter, one of the following must be used: 'placename' or 'placeid'.")

        if "date" in request.args:
            try:
                date = datetime.fromisoformat(request.args["date"])
            except ValueError:
                return create_error_json(400, "Unable to parse 'date', provide it with the format 'yyyy-mm-dd' or 'yyyymmdd'.")
        else:
            date = datetime.today()

        if "time" in request.args:
            try:
                parsed_time = datetime.strptime(request.args["time"], "%H:%M").time()
                date = datetime.combine(date.date(), parsed_time)
            except ValueError:
                return create_error_json(400, "Unable to parse 'time', provide it with the format 'HH:MM'.")

        details = False
        if "details" in request.args:
            if request.args["details"].lower() == "true":
                details = True
            elif request.args["details"].lower() == "false":
                pass
            else:
                return create_error_json(400, "Unable to parse 'details', value must be 'true' or 'false'.")

        forecast = Forecast.query.filter_by(placeid=placeid, date=date).first()

        if forecast is None:
            return create_error_json(404, "Nothing was found in the database with the parameters specified.")

        result = {"id": forecast.id,
                  "placeid": forecast.placeid,
                  "date": forecast.date,
                  "condition": forecast.condition,
                  "temperature": forecast.temperature,
                  "rain": forecast.rain,
                  "humidity": forecast.humidity,
                  "wind": forecast.wind,
                  "wind_direction": forecast.wind_direction}
        if details:
            condition = Condition.query.filter_by(id=forecast.condition).first()
            result["condition_description"] = condition.description
            place = Place.query.filter_by(id=forecast.placeid).first()
            result["placename"] = place.name

        if user is not None and user.is_premium:
            saved_query = SavedQuery(user_id=user.id,
                                      placeid=placeid,
                                      date=date,
                                      result_json=json.dumps(result, default=str))
            db.session.add(saved_query)
            db.session.commit()

        result["requests_remaining_today"] = (limit - count) if limit is not None else "unlimited"
        return result

    def put(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        if not user.is_admin:
            return create_error_json(403, "Managing forecasts requires an admin account.")

        if "placeid" in request.form:
            placeid = request.form["placeid"]
        else:
            return create_error_json(400, "Missing required parameter 'placeid'.")

        if "date" in request.form:
            date = datetime.fromisoformat(request.form["date"])
        else:
            return create_error_json(400, "Missing required parameter 'date'.")

        condition = request.form.get("condition", None)
        temperature = request.form.get("temperature", None)
        rain = request.form.get("rain", None)
        humidity = request.form.get("humidity", None)
        wind = request.form.get("wind", None)
        wind_direction = request.form.get("wind_direction", None)
      
        forecast = Forecast.query.filter_by(placeid=placeid, date=date).first()
        created = forecast is None
        if forecast is None:
            forecast = Forecast(placeid=placeid, date=date)
            db.session.add(forecast)

        if condition is not None:
            forecast.condition = condition
        if temperature is not None:
            forecast.temperature = temperature
        if rain is not None:
            forecast.rain = rain
        if humidity is not None:
            forecast.humidity = humidity
        if wind is not None:
            forecast.wind = wind
        if wind_direction is not None:
            forecast.wind_direction = wind_direction

        db.session.commit()

        message = "Forecast created successfully" if created else "Forecast updated successfully"
        return {"message": message, "id": forecast.id}, 201 if created else 200

    def delete(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        
        if not user.is_admin:
            return create_error_json(403, "Managing forecasts requires an admin account.")

        if "forecastid" in request.form:
            forecastid = request.form["forecastid"]
        else:
            return create_error_json(400, "Missing required parameter 'forecastid'")

        forecast = Forecast.query.filter_by(id=forecastid).first()
        if forecast is None:
            return create_error_json(404, "Nothing was found in the database with the parameters specified.")

        db.session.delete(forecast)
        db.session.commit()

        return {"message": "Forecast deleted successfully"}, 200

class PlacesAPI(MethodView):
    """GET requires a valid token (any role). PUT/DELETE (managing places) require an admin account."""

    def get(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error

        if "placename" in request.args:
            place = Place.query.filter(func.lower(Place.name) == func.lower(request.args["placename"])).first()
        elif "placeid" in request.args:
            place = Place.query.filter_by(id=request.args["placeid"]).first()
        else:
            return create_error_json(400, "Missing required parameter, one of the following must be used: 'placename', 'placeid'")

        if place is None:
            return create_error_json(404, "Nothing was found in the database with the parameters specified.")
        return to_dict(place)

    def put(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        if not user.is_admin:
            return create_error_json(403, "Managing places requires an admin account.")

        if "placeid" in request.form:
            placeid = request.form["placeid"]
            placename = request.form.get("placename", None)
        else:
            placeid = None
            if "placename" in request.form:
                placename = request.form["placename"]
            else:
                return create_error_json(400, "Missing required parameter, one of the following must be used: 'placename', 'placeid'")

        coords = request.form.get("coords", None)
        lat = request.form.get("lat", None)
        lon = request.form.get("lon", None)
        if lat and lon:
            pass
        elif coords:
            try:
                lat, lon = coords.split(",")
                lat = float(lat)
                lon = float(lon)
            except Exception:
                return create_error_json(400, "Unable to parse 'coords', value must be of format 'float,float'.")
        else:
            return create_error_json(400, "Missing required parameter, one of the following must be used: 'coords' or 'lat' and 'lon'.")

        if placeid is not None:
            place = Place.query.filter_by(id=placeid).first()
            if place is None:
                return create_error_json(404, "No place was found in the database with the 'placeid' specified.")
            else:
                if placename is not None:
                    place.name = placename
                if lat is not None:
                    place.lat = lat
                if lon is not None:
                    place.lon = lon
        else:
            place = Place.query.filter_by(name=placename).first()
            created = place is None
            if place is None:
                place = Place(name=placename, lat=lat, lon=lon)
                db.session.add(place)
            else:
                place.lat = lat
                place.lon = lon

        db.session.commit()

        message = "Place created successfully" if created else "Place updated successfully"
        status_code = 201 if created else 200
        return {"message": message, "id": place.id}, status_code

    def delete(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        if not user.is_admin:
            return create_error_json(403, "Managing places requires an admin account.")

        if "placeid" in request.form:
            placeid = request.form["placeid"]
            place = Place.query.filter_by(id=placeid).first()
        elif "placename" in request.form:
            placename = request.form["placename"]
            place = Place.query.filter(func.lower(Place.name) == func.lower(placename)).first()
        else:
            return create_error_json(400, "Missing required parameter, one of the following must be used: 'placename', 'placeid'")

        if place is None:
            return create_error_json(404, "Nothing was found in the database with the 'placeid' specified.")

        deleted_forecasts = Forecast.query.filter_by(placeid=place.id).delete()

        db.session.delete(place)
        db.session.commit()

        return {"message": "Place deleted successfully", "forecasts_deleted": deleted_forecasts}, 200


class ConditionsAPI(MethodView):
    def get(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error

        if "id" in request.args:
            condition = Condition.query.filter_by(id=request.args["id"]).first()
            if condition is None:
                return create_error_json(404, "Nothing was found in the database with the parameters specified.")
            return to_dict(condition)
        else:
            data = {}
            for condition in Condition.query.all():
                data[condition.id] = condition.description
            return data


class SavedQueryListAPI(MethodView):
    """Premium only. Lists the saved forecast query history for the authenticated user (JSON only)."""

    def get(self):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        if not user.is_premium:
            return create_error_json(403, "Saved query history is a premium feature. Upgrade your account to access it.")

        queries = SavedQuery.query.filter_by(user_id=user.id).order_by(SavedQuery.requested_at.desc()).all()
        data = [{"id": q.id, "placeid": q.placeid, "date": q.date, "requested_at": to_italian_time_str(q.requested_at)} for q in queries]
        return jsonify(data)


class SavedQueryDetailAPI(MethodView):
    """Premium only. Returns the full detail of one saved query, including the original forecast result."""

    def get(self, query_id):
        user, error = require_authenticated_user()
        if error is not None:
            return error
        if not user.is_premium:
            return create_error_json(403, "Saved query history is a premium feature. Upgrade your account to access it.")

        saved_query = SavedQuery.query.filter_by(id=query_id, user_id=user.id).first()
        if saved_query is None:
            return create_error_json(404, "No saved query was found with this id for your account.")

        try:
            result = json.loads(saved_query.result_json) if saved_query.result_json else None
        except (TypeError, ValueError):
            result = None

        return jsonify({"id": saved_query.id,
                         "placeid": saved_query.placeid,
                         "date": saved_query.date,
                         "requested_at": to_italian_time_str(saved_query.requested_at),
                         "result": result})


class AllTablesAPI(MethodView):
    """Debug-only endpoint: dumps every row of every table."""

    def get(self):
        metadata = db.MetaData()
        metadata.reflect(bind=db.engine)

        result = []
        for table_name in metadata.tables.keys():
            table = Table(table_name, metadata, autoload_with=db.engine)
            tb = {table_name: []}
            for row in db.session.query(table).all():
                row_data = {column.name: getattr(row, column.name) for column in table.columns}
                tb[table_name].append(row_data)
            result.append(tb)

        return jsonify(result)


api_bp.add_url_rule('/auth/login', view_func=AuthLoginAPI.as_view('auth_login_api'))
api_bp.add_url_rule('/forecast', view_func=ForecastAPI.as_view('forecast_api'))
api_bp.add_url_rule('/places', view_func=PlacesAPI.as_view('places_api'))
api_bp.add_url_rule('/conditions', view_func=ConditionsAPI.as_view('conditions_api'))
api_bp.add_url_rule('/queries', view_func=SavedQueryListAPI.as_view('queries_list_api'))
api_bp.add_url_rule('/queries/<int:query_id>', view_func=SavedQueryDetailAPI.as_view('queries_detail_api'))
api_bp.add_url_rule('/alltables', view_func=AllTablesAPI.as_view('alltables_api'))
