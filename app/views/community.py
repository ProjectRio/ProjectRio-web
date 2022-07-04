from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ..email import send_email
import secrets
from ..models import db, RioUser, CommunityUser, Community, Tag
from ..consts import *
import time

@app.route('/community/create', methods=['POST'])
@jwt_required()
def community_create():
    in_comm_name = request.json['Name']
    private = (request.json['Private'] == 1)
    create_global_link = (request.json['Global Link'] == 1)
    in_comm_desc = request.json['Description']

    # Get user making the new community
    current_user_username = get_jwt_identity()
    user = RioUser.query.filter_by(username=current_user_username).first()


    #TODO possible work around if we don't want to use JWT tokens right away
    #user = RioUser.query.filter_by(username_lowercase=username_lowercase).first()
    #user_by_email = RioUser.query.filter_by(email=in_email).first()

    if user == None:
        return abort(409, description='Username associated with JWT not found. Community not created')
    elif in_comm_name.isalnum() == False:
        return abort(406, description='Provided community name is not alphanumeric. Community not created')
    else:
        # === Create Community row ===
        new_comm = Community(in_comm_name, private, create_global_link, in_comm_desc)
        db.session.add(new_comm)
        db.session.commit()

        # === Create CommunityUser (admin)
        new_comm_user = CommunityUser(user.id, new_comm.id, True, False, True)
        db.session.add(new_comm_user)
        db.session.commit()

        # === Create Community Tag ===
        new_comm_tag = Tag(new_comm.id, new_comm.name, "Community", "Community tag for {new_comm.name}")
        db.session.add(new_comm_user)
        db.session.commit()

        # === Send Email ===
        subject = 'ProjectRio - New community created!'

        community_type = 'private' if private else 'public'
        html_content = (
            f'''
            <h1>Congratulations on starting a new {community_type} community, {new_comm.name}!</h1>
            <br/>
            <p>Happy Hitting!</p>
            <p>Rio Team</p>
            '''
        )

        try:
            send_email(user.email, subject, html_content)
        except:
            return abort(502, 'Failed to send email')
        
    return jsonify({
        'name': new_comm.name,
        'private': new_comm.private,
        'active_url': new_comm.active_url
    })

@app.route('/community/join', methods=['POST'])
@jwt_required()
def community_join():
    # Ways to join a community
    # If public: provide the community id
    # If private:
    #    If Global URL: provide active url
    #    If User has been invite, provide users active URL

    in_comm_name = request.json['Name']
    comm_name_lower = in_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    current_user_username = get_jwt_identity()
    user = RioUser.query.filter_by(username=current_user_username).first()

    if user == None:
        return abort(409, description='Username associated with JWT not found.')
    if comm == None:
        return abort(409, description='Could not find community with name={in_comm_name}')


    if comm.private == False:
        #No need to check anything else, join community
        new_comm_user = CommunityUser(in_user_id=user.id, in_comm_id=comm.id, in_is_admin=False, in_gen_url=False, in_accepted=True)
        db.session.add(new_comm_user)
        db.session.commit()
        return jsonify({
            'name': comm.name,
            'accepted': new_comm_user.accepted
        })
    else:
        #Active URL must have been provided
        in_active_url = request.args.get('url')

        if in_active_url == None:
            return abort(409, description='URL not provided to join private community {comm.name}')

        #Check if CommunityUser already exists
        comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()
        if comm_user != None: #User has been invited
            if in_active_url == comm_user.active_url:
                #Update user to be an active memeber
                comm_user.accepted
                comm_user.date_joined = int( time.time() )
                comm_user.active_url = None
                db.session.add(comm_user)
                db.session.commit()
                return jsonify({
                    'name': comm.name,
                    'accepted': new_comm_user.accepted
                })

        if in_active_url == comm.active_url: 
            new_comm_user = CommunityUser(in_user_id=user.id, in_comm_id=comm.id, in_is_admin=False, in_gen_url=False, in_accepted=True)
            db.session.add(new_comm_user)
            db.session.commit()
            return jsonify({
                'name': comm.name,
                'accepted': new_comm_user.accepted
            })

        #If we get here, none of the above was true, fail 
        return abort(409, description='''
            Unable to join community. Community status (public/private): {com.private}.\n
            Community URL: {comm.active_url}.\n
            Provided URL: {in_active_url}./n
            CommunityUser URL: {comm_user.active_url}.
            ''')


