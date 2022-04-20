import os
from datetime import timedelta

# SQLITE3 CONFIG
# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
# DB_URL = 'sqlite:///{}'.format(DB_PATH)


# DB URL creation
POSTGRES_URL = os.getenv("POSTGRES_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER,pw=POSTGRES_PW,url=POSTGRES_URL,db=POSTGRES_DB)

# SQL ALCHEMY CONFIG
SQLALCHEMY_DATABASE_URI = DB_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
DEBUG = True

SECRET_KEY = 'S#perS3crEt_007'

# JWT CONFIG
JWT_SECRET_KEY = 'S#perS3crEt_008'
JWT_TOKEN_LOCATION = ['cookies']
JWT_COOKIE_SECURE = True
JWT_COOKIE_CSRF_PROTECT = True
JWT_ACCESS_TOKEN_EXPIRES = timedelta(weeks=2)
