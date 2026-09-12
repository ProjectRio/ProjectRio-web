'''Database access for the per-season advanced percentiles.

Companion to season_metrics.py, which holds the definitions and the pure
computation. The split is deliberate: that module imports only `math` and can
be unit tested directly, while everything that touches the database lives here.

The per-season aggregate is ONE statement. The production database caps
max_connections at 25 and managed-platform agents hold a large share of that,
so a refresh must open one connection, make one pass over the season's events,
and close. A statement per metric is not an option at that ceiling.
'''
import time
from contextlib import contextmanager

from flask import current_app
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import db, SeasonMetric
from .season_metrics import (
    cCHARGE_TIMING_CHARS,
    cPOWER_CHARS,
    build_rows,
)


# Advisory lock key. The scheduler runs in a single process today, so the job
# cannot double-fire on its own, but a real WSGI server with multiple workers
# would start one scheduler per worker -- and the refresh endpoint already
# gives a second caller running in a web worker against the same pool.
cLOCK_KEY = 8151723

# S9 Superstars Off is typed 'League' rather than 'Season', so it cannot be
# found by the discovery rule below. It is the only main-line season that
# needs naming explicitly.
cSEASON_ID_EXCEPTIONS = (74,)

# Main-line Stars Off seasons, discoverable without a maintained list.
# tag_set.name_lowercase strips punctuation, so matching names that END in
# 'superstarsoff' excludes the Hazards / Mega / Randoms variants without
# naming them, and type='Season' excludes tournaments in the same window.
cSEASON_DISCOVERY_SQL = text('''
    SELECT id
    FROM tag_set
    WHERE (
            type = 'Season'
            AND (name_lowercase LIKE '%%superstarsoff'
                 OR name_lowercase LIKE 'starsoffseason%%')
            AND name_lowercase NOT LIKE 'practice%%'
          )
       OR id = ANY(:exceptions)
''')

# Order of the numerator/denominator pairs returned by cAGGREGATE_SQL for each
# role. Position is the contract between the SQL and Python -- keep in step.
cBATTING_ORDER = (
    'bat_barrel_pct',
    'bat_chase_pct',
    'bat_whiff_pct',
    'bat_ozone_contact_pct',
    'bat_k_pct',
    'bat_charge_timing_pct',
    'bat_slap_timing_pct',
    'bat_charge_down_input_pct',
)
cPITCHING_ORDER = (
    'pitch_barrels_allowed_pct',
    'pitch_whiff_pct',
    'pitch_k_pct',
    'pitch_hr_allowed_pct',
)

