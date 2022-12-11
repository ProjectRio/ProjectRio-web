import os
from google.oauth2 import service_account
import googleapiclient.discovery

class GoogleCredentials(object):
    def __init__(self):
        self.credentials = {
            "type": os.getenv("GOAUTH_TYPE"),
            "project_id": os.getenv("GOAUTH_PROJECT_ID"),
            "private_key_id": os.getenv("GOAUTH_PK_ID"),
            "private_key": os.getenv("GOAUTH_PK").replace('\\n', '\n'),
            "client_email": os.getenv("GOAUTH_CLIENT_EMAIL"),
            "client_id": os.getenv("GOAUTH_CLIENT_ID"),
            "auth_uri": os.getenv("GOAUTH_AUTH_URI"),
            "token_uri": os.getenv("GOAUTH_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("GOAUTH_AUTH_PROVIDER_x509_CERT_URL"),
            "client_x509_cert_url": os.getenv("GOAUTH_CLIENT_X509_CERT_URL")
        }
    
    def generate_drive_credential(self):
        SCOPES = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_info(self.credentials, scopes=SCOPES)
        delegated_credentials = credentials.with_subject('devs@projectrio.app')
        try:
            service = googleapiclient.discovery.build('drive', 'v3', credentials=delegated_credentials)
            return service
        except:
            return "Error attempting to build google drive service"


    def generate_email_credential(self):
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        credentials = service_account.Credentials.from_service_account_info(self.credentials, scopes=SCOPES)
        delegated_credentials = credentials.with_subject('devs@projectrio.app')
        try:
            service = googleapiclient.discovery.build('gmail', 'v1', credentials=delegated_credentials)
            return service
        except:
            return "Error attempting to build gmail service"
