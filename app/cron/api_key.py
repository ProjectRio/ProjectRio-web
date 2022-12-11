from flask import current_app as app
from models import db, ApiKey, RioUser
from send_email import send_email

def update_api_key_tracking():
 # Check if RioUser has correct group privledge
    api_keys = db.session.query(
        ApiKey
    ).join(
        RioUser
    ).all()

    for api_key in api_keys:
        # If it is Saturday...
        if 0:
            # Build Email
            subject = 'Your weekly API usage!'
            html_content = (
                f'''
                    <h1>API Usage</h1>
                    <p>Your API stats to date are:</p>
                    <ul>
                        <li>Pings this week: {api_key.pings_weekly}</li>
                        <li>Pings all-time: {api_key.total_pings}</li>
                    </ul>
                    <br/>
                    <p>Happy Hitting!</p>
                    <p>Rio Team</p>
                '''
            )
            text_content = (
                f'''
                    Api Usage\n
                    Your API stats to date are:\n
                    \n
                    Pings this week: {api_key.pings_weekly}\n
                    Pings all-time: {api_key.total_pings}\n
                    \n
                    Happy Hitting!\n
                    Rio Team\n
                '''
            )

            # Reset weekly pings since this only happens on Saturdays
            api_key.pings_weekly = 0

            # Send email
            send_email(api_key.email, subject, html_content, text_content)

        # Reset pings_daily for the next day
        api_key.pings_daily = 0

        # Add updated rows to be sent at function end
        db.session.add(api_key)

    # Commit database changes 
    db.session.commit()
    return

    