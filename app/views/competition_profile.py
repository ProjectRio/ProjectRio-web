'''competition_profile endpoints: read every competition's profile, and let an
admin change one (rules in app/competition_profile.py).

Changing a competition rebuilds the RE24 table straight away from the stored
per-game rows, so a re-sorted competition shows up in RE24 without waiting for
the night.
'''
import time

from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required

from ..models import db, CompetitionProfile
from ..decorators import api_key_check
from ..user_util import get_user
from ..competition_profile import cCATEGORIES, cFLAGS, cSTATUSES, cTYPES
from ..re24_db import rebuild_re24_locked

cNOTE_LENGTH = 500


@app.route('/competition_profile/', methods=['GET'])
def endpoint_competition_profile():
    '''Every competition's profile.

    Query args (all optional):
      status    pending, auto or reviewed
      category  stars off, stars on, big balla, hazards or other
    '''
    query = db.session.query(CompetitionProfile)
    status = request.args.get('status')
    if status is not None:
        if status not in cSTATUSES:
            abort(400, 'status must be one of: {}'.format(', '.join(cSTATUSES)))
        query = query.filter(CompetitionProfile.status == status)
    category = request.args.get('category')
    if category is not None:
        category = category.strip().lower()
        if category not in cCATEGORIES:
            abort(400, 'category must be one of: {}'.format(', '.join(cCATEGORIES)))
        query = query.filter(CompetitionProfile.category == category)
    rows = query.order_by(CompetitionProfile.tag_set_id).all()
    return jsonify({'competitions': [row.to_dict() for row in rows]})


@app.route('/competition_profile/update/', methods=['POST'])
@jwt_required(optional=True)
@api_key_check(['Admin'])
def endpoint_competition_profile_update():
    '''Change one competition's profile (admins only).

    JSON body:
      tag_set_id  required
      category, type, q_ranked, q_league_stats, q_player_stats,
      q_character_stats, q_pick_rates, note   any of these
      status      optional; an admin's change marks the row 'reviewed' unless
                  another status is given

    Returns the updated row, and whether the RE24 table was rebuilt.
    '''
    body = request.get_json(silent=True) or {}
    try:
        tag_set_id = int(body.get('tag_set_id'))
    except (TypeError, ValueError):
        abort(400, 'tag_set_id is required')
    profile = db.session.get(CompetitionProfile, tag_set_id)
    if profile is None:
        abort(404, 'No competition_profile row for tag_set_id {}'.format(tag_set_id))

    changes = {}
    if 'category' in body:
        category = str(body['category']).strip().lower()
        if category not in cCATEGORIES:
            abort(400, 'category must be one of: {}'.format(', '.join(cCATEGORIES)))
        changes['category'] = category
    if 'type' in body:
        kind = str(body['type']).strip().capitalize()
        if kind not in cTYPES:
            abort(400, 'type must be one of: {}'.format(', '.join(cTYPES)))
        changes['type'] = kind
    for flag in cFLAGS:
        if flag in body:
            if not isinstance(body[flag], bool):
                abort(400, '{} must be true or false'.format(flag))
            changes[flag] = body[flag]
    if 'note' in body:
        note = body['note']
        if note is not None and (not isinstance(note, str) or len(note) > cNOTE_LENGTH):
            abort(400, 'note must be text of at most {} characters'.format(cNOTE_LENGTH))
        changes['note'] = note or None
    status = body.get('status', 'reviewed')
    if status not in cSTATUSES:
        abort(400, 'status must be one of: {}'.format(', '.join(cSTATUSES)))
    changes['status'] = status
    if len(changes) == 1 and 'status' not in body:
        abort(400, 'Nothing to change')

    for key, value in changes.items():
        setattr(profile, key, value)
    profile.updated_at = int(time.time())
    user = get_user(request)
    profile.updated_by = user.id if user is not None else None
    db.session.commit()

    rebuilt = rebuild_re24_locked()
    return jsonify({'competition': profile.to_dict(), 're24_rebuilt': rebuilt is not None})
