from flask import current_app as app
from flask import render_template, request, jsonify, abort
import secrets
from datetime import datetime, timedelta, timezone
from .. import bc
from ..models import db, RioUser, GameTag
from ..email import send_email

@app.route("/reverification/")
def reverify_email():
    return render_template("reverify_email.html")

@app.route("/submit_reverification/", methods=["POST"])
def submit_reverify_email():
    # Get Username, Email, Rio Key, and Password from json
    username = request.json['Username']
    username_lowercase = username.lower()
    password = request.json['Password']
    email_lowercase = request.json['Email'].lower()
    riokey = request.json['Rio Key']

    # Validate username
    if not len(username) > 0:
        return abort(409, description="Username must be at least 1 character long.")
    if any(c.isalnum() or c.isspace() for c in username):
        return abort(409, description='Provided username is not alphanumeric.')

    # Validate password
    if len(password) < 8:
        return abort(409, description="Password too short.")
    if not any(not c.isalnum() and not c.isspace() for c in password):
        return abort(409, description="No special character provided")
    if not any(c.isupper() for c in password):
        return abort(409, description="No uppercase character provided")
    if not any(c.islower() for c in password):
        return abort(409, description="No lowercase character provided")

    # Validate email
    if not email.contains("@") or not email.contains("."):
        return abort(409, description="Invalid email address")

    # Verify that Username and Rio Key match a Rio User
    user = db.session.query(
        RioUser
    ).filter(
        (RioUser.username_lowercase == username_lowercase)
        & (RioUser.rio_key == riokey)
    ).first()

    if not user:
        abort(409, description='Matching Rio User not found.')

    # Update RioUser with provided email and password for verification
    user.verified = False
    user.email = email_lowercase
    user.password = password
    user.active_url = secrets.token_urlsafe(32)

    # Send Email with link to verify
    subject = 'Complete your reverification!'
    html_content = (
        f'''
        <h1>Hey, {user.username}!</h1>
        <p>Your reverification is underway!</p> 
        <br/>
        <h3>Next steps</h3>
        <p>Please click the following link to reverify your account</p>
        <a href={'https://projectrio-api-1.api.projectrio.app/confirm_reverification/' + user.active_url}>Reverify Me!</a>
        <br/>
        <p>Happy Hitting!</p>
        <p>Rio Team</p>
        '''
    )
    try:
        send_email(user.email, subject, html_content)
    except:
        return abort(502, 'Failed to send email')
    
    db.session.add(user)
    db.session.commit()
    
    return 200, "Email sent"

@app.route("/confirm_reverification/<active_url>", methods=["GET"])
def confirm_reverification(active_url):
    user = RioUser.query.filter_by(active_url=active_url).first()
    if not user:
        abort(409, "Invalid active_url")
    user.verified = True
    user.active_url = None
    db.session.add(user)
    db.session.commit()
    return 200, "Reverification complete!"
