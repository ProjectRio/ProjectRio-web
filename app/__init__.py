import os.path
from decouple import config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow

# Globally accessible libraries
db = SQLAlchemy()
lm = LoginManager()
bc = Bcrypt()
ma = Marshmallow()

def init_app():
    # Construct core application
    app = Flask(__name__)

    # Configuration (MOVE TO config.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
    DB_URI = 'sqlite:///{}'.format(DB_PATH)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.config['SECRET_KEY'] = config('SECRET_KEY', default='S#perS3crEt_007')

    # Initialize Plugins
    db.init_app(app)
    lm.init_app(app)
    bc.init_app(app)
    ma.init_app(app)

    with app.app_context():
        #import routes
        from . import views
        
        #create sql tables for data models
        db.create_all()

        return app
