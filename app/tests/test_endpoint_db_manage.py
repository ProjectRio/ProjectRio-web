import json
import requests
from helpers import *
from connection import Connection

def test_endpoint_db_to_sqlite():
    data_json={"ADMIN_KEY": "NUKE"}
    response = requests.post("http://127.0.0.1:5000/db_to_sqlite/", json=data_json)
    assert response.status_code == 200

def test_endpoint_reset():
    wipe_db()