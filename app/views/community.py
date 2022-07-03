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
        new_comm_user = CommunityUser(user.id, new_comm.id, True, False)
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
        in_active_url = request.json['Active URL']

        #Check if CommunityUser already exists
        comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()
        if comm_user != None: #User has been invited
            if in_active_url == comm_user.active_url:
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