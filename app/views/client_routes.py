from flask import request, abort
from flask import current_app as app
from ..models import db, RioUser, Tag, GameTag

# Evaluate users provided to Client
# example: /validate_user_from_client/?username=demouser1&rio_key=_______
@app.route('/validate_user_from_client/', methods=['GET'])
def validate_user_from_client():
    in_username = request.args.get('username')
    in_username_lower = in_username.lower()
    in_rio_key = request.args.get('rio_key')

    user = RioUser.query.filter_by(username_lowercase = in_username_lower, rio_key = in_rio_key).first()

    if user is None:
        abort(404, 'Invalid UserID or RioKey')

    return {'msg': 'success'}


@app.route('/get_available_tags/<username>/', methods=['GET'])
def get_available_tags(username):
    in_username_lower = username.lower()

    query = (
        'SELECT '
        'tag.name AS name '
        'FROM tag '
        'WHERE tag.community_id IS NULL'
    )

    tags = db.session.execute(query).all()

    available_tags = []
    for tag in tags:
        available_tags.append(tag.name)

    return { 'available_tags': available_tags }


