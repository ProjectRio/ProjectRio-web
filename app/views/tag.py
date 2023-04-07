from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from app.utils.send_email import send_email
import secrets
from ..models import *
from ..consts import *
from ..util import *
from app.views.user_groups import *
import time
from pprint import pprint

@app.route('/tag/create', methods=['POST'])
@jwt_required(optional=True)
def tag_create():
    in_tag_name = request.json['Tag Name']
    in_tag_desc = request.json['Description']
    in_tag_comm_name = request.json['Community Name']
    in_tag_type = request.json['Tag Type']

    #Fields for gecko codes only
    gecko_code_desc_provided = request.is_json and 'Gecko Code Desc' in request.json
    gecko_code_desc = request.json.get('Gecko Code Desc') if gecko_code_desc_provided else None

    gecko_code_provided = request.is_json and 'Gecko Code' in request.json
    gecko_code = request.json.get('Gecko Code') if gecko_code_provided else None

    comm_name_lower = lower_and_remove_nonalphanumeric(in_tag_comm_name)
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    creating_gecko_code = (in_tag_type == "Gecko Code" and gecko_code_desc_provided and gecko_code_provided)

    if comm == None:
        return abort(409, description="No community found with name={in_tag_comm_name}")
    if in_tag_type not in cTAG_TYPES.values() or in_tag_type == "Competition" or in_tag_type == "Community":
        return abort(410, description="Invalid tag type '{in_tag_type}'")
    if ((in_tag_type == "Gecko Code" or in_tag_type == "Client Code") and not comm.comm_type == 'Official'):
        return abort(411, description="Gecko codes must be added to official community")
    if (in_tag_type == "Gecko Code" and (not gecko_code_desc_provided or not gecko_code_provided)):
        return abort(412, description="Type is gecko code but code details not provided")
    if (in_tag_type == "Gecko Code" and not validate_gecko_code(gecko_code)):
        return abort(415, description="Type is gecko code but code is not formatted correctly (<CODE> <CODE><\n>)")


    #Make sure that tag does not use the same name as an existing tag, comm, or tag_set
    tag = Tag.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_name)).first()
    comm_name_check = Community.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_name)).first()
    tag_set = TagSet.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_name)).first()

    if tag != None or comm_name_check != None or tag_set != None:
        return abort(413, description='Name already in use (Tag, TagSet, or Community)')

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

    if ((comm_user == None or comm_user.admin == False) and not is_user_in_groups(user.id, ['Admin'])):
        return abort(409, description='User not a part of community or not an admin')

    # === Tag Creation ===
    new_tag = Tag( in_comm_id=comm.id, in_tag_name=in_tag_name, in_tag_type=in_tag_type, in_desc=in_tag_desc)
    db.session.add(new_tag)
    db.session.commit()

    # === Code Tag Creation ===
    if (creating_gecko_code):
        new_code_tag = GeckoCodeTag(in_tag_id=new_tag.id, in_gecko_code_desc=gecko_code_desc, in_gecko_code=gecko_code)
        db.session.add(new_code_tag)
        db.session.commit()
    
    tag_dict = new_tag.to_dict()
    if (new_tag.tag_type == 'Gecko Code'):
        tag_dict["gecko_code_desc"] = gecko_code_desc
        tag_dict["gecko_code"] = gecko_code
    return jsonify(tag_dict)


