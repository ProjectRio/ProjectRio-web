'''Database access and the nightly job for RE24 (the math is in re24.py).

The job, refresh_re24(), runs once a night under a Postgres advisory lock:

  1. sync_competitions(): every tag set has a competition_profile row.
  2. Re-read games first read in the last two days whose event count has changed
     (populate_db commits a game's row before its events, one at a time).
  3. Read every game missing from the re24_game ledger, in batches, and store its
     per-state pitches and runs in re24_game_state. Only these games touch the
     event table: about a day's worth on a normal night.
  4. Rebuild the re24 table from re24_game_state for the competitions whose
     category is a game type and whose q_league_stats is on. That reads only the
     small per-game table, so it also runs on its own after an admin changes a
     competition (rebuild_re24_locked).

The first run reads every game in the database, then later runs read only new
ones. Each batch is its own transaction, so an interrupted run keeps what it
finished and the next one carries on.
'''
import time
from contextlib import contextmanager

from flask import current_app
from sqlalchemy import text

from .models import db, Re24, Re24Game, Re24GameState
from .re24 import cGAME_TYPES, game_states, log_is_complete, re24_rows
from .competition_profile_db import sync_competitions

# Advisory lock key, distinct from any other job's.
cLOCK_KEY = 2402408
cBATCH_GAMES = 500
cRECHECK_SECONDS = 2 * 24 * 60 * 60

cUNREAD_SQL = text('''
    SELECT g.game_id, g.away_score, g.home_score, g.innings_played
    FROM game g
    WHERE NOT EXISTS (SELECT 1 FROM re24_game r WHERE r.game_id = g.game_id)
    ORDER BY g.game_id
    LIMIT :limit
''')

cBOX_PITCHES_SQL = text('''
    SELECT game_id, COALESCE(SUM(pitches_thrown), 0)
    FROM character_game_summary
    WHERE game_id = ANY(:ids)
    GROUP BY game_id
''')

cPITCHES_SQL = text('''
    SELECT game_id, inning, half_inning, outs,
           runner_on_1 IS NOT NULL, runner_on_2 IS NOT NULL, runner_on_3 IS NOT NULL,
           away_score, home_score
    FROM event
    WHERE game_id = ANY(:ids)
    ORDER BY game_id, event_num, id
''')

# Games first read in the recheck window whose event count no longer matches.
cCHANGED_SQL = text('''
    SELECT r.game_id
    FROM re24_game r
    WHERE r.processed_at >= :since
      AND r.pitches <> (SELECT COUNT(*) FROM event e WHERE e.game_id = r.game_id)
''')

# A game filed under more than one competition counts under its first.
cSUMS_SQL = text('''
    SELECT p.category, s.outs, s.runners, SUM(s.pitches), SUM(s.runs)
    FROM re24_game_state s
    JOIN (SELECT DISTINCT ON (game_id) game_id, tag_set_id
          FROM game_history
          WHERE game_id IS NOT NULL
          ORDER BY game_id, id) h ON h.game_id = s.game_id
    JOIN competition_profile p ON p.tag_set_id = h.tag_set_id
    WHERE p.q_league_stats AND p.category = ANY(:game_types)
    GROUP BY p.category, s.outs, s.runners
''')

cGAMES_SQL = text('''
    SELECT p.category, COUNT(*)
    FROM re24_game r
    JOIN (SELECT DISTINCT ON (game_id) game_id, tag_set_id
          FROM game_history
          WHERE game_id IS NOT NULL
          ORDER BY game_id, id) h ON h.game_id = r.game_id
    JOIN competition_profile p ON p.tag_set_id = h.tag_set_id
    WHERE r.complete AND p.q_league_stats AND p.category = ANY(:game_types)
    GROUP BY p.category
''')


def recheck_recent_games(now):
    '''Forget games first read in the recheck window whose events have changed
    since, so this run reads them again. Returns how many.'''
    changed = [row[0] for row in db.session.execute(cCHANGED_SQL, {'since': now - cRECHECK_SECONDS})]
    if changed:
        # re24_game_state rows go with their ledger row (ON DELETE CASCADE).
        db.session.query(Re24Game).filter(Re24Game.game_id.in_(changed)).delete(synchronize_session=False)
        db.session.commit()
    return len(changed)


