import json
import requests
from helpers import *
from connection import Connection

db = Connection()

def wipe_db():
    response = requests.post("http://127.0.0.1:5000/wipe_db/", json={"RESET_DB": "NUKE"})
    return response.status_code == 200


def test_community_create_official():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    nonmember = User()
    nonmember.register()

    #Check that the new user is registered after creating a new official community

    # Assert community is not created, founder not admin
    community = Community(founder, True, False, False)
    assert community.success == False

    assert founder.add_to_group('admin') == True

    # Assert community IS created, founder is admin
    community = Community(founder, True, False, False)
    assert community.success == True

    # Did both users get added to the community
    assert len(community.members) == 2

   
def test_community_create_unofficial():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    nonmember = User()
    nonmember.register()

    #Check that the new user is registered after creating a new official community

    # Assert community is not created, founder not admin
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Did both users get added to the community
    assert len(community.members) == 1

    # Join community as nonmember
    assert community.join_via_request(nonmember) == True

    assert len(community.members) == 2

    assert community.get_member(nonmember).active == True

    # Extra Credit: check that a user can be invited to public community
    invitee = User()
    invitee.register()
    community.invite(founder, {invitee.pk: invitee})
    assert community.get_member(invitee).active  == False

def test_community_create_private_nolink():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    nonmember = User()
    nonmember.register()

    #Check that the new user is registered after creating a new official community

    # Assert community is not created, founder not admin
    community = Community(founder, official=False, private=True, link=False)
    assert community.success == True

    # Join community via link (should not work, user will request)
    community.join_via_url(nonmember)
    assert community.get_member(nonmember).active == False

    # Invite -> Request = Join
    invitee = User()
    invitee.register()
    community.invite(founder, {invitee.pk: invitee})
    assert community.get_member(invitee).active == False

    assert community.join_via_request(invitee) == True
    assert community.get_member(invitee).active == True


    # Request -> Invite = Join
    requester = User()
    requester.register()

    assert community.join_via_request(requester) == True
    assert community.get_member(requester).active == False

    community.invite(founder, {requester.pk: requester})
    assert community.get_member(requester).active == True

def test_community_create_private_link():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    nonmember = User()
    nonmember.register()

    #Check that the new user is registered after creating a new official community

    # Assert community is not created, founder not admin
    community = Community(founder, official=False, private=True, link=True)
    assert community.success == True

    # Join community via link (should not work, user will request)
    community.join_via_url(nonmember)
    assert community.get_member(nonmember).active == True

    # Invite -> Request = Join
    invitee = User()
    invitee.register()
    community.invite(founder, {invitee.pk: invitee})
    assert community.get_member(invitee).active == False

    assert community.join_via_request(invitee) == True
    assert community.get_member(invitee).active == True


    # Request -> Invite = Join
    requester = User()
    requester.register()

    assert community.join_via_request(requester) == True
    assert community.get_member(requester).active == False

    community.invite(founder, {requester.pk: requester})
    assert community.get_member(requester).active == True

def test_community_manage_admin():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    member = User()
    member.register()

    future_admin = User()
    future_admin.register()
    
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Member join
    assert community.join_via_request(member)
    assert community.join_via_request(future_admin)

    # Upgrade future admin user as non-admin (not permitted)
    assert not community.manage(member, [future_admin], "admin")
    assert not community.get_member(future_admin).admin

    # Upgrade future admin user as admin
    assert community.manage(founder, [future_admin], "admin")
    assert community.get_member(future_admin).admin

def test_community_manage_ban():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    member = User()
    member.register()

    future_bannee = User()
    future_bannee.register()
    
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Member join
    assert community.join_via_request(member)
    assert community.join_via_request(future_bannee)

    # Upgrade future admin user as non-admin (not permitted)
    assert not community.manage(member, [future_bannee], "ban")
    assert not community.get_member(future_bannee).banned

    # Upgrade future admin user as admin
    assert community.manage(founder, [future_bannee], "ban")
    assert community.get_member(future_bannee).banned


def test_community_manage_remove():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    member = User()
    member.register()

    future_removee = User()
    future_removee.register()
    
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Member join
    assert community.join_via_request(member)
    assert community.join_via_request(future_removee)

    # Remove user as non-admin (not permitted)
    assert not community.manage(member, [future_removee], "remove")
    assert community.get_member(future_removee).active

    # Remove user as admin
    assert community.manage(founder, [future_removee], "remove")
    assert not community.get_member(future_removee).active

def test_community_tags():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    member = User()
    member.register()
    
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True
    # Member join
    assert community.join_via_request(member)

    # Should just have community tag
    assert len(community.tags) == 1

    # Add tag with non-admin (should not work)
    tag = Tag(community.get_member(member), community)
    tag.create()
    assert not tag.success
    assert len(community.tags) == 1

    # Add tag with admin
    tag = Tag(community.founder, community)
    tag.create()

    assert tag.active
    assert tag.type == 'Component'
    assert len(community.tags) == 2

