from flask import current_app as app
from models import db, ApiKey, RioUser, UserGroupUser, CommunityUser
from send_email import send_email

def check_for_and_remove_unverified_users():
    return