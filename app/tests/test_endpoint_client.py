#This test should only be used to create rio users, a community, and a tagset for client testing
import json
import os
import requests
from pprint import pprint
from helpers import *
from connection import Connection

def test_banned_user():
    wipe_db()
    user1 = User()
    user1.register()
    user1.verify_user()

    response = requests.get(f"http://127.0.0.1:5000/validate_user_from_client/?username={user1.username}&rio_key={user1.rk}")
    assert response.status_code == 200

    assert user1.add_to_group('Banned') == True

    response = requests.get(f"http://127.0.0.1:5000/validate_user_from_client/?username={user1.username}&rio_key={user1.rk}")
    assert response.status_code == 405