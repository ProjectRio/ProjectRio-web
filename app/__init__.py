from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
import logging
from logging.handlers import RotatingFileHandler

# Globally accessible libraries
db = SQLAlchemy()
bc = Bcrypt()
jwt = JWTManager()

def init_app():
    # Construct core application
    app = Flask(__name__)
    app.config.from_pyfile('config.py')

    # Initialize Plugins
    db.init_app(app)
    bc.init_app(app)
    jwt.init_app(app)

    #Set logger properties
    #Rotating log file
    handler = RotatingFileHandler('endpoint_log.log', maxBytes=10000000, backupCount=2) #10 MB file size
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    with app.app_context():
        #import routes
        from .views import populate_db
        from .views import user
        from .views import db_setup
        from .views import client_routes
        from .views import stat_retrieval
        from .views.stats import box_score
        from .views.stats import user_summary
        from .views import api_key
        from .views import log
        
        #create sql tables for data models
        db.create_all()

        # #Populate character, chemistry, and tag tables
        # if (Character.query.all() == None):
        #     print("Loading character tables")
        #     db_setup.create_character_tables()
        # if (Tag.query.filter(Tag.name.in_(["Ranked", "Unranked", "Superstar", "Normal"])).all() == None):
        #     print("Loading standard tags")
        #     db_setup.create_default_tags()

        return app