def test_community_tagsets():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Add tag with admin
    tag = Tag(community.founder, community)
    tag.create()

    tagset = TagSet(community.founder, community, [tag], 'League')
    tagset.create()

    assert tagset.success
    assert len(community.tags) == 3

def test_endpoint_community_get_tags():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True


    tag1 = Tag(community.founder, community)
    tag1.create()


    tag2 = Tag(community.founder, community)
    tag2.create()

    tagset = TagSet(community.founder, community, [tag1, tag2], 'League')
    tagset.create()

    tags = get_community_tags(community.name, founder)

    assert tags[0]

    # 2 tags above + tagset tag + the community tag
    assert len(tags[1]['Tags']) == 4

    #Check that all tags match what we have been tracking
    for x in tags[1]['Tags']:
        assert compare_comm_tag_to_dict(x, community.tags[x['id']])

def test_endpoint_community_get_members():
    wipe_db()

    founder = User()
    founder.register()
    assert founder.success == True

    member = User()
    member.register()

    future_admin = User()
    future_admin.register()
    
    community = Community(founder, official=False, private=False, link=False)
    assert community.success == True

    # Member join
    assert community.join_via_request(member)
    assert community.join_via_request(future_admin)

    # Upgrade future admin user as admin
    assert community.manage(founder, [future_admin], "admin")
    assert community.get_member(future_admin).admin

    members = get_community_members(community.name, founder)

    assert members[0]

    assert len(members[1]['Members']) == 3

    for x in members[1]['Members']:
        assert compare_comm_user_to_dict(x, community.members[x['id']])

# # Users we will actually create
# cFOUNDER_USER = {"Username": "founder", "Password": "123password", "Email": "founder@test"}
# cADMIN_USER = {"Username": "admin", "Password": "123password", "Email": "admin@test"}
# cMEMBER_USER = {"Username": "member", "Password": "123password", "Email": "member@test"}
# cNONMEMBER_USER = {"Username": "nonmember", "Password": "123password", "Email": "nonmember@test"}

# cPRIVATE_GLOBAL_COMM = {'Community Name': 'PrivateGlobal', 'Type': 'Unofficial', 'Private': 1, 'Global Link': 1, 'Description': 'Test'}
# cPRIVATE_NONGLOBAL_COMM = {'Community Name': 'PrivateNonGlobal', 'Type': 'Unofficial', 'Private': 1, 'Global Link': 0, 'Description': 'Test'}
# cPUBLIC_COMM = {'Community Name': 'Public', 'Type': 'Unofficial', 'Private': 0, 'Global Link': 0, 'Description': 'Test'}

# cOFFICIAL_COMM = {}

# # External tests
# def test_external_endpoint_community_create():
#     #Wipe db
#     response = requests.post("http://127.0.0.1:5000/wipe_db/", json={"RESET_DB": "NUKE"})

#     #Create users
#     response = requests.post("http://127.0.0.1:5000/register/", json=cFOUNDER_USER)


#     #Create users
#     response = requests.post("http://127.0.0.1:5000/register/", json=cMEMBER_USER)

#     # Get founder info
#     query = 'SELECT * FROM rio_user WHERE username = %s'
#     params = (cFOUNDER_USER["Username"],)
#     result = db.query(query, params)
#     founder_rio_key = result[0]['rio_key']
#     founder_primary_key = result[0]['id']

#     # Get member info
#     query = 'SELECT * FROM rio_user WHERE username = %s'
#     params = (cMEMBER_USER["Username"],)
#     result = db.query(query, params)
#     member_rio_key = result[0]['rio_key']
#     member_primary_key = result[0]['id']

#     # Create first community
#     cPRIVATE_NONGLOBAL_COMM['Rio Key'] = founder_rio_key
#     response = requests.post("http://127.0.0.1:5000/community/create", json=cPRIVATE_NONGLOBAL_COMM)
#     assert response.status_code == 200

#     # Check that community user, communty, and tag get created

#     # Community created check
#     # Check database to confirm creation
#     query = 'SELECT * FROM community WHERE name = %s'
#     params = (cPRIVATE_NONGLOBAL_COMM["Community Name"],)
#     result = db.query(query, params)

#     assert len(result) == 1
#     assert result[0]['private'] == True
#     assert result[0]['active_url'] == None
#     community_id = result[0]['id']

#     # Community user created check
#     # Check database to confirm creation
#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(community_id),str(founder_primary_key),)
#     result = db.query(query, params)

