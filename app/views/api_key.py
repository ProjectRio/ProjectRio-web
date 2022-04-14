from flask import request, abort
from flask import current_app as app
import smtplib
import ssl
import secrets
from .. import bc
from ..models import db, ApiKey
import time

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

    try:
        send_verify_api_key_email(in_email, new_api_key.active_url)
    except:
        return abort(502, 'Failed to send email')

    return "Success..."


def send_verify_api_key_email(receiver_email, active_url):
    port = 465
    smtp_server = 'smtp.gmail.com'
    sender_email = 'projectrio.webtest@gmail.com'

    # password temporarily passed in api call until deployment
    password = request.json['password']

    message = (
        'Subject: Verify your email to recieve your Project Rio API Key\n'
        'Please click the following link to verify your email address and get your Project Rio API Key.\n'
        '{0}'
        '\n'
        'Happy Hitting!\n'
        'Project Rio Web Team'
    ).format(
        active_url
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

    return

  
@app.route('/api_key/verify/', methods=['POST'])
def verify_api_key():
    try:
      in_active_url = request.json['active_url']
      api_key = ApiKey.query.filter_by(active_url=in_active_url).first()
      api_key.verified = True
      api_key.active_url = None
      api_key.pings_today = 0
      api_key.api_key = secrets.token_urlsafe(32)

      db.session.add(api_key)
      db.session.commit()

      try:
        send_api_key_email(api_key.email, api_key.api_key)
      except:
        abort(502, 'Failed to send email')

      return "Sucess..."
    except:
      return abort(422, 'Invalid key')

def send_api_key_email(receiver_email, api_key):
    port = 465
    smtp_server = 'smtp.gmail.com'
    sender_email = 'projectrio.webtest@gmail.com'

    # password temporarily passed in api call until deployment
    password = request.json['password']

    message = (
        'Subject: Your email has been verifiec.\n'
        'Your Project Rio API Key is listed below.\n'
        '{0}'
        '\n'
        'Happy Hitting!\n'
        'Project Rio Web Team'
    ).format(
        api_key
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

    return
