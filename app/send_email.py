from __future__ import print_function
import os
from flask import abort as kill
import base64
from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SERVICE_ACCOUNT_FILE = 'app/rioweb-d74bf247c1d7.json'

def send_email(to_email, subject, html_content, text_content):
    # If the application is running in production, send emails.
    if (os.getenv('rio_env') == "production"):
        # Create OAuth credentials for sending email
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        delegated_credentials = credentials.with_subject('devs@projectrio.app')

        try:
            # create gmail api client
            service = googleapiclient.discovery.build('gmail', 'v1', credentials=delegated_credentials)

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
            print(F'An error occurred: {error}')
            return kill(502, 'Failed to send email')
    return