import random
import string
import requests

from connection import Connection

db = Connection()

class User:
    pk       = None
    rk       = None
    url      = None
    verified = False
    groups   = list()
    success  = False

    def __init__(self, in_user_dict=None):
        # If user details are not specified, randomize user
        if in_user_dict == None:
            in_user_dict = dict()
            length = random.randint(3,20)
            in_user_dict['Username'] = ''.join(random.choices(string.ascii_letters, k=length))
            in_user_dict['Email'] =  ''.join(random.choices(string.ascii_letters, k=length)) + "@email.com"
            in_user_dict['Password'] =  ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation , k=length))
        self.username = in_user_dict['Username']
        self.email = in_user_dict['Email']
        self.password = in_user_dict['Password']

    def register(self):
        # Post new user
        json = {'Username': self.username, 'Email': self.email, 'Password': self.password}
        response = requests.post("http://127.0.0.1:5000/register/", json=json)
        self.success = (response.status_code == 200)

        # Get user info from db
        query = 'SELECT * FROM rio_user WHERE username = %s'
        params = (self.username,)
        result = db.query(query, params)
        
        self.pk       = result[0]['id']
        self.username = result[0]['username']
        self.email    = result[0]['email']
        self.rk       = result[0]['rio_key']
        self.url      = result[0]['active_url']
        self.password = None # Zero password, even for testing
        self.verified = False

    def verify_user(self):
        response = requests.post(f"http://127.0.0.1:5000/verify_email/{self.url}")
        # Confirm user is verified
        query = 'SELECT * FROM rio_user WHERE username = %s'
        params = (self.username,)
        result = db.query(query, params)
        self.verified = (result[0]['verified'] == True)

        return (response.status_code == 200)

    def add_to_group(self, group_name):
        json = {'username': self.username, 'group_name': group_name}
        response = requests.post(f"http://127.0.0.1:5000/user_group/add_user", json=json)
        success = (response.status_code == 200)

        if not success:
            return success
        
        self.groups.append('group_name'.lower())
        return success



class CommUser():
    def __init__(self, user, comm_user_pk, comm_id, admin, invited, active, banned):
        self.pk = comm_user_pk
        self.user = user
        self.comm_id = comm_id
        self.admin = admin
        self.invited = invited
        self.active = active
        self.banned = banned

