from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
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
    CORS(app)

    # Initialize Plugins
    db.init_app(app)
    bc.init_app(app)
    jwt.init_app(app)
    migrate = Migrate(app, db)

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
        from .views import recreate_stat_files
        from .views import client_routes
        from .views import stat_retrieval
        from .views.stats import box_score
        from .views.stats import user_summary
        from .views import api_key
        from .views import user_groups
        from .views import community
        # from .views import log
        
        #create sql tables for data models
        db.create_all()

        return app
