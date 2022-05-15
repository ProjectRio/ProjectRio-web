import os
from flask import abort as kill
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    message = Mail(
        from_email='email@projectrio.app',
        to_emails=os.getenv("SEND_GRID_KEY"),
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(os.getenv("SEND_GRID_KEY"))
        response = sg.send(message)
    except:
        kill(502, 'Failed to send email')

    return "Email sent..."
