from flask import request, abort
from flask import current_app as app
from ..models import Community, db, RioUser, UserGroup, UserGroupUser
from ..decorators import api_key_check
from ..util import format_list_for_SQL
import os
import requests as req
from pprint import pprint
from ..consts import *

# Switch to ApiKey -- Usergroup id


# Create UserGroup
@app.route('/user_group/create', methods=['GET'])
@api_key_check(['Admin'])
def create_user_group():
    # if os.getenv('RESET_DB') == request.json['RESET_DB']:
    if True:
        in_group_name = request.json['group_name']
        in_group_name_lower = in_group_name.lower()

        # Verify Group Name is alphanumeric
        if in_group_name.isalnum() == False:
            return abort(406, description='Provided username is not alphanumeric')        

        # Check if a Group with that name already exists
        group = UserGroup.query.filter_by(name_lowercase=in_group_name_lower).first()
        if not group:
            return abort(409, description='User Group name already taken.')

        try:
            new_group = UserGroup(name = in_group_name)
            db.session.add(new_group)
            db.session.commit()
            return 'User Group created.'
        except:
            return abort(400, description='Error creating User Group')

# Add RioUser to UserGroup using RioKey
@app.route('/user_group/add_user', methods=['POST'])
@api_key_check(['Admin'])
def add_user_to_user_group(in_username = None, in_group_name = None):
    if os.getenv('RESET_DB') == request.json['RESET_DB']:
        in_username = in_username if in_username != None else request.json['username']
        in_username_lower = in_username.lower()
        in_group_name = in_group_name if in_group_name != None else request.json['group_name']
        in_group_name_lower = in_group_name.lower()

        # Verify User exists
        user = RioUser.query.filter_by(username_lowercase=in_username_lower).first()
        if not user:
            return abort(409, description='User does not exist.')
        if not user.verified:
            return abort(409, description='User is not verified.')

        # Verify Group exists
        user_group = UserGroup.query.filter_by(name_lowercase=in_group_name_lower).first()
        if not user_group:
            return abort(409, description='UserGroup does not exist.')

        # Verify User is not a member of this group
        user_group_user = UserGroupUser.query.filter_by(
            user_id=user.id,
            user_group_id=user_group.id
        ).first()
        if user_group_user:
            return {200: 'User is already a member of this group.'}

        # Create a UserGroupUser row
        try:
            new_user_group_user = UserGroupUser(
                user_id=user.id,
                user_group_id=user_group.id
            )
            db.session.add(new_user_group_user)
            db.session.commit()
            return 'User added to User Group.'
        except:
            return abort(400, description='Error adding User to UserGroup')
    else:
        return abort(400, description='Incorrect Password')

# Check if a single user is a member of a group
@app.route('/user_group/check_for_member', methods=['GET'])
def check_if_user_in_user_group():
    in_username = request.args.get('username')
    in_username_lower = in_username.lower()
    in_group_name = request.args.get('group_name')
    in_group_name_lower = in_group_name.lower()

    # Get RioUser
    user = RioUser.query.filter_by(username_lowercase=in_username_lower).first()
    if not user:
        return abort(409, description='User does not exist.')

    # Get UserGroup
    user_group = UserGroup.query.filter_by(name_lowercase=in_group_name_lower).first()
    if not user_group:
        return abort(409, description='UserGroup does not exist.')
    
    # Check for UserGroupUser
    user_group_user = UserGroupUser.query.filter_by(
        user_id=user.id,
        user_group_id=user_group.id
    ).first()
    if user_group_user:
        return {"is_member": True}
    else:
        return {"is_member": False}


# Get list of users in group
@app.route('/user_group/members', methods=['GET'])
def get_group_member():
    in_group_name = request.args.get('group_name')
    in_group_name_lower = in_group_name.lower()

    # Get UserGroup
    user_group = UserGroup.query.filter_by(name_lowercase=in_group_name_lower).first()
    if not user_group:
        return abort(409, description='UserGroup does not exist.')

    # Get UserGroupUser user_ids
    users = db.session.query(
        UserGroup
    ).join(
        UserGroupUser
    ).join(
        RioUser
    ).filter(
        UserGroup.name_lowercase == in_group_name_lower
    ).all()

    # Get Users
    usernames = [user.username for user in users]

    return {
        "users": usernames
    }

