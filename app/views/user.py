from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
import secrets
from datetime import datetime, timedelta, timezone
from .. import bc
from ..models import db, RioUser
from ..email import send_email
import os

# === User registration endpoints ===
@app.route('/register/', methods=['POST'])
def register():    
    in_username = request.json['Username']
    username_lowercase = in_username.lower()
    in_password = request.json['Password']
    in_email    = request.json['Email'].lower()

    user = RioUser.query.filter_by(username_lowercase=username_lowercase).first()
    user_by_email = RioUser.query.filter_by(email=in_email).first()

    if user or user_by_email:
        return abort(409, description='Username or Email has already been taken')
    elif in_username.isalnum() == False:
        return abort(406, description='Provided username is not alphanumeric')
    else:
        # === Create User row ===
        new_user = RioUser(in_username, username_lowercase, in_email, in_password)
        db.session.add(new_user)
        db.session.commit()

        message = (
            'Subject: Verify your Project Rio Account\n'
            f'Dear {in_username},\n'
            '\n'
            'Please click the following link to verify your email address and get your Rio Key.\n'
            f'{new_user.active_url}'
            '\n'
            'Happy Hitting!\n'
            'Project Rio Web Team'
        )

        password = os.getenv("EMAIL_PASSWORD")

        try:
            send_email(in_email, message, password)
        except:
            return abort(502, 'Failed to send email')
        
    return jsonify({
        'username': new_user.username
    })

@app.route('/verify_email/', methods=['POST'])
def verify_email():
    try:
        active_url = request.json['active_url']
        user = RioUser.query.filter_by(active_url=active_url).first()
        user.verified = True
        user.active_url = None

        db.session.add(user)
        db.session.commit()
        return {
            'Rio Key': user.rio_key,
        }, 200
    except:
        return abort(422, 'Invalid Key')


# === Password change endpoints ===
@app.route('/request_password_change/', methods=['POST'])
def request_password_change():
    if '@' in request.json['username or email']:
        email_lowercase = request.json['username or email'].lower()
        user = RioUser.query.filter_by(email=email_lowercase).first()
    else:
        username_lower = request.json['username or email'].lower()
        user = RioUser.query.filter_by(username_lowercase=username_lower).first()

    if not user:
        abort(408, 'Corresponding user does not exist')

    if user.verified == False:
        abort(401, 'Email unverified')

    active_url = secrets.token_urlsafe(32)
    user.active_url = active_url
    db.session.add(user)
    db.session.commit()

    message =  (
        'Subject: Project Rio Password Reset\n'

        f'Dear {user.email},\n'
        '\n'
        'We received a password reset request. If you did not make this request, please ignore this email.\n'
        'Otherwise, follow this link to reset your account\n'
        f'{user.active_url}\n'
        '\n'
        'Happy hitting!\n'
        'Project Rio Web Team'
    )
    
    password = os.getenv("EMAIL_PASSWORD")

    try:
        send_email(user.email, message, password)
    except:
        abort(502, 'Failed to send email')

    return {
        'msg': 'Link emailed...'
    }


@app.route('/change_password/', methods=['POST'])
def change_password():
    active_url = request.json['active_url']
    password = request.json['password']

    user = RioUser.query.filter_by(active_url=active_url).first()

    if not user:
        return abort(422, 'Invalid Key')

    if user.verified == False:
        return abort(401, 'Email unverified')

    user.password = bc.generate_password_hash(password)
    user.active_url = None
    db.session.add(user)
    db.session.commit()

    return {
        'msg': 'Password changed...'
    }, 200



# === JWT endpoints ===
@app.route('/login/', methods=['POST'])
def login():
    in_username = request.json['Username'].lower()
    in_password = request.json['Password']
    in_email    = request.json['Email'].lower()

    # filter User out of database through username
    user = RioUser.query.filter_by(username_lowercase=in_username).first()

    # filter User out of database through email
    user_by_email = RioUser.query.filter_by(email=in_email).first()

    if user == user_by_email:
        if bc.check_password_hash(user.password, in_password):            
            # Creating JWT and Cookies
            response = jsonify({
                'msg': 'login successful',
                'username': user.username,
            })
            access_token = create_access_token(identity=user.username)
            set_access_cookies(response, access_token)

            return response
        else:
            return abort(401, description='Incorrect password')
    else:
        return abort(408, description='Incorrect Username or Password')

@app.route('/logout/', methods=['POST'])
def logout():    
    response = jsonify({'msg': 'logout successful'})
    unset_jwt_cookies(response)
    return response

@app.route('/validate_JWT/', methods = ['GET'])
@jwt_required(optional=True)
def validate_JWT():
    try:
        current_user_username = get_jwt_identity()
        return jsonify(logged_in_as=current_user_username)
    except:
        return 'No JWT...'

# Refresh any JWT within 7 days of expiration after requests
@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()['exp']
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(days=7))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where JWT is invalid, return original response
        return response



# === Get/Set user settings ===
#GET retreives user key, POST with empty JSON will generate new rio key and return it
@app.route('/key/', methods=['GET', 'POST'])
@jwt_required()
def update_rio_key():
    current_user_username = get_jwt_identity()
    current_user = RioUser.query.filter_by(username=current_user_username).first()

    if request.method == 'GET':
        return jsonify({
            "riokey": current_user.rio_key
        })
    elif request.method == 'POST':
        current_user.rio_key = secrets.token_urlsafe(32)
        db.session.commit()
        return jsonify({
            "riokey": current_user.rio_key
        })

#GET retreives user privacy, POST with empty JSON will swap privacy setting and return it
@app.route('/set_privacy/', methods = ['GET', 'POST'])
@jwt_required()
def set_privacy():
    current_user_username = get_jwt_identity()
    current_user = RioUser.query.filter_by(username=current_user_username).first()

    if request.method == 'GET':
        return jsonify({
            'private': current_user.private
        })
    if request.method == 'POST':
        current_user.private = not current_user.private
        db.session.commit()
        return jsonify({
            'private': current_user.private
        })
