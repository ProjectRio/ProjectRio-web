'''RE24 endpoints: the public table, and an admin endpoint that runs the job now.

RE24 = average runs scored from each base-out state to the end of the
half-inning, per game type (method in app/re24.py). The table changes once a
night, so responses carry a one-hour cache header.
'''
from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required

from .. import sched
from ..models import db, Re24
from ..decorators import api_key_check
from ..re24 import cGAME_TYPES
from ..re24_db import refresh_re24_job

cCACHE_SECONDS = 60 * 60


@app.route('/re24/', methods=['GET'])
def endpoint_re24():
    '''The RE24 table.

    Query args:
      gametype  optional: stars off, stars on, big balla or hazards (all four if absent)

    Each row: gametype, outs (0-2), runners (0-7: 1st = 1, 2nd = 2, 3rd = 4,
    added together), xruns (4 decimals; show 2) and pitches, the sample behind
    xruns.
    '''
    query = db.session.query(Re24)
    game_type = request.args.get('gametype')
    if game_type is not None:
        game_type = game_type.strip().lower()
        if game_type not in cGAME_TYPES:
            abort(400, 'gametype must be one of: {}'.format(', '.join(cGAME_TYPES)))
        query = query.filter(Re24.gametype == game_type)
    rows = query.all()
    order = {name: i for i, name in enumerate(cGAME_TYPES)}
    rows.sort(key=lambda r: (order[r.gametype], r.outs, r.runners))

    response = jsonify({
        're24': [row.to_dict() for row in rows],
        'computed_at': max((row.computed_at for row in rows), default=None),
    })
    response.headers['Cache-Control'] = 'public, max-age={}'.format(cCACHE_SECONDS)
    return response


@app.route('/re24/refresh/', methods=['POST'])
@jwt_required(optional=True)
@api_key_check(['Admin'])
def endpoint_re24_refresh():
    '''Run the nightly RE24 job now (admins only), e.g. for the first fill after
    deploying. The job reads every game the first time, which takes minutes, so
    it is queued on the scheduler and this returns at once; the log reports the
    result. A run already in progress makes the queued one a no-op.'''
    sched.add_job(refresh_re24_job, args=[app._get_current_object()],
                  id='re24_refresh_now', replace_existing=True)
    return jsonify({'queued': True}), 202
