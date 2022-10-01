import requests
from connection import Connection
db = Connection()

cADMIN_USER = {"Username": "AdminGroupUser", "Password": "123password", "Email": "admingroupuser@test"}
cNONADMIN_USER = {"Username": "NonAdminGroupUser", "Password": "123password", "Email": "nonadmingroupuser@test"}
cUNIQUE_GROUP_NAME = {"group_name": "UnitTestGroup"}
cNONALPHANUMERIC_GROUP_NAME = {"group_name": "Non-Alphanumeric Group"}
cNOT_UNIQUE_GROUP_NAME = {"group_name": "Admin"}

cVALID_USER_WITH_VALID_GROUP_NAME = {"username": "NonAdminGroupUser", "group_name": "UnitTestGroup"}
cINVALID_USER_WITH_VALID_GROUP_NAME = {"username": "NonExistantUser", "group_name": "UnitTestGroup"}
cVALID_USER_WITH_INVALID_GROUP_NAME = {"username": "NonAdminGroupUser", "group_name": "This Group Does Not Exist"}
cVALID_USER_ALREADY_IN_GROUP = {"username": "AdminGroupUser", "group_name": "Admin"}

admin_api_key = db.query('SELECT api_key FROM api_key JOIN rio_user ON api_key.id = rio_user.api_key_id WHERE rio_user.username = %s', ('MaybeJon',))[0]['api_key']
non_admin_api_key = db.query('SELECT api_key FROM api_key JOIN rio_user ON api_key.id = rio_user.api_key_id WHERE rio_user.username = %s', ('GenericHomeUser',))[0]['api_key']

'''
/user_group/create
Fail cases:
1. Invalid api_key aborts
2. No api_key aborts
3. Non-admin api_key aborts
4. Non-alphanumeric group name aborts
5. Already taken group name aborts
6. No provided group name aborts
Success cases:
7. Correct api_key and unique name passes
'''
# 1. Invalid api_key aborts
def test_user_group_create_with_invalid_api_key():
    invalid_api_key = 'Invalid Api Key'
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={invalid_api_key}", json=cUNIQUE_GROUP_NAME)
    assert response.message == 'Invalid api_key'

# 2. No api_key aborts
def test_no_api_key_aborts():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/", json=cUNIQUE_GROUP_NAME)
    assert response.message == 'No api_key provided'

# 3. Non-admin api_key aborts
def test_user_group_create_with_non_admin_api_key():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={non_admin_api_key}", json=cUNIQUE_GROUP_NAME)
    assert response.message == 'You do not have valid permissions to use this endpoint.'

# 4. Non-alphanumeric group_name aborts
def test_non_alphanumeric_group_name_aborts():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={admin_api_key}", json=cNONALPHANUMERIC_GROUP_NAME)
    assert response.message == 'Provided username is not alphanumeric'

# 5. Already taken group name aborts
def test_already_taken_group_name_aborts():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={admin_api_key}", json=cNOT_UNIQUE_GROUP_NAME)
    assert response.message == 'User Group name already taken.'    

# 6. No provided group name aborts
def test_already_taken_group_name_aborts():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={admin_api_key}")
    assert response.message == 'No group_name provided.'    

# 7. Correct api_key and unique name passes
def test_user_group_create_with_unique_name_and_valid_key():
    response = requests.post(f"http://127.0.0.1:5000/user_group/create/?api_key={admin_api_key}", json=cUNIQUE_GROUP_NAME)
    assert response.message == 'User Group created.'

'''
/user_group/add_user
Fail cases:
1. Attempt to add user with invalid api_key
2. Attempt to add user without providing api_key
3. Attempt to add user with non admin api_key
4. Attempt to add an invalid RioUser
5. Attempt to add user with invalid UserGroup
6. Attempt to add user that is already a member
Pass cases:
7. Attempt to add user with corret api_key and valid RioUser that is not a member of UserGroup
'''
# 1. Attempt to add user with invalid api_key
def test_user_group_add_with_invalid_api_key():
    api_key = 'Invalid Api Key'
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={api_key}", json=cVALID_USER_WITH_VALID_GROUP_NAME)
    assert response.message == 'Invalid api_key'

