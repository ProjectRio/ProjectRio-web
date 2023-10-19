from .models import db, RioUser, ApiKey, CommunityUser, UserIpAddress
import time
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies

def get_user(request):
  #Rio Key or Community Key
  rio_key = None

  # Check if "Rio Key" or "rio_key" is provided in JSON data
  if request.is_json:
      rio_key = request.json.get("Rio Key", request.json.get("rio_key"))

  # If not found in JSON data, check URL arguments
  if rio_key is None:
      rio_key = request.args.get("rio_key")

  if rio_key is not None:
    # Handle the case where rio_key is not provided
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

def update_ip_address_entry(rio_user, request):
    # Get the user's public IP address from the request
    user_ip_address = get_client_ip(request)

    # Query the database to find an entry for this user and IP address
    user_ip_entry = UserIpAddress.query.filter_by(user_id=rio_user.id, ip_address=user_ip_address).first()

    if user_ip_entry != None:
        # If the entry exists, update use_count and last_use_date
        user_ip_entry.use_count += 1
        user_ip_entry.last_use_date = int(time.time())
    else:
        # If the entry doesn't exist, create a new entry
        new_entry = UserIpAddress(user_id=rio_user.id, ip_address=user_ip_address)
        db.session.add(new_entry)
    
    # Commit changes to the database
    db.session.commit()
    return

def get_client_ip(request):
    # Check the X-Forwarded-For (XFF) header for the client's IP address
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # If the XFF header is present, it may contain a list of IP addresses; take the first one
        client_ips = x_forwarded_for.split(',')
        return client_ips[0].strip()
    # If the XFF header is not present, use the remote_addr
    return request.remote_addr