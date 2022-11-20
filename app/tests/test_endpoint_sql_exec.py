import requests
from connection import Connection

db = Connection()

# External tests
'''
def test_external_endpoint_gen_woba_data():
    response = requests.post("http://127.0.0.1:5000/sql_test/")
    print(response)
    assert response.status_code == 200
'''