#     assert len(result) == 1
#     assert result[0]['invited'] == False
#     assert result[0]['admin'] == True
#     assert result[0]['active'] == True

#     # Community tag created check
#     # Check database to confirm creation
#     query = 'SELECT * FROM tag WHERE name = %s'
#     params = (cPRIVATE_NONGLOBAL_COMM["Community Name"],)
#     result = db.query(query, params)

#     assert len(result) == 1
#     assert result[0]['community_id'] == community_id
#     assert result[0]['active'] == True
#     assert result[0]['tag_type'] == "Community"

#     # ==== Repeat creation with Private Community with a global link
#     cPRIVATE_GLOBAL_COMM['Rio Key'] = founder_rio_key
#     response = requests.post("http://127.0.0.1:5000/community/create", json=cPRIVATE_GLOBAL_COMM)
#     assert response.status_code == 200

#     # Community created check, do not check comm user and tag (they function the same regardless, redundant)
#     query = 'SELECT * FROM community WHERE name = %s'
#     params = (cPRIVATE_GLOBAL_COMM["Community Name"],)
#     result = db.query(query, params)

#     assert len(result) == 1
#     assert result[0]['private'] == True
#     assert result[0]['active_url'] != None
#     private_w_global_url = result[0]['active_url']
#     private_w_global_id = result[0]['id']
    
#     # ==== Repeat creation with public Community with a global link
#     cPUBLIC_COMM['Rio Key'] = founder_rio_key
#     response = requests.post("http://127.0.0.1:5000/community/create", json=cPUBLIC_COMM)
#     assert response.status_code == 200

#     # Community created check, do not check comm user and tag (they function the same regardless, redundant)
#     query = 'SELECT * FROM community WHERE name = %s'
#     params = (cPUBLIC_COMM["Community Name"],)
#     result = db.query(query, params)

#     assert len(result) == 1
#     assert result[0]['private'] == False
#     assert result[0]['active_url'] != None
#     public_w_global_url = result[0]['active_url']

#     # def test_external_endpoint_community_join():
#     # check join for each type (private GL, public GL, private invite, )

#     # == Private Community, Global Link ===

#     # Private community, global link. Incorrect link. User will request to join
#     response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(cPRIVATE_GLOBAL_COMM['Community Name'], private_w_global_url+"L"), json={'Rio Key': member_rio_key})
#     assert response.status_code == 200

#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(private_w_global_id),str(member_primary_key),)
#     result = db.query(query, params)
#     assert len(result) == 1
#     assert result[0]['active'] == False
#     assert result[0]['invited'] == False

#     # Private community, global link. Incorrect name
#     response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(cPRIVATE_GLOBAL_COMM['Community Name'] +"L", private_w_global_url), json={'Rio Key': member_rio_key})
#     assert response.status_code == 409

#     # Private community, global link. Incorrect rio key (none)
#     response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(cPRIVATE_GLOBAL_COMM['Community Name'], private_w_global_url))
#     assert response.status_code == 409

#     # Private community, global link. Correct key
#     response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(cPRIVATE_GLOBAL_COMM['Community Name'], private_w_global_url), json={'Rio Key': member_rio_key})
#     assert response.status_code == 200

#     #User should now be active
#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(private_w_global_id),str(member_primary_key),)
#     result = db.query(query, params)
#     assert len(result) == 1
#     assert result[0]['active'] == True
#     assert result[0]['invited'] == False

#     # == Public Community, Global Link ===

#     # Public community, incorrect link
#     #Should pass since we don't actually need the link to join a public community
#     response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(cPUBLIC_COMM['Community Name'], public_w_global_url+"L"), json={'Rio Key': member_rio_key})
#     assert response.status_code == 200

#     # === Private community, No Global Link===
#     #Test inviting a user, wrong username
#     invite_json = {'Rio Key': founder_rio_key, 'Community Name': cPRIVATE_NONGLOBAL_COMM["Community Name"], "Invite List": ["invld"]}
#     response = requests.post("http://127.0.0.1:5000/community/invite", json=invite_json)
#     assert response.status_code == 409

#     #Inviting a user, correct username
#     invite_json = {'Rio Key': founder_rio_key, 'Community Name': cPRIVATE_NONGLOBAL_COMM["Community Name"], "Invite List": [cMEMBER_USER["Username"]]}
#     response = requests.post("http://127.0.0.1:5000/community/invite", json=invite_json)
#     assert response.status_code == 200

#     #User should be invited but not active
#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(community_id),str(member_primary_key),)
#     result = db.query(query, params)
#     assert len(result) == 1
#     assert result[0]['active'] == False
#     assert result[0]['invited'] == True

