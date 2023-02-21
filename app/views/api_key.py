from flask import request, abort
from flask import current_app as app
import secrets
from ..models import db, ApiKey, RioUser
from ..util import *
from app.utils.send_email import send_email

@app.route('/api_key/register/', methods=['POST'])
def request_apikey():
    # Get RioUser
    in_username_lowercase = lower_and_remove_nonalphanumeric(request.json['Username'])

    # Check if email is related to RioUser
    rio_user = RioUser.query.filter_by(username_lowercase=in_username_lowercase).first()
    if not rio_user:
        return abort(409, description= "Not a valid username.")

    # Check if user is verified
    if rio_user.verified != True:
        return abort(409, "Please verify your RioWeb account before creating an ApiKey.")

    # Check if user already has an api key
    if rio_user.api_key_id:
        return abort(409, 'This account already has an api key. If you have lost your api key, please go to /api_key/reset')
    
    new_api_key = ApiKey()
    db.session.add(new_api_key)
    db.session.commit()
    rio_user.api_key_id = new_api_key.id
    db.session.add(rio_user)
    db.session.commit()

    subject = 'Your Rio Web API Key!'
    html_content = (
        f'''
            <h1>Here is your Rio Web API Key:</h1>
            <p>{new_api_key.api_key}</p>
            <p>We look forward to seeing what you do with it!</p>
            </br>
            <p>Happy Hitting!</p>
            <p>Project Rio Web Team</p>
        '''
    )
    text_content = (
        f'''
            Here is your Rio Web API Key:\n
            {new_api_key.api_key}\n
            We look forward to seeing what you do with it!\n
            Happy Hitting!\n
            Project Rio Web Team
        '''
    )

    try:
        send_email(rio_user.email, subject, html_content, text_content)
    except:
        return abort(502, 'Failed to send email')

    return "Check your email address for your api key."

# TODO: Send email with API Key, not active_url
@app.route('/api_key/reset/', methods=['POST'])
def reset_api_key():
    email_lowercase = request.json['Email'].lower()
    if '@' in email_lowercase:  
        api_key = ApiKey.query.filter_by(email=email_lowercase).first()
        if not api_key:
            return abort(408, description= "Invalid email address.")

        api_key.api_key = secrets.token_urlsafe(32)
        db.session.add(api_key)
        db.session.commit()

        subject = 'Your Project Rio API Key has been reset'
        html_content = (
            f'''
                <h1>Your new Project Rio API Key is listed below:</h1>
                <p>{api_key.api_key}</p>
                </br>
                <p>Happy Hitting!</p>
                <p>Project Rio Web Team</p>
            '''
        )
        text_content = (
            f'''
                Your new Project Rio API Key is listed below.\n
                {api_key.api_key}\n
                Happy Hitting!\n
                Project Rio Web Team
            '''
        )
      
        try:
            send_email(api_key.email, subject, html_content, text_content)
        except:
            abort(502, 'Failed to send email')

    else:
        return abort(409, description= "Not a valid email address.")
    

    return 'Success...'