'''Read endpoints for the per-season advanced percentiles, plus an admin
endpoint to force a recompute.

Public reads are unauthenticated, matching /characters/ and /stats/. The bot
calls these with no API key today, and these carry no more information than the
existing stat endpoints already expose.
'''
import os
import time

from flask import request, jsonify, abort
from flask import current_app as app

from ..models import db, RioUser, TagSet, SeasonMetric
from ..util import *
from ..season_metrics import cSEASON_METRICS, cMETRIC_RULES
from ..season_metrics_db import refresh_one_season, refresh_stale_seasons, season_ids


def _resolve_tag_set(season_arg):
    '''Find the tag set for a season name, or the one currently running.

    tag_set.name_lowercase strips punctuation, so 'S15 Superstars Off' and
    's15superstarsoff' both resolve. Without an argument this returns the
    season whose start/end dates bracket now, newest first.
    '''
    if season_arg:
        normalized = lower_and_remove_nonalphanumeric(season_arg)
        tag_set = db.session.query(TagSet).filter(
            TagSet.name_lowercase == normalized).one_or_none()
        if tag_set is None:
            abort(400, 'Unknown season "{}"'.format(season_arg))
        return tag_set

    now = int(time.time())
    return db.session.query(TagSet).filter(
        TagSet.id.in_(season_ids()),
        TagSet.start_date <= now,
        TagSet.end_date >= now,
    ).order_by(TagSet.start_date.desc()).first()


@app.route('/season_stats/', methods=['GET'])
def endpoint_season_stats():
    '''One player's metrics for one season.

    Query args:
      user    required, username (case insensitive)
      season  optional, defaults to the season running now

    A metric present with qualified=false means the player was measured and
    missed the floor. A metric absent from the response has not been computed.

    Each qualified metric carries pool_size, the number of players its
    percentile was ranked over. It differs per metric, since the
    character-restricted metrics carry their own extra floor and far fewer
    players clear them. A percentile does not mean anything without it.
    '''
    username = request.args.get('user')
    if not username:
        abort(400, 'user is required')

    rio_user = db.session.query(RioUser).filter(
        RioUser.username_lowercase == username.lower()).one_or_none()
    if rio_user is None:
        abort(400, 'Unknown user "{}"'.format(username))

    tag_set = _resolve_tag_set(request.args.get('season'))
    if tag_set is None:
        abort(400, 'No season is currently running; pass season=')

    rows = db.session.query(SeasonMetric).filter(
        SeasonMetric.tag_set_id == tag_set.id,
        SeasonMetric.user_id == rio_user.id,
    ).all()

    metrics = {row.metric: row.to_dict() for row in rows}
    return jsonify({
        'user': rio_user.username,
        'season': tag_set.name,
        'tag_set_id': tag_set.id,
        'computed_at': max([r.computed_at for r in rows], default=None),
        'qualified_metrics': sum(1 for r in rows if r.qualified),
        'metrics': metrics,
    })


@app.route('/season_stats/leaderboard/', methods=['GET'])
def endpoint_season_leaderboard():
    '''Top players for one metric in one season, best first.

    Query args:
      metric  required, one of the keys in cSEASON_METRICS
      season  optional, defaults to the season running now
      limit   optional, capped at 100. Omit for the whole board.

    The board is not truncated by default. Qualification requires ten games in
    the season, so the pool is bounded by the number of active players rather
    than by games or events, which is a few dozen rows.

    qualified_players is the pool the percentiles were ranked over, which is
    NOT the same as the number of rows returned once a limit is passed.
    '''
    metric = request.args.get('metric')
    if metric not in cSEASON_METRICS:
        abort(400, 'metric must be one of: {}'.format(', '.join(cSEASON_METRICS)))

    tag_set = _resolve_tag_set(request.args.get('season'))
    if tag_set is None:
        abort(400, 'No season is currently running; pass season=')

    limit = None
    if request.args.get('limit') is not None:
        try:
            limit = int(request.args.get('limit'))
        except ValueError:
            abort(400, 'limit must be a number')
        if limit < 1:
            abort(400, 'limit must be at least 1')
        limit = min(limit, 100)

    # Ties share a percentile by design, so username breaks them to keep the
    # ordering, and therefore rank, stable between identical calls.
    query = db.session.query(SeasonMetric, RioUser.username).join(
        RioUser, RioUser.id == SeasonMetric.user_id
    ).filter(
        SeasonMetric.tag_set_id == tag_set.id,
        SeasonMetric.metric == metric,
        SeasonMetric.qualified.is_(True),
    ).order_by(SeasonMetric.percentile.desc(), RioUser.username.asc())
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()

    higher_is_better = cMETRIC_RULES[metric][0]
    return jsonify({
        'season': tag_set.name,
        'tag_set_id': tag_set.id,
        'metric': metric,
        'higher_is_better': higher_is_better,
        # The pool the percentiles were ranked over. Identical on every
        # qualified row for this season and metric, so the first row carries
        # it. Counting the returned rows here would report the page size.
        'qualified_players': rows[0][0].pool_size if rows else 0,
        'returned': len(rows),
        'leaderboard': [dict(row.to_dict(), username=username, rank=i + 1)
                        for i, (row, username) in enumerate(rows)],
    })


@app.route('/season_stats/refresh/', methods=['POST'])
def endpoint_season_stats_refresh():
    '''Force a recompute. Used for the initial backfill and after a game move.

    Body:
      ADMIN_KEY   required
      tag_set_id  optional, a single season. Omit to refresh every season with
                  games newer than its last computation.

    A game moved between tag sets does not change its date_created, so the
    scheduled job will not notice it. This endpoint is how you fix that.
    '''
    body = request.json or {}
    if os.getenv('ADMIN_KEY') != body.get('ADMIN_KEY'):
        return abort(403, 'Invalid admin key')

    tag_set_id = body.get('tag_set_id')
    try:
        if tag_set_id is not None:
            # Locked like the scheduled path: a backfill through this endpoint
            # and the 04:00 job can otherwise upsert the same season at once.
            rows = refresh_one_season(int(tag_set_id))
            written = None if rows is None else {tag_set_id: rows}
        else:
            written = refresh_stale_seasons()
    except Exception as e:
        db.session.rollback()
        app.logger.exception('season metric refresh failed')
        return abort(500, 'Refresh failed: {}'.format(e))

    if written is None:
        return jsonify({
            'skipped': True,
            'reason': 'another refresh is already running',
            'seasons_refreshed': 0,
            'rows_written': {},
        })

    return jsonify({
        'skipped': False,
        'seasons_refreshed': len(written),
        'rows_written': written,
    })