# One pass over the season's events, producing every numerator and denominator
# for both roles. Batting fills all eight pairs; pitching fills four and pads
# the rest with NULL so the two halves can be UNIONed.
#
# Enum values: result_of_ab 1 strikeout / 2 walk / 3 HBP / 10 HR (1-16 is the
# decodable range, so "not none" is `BETWEEN 1 AND 16`). type_of_swing 1 slap,
# 2 charge. type_of_contact 1/2/3 are the barrel values out of 0-4.
# input_direction_stick 4/5/6 are down, down-left, down-right.
cAGGREGATE_SQL = text('''
WITH sg AS (
    SELECT DISTINCT gh.game_id
    FROM game_history gh
    WHERE gh.tag_set_id = :tag_set_id
      AND gh.game_id IS NOT NULL
),
ev AS MATERIALIZED (
    SELECT
        CASE WHEN e.half_inning = 0 THEN g.away_player_id ELSE g.home_player_id END AS batter_user,
        CASE WHEN e.half_inning = 0 THEN g.home_player_id ELSE g.away_player_id END AS pitcher_user,
        ch.name_lowercase AS batter_char,
        e.result_of_ab,
        ps.type_of_swing,
        ps.in_strikezone,
        ps.contact_summary_id,
        cs.type_of_contact,
        cs.frame_of_swing_upon_contact AS frame,
        cs.input_direction_stick AS stick
    FROM sg
    JOIN game g ON g.game_id = sg.game_id
    JOIN event e ON e.game_id = sg.game_id
    LEFT JOIN pitch_summary ps ON ps.id = e.pitch_summary_id
    LEFT JOIN contact_summary cs ON cs.id = ps.contact_summary_id
    LEFT JOIN character_game_summary bcgs ON bcgs.id = e.batter_id
    LEFT JOIN character ch ON ch.char_id = bcgs.char_id
)
SELECT 'bat' AS role, batter_user AS user_id,
    COUNT(*) FILTER (WHERE contact_summary_id IS NOT NULL AND type_of_contact IN (1,2,3))            AS n1,
    COUNT(*) FILTER (WHERE contact_summary_id IS NOT NULL AND type_of_contact IN (0,1,2,3,4))        AS d1,
    COUNT(*) FILTER (WHERE in_strikezone IS FALSE AND type_of_swing IS NOT NULL AND type_of_swing <> 0) AS n2,
    COUNT(*) FILTER (WHERE in_strikezone IS FALSE)                                                   AS d2,
    COUNT(*) FILTER (WHERE type_of_swing IS NOT NULL AND type_of_swing <> 0 AND contact_summary_id IS NULL) AS n3,
    COUNT(*) FILTER (WHERE type_of_swing IS NOT NULL AND type_of_swing <> 0)                         AS d3,
    COUNT(*) FILTER (WHERE in_strikezone IS FALSE AND type_of_swing IS NOT NULL AND type_of_swing <> 0
                       AND contact_summary_id IS NOT NULL)                                           AS n4,
    COUNT(*) FILTER (WHERE in_strikezone IS FALSE AND type_of_swing IS NOT NULL AND type_of_swing <> 0) AS d4,
    COUNT(*) FILTER (WHERE result_of_ab = 1)                                                         AS n5,
    COUNT(*) FILTER (WHERE result_of_ab BETWEEN 1 AND 16)                                            AS d5,
    COUNT(*) FILTER (WHERE type_of_swing = 2 AND batter_char = ANY(:charge_chars)
                       AND frame IN (7,8,9))                                                         AS n6,
    COUNT(*) FILTER (WHERE type_of_swing = 2 AND batter_char = ANY(:charge_chars)
                       AND frame BETWEEN 2 AND 10)                                                   AS d6,
    COUNT(*) FILTER (WHERE type_of_swing = 1 AND frame IN (3,4,5))                                   AS n7,
    COUNT(*) FILTER (WHERE type_of_swing = 1 AND frame BETWEEN 2 AND 10)                             AS d7,
    COUNT(*) FILTER (WHERE type_of_swing = 2 AND contact_summary_id IS NOT NULL
                       AND batter_char = ANY(:power_chars) AND stick IN (4,5,6))                     AS n8,
    COUNT(*) FILTER (WHERE type_of_swing = 2 AND contact_summary_id IS NOT NULL
                       AND batter_char = ANY(:power_chars))                                          AS d8
FROM ev
WHERE batter_user IS NOT NULL
GROUP BY batter_user

UNION ALL

SELECT 'pitch', pitcher_user,
    COUNT(*) FILTER (WHERE contact_summary_id IS NOT NULL AND type_of_contact IN (1,2,3))            AS n1,
    COUNT(*) FILTER (WHERE contact_summary_id IS NOT NULL AND type_of_contact IN (0,1,2,3,4))        AS d1,
    COUNT(*) FILTER (WHERE type_of_swing IS NOT NULL AND type_of_swing <> 0 AND contact_summary_id IS NULL) AS n2,
    COUNT(*) FILTER (WHERE type_of_swing IS NOT NULL AND type_of_swing <> 0)                         AS d2,
    COUNT(*) FILTER (WHERE result_of_ab = 1)                                                         AS n3,
    COUNT(*) FILTER (WHERE result_of_ab BETWEEN 1 AND 16)                                            AS d3,
    COUNT(*) FILTER (WHERE result_of_ab = 10 AND batter_char = ANY(:power_chars))                    AS n4,
    COUNT(*) FILTER (WHERE result_of_ab BETWEEN 1 AND 16 AND result_of_ab NOT IN (2,3)
                       AND batter_char = ANY(:power_chars))                                          AS d4,
    NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM ev
WHERE pitcher_user IS NOT NULL
GROUP BY pitcher_user
''')

