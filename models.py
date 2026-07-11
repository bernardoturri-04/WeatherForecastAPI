from datetime import datetime

from extensions import db


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)


class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(50))


class Forecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placeid = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    condition = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    rain = db.Column(db.Float)
    humidity = db.Column(db.Integer)
    wind = db.Column(db.Integer)
    wind_direction = db.Column(db.String(5))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    hashed_pw = db.Column(db.String(64))
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)


class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), nullable=False)
    day = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (db.UniqueConstraint('identifier', 'day', name='uq_requestlog_identifier_day'),)


class SavedQuery(db.Model):
    #Stores the history of forecast queries made by premium users.
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    placeid = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    result_json = db.Column(db.Text)
