from flask import request, abort, jsonify
from flask import current_app as app
from ..models import *
import json
import os
import subprocess

@app.route('/db_to_sqlite/', methods=['POST'])
def endpoint_db_to_sqlite():
    if os.getenv('RESET_DB') == request.json['RESET_DB']:
        run_db_to_sqlite()
        return jsonify({'Success':200})
    return abort(409, description='Invalid passcode')

def run_db_to_sqlite():
    cmd = 'db-to-sqlite'
    # TODO rename
    output_name = 'backup_db.sqlite'
    
    connection_string = ('postgresql://' 
                       + os.getenv('POSTGRES_USER') + ':' 
                       + os.getenv('POSTGRES_PW') + '@' 
                       + os.getenv('POSTGRES_URL') + '/' 
                       + os.getenv('POSTGRES_DB') + '?sslmode=require')

    subprocess.run([cmd, connection_string, output_name, '--all', '--redact', 'rio_user', 'email', '--redact', 'rio_user', 'password'], capture_output=True)
