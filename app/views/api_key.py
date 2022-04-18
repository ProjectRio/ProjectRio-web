from flask import request, abort
from flask import current_app as app
import secrets
from .. import bc
from ..models import db, ApiKey
import time
from ..email import send_email

@app.route('/api_key/register/', methods=['POST'])
def request_apikey():
    in_email = request.json['Email'].lower()

    if "@" not in in_email:
        return abort(409, description= "Not a valid email address.")
    
    api_key = ApiKey.query.filter_by(email=in_email).first()
    if api_key:
        return abort(409, description="Email already in use.")

    current_time = int(time.time())
    new_api_key = ApiKey(in_email, current_time)
    db.session.add(new_api_key)
    db.session.commit()

    message = (
        'Subject: Verify your email to recieve your Project Rio API Key\n'
        'Please click the following link to verify your email address and get your Project Rio API Key.\n'
        f'{new_api_key.active_url}'
        '\n'
        'Happy Hitting!\n'
        'Project Rio Web Team'
    )

    # password temporarily passed in api call until deployment
    password = request.json['password']

    try:
        send_email(in_email, message, password)
    except:
        return abort(502, 'Failed to send email')

    return "Success..."
  

@app.route('/api_key/verify/', methods=['POST'])
def verify_api_key():
    in_active_url = request.json['active_url']
    api_key = ApiKey.query.filter_by(active_url=in_active_url).first()

    if not api_key:
        return abort(422, 'Invalid key')

    api_key.verified = True
    api_key.active_url = None
    api_key.pings_today = 0
    api_key.api_key = secrets.token_urlsafe(32)

    db.session.add(api_key)
    db.session.commit()

    message = (
        'Subject: Your email has been verified.\n'
        'Your Project Rio API Key is listed below.\n'
        f'{api_key.api_key}'
        '\n'
        'Happy Hitting!\n'
        'Project Rio Web Team'
    )

    # password temporarily passed in api call until deployment
    password = request.json['password']

    try:
        send_email(api_key.email, message, password)
    except:
        abort(502, 'Failed to send email')

    return "Success..."



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

        message = (
            'Subject: Your API Key has been reset.\n'
            'Your new Project Rio API Key is listed below.\n'
            f'{api_key.api_key}'
            '\n'
            'Happy Hitting!\n'
            'Project Rio Web Team'
        )
        
        # password temporarily passed in api call until deployment
        password = request.json['password']
      
        try:
            send_email(api_key.email, message, password)
        except:
            abort(502, 'Failed to send email')

    else:
        return abort(409, description= "Not a valid email address.")
    

    return 'Success...'