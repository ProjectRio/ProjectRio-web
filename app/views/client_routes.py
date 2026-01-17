from flask import request, abort
from flask import current_app as app
from ..models import db, RioUser, CommunityUser
from ..util import *
from app.views.user_groups import *
from ..decorators import *

# Evaluate users provided to Client
# example: /validate_user_from_client/?username=demouser1&rio_key=_______
@app.route('/validate_user_from_client/', methods=['GET'])
@record_ip_address
def validate_user_from_client():
    in_username = request.args.get('username')
    in_username_lower = lower_and_remove_nonalphanumeric(in_username)
    in_rio_key = request.args.get('rio_key')

    print('validate_user_from_client')

    user = None
    if (len(in_rio_key) == 4): # Community Key
        user = db.session.query(
            RioUser
        ).join(
            CommunityUser
        ).filter(
            (CommunityUser.community_key == in_rio_key)
            & (RioUser.username_lowercase == in_username_lower)
        ).first()
    else: # Full Rio Key
        user = RioUser.query.filter_by(rio_key=in_rio_key, username_lowercase=in_username_lower).first()

    if user is None:
        return abort(404, description='Invalid UserID or RioKey')

    if is_user_in_groups(user.id, ['Banned']):
        return abort(405, description='User is banned')

    return {'msg': 'success'}
