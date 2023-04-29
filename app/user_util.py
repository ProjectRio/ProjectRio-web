from .models import db, RioUser, ApiKey, CommunityUser
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies

def get_user(request):
  #Rio Key or Community Key
  rio_key_provided = request.is_json and (('Rio Key' in request.json) or ('rio_key' in request.json))
  if rio_key_provided:
    try:
      rio_key = request.json['Rio Key']
    except:
      rio_key = request.json['rio_key']
    #Check for community key or rio key based on length. TODO figure out if its worth having the client
    #distinguish between the 2 (leaning towards no)
    if len(rio_key) == 4: #Community Key 
      user = db.session.query(
          RioUser
      ).join(
          CommunityUser
      ).filter(
          CommunityUser.community_key == rio_key
      ).first()
    else: #Rio Key
      user = RioUser.query.filter_by(rio_key=rio_key).first()
    return user
  
  community_key_provided = request.is_json and ('community_key' in request.json)
  if community_key_provided:
    comm_key = request.json['community_key']
    user = db.session.query(
        RioUser
    ).join(
        CommunityUser
    ).filter(
        CommunityUser.community_key == comm_key
    ).first()
    return user
  
  #API Key
  api_key_provided = request.is_json and 'api_key' in request.json
  if api_key_provided:
    api_key = request.json['api_key']
    user = db.session.query(
        ApiKey
    ).join(
        RioUser
    ).filter(
        ApiKey.api_key == api_key
    ).first()
    return user
  
  #JWT
  current_user_username = get_jwt_identity()
  if current_user_username:
    user = RioUser.query.filter_by(username=current_user_username).first()
    return user
  
  # Return
  return None

def get_user_via_rio_or_comm_key(key):
    user = None
    if len(key) == 4: #Community Key 
        user = db.session.query(
            RioUser
        ).join(
            CommunityUser
        ).filter(
            CommunityUser.community_key == key
        ).first()
    else: #Rio Key
        user = RioUser.query.filter_by(rio_key=key).first()
    return user