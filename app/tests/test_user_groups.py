import requests
from connection import Connection
db = Connection()

'''
/user_group/create
Fail cases:
1. Invalid api_key aborts
2. Non-admin api_key aborts
3. Non-alphanumeric group name aborts
4. Already taken group name aborts
Success cases:
5. Correct api_key and unique name passes
'''
# Invalid api_key aborts
def test_user_group_create_with_invalid_api_key():
    result = db.query('SELECT api_key FROM api_key JOIN rio_user WHERE rio_user.username = %s', ('MaybeJon',))
    api_key = result[0]['api_key']
    response = requests.get(f"http://127.0.0.1:5000/user_group/create/?api_key={api_key}")

# Non-admin api_key aborts
def test_user_group_create_with_non_admin_api_key():
    return "200"

'''
/user_group/add_user
Fail cases:
1. Attempt with invalid api_key
2. Attempt with non admin api_key
3. Attempt with invalid RioUser
4. Attempt with invalid UserGroup
5. Attempt with RioUser that is already a member of UserGroup
Pass cases:
6. Attempt with corret api_key and valid RioUser that is not a member of UserGroup
'''


'''
/user_group/check_for_member
Fail cases:
1. Attempt with invalid RioUser
2. Attempt with Invalid UserGroup
Pass cases:
1. Attempt with valid RioUser and valid UserGroup where RioUser is not member of group
1. Attempt with valid RioUser and valid UserGroup where RioUser is member of group
'''


'''
/user_group/members
Fail cases:
1. Invalid UserGroup aborts
Pass cases:
2. Valid UserGroup returns array of usernames
'''