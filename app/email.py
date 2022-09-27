import os
from flask import abort as kill, current_app as app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From

def send_email(to_email, subject, html_content):
    # If the application is running in production, send emails using sendgrid.
    if (app.config['rio_env'] == "production"):
        message = Mail(
            from_email=From('email@projectrio.app', 'Rio Web'),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        try:
            sg = SendGridAPIClient(os.getenv("SEND_GRID_KEY"))
            response = sg.send(message)
        except:
            kill(502, 'Failed to send email')

    return "Email sent..."
