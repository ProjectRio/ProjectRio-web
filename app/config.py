from os import path
from datetime import timedelta

# Get DB_URI for SQLALCHEMY_DATABASE_URI
BASE_DIR = path.abspath(path.dirname(__file__))
DB_PATH = path.join(BASE_DIR, 'db.sqlite3')
DB_URI = 'sqlite:///{}'.format(DB_PATH)

SQLALCHEMY_DATABASE_URI = DB_URI
SECRET_KEY = 'S#perS3crEt_007'
SQLALCHEMY_TRACK_MODIFICATIONS = False
DEBUG = True


JWT_SECRET_KEY = 'S#perS3crEt_008'
JWT_TOKEN_LOCATION = ['cookies']
JWT_COOKIE_SECURE = True
JWT_COOKIE_CSRF_PROTECT = True
JWT_ACCESS_TOKEN_EXPIRES = timedelta(weeks=2)