# Get groups for users
@app.route('/user_groups/get_groups/')
def get_groups_for_users():
    return '200'

# Remove user from group
@app.route('/user_group/remove_member', methods=['GET'])
def remove_user_from_group():
    return '200'

def is_user_in_groups(user_id, group_list, all=False):
    group_list = [group.lower() for group in group_list]
        
    user_groups = UserGroup.query.filter(UserGroup.name_lowercase.in_(group_list))
    group_id_list = []
    for group in user_groups:
        group_id_list.append(group.id)
    user_group_user_count = UserGroupUser.query.filter(
        (UserGroupUser.user_id==user_id) & (UserGroupUser.user_group_id.in_(group_id_list))).count()

    if (all==False):
        return (user_group_user_count > 0)
    else:
        return (user_group_user_count == len(group_list))


def wipe_patrons():
    # Get Patreon UserGroups
    patreon_user_groups = db.session.query(UserGroup).filter(UserGroup.name.in_(cPATREON_TIERS)).all()

    # Create an array of UserGroup ids
    patreon_user_group_ids = [group.id for group in patreon_user_groups]
    patreon_user_group_ids_tuple, empty = format_list_for_SQL(patreon_user_group_ids)

    # SQL to clear all users from patron groups
    cmd = (
        'DELETE from user_group_user \n'
       f'WHERE user_group_id IN {patreon_user_group_ids_tuple}'
    )
    db.session.execute(cmd)

