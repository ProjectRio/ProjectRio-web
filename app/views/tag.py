from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ..email import send_email
import secrets
from ..models import db, RioUser, CommunityUser, Community, Tag, TagSet, TagSetTag
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
        return abort(409, "No community found with name={in_tag_comm_name}")

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
            return abort(409, "No Rio Key or JWT Provided")

    if user == None:
        return abort(409, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if (comm_user == None or comm_user.admin == False):
        return abort(409, description='User not apart of community or not an admin')

    # === Tag Creation ===
    new_tag = Tag( in_comm_id=comm.id, in_tag_name=in_tag_name, in_tag_type="Component", in_desc=in_tag_desc)
    db.session.add(new_tag)
    db.session.commit()

    #TODO this might not work, but its late and I gotta end this
    #"this" meaning the coding session
    return jsonify(new_tag.name)

@app.route('/tag/list', methods=['GET'])
def tag_list(all_tags=False):
    # community_list = None

    type_like_statement = ''
    print(request.is_json)
    types_provided = request.is_json and 'Types' in request.json
    if types_provided and not all_tags:
        type_like_statement = 'AND ('
        for idx, type in enumerate(request.json.get('Types')):
            print("In values?", type not in cTAG_TYPES.values())
            if type not in cTAG_TYPES.values():
                return abort(409, description="Invalid tag type provided")
            if idx > 0:
                type_like_statement += "OR "
            type_like_statement += f"tag.tag_type LIKE '%{type}%' "
        type_like_statement += ") "

    query = (
        'SELECT \n'
        'tag.id AS id, \n'
        'tag.community_id AS comm_id, \n'
        'comm.name AS comm_name, \n'
        'tag.name AS tag_name, \n'
        'tag.tag_type AS type, \n'
       f"{'tag.desc AS desc, ' if types_provided or all_tags else ''} \n"
        'tag.active AS active \n'
        'FROM tag \n'
        'LEFT JOIN community AS comm ON tag.id = comm.id \n' #Join communities
       f"WHERE active = true {type_like_statement}"
    )

    print(query)

    result = db.session.execute(query).all()

    tags = []
    for entry in result:
        tags.append(entry._asdict() )
    return { 'Tags': tags }

#TODO support duration along with end data so eiither can be supplied
@app.route('/tag_set/create', methods=['POST'])
@jwt_required(optional=True)
def tag_create():
    in_tag_set_name = request.json['Tag Name']
    in_tag_set_desc = request.json['Description']
    in_tag_set_comm_name = request.json['Community Name']
    in_tag_ids = request.json['Tags']
    in_tag_set_start_time = request.json['Start']
    in_tag_set_end_time = request.json['End']

    comm_name_lower = in_tag_set_comm_name.lower()
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    if comm == None:
        return abort(409, "No community found with name={in_tag_set_comm_name}")

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
            return abort(409, "No Rio Key or JWT Provided")

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
    new_tag_set = TagSet(in_comm_id=comm.id, in_tag_name=in_tag_set_name, in_start=in_tag_set_start_time, in_end=in_tag_set_end_time)
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
        tag_set_tag = TagSetTag(
            tag_id = tag.id,
            tag_set_id = new_tag_set.id
        )
        db.session.add(tag_set_tag)
    return jsonify(new_tag_set)

# If RioKey/JWT provided get TagSet for user. Else get all
# Uses:
#   Get all active TagSets
#   Get users TagSets
#   Get community TagSets
@app.route('/tag_set/list', methods=['GET'])
def tag_list():
    statement_list = list()
    
    active_only = request.is_json and 'Active' in request.json and request.json['Active'].lower() in ['yes', 'y', 'true', 't']
    if (active_only):
        current_unix_time = int( time.time() )
        where_active_statement = f"(tagset.start_date < {current_unix_time} AND tagset.end_date > {current_unix_time}) "
        statement_list.append(where_active_statement)

    communities_provided = request.is_json and 'Communities' in request.json
    if (communities_provided):
        comm_like_statement = " ("
        for idx, name in enumerate(request.json.get('Communities')):
            if idx > 0:
                type_like_statement += "OR "
            name_lower = name.lower()
            comm_like_statement += f"comm.name_lowercase LIKE '%{name_lower}%' "
        comm_like_statement += ") "
        statement_list.append(comm_like_statement)

    rio_key_provided = request.is_json and 'Rio Key' in request.json
    if rio_key_provided:
        rio_key = request.json['Rio Key']
        where_rio_user_statement = f"(rio_user.rio_key == {rio_key})"
        statement_list.append(where_rio_user_statement)


    where_statement = ' AND '.join(where_statement)
    if (len(statement_list) > 1):
        where_statement = "WHERE " + where_statement
    query = (
        'SELECT \n'
        'tagset.id AS id, \n'
        'tagset.name AS name, \n'
        'tagset.community_id AS comm_id, \n'
        'tagset.start_date AS start_date \n'
        'tagset.end_date AS end_date \n'
        'FROM tag \n'
        'JOIN community AS comm ON tag.id = comm.id \n' #Join communities
        'JOIN community_user AS comm_user ON comm.id = comm_user.comm_id \n' #Join communities users
        'JOIN rio_user ON comm_user.user_id = rio_user.id \n'
       f"WHERE {where_statement}"
    )