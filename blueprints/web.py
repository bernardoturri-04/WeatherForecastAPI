from flask import Blueprint, request, render_template, session, redirect

from extensions import db
from models import User
from helpers import hash_password, generate_token

web_bp = Blueprint('web', __name__)


@web_bp.route("/")
def home():
    return render_template("index.html", error="")


@web_bp.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "GET":
        if "username" in session and session["username"] is not None:
            return redirect('/dashboard')
        else:
            return render_template("login.html", error="")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = hash_password(password)

        user = User.query.filter_by(username=username, hashed_pw=hashed_pw).first()
        if user is None:
            return render_template("login.html", error="Wrong username or password!")
        else:
            session['username'] = username
            return redirect('/dashboard')


@web_bp.route("/logout")
def logout():
    if request.method == "GET":
        if "username" in session:
            del session["username"]
    return redirect('/')


@web_bp.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == "GET":
        return render_template("login.html", error="")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = hash_password(password)

        user = User.query.filter_by(username=username).first()
        if user is not None:
            return render_template("login.html", error="An user with this username already exists!")

        user = User(username=username, hashed_pw=hashed_pw)
        db.session.add(user)
        session['username'] = username
        db.session.commit()

        return redirect('/dashboard')


@web_bp.route("/apicalls")
def apicalls():
    return render_template("apicalls.html")


@web_bp.route("/urlslist")
def urlslist():
    return render_template("urlslist.html")


@web_bp.route("/dashboard")
def dashboard():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        return render_template("dashboard.html", username=session["username"], is_premium=user.is_premium)
    else:
        return redirect('/')


@web_bp.route("/upgrade", methods=["GET"])
def upgrade():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        user.is_premium = True
        db.session.commit()
        return redirect('/dashboard')
    else:
        return "User is not authenticated yet. Go to homepage to login."


@web_bp.route("/downgrade", methods=["GET"])
def downgrade():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        user.is_premium = False
        db.session.commit()
        return redirect('/dashboard')
    else:
        return "User is not authenticated yet. Go to homepage to login."


@web_bp.route("/generatetoken", methods=["GET"])
def generatetoken():
    if request.method == "GET":
        if "username" in session:
            user = User.query.filter_by(username=session["username"]).first()
            token = generate_token(user)
            return token
        else:
            return "User is not authenticated yet. Go to homepage to login."
