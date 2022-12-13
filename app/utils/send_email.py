from __future__ import print_function
import os
from flask import abort as kill
import base64
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.utils.google_oauth import GoogleCredentials


def send_email(to_email, subject, html_content, text_content):
    # If the application is running in production, send emails.
    if (os.getenv('RIO_ENV') == "production"):
        # Create OAuth credentials for sending email
        credentials = GoogleCredentials()

        try:
            # create gmail api client
            service = credentials.generate_email_credential()

            # alternative mimemultipart allows html and text to both be sent
            # and the recieving email client decides which to display
            msg = MIMEMultipart('alternative') 

            # build email message
            msg['Subject'] = subject
            msg['From'] = 'Rio Web <devs@projectrio.app>'
            msg['To'] = to_email
            plaintext = MIMEText(text_content, 'plain')
            html = MIMEText(html_content, 'html')
            msg.attach(plaintext)
            msg.attach(html)

            # encode message
            encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            message = {'raw': encoded_message}

            # send message
            service.users().messages().send(userId="me",body=message).execute()

        except HttpError as error:
            return kill(400, 'Error sending email.')
    return