def read_new_games(now, batch=cBATCH_GAMES):
    '''Read every game missing from the ledger. Returns (games read, complete).'''
    read = complete = 0
    while True:
        games = db.session.execute(cUNREAD_SQL, {'limit': batch}).fetchall()
        if not games:
            return read, complete
        ids = [g[0] for g in games]
        box = dict(db.session.execute(cBOX_PITCHES_SQL, {'ids': ids}).fetchall())
        pitches = {game_id: [] for game_id in ids}
        for row in db.session.execute(cPITCHES_SQL, {'ids': ids}):
            pitches[row[0]].append(tuple(row[1:]))

        ledger, states = [], []
        for game_id, away, home, innings_played in games:
            log = pitches[game_id]
            is_complete = log_is_complete(log, innings_played, box.get(game_id))
            ledger.append({'game_id': game_id, 'complete': is_complete,
                           'pitches': len(log), 'processed_at': now})
            if is_complete:
                for (outs, runners), (seen, runs) in game_states(log, away, home).items():
                    states.append({'game_id': game_id, 'outs': outs, 'runners': runners,
                                   'pitches': seen, 'runs': runs})
                complete += 1
        db.session.execute(Re24Game.__table__.insert(), ledger)
        if states:
            db.session.execute(Re24GameState.__table__.insert(), states)
        db.session.commit()
        read += len(games)


def rebuild_re24(now):
    '''Replace the re24 table from re24_game_state. Returns the rows written.'''
    sums = {}
    for category, outs, runners, pitches, runs in db.session.execute(
            cSUMS_SQL, {'game_types': list(cGAME_TYPES)}):
        sums[(category, outs, runners)] = (int(pitches), int(runs))
    rows = re24_rows(sums)
    db.session.query(Re24).delete(synchronize_session=False)
    if rows:
        db.session.execute(Re24.__table__.insert(), [dict(row, computed_at=now) for row in rows])
    db.session.commit()
    return rows


def games_used():
    '''Complete games behind the current table, per game type (for the job's log).'''
    return {category: n for category, n in db.session.execute(
        cGAMES_SQL, {'game_types': list(cGAME_TYPES)})}


@contextmanager
def advisory_lock():
    '''Hold the RE24 lock on a connection of its own for the whole block.

    Yields True when the lock was taken, False when another run holds it. The
    lock lives on its own AUTOCOMMIT connection because db.session returns its
    connection to the pool on every commit, and an advisory lock belongs to the
    connection that took it.
    '''
    with db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        if not conn.execute(text('SELECT pg_try_advisory_lock(:key)'), {'key': cLOCK_KEY}).scalar():
            current_app.logger.info('RE24 refresh skipped: another run holds the lock')
            yield False
            return
        try:
            yield True
        finally:
            conn.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': cLOCK_KEY})


def refresh_re24():
    '''The nightly job's work, under the lock. Returns a summary, or None when
    another run already holds the lock.'''
    with advisory_lock() as got_lock:
        if not got_lock:
            return None
        started = time.time()
        now = int(started)
        competitions = sync_competitions()
        rechecked = recheck_recent_games(now)
        read, complete = read_new_games(now)
        rows = rebuild_re24(now)
        return {
            'competitions': competitions,
            'games_rechecked': rechecked,
            'games_read': read,
            'games_complete': complete,
            're24_rows': len(rows),
            'games_used': games_used(),
            'seconds': round(time.time() - started, 1),
        }


def rebuild_re24_locked():
    '''Rebuild the table only (after an admin changes a competition), under the
    lock. Returns the rows written, or None when a run already holds the lock;
    that run rebuilds the table itself before it finishes.'''
    with advisory_lock() as got_lock:
        if not got_lock:
            return None
        return rebuild_re24(int(time.time()))


def refresh_re24_job(app):
    '''Scheduler entry point.'''
    with app.app_context():
        try:
            summary = refresh_re24()
            if summary is not None:
                app.logger.info('RE24 refresh: %s', summary)
        except Exception:
            db.session.rollback()
            app.logger.exception('RE24 refresh failed')
