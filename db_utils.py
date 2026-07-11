from datetime import datetime
import hashlib

from extensions import db
from models import Place, Condition, Forecast, User

conditions = [
    "Clear",
    "Partly Cloudy",
    "Mostly Cloudy",
    "Cloudy",
    "Foggy",
    "Light Rain",
    "Rain",
    "Heavy Rain",
    "Showers",
    "Thunderstorm",
    "Snow",
    "Windy"
]


# erases all the db and repopulates the tables with some example data
def reset_db(app):
    with app.app_context():
        db.create_all()

        # erases db
        metadata = db.MetaData()
        metadata.reflect(bind=db.engine)
        for table in reversed(metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        for condition in conditions:
            db.session.add(Condition(description=condition))
            
        db.session.add(Place(id=1, name="Bruxelles", lat=50.85045, lon=4.34878))
        db.session.add(Place(id=2, name="Lubiana", lat=46.0564, lon=14.50575))
        db.session.add(Place(id=3, name="Faenza", lat=44.285557, lon=11.883333))
        db.session.add(Place(id=4, name="Roma", lat=43.8777, lon=11.1022))

        # add sample entities to db for testing purpose
        db.session.add(Forecast(placeid=1, date=datetime(2026, 7, 1), condition=1, temperature=31.3, rain=0, humidity=30, wind=3, wind_direction="N"))
        db.session.add(Forecast(placeid=2, date=datetime(2026, 7, 1), condition=1, temperature=30.1, rain=0, humidity=32, wind=5, wind_direction="NE"))
        db.session.add(Forecast(placeid=3, date=datetime(2026, 7, 1), condition=2, temperature=32.1, rain=0, humidity=32, wind=5, wind_direction="NO"))
        db.session.add(Forecast(placeid=4, date=datetime(2026, 7, 1), condition=4, temperature=29.1, rain=0, humidity=72, wind=2, wind_direction="SE"))

        db.session.add(Forecast(placeid=1, date=datetime(2026, 7, 2), condition=2, temperature=29.4, rain=0, humidity=35, wind=8, wind_direction="S"))
        db.session.add(Forecast(placeid=2, date=datetime(2026, 7, 2), condition=2, temperature=27.5, rain=0, humidity=40, wind=7, wind_direction="SO"))
        db.session.add(Forecast(placeid=3, date=datetime(2026, 7, 2), condition=3, temperature=24.1, rain=0, humidity=42, wind=7, wind_direction="SE"))
        db.session.add(Forecast(placeid=4, date=datetime(2026, 7, 2), condition=5, temperature=30.1, rain=0, humidity=12, wind=7, wind_direction="S"))
        
        db.session.add(Forecast(placeid=1, date=datetime(2026, 7, 3), condition=3, temperature=28.7, rain=0, humidity=30, wind=4, wind_direction="E"))
        db.session.add(Forecast(placeid=2, date=datetime(2026, 7, 3), condition=3, temperature=27.3, rain=0, humidity=30, wind=9, wind_direction="E"))
        db.session.add(Forecast(placeid=3, date=datetime(2026, 7, 3), condition=5, temperature=19.8, rain=1, humidity=52, wind=8, wind_direction="O"))
        db.session.add(Forecast(placeid=4, date=datetime(2026, 7, 3), condition=10, temperature=15.8, rain=1, humidity=92, wind=8, wind_direction="SW"))
        
        db.session.add(User(username="admin_demo",
                             hashed_pw=hashlib.sha256("admin12345".encode("utf-8")).hexdigest(),
                             is_admin=True))
        db.session.add(User(username="premium_demo",
                             hashed_pw=hashlib.sha256("premium12345".encode("utf-8")).hexdigest(),
                             is_premium=True))
        db.session.add(User(username="user_demo",
                             hashed_pw=hashlib.sha256("user12345".encode("utf-8")).hexdigest()))

        db.session.commit()
