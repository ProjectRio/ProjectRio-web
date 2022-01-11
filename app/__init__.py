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
    app.config.from_pyfile('config.py')

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
