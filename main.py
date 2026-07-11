import os
import secrets

from flask import Flask

from extensions import db
from db_utils import reset_db


def create_app():
    if "VERCEL" in os.environ:
        flask_app = Flask(__name__, instance_path="/tmp")
    else:
        flask_app = Flask(__name__)

    flask_app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
    flask_app.json.compact = False

    db.init_app(flask_app)

    from blueprints.web import web_bp
    from blueprints.api import api_bp
    flask_app.register_blueprint(web_bp)
    flask_app.register_blueprint(api_bp)

    with flask_app.app_context():
        metadata = db.MetaData()
        metadata.reflect(bind=db.engine)
        if len(metadata.sorted_tables) == 0:
            reset_db(flask_app)

    return flask_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False)
