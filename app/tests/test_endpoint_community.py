import requests
from connection import Connection

db = Connection()

# Users we will actually create
cFOUNDER_USER = {"Username": "founder", "Password": "123password", "Email": "founder@test"}
cADMIN_USER = {"Username": "admin", "Password": "123password", "Email": "admin@test"}
cMEMBER_USER = {"Username": "member", "Password": "123password", "Email": "member@test"}
cNONMEMBER_USER = {"Username": "nonmember", "Password": "123password", "Email": "nonmember@test"}

cPRIVATE_GLOBAL_COMM = {'Community Name': 'PrivateGlobal', 'Private': 1, 'Global Link': 1, 'Description': 'Test'}

cPRIVATE_NONGLOBAL_COMM = {'Community Name': 'PrivateNonGlobal', 'Private': 1, 'Global Link': 1, 'Description': 'Test'}
cPRIVATE_GLOBAL_COMM = {'Community Name': 'PrivateGlobal', 'Private': 1, 'Global Link': 0, 'Description': 'Test'}
cPUBLIC_COMM = {'Community Name': 'Public', 'Private': 0, 'Global Link': 0, 'Description': 'Test'}

# External tests
def test_external_endpoint_zcommunity_create_private():
    #Create users
    response = requests.post("http://127.0.0.1:5000/register", json=cFOUNDER_USER)

    # Get founder info
    query = 'SELECT * FROM rio_user WHERE username = %s'
    params = (cFOUNDER_USER["Username"],)
    result = db.query(query, params)
    founder_rio_key = result[0]['rio_key']

    # Create first community
    cPRIVATE_NONGLOBAL_COMM['Rio Key'] = founder_rio_key
    print(cPRIVATE_NONGLOBAL_COMM)
    response = requests.post("http://127.0.0.1:5000/community/create", json=cPRIVATE_NONGLOBAL_COMM)
    assert response.status_code == 200

    #Check that community user, communty, and tag get created

    #Check that community properties are correct (global link, private)
