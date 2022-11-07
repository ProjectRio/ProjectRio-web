from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ..send_email import send_email
import secrets
from ..models import db, RioUser, CommunityUser, Community, Tag, TagSet
from ..consts import *
import time

@app.route('/tag/create', methods=['POST'])
@jwt_required(optional=True)
def tag_create():
    in_tag_name = request.json['Tag Name']
    in_tag_desc = request.json['Description']
    in_tag_comm_name = request.json['Community Name']

    comm_name_lower = in_tag_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    if comm == None:
        return abort(409, description="No community found with name={in_tag_comm_name}")

    # Get user making the new community
    #Get user via JWT or RioKey
    user=None
    current_user_username = get_jwt_identity()
    if current_user_username:
        user = RioUser.query.filter_by(username=current_user_username).first()
    else:
        try:
            user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()
        except:
            return abort(409, description="No Rio Key or JWT Provided")

    if user == None:
        return abort(409, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if (comm_user == None or comm_user.admin == False):
        return abort(409, description='User not a part of community or not an admin')

    # === Tag Creation ===
    new_tag = Tag( in_comm_id=comm.id, in_tag_name=in_tag_name, in_tag_type="Component", in_desc=in_tag_desc)
    db.session.add(new_tag)
    db.session.commit()

    #TODO this might not work, but its late and I gotta end this
    #"this" meaning the coding session
    return jsonify(new_tag.name)

@app.route('/tag/list', methods=['GET'])
def tag_list():
    types_provided = request.is_json and 'Types' in request.json
    types_list = request.json.get('Types') if types_provided else list()

    # Abort if any of the provided types are not valid
    if (types_provided and not any(x in types_list for x in cTAG_TYPES.values())):
        return abort(409, description=f"Illegal type name provided. Valid types {cTAG_TYPES.values()}")

    communities_provided = request.is_json and 'Communities' in request.json
    community_id_list = request.json.get('Communities') if communities_provided else list() 

    result = list()
    if types_provided and not communities_provided:
        result = Tag.query.filter(Tag.tag_type.in_(types_list))
    elif not types_provided and communities_provided:
        result = Tag.query.join(Community, Tag.community_id == Community.id)\
            .filter(Community.id.in_(community_id_list))
    elif not types_provided and communities_provided:
        result = Tag.query.join(Community, Tag.community_id == Community.id)\
            .filter((Community.id.in_(community_id_list)) & (Tag.tag_type.in_(types_list)))
    else:
        result = Tag.query.all()

    tags = list()
    for tag in result:
        tags.append(tag.to_dict())
    return { 'Tags': tags }

#TODO support duration along with end data so eiither can be supplied
@app.route('/tag_set/create', methods=['POST'])
@jwt_required(optional=True)
def tagset_create():
    in_tag_set_name = request.json['TagSet Name']
    in_tag_set_desc = request.json['Description']
    in_tag_set_type = request.json['Type']
    in_tag_set_comm_name = request.json['Community Name']
    in_tag_ids = request.json['Tags']
    in_tag_set_start_time = request.json['Start']
    in_tag_set_end_time = request.json['End']

    comm_name_lower = in_tag_set_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    if comm == None:
        return abort(409, description=f"No community found with name={in_tag_set_comm_name}")
    if comm.sponsor_id == None:
        return abort(410, description=f"Community is not sponsored")
    if in_tag_set_name.isalnum() == False:
        return abort(406, description='Provided tag set name is not alphanumeric. Community not created')
    if in_tag_set_end_time < in_tag_set_start_time:
        return abort(409, description='Invalid start/end times')
    if in_tag_set_type not in cTAG_SET_TYPES.values():
        return abort(409, description='Invalid tag type')

    # Get user making the new community
    #Get user via JWT or RioKey
    user=None
    current_user_username = get_jwt_identity()
    if current_user_username:
        user = RioUser.query.filter_by(username=current_user_username).first()
    else:
        try:
            user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()
        except:
            return abort(409, description="No Rio Key or JWT Provided")

    if user == None:
        return abort(409, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if (comm_user == None or comm_user.admin == False):
        return abort(409, description='User not apart of community or not an admin')

    # Validate all tag ids, add to list
    tags = list()
    for id in in_tag_ids:
        tag = Tag.query.filter_by(id=id).first()
        if tag == None:
            return abort(409, f'Tag with ID={id} not found')
        if tag.tag_type != "Component":
            return abort(409, f'Tag with ID={id} not a component tag')
        tags.append(tag)

    # === Tag Set Creation ===
    new_tag_set = TagSet(in_comm_id=comm.id, in_name=in_tag_set_name,in_type=in_tag_set_type, in_start=in_tag_set_start_time, in_end=in_tag_set_end_time)
    db.session.add(new_tag_set)
    db.session.commit()

    # === Tag Creation ===
    new_tag_set_tag = Tag( in_comm_id=comm.id, in_tag_name=in_tag_set_name, in_tag_type="Competition", in_desc=in_tag_set_desc)
    db.session.add(new_tag_set_tag)
    db.session.commit()
    tags.append(new_tag_set_tag)

    # TagSetTags
    # Get Comm tag
    comm_tag = Tag.query.filter_by(community_id=comm.id, tag_type="Community").first()
    if comm_tag == None:
        return abort(409, description='Could not find community tag for community')
    tags.append(comm_tag)

    for tag in tags:
        new_tag_set.tags.append(tag)
    
    db.session.commit()
    return jsonify(new_tag_set.to_dict())

# If RioKey/JWT provided get TagSet for user. Else get all
# Uses:
#   Get all active TagSets for rio_key
#   Get all active and inactive TagSets for rio_key
#   Get all active/inactive TagSets for provided communities per RioKey
@app.route('/tag_set/list', methods=['POST'])
def tagset_list():    
    current_unix_time = int( time.time() )
    active_only = request.is_json and 'Active' in request.json and request.json['Active'].lower() in ['yes', 'y', 'true', 't']
    communities_provided = request.is_json and 'Communities' in request.json
    community_id_list = request.json.get('Communities') if communities_provided else list()

    if (communities_provided and len(community_id_list) > 0):
        return abort(409, description="Communities key added to JSON but no community ids passed")
    
    rio_key_provided = request.is_json and 'Rio Key' in request.json
    if rio_key_provided:
        rio_key = request.json.get('Rio Key')
        tag_sets = db.session.query(
            TagSet
        ).join(
            Community
        ).join(
            CommunityUser
        ).join(
            RioUser
        ).filter(
            RioUser.rio_key == rio_key
        ).all()

        tag_set_list = list()
        for tag_set in tag_sets:
            # Skip this tag set if current time is not within start/end time
            if (active_only and (current_unix_time < tag_set.start_date or current_unix_time > tag_set.end_date)):
                continue
            # Skip this tag set if community_id is not from a requested community
            if (communities_provided and tag_set.community_id not in community_id_list):
                continue

            # Append passing tag set information
            tag_set_list.append(tag_set.to_dict())
    else:
        abort(409, "No Rio Key provided")

    return {"Tag Sets": tag_set_list}

@app.route('/tag_set/<tag_set_id>', methods=['GET'])
def tagset_get_tags(tag_set_id):
    result = TagSet.query.filter_by(id = tag_set_id).first()
    if result == None:
        return abort(409, description=f"Could not find TagSet with id={tag_set_id}")

    return {"Tag Set": [result.to_dict()]}