# Distinct games each player appeared in, for the shared 10-game floor and for
# the gen_games_played metric. Note this is NOT the same count the ELO formula
# uses: a player can appear in a game that has no rated game_history row.
cGAMES_SQL = text('''
WITH sg AS (
    SELECT DISTINCT gh.game_id
    FROM game_history gh
    WHERE gh.tag_set_id = :tag_set_id
      AND gh.game_id IS NOT NULL
)
SELECT x.user_id, COUNT(DISTINCT x.game_id) AS games
FROM (
    SELECT sg.game_id, g.away_player_id AS user_id FROM sg JOIN game g ON g.game_id = sg.game_id
    UNION ALL
    SELECT sg.game_id, g.home_player_id            FROM sg JOIN game g ON g.game_id = sg.game_id
) x
WHERE x.user_id IS NOT NULL
GROUP BY x.user_id
''')

# Inputs for the adjusted ELO formula. Rating is the result ELO on the most
# recent rated game of the season; wins and games come from that same sequence.
cELO_SQL = text('''
WITH pl AS (
    SELECT gh.id,
           gh.date_created,
           cu.user_id,
           (gh.winner_comm_user_id = cu.id) AS won,
           CASE WHEN gh.winner_comm_user_id = cu.id
                THEN gh.winner_result_elo ELSE gh.loser_result_elo END AS result_elo
    FROM game_history gh
    JOIN community_user cu
      ON cu.id IN (gh.winner_comm_user_id, gh.loser_comm_user_id)
    WHERE gh.tag_set_id = :tag_set_id
),
agg AS (
    SELECT user_id, COUNT(*) AS games, COUNT(*) FILTER (WHERE won) AS wins
    FROM pl GROUP BY user_id
),
latest AS (
    SELECT DISTINCT ON (user_id) user_id, result_elo
    FROM pl ORDER BY user_id, date_created DESC, id DESC
)
SELECT a.user_id, a.wins, a.games, l.result_elo
FROM agg a JOIN latest l ON l.user_id = a.user_id
''')

# Seasons with a rated game newer than the last time we computed them, plus
# seasons never computed at all.
cSTALE_SQL = text('''
SELECT ts.id
FROM tag_set ts
WHERE ts.id = ANY(:season_ids)
  AND EXISTS (SELECT 1 FROM game_history gh WHERE gh.tag_set_id = ts.id)
  AND COALESCE(
        (SELECT MAX(gh.date_created) FROM game_history gh WHERE gh.tag_set_id = ts.id), 0
      ) > COALESCE(
        (SELECT MAX(sm.computed_at) FROM season_metric sm WHERE sm.tag_set_id = ts.id), -1
      )
''')


def season_ids():
    '''Every main-line Stars Off season, newest first.'''
    rows = db.session.execute(
        cSEASON_DISCOVERY_SQL, {'exceptions': list(cSEASON_ID_EXCEPTIONS)}).fetchall()
    return [r[0] for r in rows]


def stale_season_ids():
    '''Seasons with games added since their last computation.'''
    ids = season_ids()
    if not ids:
        return []
    rows = db.session.execute(cSTALE_SQL, {'season_ids': ids}).fetchall()
    return [r[0] for r in rows]


def collect(tag_set_id):
    '''Gather everything build_rows() needs for one season, in three queries.'''
    per_user = {}

    def record(user_id):
        if user_id not in per_user:
            per_user[user_id] = {'games': 0, 'elo_rating': None, 'elo_wins': 0,
                                 'elo_games': 0, 'counts': {}}
        return per_user[user_id]

    for user_id, games in db.session.execute(cGAMES_SQL, {'tag_set_id': tag_set_id}):
        record(user_id)['games'] = games

    for user_id, wins, games, rating in db.session.execute(cELO_SQL, {'tag_set_id': tag_set_id}):
        rec = record(user_id)
        rec['elo_wins'] = wins
        rec['elo_games'] = games
        rec['elo_rating'] = rating

    params = {
        'tag_set_id': tag_set_id,
        'charge_chars': list(cCHARGE_TIMING_CHARS),
        'power_chars': list(cPOWER_CHARS),
    }
    for row in db.session.execute(cAGGREGATE_SQL, params):
        role, user_id = row[0], row[1]
        order = cBATTING_ORDER if role == 'bat' else cPITCHING_ORDER
        counts = record(user_id)['counts']
        for i, metric in enumerate(order):
            counts[metric] = (row[2 + i * 2], row[3 + i * 2])

    return per_user