class Community:
    def __init__(self, founder_user, official, private, link, in_comm_dict=None):
        if in_comm_dict == None:
            in_comm_dict = dict()
            length = random.randint(3,20)
            in_comm_dict['Community Name'] =  ''.join(random.choices(string.ascii_letters, k=length))
            in_comm_dict['Description'] =  ''.join(random.choices(string.ascii_letters, k=length))

        in_comm_dict['Type'] = 'Official' if official else 'Unofficial'
        in_comm_dict['Private'] = 1 if private else 0
        in_comm_dict['Global Link'] = 1 if link else 0
        in_comm_dict['Rio Key'] = founder_user.rk

        response = requests.post("http://127.0.0.1:5000/community/create", json=in_comm_dict)
        self.success = (response.status_code == 200)

        if not self.success:
            return None

        # Community created check, do not check comm user and tag (they function the same regardless, redundant)
        query = 'SELECT * FROM community WHERE name = %s'
        params = (in_comm_dict["Community Name"],)
        result = db.query(query, params)

        self.pk = result[0]['id']
        self.name = result[0]['name']
        self.type = result[0]['comm_type']
        self.private = (result[0]['private'] == True)
        self.url = result[0]['active_url']

        # Get founder community user
        query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
        params = (str(self.pk),str(founder_user.pk))
        result = db.query(query, params)
        self.founder = CommUser(founder_user, result[0]['id'], self.pk, result[0]['admin'], result[0]['invited'], 
                                result[0]['active'], result[0]['banned'])
        self.members = dict()
        self.members[self.founder.pk] = self.founder

        #Get all users (if official community)
        self.refresh()

    #def join_via_url(self, user, name_err=False, url_err=False, rk_err=False):
    def join_via_url(self, user):
        response = requests.post("http://127.0.0.1:5000/community/join/{}/{}".format(self.name, self.url), json={'Rio Key': user.rk})
        success = (response.status_code == 200)

        if not success:
            return success
            
        # Get community user
        query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
        params = (str(self.pk),str(user.pk),)
        result = db.query(query, params)
        comm_user = CommUser(user, result[0]['id'], self.pk, result[0]['admin'], result[0]['invited'], 
                             result[0]['active'], result[0]['banned'])
        self.members[comm_user.pk] = comm_user
        return success
        
    # If invited, join. If not, request outstanding
    def join_via_request(self, user):
        response = requests.post("http://127.0.0.1:5000/community/join", json={'Community Name': self.name, 'Rio Key': user.rk})
        success = (response.status_code == 200)

        if not success:
            return success

        # Get community user
        query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
        params = (str(self.pk),str(user.pk),)
        result = db.query(query, params)
        comm_user = CommUser(user, result[0]['id'], self.pk, result[0]['admin'], result[0]['invited'], 
                             result[0]['active'], result[0]['banned'])
        self.members[comm_user.pk] = comm_user

        return success
        
    # If requested to join, accept. If not, invite
    def invite(self, admin_user, invitee_dict):
        invite_json = {'Rio Key': admin_user.rk, 
                       'Community Name': self.name, 
                       'Invite List': [invitee.username for invitee in invitee_dict.values()] }
        print(invite_json)
        response = requests.post("http://127.0.0.1:5000/community/invite", json=invite_json)
        success = (response.status_code == 200)

        if (success):
            self.refresh()
        return success

    # If requested to join, accept. If not, invite
    def manage(self, admin_user, user_list, modification):
        manage_user_list = list()
        for user in user_list:
            temp_dict = {'Username': user.name}
            if modification == 'Admin':
                temp_dict['Admin'] = 't'
            elif modification == 'Ban':
                temp_dict['Ban'] = 't'
            manage_user_list.append(temp_dict)

        
        response = requests.post("http://127.0.0.1:5000/community/manage", json={'Community Name': self.name, 
                                                                             'Rio Key': admin_user.rk, 
                                                                             'User List': manage_user_list })
        success = (response.status_code == 200)

        if (success):
            #Update list of comm users from DB
            for user in user_list:
                query = 'SELECT * FROM community_user WHERE community_id = %s AND user_id = %s'
                params = (str(self.pk),str(user.pk),)
                result = db.query(query, params)

                comm_user = self.members[result[0]['id']]
                comm_user.admin = result[0]['admin']
                comm_user.banned = result[0]['banned']
        return success
    
    # Pulls all comm users and updates members list
    def refresh(self):
        query = ('SELECT * \n'
                 'FROM community_user \n'
                 'JOIN rio_user ON community_user.user_id = rio_user.id \n'
                 'WHERE community_id = %s')
        params = (str(self.pk),)
        result = db.query(query, params)
        for result_row in result:
            user = User()
            user.username = result_row['username']
            user.email    = result_row['email']
            user.pk       = result_row['user_id']
            user.verified = result_row['verified']
            user.rk       = result_row['rio_key']
            comm_user = CommUser(user, result_row['id'], self.pk, result_row['admin'], result_row['invited'], 
                                    result_row['active'], result_row['banned'])
            self.members[comm_user.pk] = comm_user

    def get_member(self, user):
        for comm_user in self.members.values():
            if comm_user.pk == user.pk:
                return comm_user
        return None

class Tag:
    def __init__(self, admin_user, community, tag_details=None):
        if tag_details == None:
            tag_details = dict()
            length = random.randint(3,20)
            tag_details['Tag Name'] =  ''.join(random.choices(string.ascii_letters, k=length))
            tag_details['Description'] =  ''.join(random.choices(string.ascii_letters, k=length))
        tag_details['Community Name'] = community.name
        tag_details['Rio Key'] = admin_user.rk

        # Post Tag
        response = requests.post("http://127.0.0.1:5000/tag/create", json=tag_details)

        self.success = (response.status_code == 200)

        query = 'SELECT * FROM tag WHERE name = %s'
        params = (tag_details['Tag Name'],)
        result = db.query(query, params)
        
        self.pk = result[0]['id']
        self.name = result[0]['name']
        self.comm_id = result[0]['community_id']
        self.type = result[0]['tag_type']
        self.active = result[0]['active']