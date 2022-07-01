from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ..email import send_email
import secrets
from ..models import db, RioUser, CommunityUser, Community
from ..consts import *
import time

@app.route('/register/', methods=['POST'])
@jwt_required()
def register():
    in_comm_name = request.json['Name']
    private = (request.json['Private'] == 1)
    create_global_link = (request.json['Global Link'] == 1)

    # Get user making the new tag
    current_user_username = get_jwt_identity()
    user = RioUser.query.filter_by(username=current_user_username).first()


    #TODO possible work around if we don't want to use JWT tokens right away
    #user = RioUser.query.filter_by(username_lowercase=username_lowercase).first()
    #user_by_email = RioUser.query.filter_by(email=in_email).first()

    if user == None:
        return abort(409, description='Username not found. Community not created')
    elif in_comm_name.isalnum() == False:
        return abort(406, description='Provided community name is not alphanumeric. Community not created')
    else:
        # === Create Community row ===
        new_comm = Community(in_comm_name, private, create_global_link)
        db.session.add(new_comm)
        db.session.commit()

        # === Create CommunityUser (admin)

        # === Create Community Tag ===


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