import requests
from connection import Connection

db = Connection()

# Users we will actually create
cVALID_USER1 = {"Username": "validuser1", "Password": "123password", "Email": "vld1@test"}
cVALID_USER2 = {"Username": "validuser2", "Password": "123password", "Email": "vld2@test"}

#Users we will attempt to create
cINVLD_USER_USERNAME = {"Username": "invld user1", "Password": "123password", "Email": "invld@test"}
cINVLD_USER_EMAIL = {"Username": "invlduser2", "Password": "123password", "Email": "invld"}
cINVLD_USER_DUP_EMAIL = {"Username": "invlduser2", "Password": "123password", "Email": "vld1@test"}
cINVLD_USER_DUP_USERNAME = {"Username": "validuser1", "Password": "123password", "Email": "invld@test"}

# External tests
'''
def test_external_endpoint_register():
    #Wipe db
    response = requests.post("http://127.0.0.1:5000/reset_db", json={"ADMIN_KEY": "NUKE"})

    # Test invalid username
    response = requests.post("http://127.0.0.1:5000/register", json=cINVLD_USER_USERNAME)
    assert response.status_code == 406

    # Test valid user, invalid email
    response = requests.post("http://127.0.0.1:5000/register", json=cINVLD_USER_EMAIL)
    assert response.status_code == 406

    # Test valid user
    response = requests.post("http://127.0.0.1:5000/register", json=cVALID_USER1)
    assert response.status_code == 200

    # Test valid user, email taken
    response = requests.post("http://127.0.0.1:5000/register", json=cINVLD_USER_DUP_EMAIL)
    assert response.status_code == 409

    # Test valid user, email taken
    response = requests.post("http://127.0.0.1:5000/register", json=cINVLD_USER_DUP_USERNAME)
    assert response.status_code == 409

    # Check database to confirm creation
    query = 'SELECT * FROM rio_user WHERE username = %s'
    params = (cVALID_USER1["Username"],)
    result = db.query(query, params)

    # Check that user was created, is not yet verified, and has an active url
    assert len(result) == 1
    assert result[0]['verified'] == False
    url = result[0]['active_url']
    assert url != None

    print(url)

    # Verify User
    response = requests.post(f"http://127.0.0.1:5000/verify_email/{url}")
    assert response.status_code == 200
    # Confirm user is verified
    query = 'SELECT * FROM rio_user WHERE username = %s'
    params = (cVALID_USER1["Username"],)
    result = db.query(query, params)
    assert result[0]['verified'] == True


    ### Make second user
    # Test valid user
    response = requests.post("http://127.0.0.1:5000/register", json=cVALID_USER2)
    assert response.status_code == 200

def test_external_endpoint_change_password():
    pass

# exclude username

# captain vs_captain exclude_captain



# COMMENTED OUT SOME MODEL UPDATES, MAKE SURE TO UNCOMMENT THEM
# Internal tests
'''