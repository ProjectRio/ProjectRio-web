from flask import request, abort
from flask import current_app as app
from ..models import db, RioUser, CommunityUser
from ..util import *

# Evaluate users provided to Client
# example: /validate_user_from_client/?username=demouser1&rio_key=_______
@app.route('/validate_user_from_client/', methods=['GET'])
def validate_user_from_client():
    in_username = request.args.get('username')
    in_username_lower = lower_and_remove_nonalphanumeric(in_username)
    in_rio_key = request.args.get('rio_key')

    user = None
    if (len(in_rio_key) == 4): # Community Key
        user = db.session.query(
            RioUser
        ).join(
            CommunityUser
        ).filter(
            CommunityUser.community_key == in_rio_key
        ).first()
    else: # Full Rio Key
        user = RioUser.query.filter_by(rio_key=in_rio_key).first()

    if user is None:
        abort(404, 'Invalid UserID or RioKey')

    return {'msg': 'success'}