# Get groups for users
@app.route('/patreon/refresh/', methods=['GET'])
@api_key_check(['Admin'])
def refresh_patrons():
    print('refresh_patrons()')
    wipe_patrons()

    campaign_api_url = 'https://www.patreon.com/api/oauth2/api/current_user/campaigns'
    header = {'Authorization': 'Bearer ' + os.getenv('PATREON_API_KEY')}

    response = req.get(campaign_api_url, headers=header)
    data = response.json()
    campaign_id = data['data'][0]['id']

    patrons_api_url = f'https://www.patreon.com/api/oauth2/api/campaigns/{campaign_id}/pledges?include=patron.null'
    response = req.get(patrons_api_url, headers=header)
    data = response.json()

    #Build a more readable dict from the patreon response
    patron_dict = dict()
    def get_patrons_from_page(data, user_dict, tier_dict):
        for entry in data['included']:
            if entry['type'] == 'user':
                # print('USER:')
                # pprint(entry)
                patron_id = int(entry['id'])
                user_dict[patron_id] = dict()
                user_dict[patron_id]['id'] = patron_id
                user_dict[patron_id]['name'] = entry['attributes']['first_name']
                user_dict[patron_id]['email'] = entry['attributes']['email']
                # print('\n')
            # Garbage reward tiers have id of -1 and 0, not sure why
            elif entry['type'] == 'reward' and int(entry['id']) > 0:
                # print('REWARD:')
                # pprint(entry)
                tier_id = int(entry['id'])
                tier_dict[tier_id] = dict()
                tier_dict[tier_id]['id'] = tier_id
                tier_dict[tier_id]['name'] = entry['attributes']['title']
                tier_dict[tier_id]['required_amount'] = entry['attributes']['amount_cents']
                tier_dict[tier_id]['required_currency'] = entry['attributes']['currency']
                # print('\n')
        
        for entry in data['data']:
            # print('LINK:')
            # pprint(entry)

            patron_id = int(entry['relationships']['patron']['data']['id'])
            if not entry['relationships'].get('reward'):
                pass
            else:
                reward_id = int(entry['relationships']['reward']['data']['id'])
                user_dict[patron_id]['tier_id'] = reward_id

            user_dict[patron_id]['amount'] = entry['attributes']['amount_cents']
            user_dict[patron_id]['currency'] = entry['attributes']['currency']
            # print('\n')

        if (data['links'].get('next')):
            next_url = data['links']['next']
            response = req.get(next_url, headers=header)
            next_data = response.json()
            get_patrons_from_page(next_data, user_dict, tier_dict)
            
        return {'users': user_dict, 'tiers': tier_dict}
    
    patron_dict = get_patrons_from_page(data, dict(), dict())
    
    # pprint(patron_dict)
    # Associate users with a tier (work around because Patreon API has a bug)
    for user in patron_dict['users'].values():
        if not user.get('amount'):
            continue
        # pprint(user)
        if not user.get('tier_id'): #Tier hasn't been returned in API (the bug) so manualy figure out
            max_tier = dict()
            for tier in patron_dict['tiers'].values():
                #If user is paying enough for this tier, and this tier is higher than one we already saw, the user is in this tier
                #TODO handle currencies
                if (user['amount'] >= tier['required_amount']) and (not max_tier or (tier['required_amount'] >= max_tier['required_amount'])):
                    max_tier = tier
            user['tier_id'] = max_tier['id']
        
        # Add usergroup for patron tier
        group_name = 'Patron: ' + patron_dict['tiers'][user['tier_id']]['name']
        rio_user = RioUser.query.filter_by(email=user['email']).first()

        if rio_user == None:
            continue
        add_user_to_user_group(rio_user.username, group_name)

    # Iterate through each community to see if the sponsor is a patron and within their limits. If not, remove sponsor
    query = (
        'SELECT \n'
        'rio_user.id, \n'
        'MAX(user_group.sponsor_limit) AS sponsor_limit, \n'
        'COUNT(*) AS communities_sponsored \n'
        'FROM rio_user \n'
        'JOIN community ON rio_user.id = community.sponsor_id \n'
        'JOIN user_group_user ON rio_user.id = user_group_user.user_id \n'
        'JOIN user_group ON user_group_user.user_group_id = user_group.id \n'
        'GROUP BY rio_user.id \n'
    )
    results = db.session.execute(query).all()
    for result_row in results:
        result_dict = result_row._asdict()
        pprint(result_dict)
        if result_dict['communities_sponsored'] > result_dict['sponsor_limit']:
            num_comms_to_remove_sponsorship_from = result_dict['communities_sponsored'] - result_dict['sponsor_limit']
            comm_list = Community.query.filter_by(sponsor_id=result_dict['id']).order_by(Community.date_created)
            for comm in comm_list:
                if num_comms_to_remove_sponsorship_from > 0:
                    comm.sponsor_id = None
                    db.session.add(comm)
                    db.session.commit()
                    num_comms_to_remove_sponsorship_from -= 1
                if num_comms_to_remove_sponsorship_from == 0:
                    break

    return 200
            
# Add all users to a single group
@app.route('/user_group/add_all_users', methods=['POST'])
@api_key_check(['Admin'])
def add_all_users_to_group(in_group_name = None):
    in_group_name = in_group_name if in_group_name != None else request.json['group_name']

    # Verify Group exists
    user_group = UserGroup.query.filter_by(name_lowercase=in_group_name.lower()).first()
    if not user_group:
        return abort(409, description='UserGroup does not exist.')

    # Iterate through user list
    rio_user_list = RioUser.query.all()
    for rio_user in rio_user_list:

        # Verify User is not a member of this group
        user_group_user = UserGroupUser.query.filter_by(
            user_id=rio_user.id,
            user_group_id=user_group.id
        ).first()

        # If user is in user group, skip user
        if user_group_user:
            continue

        # Create a UserGroupUser row
        try:
            new_user_group_user = UserGroupUser(
                user_id=rio_user.id,
                user_group_id=user_group.id
            )
            db.session.add(new_user_group_user)
            db.session.commit()
            return 'User added to User Group.'
        except:
            return abort(410, description='Error adding User to UserGroup')
    return
