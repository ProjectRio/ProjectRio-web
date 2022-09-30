from flask import request, abort
from flask import current_app as app
from ..models import db, RioUser, UserGroup, UserGroupUser
from ..decorators import api_key_check

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
def add_user_to_user_group():
    # if os.getenv('RESET_DB') == request.json['RESET_DB']:
    if True:
        in_username = request.json['username']
        in_username_lower = in_username.lower()
        in_group_name = request.json['group_name']
        in_group_name_lower = in_group_name.lower()

        # Verify User exists
        user = RioUser.query.filter_by(username_lowercase=in_username_lower).first()
        if not user:
            return abort(409, description='User does not exist.')

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
            return abort(409, description='User is already a member of this group.')

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

def is_user_in_groups(user_id, group_list):
    group_list = [group.lower() for group in group_list]
        
    user_groups = UserGroup.query.filter(UserGroup.name_lowercase.in_(group_list))
    group_id_list = []
    for group in user_groups:
        group_id_list.append(group.id)
    user_group_user_count = UserGroupUser.query.filter(
        (UserGroupUser.user_id==user_id) & (UserGroupUser.id.in_(group_id_list))).count()
    return (user_group_user_count > 0)