#     # Request to join
#     response = requests.post("http://127.0.0.1:5000/community/join", json={'Community Name': cPRIVATE_NONGLOBAL_COMM['Community Name'], 'Rio Key': member_rio_key})
#     assert response.status_code == 200

#     #Check user has joined
#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(community_id),str(member_primary_key),)
#     result = db.query(query, params)
#     assert len(result) == 1
#     assert result[0]['active'] == True
#     assert result[0]['invited'] == True

#     # === Manage ===
#     # Upgrade to admin as non admin

#     response = requests.post("http://127.0.0.1:5000/community/manage", json={'Community Name': cPRIVATE_NONGLOBAL_COMM['Community Name'], 
#                                                                              'Rio Key': member_rio_key, 
#                                                                              'User List': [{'Username': cMEMBER_USER["Username"], 'Admin': 't'}]})

#     assert response.status_code == 409

#     #Upgrade to admin as admin
#     response = requests.post("http://127.0.0.1:5000/community/manage", json={'Community Name': cPRIVATE_NONGLOBAL_COMM['Community Name'], 
#                                                                              'Rio Key': founder_rio_key, 
#                                                                              'User List': [{'Username': cMEMBER_USER["Username"], 'Admin': 't'}]})

#     assert response.status_code == 200

#     #Check user is admin
#     query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
#     params = (str(community_id),str(member_primary_key),)
#     result = db.query(query, params)
#     assert len(result) == 1
#     assert result[0]['admin'] == True

#     #Get members
#     response = requests.get("http://127.0.0.1:5000/community/members", json={'Community Name': cPRIVATE_NONGLOBAL_COMM['Community Name'], 
#                                                                              'Rio Key': member_rio_key})
#     data = response.json()
#     assert len(data['Members']) == 2

    
#     # === Create Tag ===
#     #Member is now admin so this will work
#     tag_json = {"Tag Name": "TestTag", "Description":"Description of tag", "Community Name":cPRIVATE_NONGLOBAL_COMM['Community Name'], 'Rio Key': member_rio_key}
#     response = requests.post("http://127.0.0.1:5000/tag/create", json=tag_json)

#     assert response.status_code == 200

#     query = 'SELECT * FROM tag WHERE name = %s'
#     params = (tag_json['Tag Name'],)
#     result = db.query(query, params)
#     assert len(result) == 1
#     tag_id = result[0]['id']

#     #See if we get tags out (4 thus far, 1 for each community + 1 we just created)
#     response = requests.get("http://127.0.0.1:5000/tag/list")
#     data = response.json()
#     assert len(data['Tags']) == 4

#     # Get only component tags, typo for 409
#     response = requests.get("http://127.0.0.1:5000/tag/list", json={'Types': ['Junk']})
#     assert response.status_code == 409

#     # Get only component tags
#     response = requests.get("http://127.0.0.1:5000/tag/list", json={'Types': ['Component']})
#     assert response.status_code == 200    
#     data = response.json()
#     assert len(data['Tags']) == 1

#     # === Create a TagSet ===
#     tagset_json={
#         'TagSet Name': 'TagSetA',
#         'Description': 'New TagSet',
#         'Community Name': cPRIVATE_NONGLOBAL_COMM['Community Name'],
#         'Tags': [tag_id],
#         'Type': 'Season',
#         'Start': 0,
#         'End': 1,
#         'Rio Key': member_rio_key
#     }
#     response = requests.post("http://127.0.0.1:5000/tag_set/create", json=tagset_json)
#     print(response)
#     assert response.status_code == 200

#     # Without any options
#     response = requests.get("http://127.0.0.1:5000/tag_set/list")
#     assert response.status_code == 200
#     assert len(response.json()) == 1

#     # With correct key
#     tagset_list_json = { 'Rio Key': [member_rio_key] }
#     response = requests.get("http://127.0.0.1:5000/tag_set/list", json=tagset_list_json)
#     assert response.status_code == 200
#     assert len(response.json()) == 1

#     # Incorrect key, pass but no data
#     tagset_list_json = { 'Rio Key': [member_rio_key + 'X'] }
#     response = requests.get("http://127.0.0.1:5000/tag_set/list", json=tagset_list_json)
#     assert response.status_code == 200
#     assert len(response.json()) == 0

#     # Incorrect community, pass but no data
#     tagset_list_json = { 'Communities': ['invalid'] }
#     response = requests.get("http://127.0.0.1:5000/tag_set/list", json=tagset_list_json)
#     assert response.status_code == 200
#     assert len(response.json()) == 0

#     # Incorrect community, pass but no data
#     tagset_list_json = { 'Active': 'true' }
#     response = requests.get("http://127.0.0.1:5000/tag_set/list", json=tagset_list_json)
#     assert response.status_code == 200
#     assert len(response.json()) == 0

