from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ..email import send_email
import secrets
from ..models import db, RioUser, CommunityUser, Community, Tag
from ..consts import *
import time

@app.route('/tag/create', methods=['POST'])
@jwt_required(optional=True)
def tag_create():
    in_tag_name = request.json['Tag Name']
    in_tag_type = request.json['Tag Type']
    in_tag_desc = request.json['Description']

    comm = None
    try:
        in_tag_comm_name = request.json['Community Name']
        comm_name_lower = in_tag_comm_name.lower()
        comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

        if comm == None:
            return abort(409, "No community found with name={in_tag_comm_name}")
    except:
        print("No community name given, assuming this is a public tag")

    # Get user making the new community
    #Get user via JWT or RioKey 
    user=None
    try:
        current_user_username = get_jwt_identity()
        user = RioUser.query.filter_by(username=current_user_username).first()
    except:
        user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()

    if user == None:
        return abort(409, description='Username associated with JWT or RioKey not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if (comm != None and (comm_user == None or comm_user.admin == False) ):
        return abort(409, description='User not apart of community or not an admin')
    if (comm == None and user.username_lower not in ['peacockslayer', 'maybejon', 'littlecoaks']): #TODO eventually use user groups for this
        return abort(403, description='Public tag is trying to be created but user is not authorized to do so')

    # === Tag Creation ===
    comm_id = None if comm == None else comm.id
    new_tag = Tag( in_comm_id=comm_id, in_tag_name=in_tag_name, in_tag_type=in_tag_type, in_desc=in_tag_desc)
    db.session.add(new_tag)
    db.session.commit()

    #TODO this might not work, but its late and I gotta end this
    return jsonify(new_tag._asdict())