# 2. No api_key aborts
def test_user_group_add_without_api_key():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/", json=cVALID_USER_WITH_VALID_GROUP_NAME)
    assert response.message == 'No api_key provided'

# 3. Non-admin api_key aborts
def test_user_group_add_with_non_admin_api_key():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={non_admin_api_key}", json=cVALID_USER_WITH_VALID_GROUP_NAME)
    assert response.message == 'You do not have valid permissions to use this endpoint.'

# 4. Attempt to add an invalid RioUser
def test_user_group_add_attempt_to_add_an_invalid_rio_user():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={admin_api_key}", json=cINVALID_USER_WITH_VALID_GROUP_NAME)
    assert response.message == 'User does not exist.'

# 5. Attempt to add user with invalid UserGroup
def test_user_group_add_attempt_to_add_user_to_invalid_user_group():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={admin_api_key}", json=cVALID_USER_WITH_INVALID_GROUP_NAME)
    assert response.message == 'UserGroup does not exist.'

# 6. Attempt to add user that is already a member
def test_user_group_add_attempt_to_add_user_to_group_they_are_already_in():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={admin_api_key}", json=cVALID_USER_ALREADY_IN_GROUP)
    assert response.message == 'User is already a member of this group.'

# 7. Attempt to add user with corret api_key and valid RioUser that is not a member of UserGroup
def test_user_group_add_attempt_to_add_user_to_group_they_are_already_in():
    response = requests.post(f"http://127.0.0.1:5000/user_group/add_user/?api_key={admin_api_key}", json=cVALID_USER_WITH_VALID_GROUP_NAME)
    assert response.message == 'User added to User Group.'


'''
/user_group/check_for_member
Fail cases:
1. Attempt with invalid RioUser
2. Attempt with Invalid UserGroup
Pass cases:
3. Attempt with valid RioUser and valid UserGroup where RioUser is not member of group
4. Attempt with valid RioUser and valid UserGroup where RioUser is member of group
'''
# 1. Attempt with invalid RioUser
def test_user_group_check_for_member_with_invalid_rio_user():
    response = requests.get('http://127.0.0.1:5000/user_group/check_for_member/?username=fakeusername&group_name=admin')
    assert response.message == 'User does not exist.'

# 2. Attempt with invalid UserGroup
def test_user_group_check_for_member_with_invalid_group_name():
    response = requests.get('http://127.0.0.1:5000/user_group/check_for_member/?username=generichomeuser&group_name=fake_group_name')
    assert response.message == 'UserGroup does not exist.'

# 3. Attempt with valid RioUser and valid UserGroup where RioUser is not a member
def test_user_group_check_for_member_with_valid_user_and_group():
    response = requests.get('http://127.0.0.1:5000/user_group/check_for_member/?username=generichomeuser&group_name=admin')
    assert response.is_member == False

# 4. Attempt with valid RioUser and valid UserGroup where RioUser is member of group
def test_user_group_check_for_member_with_valid_user_and_group():
    response = requests.get('http://127.0.0.1:5000/user_group/check_for_member/?username=maybejon&group_name=admin')
    assert response.is_member == True

'''
/user_group/members
Fail cases:
1. Invalid UserGroup aborts
2. No group_name provided aborts
Pass cases:
3. Valid UserGroup returns array of usernames
'''
# 1. Invalid UserGroup aborts
def test_user_group_members_with_invalid_user_group():
    response = requests.get('http://127.0.0.1:5000/user_group/members/?group_name=fake_group_name')
    assert response.message == 'UserGroup does not exist.' 

# 2. No group_name provided aborts
def test_user_group_members_with_invalid_user_group():
    response = requests.get('http://127.0.0.1:5000/user_group/members/')
    assert response.message == 'No group_name provided.'

# 3. Valid UserGroup returns array of usernames
def test_user_group_members_with_valid_user_group():
    response = requests.get('http://127.0.0.1:5000/user_group/members/?group_name=admin')
    assert response.users
