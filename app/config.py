from os import path

# Get DB_URI for SQLALCHEMY_DATABASE_URI
BASE_DIR = path.abspath(path.dirname(__file__))
DB_PATH = path.join(BASE_DIR, 'db.sqlite3')
DB_URI = 'sqlite:///{}'.format(DB_PATH)

SQLALCHEMY_DATABASE_URI = DB_URI
SECRET_KEY = 'S#perS3crEt_007'
SQLALCHEMY_TRACK_MODIFICATIONS = False
DEBUG = True