@app.route('/tag/update', methods=['POST'])
@jwt_required(optional=True)
def tag_update():
    in_tag_id = request.json['tag_id'] # Required

    #Optional Args
    name_provided = request.is_json and 'name' in request.json
    new_name = request.json['name']
    desc_provided = request.is_json and 'desc' in request.json
    new_desc = request.json['desc']
    type_provided = request.is_json and 'type' in request.json
    new_type = request.json['type']

    gecko_code_provided = request.is_json and 'gecko_code' in request.json
    new_gecko_code = request.json['gecko_code']
    gecko_code_desc_provided = request.is_json and 'gecko_code_desc' in request.json
    new_gecko_code_desc = request.json['gecko_code_desc']
    


    if type_provided and (new_type not in cTAG_TYPES.values() or new_type == "Competition" or new_type == "Community"):
        return abort(410, description="Invalid tag type '{in_tag_type}'")
    if type_provided and (new_type == "Gecko Code" and (not gecko_code_desc_provided or not gecko_code_provided)):
        return abort(412, description="Type is gecko code but code details not provided")
    if type_provided and (new_type == "Gecko Code" and not validate_gecko_code(new_gecko_code)):
        return abort(415, description="Type is gecko code but code is not formatted correctly (<CODE> <CODE><\n>)")

    # Get Tag and Comm
    tag = Tag.query.filter_by(id=in_tag_id).first()
    if tag == None:
        return abort(409, description="No tag found with id={in_tag_id}")
    comm = Community.query.filter_by(id=tag.community_id).first()

    if type_provided and (((new_type == "Gecko Code" or new_type == "Client Code") and not comm.comm_type == 'Official')):
        return abort(416, description="Gecko codes must be added to official community")
    #Check that if gecko code is provided that new or existing type is gecko code
    if gecko_code_provided and (tag.type != 'Gecko Code' and (type_provided and new_type != 'Gecko Code')):
        return abort(417, description="Gecko codes can only be added to gecko code tags")
    if gecko_code_desc_provided and (tag.type != 'Gecko Code' and (type_provided and new_type != 'Gecko Code')):
        return abort(418, description="Gecko codes desc can only be added to gecko code tags")

    #Make sure user is admin of community or Rio admin
    user=None
    current_user_username = get_jwt_identity()
    if current_user_username:
        user = RioUser.query.filter_by(username=current_user_username).first()
    else:
        try:
            user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()
        except:
            return abort(410, description="No Rio Key or JWT Provided")

    if user == None:
        return abort(411, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    authorized_user = (comm_user != None and comm_user.admin) or is_user_in_groups(user.id, ['Admin'])
    if not authorized_user:
        return abort(412, description='User not a part of community or not an admin')
    
    #User is authorized
    #Begin evaluating actions
    if name_provided:
        #Make sure that tag does not use the same name as an existing tag, comm, or tag_set
        tag_check = Tag.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()
        comm_name_check = Community.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()
        tag_set_check = TagSet.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()

        if tag_check != None or comm_name_check != None or tag_set_check != None:
            return abort(413, description='Name already in use (Tag, TagSet, or Community)')
        
        tag.name = new_name
        tag.name_lowercase = lower_and_remove_nonalphanumeric(new_name)
    if desc_provided:
        tag.desc = new_desc
    if type_provided:
        #If tag was gecko code but is no longer
        if (tag.type == 'Gecko Code' and new_type != 'Gecko Code'):
            gecko_code = GeckoCodeTag.query.filter_by(tag_id=tag.id).first()
            if gecko_code == None:
                return abort(414, description='Could not find gecko code associated with gecko code tag')
            db.session.delete(gecko_code)
        #If tag is being upgraded to gecko code
        elif (tag.type != 'Gecko Code' and new_type == 'Gecko Code'):
            new_code_tag = GeckoCodeTag(in_tag_id=tag.id, in_gecko_code_desc=new_gecko_code_desc, in_gecko_code=gecko_code)
            db.session.add(new_code_tag)
        tag.type = new_type
    if gecko_code_provided:
        gecko_code = GeckoCodeTag.query.filter_by(tag_id=tag.id).first()
        gecko_code.gecko_code = new_gecko_code
    if gecko_code_desc_provided:
        gecko_code = GeckoCodeTag.query.filter_by(tag_id=tag.id).first()
        gecko_code.gecko_code_desc = new_gecko_code_desc

                
    db.session.add(tag)
    db.session.commit()
    return 200


@app.route('/tag/list', methods=['GET', 'POST'])
def tag_list():
    result = None
    client = False
    if request.method == "GET":
        result = Tag.query.filter(Tag.tag_type.in_(["Gecko Code", "Client Code", "Component"]))
    elif request.method == "POST":
        client = request.is_json and 'Client' in request.json and request.json['Client'].lower() in ['yes', 'y', 'true', 't']

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
        elif types_provided and communities_provided:
            result = Tag.query.join(Community, Tag.community_id == Community.id)\
                .filter((Community.id.in_(community_id_list)) & (Tag.tag_type.in_(types_list)))
        else:
            result = Tag.query.all()

    #IF CALLED BY CLIENT THE FOLLOWING COMMENT APPLIES
    #The return type of this function is a list of tag dicts. When called from the client, the tag dicts contain additional
    #fields from the GeckoCodeTag table even if the Tag does not have an associated GeckoCodeTag. In that case the two 
    # GeckoCodeTag values are empty strings. This is to make life easier for the client c++ code to parse
    tags = list()
    for tag in result:
        tag_dict = tag.to_dict()
        if (tag.tag_type == 'Gecko Code'):
            result = GeckoCodeTag.query.filter_by(tag_id=tag.id).first()
            if (result != None):
                tag_dict = tag_dict | result.to_dict()
        elif client:
            tag_dict = tag_dict | {"gecko_code_desc": "", "gecko_code": ""}
        tags.append(tag_dict)
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

    comm_name_lower = lower_and_remove_nonalphanumeric(in_tag_set_comm_name)
    comm = Community.query.filter_by(name_lowercase=comm_name_lower).first()

    if comm == None:
        return abort(409, description=f"No community found with name={in_tag_set_comm_name}")
    if comm.sponsor_id == None:
        return abort(410, description=f"Community is not sponsored")
    if in_tag_set_end_time < in_tag_set_start_time:
        return abort(412, description='Invalid start/end times')
    if in_tag_set_type not in cTAG_SET_TYPES.values():
        return abort(413, description='Invalid tag type')

    
    #Make sure that tag_set does not use the same name as a tag, comm, or other tag_set
    tag = Tag.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_set_name)).first()
    comm_name_check = Community.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_set_name)).first()
    tag_set = TagSet.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(in_tag_set_name)).first()

    if tag != None or comm_name_check != None or tag_set != None:
        return abort(414, description='Name already in use (Tag, TagSet, or Community)')

    # Make sure community is under the limit of active tag types
    current_unix_time = int( time.time() )

    query = (
        'SELECT \n'
        'MAX(community.active_tag_set_limit) AS tag_set_limit, \n'
        'COUNT(*) AS active_tag_sets \n'
        'FROM tag_set \n'
        'JOIN community ON community.id = tag_set.community_id \n'
       f'WHERE tag_set.end_date > {current_unix_time} \n'
        'GROUP BY tag_set.community_id \n'
    )
    results = db.session.execute(query).first()
    if results != None:
        result_dict = results._asdict()
        #Only unofficial comms have tag_set limits
        if comm.comm_type != 'Official' and (result_dict['active_tag_sets'] >= result_dict['tag_set_limit']):
            return abort(415, description='Community has reached active tag_set_limit')

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
            return abort(416, description="No Rio Key or JWT Provided")

    if user == None:
        return abort(417, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    if ((comm_user == None or comm_user.admin == False) and not is_user_in_groups(user.id, ['Admin'])):
        return abort(418, description='User not apart of community or not an admin')

    # Validate all tag ids, add to list
    tags = list()
    for id in in_tag_ids:
        tag = Tag.query.filter_by(id=id).first()
        if tag == None:
            return abort(419, f'Tag with ID={id} not found')
        if tag.tag_type == "Community" or tag.tag_type == "Competition":
            return abort(420, f'Tag with ID={id} not a valid type tag')
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
# TODO: Should this work without providing a rio key and get all tagsets?
@app.route('/tag_set/list', methods=['POST'])
def tagset_list():    
    current_unix_time = int( time.time() )
    client = request.is_json and 'Client' in request.json and request.json['Client'].lower() in ['yes', 'y', 'true', 't']
    active_only = request.is_json and 'Active' in request.json and request.json['Active'].lower() in ['yes', 'y', 'true', 't']
    communities_provided = request.is_json and 'Communities' in request.json
    community_id_list = request.json.get('Communities') if communities_provided else list()

    if (communities_provided and len(community_id_list) == 0):
        return abort(409, description="Communities key added to JSON but no community ids passed")
    pprint(request.json)
    tag_sets = None
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
    else:
        tag_sets = TagSet.query.all()
    
    #The rio key was bad or there are no tag sets to return
    if tag_sets is None or len(tag_sets) == 0:
        abort(409, "No/Invalid Rio Key provided or something else went wrong and no TagSets were created")

    tag_set_list = list()
    for tag_set in tag_sets:
        # Skip this tag set if current time is not within start/end time
        if (active_only and (current_unix_time < tag_set.start_date or current_unix_time > tag_set.end_date)):
            continue
        # Skip this tag set if community_id is not from a requested community
        if (communities_provided and tag_set.community_id not in community_id_list):
            continue

        if (rio_key_provided):
            user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()
            #If user is not in the Beta Tester group do not return Test TagSets
            if (tag_set.type == "Test" and not is_user_in_groups(user.id, ['Admin', 'Developer', 'BetaTester'])):
                continue

        #Determine if community, and therefore TagSet, is Official
        #TODO do this with SQLalchemy instead to eliminate extra query
        comm = Community.query.filter_by(id=tag_set.community_id).first()

        #IF CALLED BY CLIENT THE FOLLOWING COMMENT APPLIES
        #The return type of this function is a list of tag_set dicts. When called from the client, the tag dicts contain additional
        #fields from the GeckoCodeTag table even if the Tag does not have an associated GeckoCodeTag. In that case the two 
        # GeckoCodeTag values are empty strings. This is to make life easier for the client c++ code to parse
        tag_set_dict = tag_set.to_dict(False)
        tag_set_dict['comm_type'] = comm.comm_type
        tag_set_dict['tags'] = list()
        for tag in tag_set.tags:
            tag_dict = tag.to_dict()
            if (tag.tag_type == 'Gecko Code'):
                result = GeckoCodeTag.query.filter_by(tag_id=tag.id).first()
                if (result != None):
                    tag_dict["gecko_code_desc"] = result.to_dict()["gecko_code_desc"]
                    tag_dict["gecko_code"] = result.to_dict()["gecko_code"]
            elif client:
                tag_dict["gecko_code_desc"] = ""
                tag_dict["gecko_code"] = ""
            tag_set_dict['tags'].append(tag_dict)

        # Append passing tag set information
        tag_set_list.append(tag_set_dict)
    pprint(tag_set_list)
    return {"Tag Sets": tag_set_list}

@app.route('/tag_set/<tag_set_id>', methods=['GET'])
def tagset_get_tags(tag_set_id):
    result = TagSet.query.filter_by(id = tag_set_id).first()
    if result == None:
        return abort(409, description=f"Could not find TagSet with id={tag_set_id}")

    return {"Tag Set": [result.to_dict()]}


@app.route('/tag_set/update', methods=['POST'])
@jwt_required(optional=True)
def tag_set_update():
    in_tagset_id = request.json['tag_set_id'] #Required

    #Optional Args
    name_provided = request.is_json and 'name' in request.json
    new_name = request.json['name']
    desc_provided = request.is_json and 'desc' in request.json
    new_desc = request.json['desc']
    type_provided = request.is_json and 'type' in request.json
    new_type = request.json['type']
    start_time_provided = request.is_json and 'start_time' in request.json
    new_start_time = request.json['start_time']
    end_time_provided = request.is_json and 'end_time' in request.json
    new_end_time = request.json['end_time']
    tags_provided = request.is_json and 'tag_ids' in request.json
    new_tag_ids = request.json['tag_ids']

    if (start_time_provided and end_time_provided and new_start_time > new_end_time):
        return abort(412, description='Invalid start/end times')
    if type_provided and new_type not in cTAG_SET_TYPES.values():
        return abort(415, description='Invalid tag type')

    # Get Tag and Comm
    tag_set = TagSet.query.filter_by(id=in_tagset_id).first()
    if tag_set == None:
        return abort(409, description="No tag found with id={in_tag_id}")
    comm = Community.query.filter_by(id=tag_set.community_id).first()

    #Check dates against existing dates if needed
    if (start_time_provided and not end_time_provided and new_start_time > tag_set.end_date):
        return abort(413, description='Invalid start/end times')
    if (not start_time_provided and end_time_provided and tag_set.start_date > new_end_time):
        return abort(414, description='Invalid start/end times')

    #Make sure user is admin of community or Rio admin
    user=None
    current_user_username = get_jwt_identity()
    if current_user_username:
        user = RioUser.query.filter_by(username=current_user_username).first()
    else:
        try:
            user = RioUser.query.filter_by(rio_key=request.json['Rio Key']).first()
        except:
            return abort(410, description="No Rio Key or JWT Provided")

    if user == None:
        return abort(411, description='Username associated with JWT not found.')
    
    #If community tag, make sure user is an admin of the community
    comm_user = CommunityUser.query.filter_by(user_id=user.id, community_id=comm.id).first()

    authorized_user = (comm_user != None and comm_user.admin) or is_user_in_groups(user.id, ['Admin'])
    if not authorized_user:
        return abort(412, description='User not a part of community or not an admin')
    
    #User is authorized
    #Begin evaluating actions
    if name_provided:
        #Make sure that tag does not use the same name as an existing tag, comm, or tag_set
        tag_check = Tag.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()
        comm_name_check = Community.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()
        tag_set_check = TagSet.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(new_name)).first()

        if tag_check != None or comm_name_check != None or tag_set_check != None:
            return abort(413, description='Name already in use (Tag, TagSet, or Community)')
        
        #Get TagSet tag
        tag = Tag.query.filter_by(name_lowercase=tag_set.name_lowercase).first()
        if tag == None:
            return abort(414, description='Could not find tag to rename')
        
        tag.name = new_name
        tag.name_lowercase = lower_and_remove_nonalphanumeric(new_name)
        db.session.add(tag)
        db.session.commit()
        
        tag_set.name = new_name
        tag_set.name_lowercase = lower_and_remove_nonalphanumeric(new_name)
    if desc_provided:
        tag_set.desc = new_desc
    if type_provided:
        tag_set.type = new_type
    if start_time_provided:
        tag_set.start_date = new_start_time
    if end_time_provided:
        tag_set.end_date = new_end_time
    if tags_provided:
        # Validate all tag ids, add to list
        tags = list()
        for id in new_tag_ids:
            tag = Tag.query.filter_by(id=id).first()
            if tag == None:
                return abort(419, f'Tag with ID={id} not found')
            if tag.tag_type == "Community" or tag.tag_type == "Competition":
                return abort(420, f'Tag with ID={id} not a valid type tag')
            tags.append(tag)
        tag_set.tags = tags

    db.session.add(tag_set)
    db.session.commit()
    return 200  


# @app.route('/tag_set/ladder', methods=['POST'])
# @jwt_required(optional=True)
# def community_sponsor():
#     pass
    
@app.route('/tag_set/ladder/', methods=['POST'])
@jwt_required(optional=True)
def get_ladder(in_tag_set=None):
    tag_set_name =  in_tag_set if in_tag_set != None else request.json['TagSet']
    tag_set = TagSet.query.filter_by(name_lowercase=lower_and_remove_nonalphanumeric(tag_set_name)).first()
    if tag_set == None:
        return abort(409, description=f"Could not find TagSet with name={tag_set_name}")

    query = (
        'SELECT \n'
        'ladder.rating, \n'
        'rio_user.id, \n'
        'rio_user.username \n'
        'FROM ladder \n'
        'JOIN community_user on community_user.id = ladder.community_user_id \n'
        'JOIN rio_user on rio_user.id = community_user.user_id \n'
       f"WHERE ladder.tag_set_id = {tag_set.id}"
    )

    results = db.session.execute(query).all()
    ladder_results = dict()
    for result_row in results:
        result_dict = result_row._asdict()
        ladder_results[result_dict['username']] = result_row._asdict()
    return jsonify(ladder_results)