def refresh_season(tag_set_id):
    '''Recompute one season and upsert it. Returns the number of rows written.'''
    rows = build_rows(collect(tag_set_id))
    if not rows:
        return 0

    now = int(time.time())
    payload = [{
        'tag_set_id': tag_set_id,
        'user_id': r['user_id'],
        'metric': r['metric'],
        'value': r['value'],
        'percentile': r['percentile'],
        'pool_size': r['pool_size'],
        'numerator': r['numerator'],
        'denominator': r['denominator'],
        'qualified': r['qualified'],
        'computed_at': now,
    } for r in rows]

    table = SeasonMetric.__table__
    # Chunked so a big season does not build one enormous statement.
    for start in range(0, len(payload), 1000):
        chunk = payload[start:start + 1000]
        stmt = pg_insert(table).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=['tag_set_id', 'user_id', 'metric'],
            set_={
                'value': stmt.excluded.value,
                'percentile': stmt.excluded.percentile,
                'pool_size': stmt.excluded.pool_size,
                'numerator': stmt.excluded.numerator,
                'denominator': stmt.excluded.denominator,
                'qualified': stmt.excluded.qualified,
                'computed_at': stmt.excluded.computed_at,
            },
        )
        db.session.execute(stmt)

    db.session.commit()
    return len(payload)


@contextmanager
def advisory_lock():
    """Hold the refresh lock on a connection of its own for the whole block.

    Yields True when the lock was taken, False when another refresh holds it.

    The connection matters. A Postgres advisory lock belongs to the backend
    session that took it, and db.session hands its connection back to the pool
    on every commit -- refresh_season() commits once per season. Taking the
    lock on db.session would therefore release it after the first season, leave
    the rest running unlocked, and then attempt the unlock from whatever
    connection had since been checked out. That unlock is a no-op, so the lock
    would ride back into the pool still held, and every later run would find it
    taken and silently do nothing until the process restarted.

    AUTOCOMMIT so the extra connection does not sit idle in a transaction for
    the duration, and so the unlock cannot be rolled back. The unlock runs on
    this connection rather than db.session, so it still succeeds when a season
    has raised and left db.session in a failed transaction.
    """
    with db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        if not conn.execute(text('SELECT pg_try_advisory_lock(:key)'),
                            {'key': cLOCK_KEY}).scalar():
            current_app.logger.info(
                'season metric refresh skipped: another refresh holds the lock')
            yield False
            return
        try:
            yield True
        finally:
            conn.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': cLOCK_KEY})


def refresh_one_season(tag_set_id):
    """Recompute one season under the lock.

    Returns rows written, or None when another refresh already holds the lock.
    """
    with advisory_lock() as got_lock:
        if not got_lock:
            return None
        return refresh_season(tag_set_id)


def refresh_stale_seasons():
    """Refresh every season with new games, under the lock.

    Returns {tag_set_id: rows written}, or None when another refresh already
    holds the lock. Those are different answers: an empty dict means there was
    nothing stale, None means this run did no work at all.
    """
    with advisory_lock() as got_lock:
        if not got_lock:
            return None
        written = {}
        for tag_set_id in stale_season_ids():
            written[tag_set_id] = refresh_season(tag_set_id)
    return written


def refresh_season_metrics_job(app):
    '''Scheduler entry point.'''
    with app.app_context():
        try:
            refresh_stale_seasons()
        except Exception:
            db.session.rollback()
            app.logger.exception('season metric refresh failed')