@app.route('/community/invite', methods=['POST'])
@jwt_required()
def community_invite():
    # Ways to join a community
    # If public: provide the community id
    # If private:
    #    If Global URL: provide active url
    #    If User has been invite, provide users active URL

    in_comm_name = request.json['Name']
    comm_name_lower = in_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    current_user_username = get_jwt_identity()
    user = RioUser.query.filter_by(username=current_user_username).first()

    if user == None:
        return abort(409, description='Username associated with JWT not found.')
    if comm == None:
        return abort(409, description='Could not find community with name={in_comm_name}')
    
    #Check if CommunityUser already exists
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if comm_user != None:
        return abort(409, description='User is not part of this community')
    if (comm.private and comm_user.is_admin == False):
        return abort(409, description='User is not an admin of this private community.')

    list_of_users_to_invite = request.json['Invite List']

    #Check that all users exist before sending invites
    for user in list_of_users_to_invite:
        invited_user = RioUser.query.filter_by(username_lower=user.lower()).first()
        if invited_user == None:
            return abort(409, description='User does not exist. Username={user}')

    #Entire list has been validated, add users to table and send emails
    list_of_invite_codes = list() #List to store dicts of comm user info
    for user in list_of_users_to_invite:
        invited_user = RioUser.query.filter_by(username_lower=user.lower()).first()

        #Now see if user has already been invited, if so skip inviting a second time
        comm_user = CommunityUser.query.filter_by(user_id=invited_user.id, community_id=comm.id).first()

        if comm_user != None:
            continue
        new_comm_user = CommunityUser(in_user_id=invited_user.id, in_comm_id=comm.id, in_is_admin=False, in_gen_url=True, in_accepted=False)
        db.session.add(new_comm_user)
        db.session.commit()

        # === Send Email ===
        subject = 'ProjectRio - You have been invited to a community!'

        #TODO figure out the URL to join
        html_content = (
            f'''
            <h1>Congratulations {invited_user.username}! You have been invited to join {comm.name}!</h1>
            <p>Follow the link below to join (TODO add link below)!</p>
            <br/>
            <p>Happy Hitting!</p>
            <p>Rio Team</p>
            '''
        )

        list_of_invite_codes.append({'Username': invited_user.username, 'Invite Code': new_comm_user.active_url})

        try:
            send_email(invited_user.email, subject, html_content)
        except:
            return abort(502, 'Failed to send email')

    #Return list of usernames and invite URLs
    return jsonify({'Invites': list_of_invite_codes})


#TODO return usernames rather than user ids
@app.route('/community/members', methods=['GET'])
@jwt_required(optional=True)
def community_members():
    in_comm_name = request.json['Name']
    comm_name_lower = in_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    user=None
    try:
        current_user_username = get_jwt_identity()
        user = RioUser.query.filter_by(username=current_user_username).first()
    except:
        user=None
    if comm == None:
        return abort(409, description='Could not find community with name={in_comm_name}')
    
    if user == None and comm.private:
        return abort(409, description='Must be logged in to see private community members.')


    #If user is logged in, must be a part of private community to see memebers
    if user != None and comm.private:
        comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()
        if comm_user == None:
            return abort(409, description='Must be a member of private community to see all members.')

    #If we get to this point the user is allowed to get the memeber list
    member_list = CommunityUser.query.filter_by(community_id=comm.id)

    accepted_list = list()
    pending_list = list()
    for member in member_list:
        if member.accepted:
            accepted_list.append(member)
        else:
            pending_list.append(member)

    return jsonify({'Members': {'Accepted': accepted_list, 'Pending': pending_list}})

