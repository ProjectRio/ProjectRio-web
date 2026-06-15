from flask import request, abort
from flask import current_app as app
from ..models import db, RioUser, Character, Game, CharacterGameSummary, Tag, Event, Runner, GameHistory, tagsettag
from ..util import *
from ..utils.db_helpers import resolve_names
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import aliased


def _empty_roster_pair():
    return ([None] * 9, [None] * 9)


def get_rosters_for_games(game_ids):
    """Batch-fetch away/home rosters for many games in a single query.

    Returns {game_id: (away_list, home_list)} where each list is indexed
    by roster_loc 0-8 (None if that slot is missing).
    Replaces the per-game 18-way self-join (N+1) that get_rosters_from_game used.
    """
    rosters = {game_id: _empty_roster_pair() for game_id in game_ids}
    if not game_ids:
        return rosters

    rows = db.session.execute(
        select(
            CharacterGameSummary.game_id,
            CharacterGameSummary.team_id,
            CharacterGameSummary.roster_loc,
            CharacterGameSummary.char_id,
        ).where(CharacterGameSummary.game_id.in_(game_ids))
    ).all()

    for row in rows:
        pair = rosters.get(row.game_id)
        if pair is None or row.roster_loc is None or not (0 <= row.roster_loc <= 8):
            continue
        away_list, home_list = pair
        target = away_list if row.team_id == 0 else home_list
        target[row.roster_loc] = row.char_id

    return rosters


def build_linescore_and_scoring_plays(game_innings, include_linescore, include_scoring_plays):
    # game_innings: {game_id: innings_played}
    # Find events where at least one runner scored (result_base == 4).
    # COUNT of scoring runners per event is the actual runs scored on that play.
    batter_cgs = aliased(CharacterGameSummary)
    pitcher_cgs = aliased(CharacterGameSummary)
    scored_runner = aliased(Runner)

    rows = db.session.execute(
        select(
            Event.id,
            Event.game_id,
            Event.event_num,
            Event.inning,
            Event.half_inning,
            Event.result_of_ab,
            Event.away_score,
            Event.home_score,
            Event.outs,
            Event.runner_on_0,
            Event.runner_on_1,
            Event.runner_on_2,
            Event.runner_on_3,
            batter_cgs.char_id.label('batter'),
            pitcher_cgs.char_id.label('pitcher'),
            func.count(scored_runner.id).label('runs_scored'),
        )
        .join(batter_cgs, Event.batter_id == batter_cgs.id)
        .join(pitcher_cgs, Event.pitcher_id == pitcher_cgs.id)
        .join(scored_runner, or_(
            Event.runner_on_0 == scored_runner.id,
            Event.runner_on_1 == scored_runner.id,
            Event.runner_on_2 == scored_runner.id,
            Event.runner_on_3 == scored_runner.id,
        ))
        .where(
            Event.game_id.in_(game_innings.keys()),
            scored_runner.result_base == 4,
        )
        .group_by(
            Event.id,
            batter_cgs.char_id,
            pitcher_cgs.char_id,
        )
        .order_by(Event.game_id, Event.event_num)
    ).all()

    # Batch-query all runners for these events (for scoring play runner state display)
    runner_lookup = {}
    if include_scoring_plays:
        runner_ids = set()
        for row in rows:
            for rid in (row.runner_on_0, row.runner_on_1, row.runner_on_2, row.runner_on_3):
                if rid is not None:
                    runner_ids.add(rid)
        if runner_ids:
            runner_rows = db.session.execute(
                select(
                    Runner.id,
                    Runner.initial_base,
                    Runner.result_base,
                    Runner.out_type,
                    Runner.out_location,
                    Runner.steal,
                    CharacterGameSummary.char_id,
                )
                .join(CharacterGameSummary, Runner.runner_character_game_summary_id == CharacterGameSummary.id)
                .where(Runner.id.in_(runner_ids))
            ).all()
            for r in runner_rows:
                runner_lookup[r.id] = {
                    'char_id': r.char_id,
                    'initial_base': r.initial_base,
                    'result_base': r.result_base,
                    'out_type': r.out_type,
                    'out_location': r.out_location,
                    'steal': r.steal,
                }

    # Accumulate runs per (game_id, inning, half_inning) and build scoring plays in one pass
    runs_by_half = {}  # {game_id: {(inning, half_inning): runs}}
    scoring_plays = {}

    for row in rows:
        game_id = row.game_id

        if include_linescore:
            if game_id not in runs_by_half:
                runs_by_half[game_id] = {}
            key = (row.inning, row.half_inning)
            runs_by_half[game_id][key] = runs_by_half[game_id].get(key, 0) + row.runs_scored

        if include_scoring_plays:
            if game_id not in scoring_plays:
                scoring_plays[game_id] = []

            runners = [
                runner_lookup.get(rid) if rid is not None else None
                for rid in (row.runner_on_0, row.runner_on_1, row.runner_on_2, row.runner_on_3)
            ]

            scoring_plays[game_id].append({
                'inning': row.inning,
                'half_inning': row.half_inning,
                'event_num': row.event_num,
                'result_rbi': row.runs_scored,
                'result_of_ab': row.result_of_ab,
                'batter': row.batter,
                'pitcher': row.pitcher,
                'away_score': row.away_score,
                'home_score': row.home_score,
                'outs': row.outs,
                'runners': runners,
            })

    # Build linescore arrays using innings_played to correctly fill scoreless innings with 0
    linescores = {}
    if include_linescore:
        for game_id, innings_played in game_innings.items():
            away = [runs_by_half.get(game_id, {}).get((i, 0), 0) for i in range(1, innings_played + 1)]
            home = [runs_by_half.get(game_id, {}).get((i, 1), 0) for i in range(1, innings_played + 1)]
            if home[-1] == 0 and sum(home) > sum(away):
                home[-1] = 'X'
            linescores[game_id] = [away, home]

    return linescores, scoring_plays



def parse_limit_games(args, default=None):
    """Parse the ``limit_games`` query param into a row limit.

    Returns:
        - ``default`` when ``limit_games`` is absent
        - ``None`` (no limit) for the falsy sentinels 'False'/'false'/'f'
        - the integer value otherwise

    Calls abort(400) on a non-integer value.
    """
    raw = args.get('limit_games')
    if raw is None:
        return default
    #TODO - support truthy and falsy values more broadly (e.g., true/false, yes/no)
    if raw in ('False', 'false', 'f'):
        return None
    try:
        return int(raw)
    except ValueError:
        abort(400, f'Invalid limit_games: {raw}')


def get_game_ids(args, default_limit=50):
    """Resolve filter args to an ordered list of game_ids.

    ``limit_games`` is parsed here (via parse_limit_games) so that every caller
    — the public /games/ endpoint and the internal event/stat endpoints alike —
    honors it through one shared code path. (Previously the limit was parsed only
    in endpoint_games(); internal callers passed a hardcoded limit and silently
    dropped limit_games, which left /landing_data/ etc. resolving an entire tag.)

    Args:
        args: request.args (or any MultiDict with the same interface)
        default_limit: cap applied when ``limit_games`` is absent. Defaults to 50
            (the newest 50 games) so no endpoint resolves an entire tag by
            accident. Pass None for no default cap. An explicit limit_games is
            always honored with no ceiling — limit_games=False returns every
            matching game and limit_games=N returns N.

    Returns:
        Ordered list of game_ids matching the filters (newest first).
        Calls abort(400) directly on invalid input.
    """
    limit = parse_limit_games(args, default=default_limit)

    # === Resolve names -> ids (each set must fully resolve) ===
    include_tag_ids = resolve_names(
        args.getlist('tag'), Tag.id, Tag.name_lowercase,
        'tag(s)', transform=lower_and_remove_nonalphanumeric)
    exclude_tag_ids = resolve_names(
        args.getlist('exclude_tag'), Tag.id, Tag.name_lowercase,
        'exclude_tag(s)', transform=lower_and_remove_nonalphanumeric)

    user_ids = resolve_names(
        args.getlist('username'), RioUser.id, RioUser.username_lowercase,
        'username(s)', transform=lower_and_remove_nonalphanumeric)
    vs_user_ids = resolve_names(
        args.getlist('vs_username'), RioUser.id, RioUser.username_lowercase,
        'vs_username(s)', transform=lower_and_remove_nonalphanumeric)
    exclude_user_ids = resolve_names(
        args.getlist('exclude_username'), RioUser.id, RioUser.username_lowercase,
        'exclude_username(s)', transform=lower_and_remove_nonalphanumeric)

    captain_ids = resolve_names(
        args.getlist('captain'), Character.char_id, Character.name_lowercase,
        'captain(s)', transform=lower_and_remove_nonalphanumeric)
    vs_captain_ids = resolve_names(
        args.getlist('vs_captain'), Character.char_id, Character.name_lowercase,
        'vs_captain(s)', transform=lower_and_remove_nonalphanumeric)
    exclude_captain_ids = resolve_names(
        args.getlist('exclude_captain'), Character.char_id, Character.name_lowercase,
        'exclude_captain(s)', transform=lower_and_remove_nonalphanumeric)

    # Stadiums (numeric ids)
    # TODO resolve stadium names. Tackle with fuzzy resolve throughout
    stadium_ids = []
    for s in args.getlist('stadium'):
        try:
            stadium_ids.append(int(s))
        except ValueError:
            abort(400, f'Invalid stadium id: {s!r}')

    # === Time bounds (both compared against Game.date_time_end) ===
    start_time_unix = None
    if args.get('start_time') is not None:
        try:
            start_time_unix = int(args.get('start_time'))
        except ValueError:
            abort(400, f'Invalid start_time: {args.get("start_time")!r}')

    end_time_unix = None
    if args.get('end_time') is not None:
        try:
            end_time_unix = int(args.get('end_time'))
        except ValueError:
            abort(400, f'Invalid end_time: {args.get("end_time")!r}')

    if (end_time_unix is not None and start_time_unix is not None
            and end_time_unix <= start_time_unix):
        abort(400, f'end_time ({end_time_unix}) must be greater than '
                   f'start_time ({start_time_unix})')

    # === Build filter conditions ===
    conditions = []

    if start_time_unix is not None:
        conditions.append(Game.date_time_end >= start_time_unix)
    if end_time_unix is not None:
        conditions.append(Game.date_time_end <= end_time_unix)

    # Users — filter directly on the indexed game columns.
    if user_ids:
        conditions.append(or_(Game.away_player_id.in_(user_ids),
                              Game.home_player_id.in_(user_ids)))
    if vs_user_ids:
        conditions.append(or_(Game.away_player_id.in_(vs_user_ids),
                              Game.home_player_id.in_(vs_user_ids)))
    if exclude_user_ids:
        conditions.append(and_(Game.away_player_id.notin_(exclude_user_ids),
                               Game.home_player_id.notin_(exclude_user_ids)))

    # Captains — match against the game's captain CharacterGameSummary rows via EXISTS
    def _captain_exists(char_ids):
        cap = aliased(CharacterGameSummary)
        return (
            select(cap.game_id)
            .where(
                cap.game_id == Game.game_id,
                cap.captain.is_(True),
                cap.char_id.in_(char_ids),
            )
            .exists()
        )
    if captain_ids:
        conditions.append(_captain_exists(captain_ids))
    if vs_captain_ids:
        conditions.append(_captain_exists(vs_captain_ids))
    if exclude_captain_ids:
        conditions.append(~_captain_exists(exclude_captain_ids))

    # Tags — match against the game's tag_set (via game_history) using EXISTS.
    # include: game's tag_set contains any requested tag.
    # exclude: game's tag_set contains none of the excluded tags.
    def _tag_exists(tag_ids):
        return (
            select(GameHistory.game_id)
            .join(tagsettag, tagsettag.c.tagset_id == GameHistory.tag_set_id)
            .where(
                GameHistory.game_id == Game.game_id,
                tagsettag.c.tag_id.in_(tag_ids),
            )
            .exists()
        )
    if include_tag_ids:
        conditions.append(_tag_exists(include_tag_ids))
    if exclude_tag_ids:
        conditions.append(~_tag_exists(exclude_tag_ids))

    if stadium_ids:
        conditions.append(Game.stadium_id.in_(stadium_ids))

    # ORDER BY date_time_end DESC + LIMIT is applied here, before any display joins,
    # so Postgres can walk the date_time_end index and stop at the limit.
    game_id_stmt = (
        select(Game.game_id)
        .where(*conditions)
        .order_by(Game.date_time_end.desc())
    )
    if limit is not None:
        game_id_stmt = game_id_stmt.limit(limit)

    return db.session.execute(game_id_stmt).scalars().all()


'''
@ Description: Returns games that fit the parameters
@ Params:
    - tag - list of tags to filter by
    - exclude_tag - List of tags to exclude from search
    - start_time - Unix time. Lower (older) bound; filtered against a game's end time.
    - end_time - Unix time. Upper (newer) bound; filtered against a game's end time.
                 Defaults to no upper bound.
    - username - list of users who appear in games to retreive
    - vs_username - list of users, one of whom MUST also appear in the game along with users
    - exclude_username - list of users to NOT include in query results
    - captain - captain name to appear in games to retrieve
     - vs_captain - list of captain names, one of whom MUST appear in game along with captain
    - exclude_captain - captain name to EXCLUDE from results
    - limit_games - Int of number of games || False to return all
    - include_linescore - bool to include per-half-inning run totals (top/bottom arrays)
    - include_scoring_plays - bool to include events where runs scored (batter, pitcher, rbi, score, etc.)

    Note: both start_time and end_time are compared against Game.date_time_end. A game
    is bucketed by when it ENDED, so a game is never split across a time boundary.

@ Output:
    - List of games and highlevel info based on flags

@ URL example: http://127.0.0.1:5000/games/?limit=5&username=demOuser4&username=demouser1&username=demouser5
'''
@app.route('/games/', methods=['GET'])
def endpoint_games():
    # get_game_ids parses limit_games and defaults to the newest 50 games.
    ordered_game_ids = get_game_ids(request.args)

    include_linescore = (request.args.get('include_linescore') == '1')
    include_scoring_plays = (request.args.get('include_scoring_plays') == '1')

    if not ordered_game_ids:
        return {'games': []}

    # === Stage 2: hydrate display fields for just this page (bounded by limit) ===
    away_player = aliased(RioUser)
    home_player = aliased(RioUser)
    away_cgs = aliased(CharacterGameSummary)
    home_cgs = aliased(CharacterGameSummary)
    away_captain = aliased(Character)
    home_captain = aliased(Character)
    gh = aliased(GameHistory)

    hydrate_stmt = (
        select(
            Game.game_id,
            Game.stadium_id.label('stadium'),
            Game.date_time_start,
            Game.date_time_end,
            Game.away_score,
            Game.home_score,
            Game.innings_played,
            Game.innings_selected,
            away_player.username.label('away_player'),
            home_player.username.label('home_player'),
            away_captain.name.label('away_captain'),
            home_captain.name.label('home_captain'),
            gh.winner_incoming_elo.label('winner_incoming_elo'),
            gh.loser_incoming_elo.label('loser_incoming_elo'),
            gh.winner_result_elo.label('winner_result_elo'),
            gh.loser_result_elo.label('loser_result_elo'),
            gh.tag_set_id.label('tag_set'),
        )
        .select_from(Game)
        .outerjoin(away_player, Game.away_player_id == away_player.id)
        .outerjoin(home_player, Game.home_player_id == home_player.id)
        .join(away_cgs, and_(
            Game.game_id == away_cgs.game_id,
            away_cgs.user_id == Game.away_player_id,
            away_cgs.captain.is_(True),
        ))
        .join(away_captain, away_cgs.char_id == away_captain.char_id)
        .join(home_cgs, and_(
            Game.game_id == home_cgs.game_id,
            home_cgs.user_id == Game.home_player_id,
            home_cgs.captain.is_(True),
        ))
        .join(home_captain, home_cgs.char_id == home_captain.char_id)
        .outerjoin(gh, Game.game_id == gh.game_id)
        .where(Game.game_id.in_(ordered_game_ids))
    )

    # A game has at most one joining game_history, so the LEFT JOIN yields one row
    # per game. Key by game_id (guarding against any unexpected duplicate) and
    # re-apply the Stage 1 ordering, which IN (...) does not preserve.
    hydrate_by_id = {}
    for row in db.session.execute(hydrate_stmt).all():
        if row.game_id not in hydrate_by_id:
            hydrate_by_id[row.game_id] = row
    results = [hydrate_by_id[gid] for gid in ordered_game_ids if gid in hydrate_by_id]

    rosters_by_game = get_rosters_for_games(ordered_game_ids)

    linescores = {}
    scoring_plays_by_game = {}
    if results and (include_linescore or include_scoring_plays):
        game_innings = {game.game_id: game.innings_played for game in results}
        linescores, scoring_plays_by_game = build_linescore_and_scoring_plays(game_innings, include_linescore, include_scoring_plays)

    games = []
    for game in results:
        away_roster, home_roster = rosters_by_game[game.game_id]
        game_dict = {
            'game_id': game.game_id,
            'stadium': game.stadium,
            'date_time_start': game.date_time_start,
            'date_time_end': game.date_time_end,
            'away_user': game.away_player,
            'away_captain': game.away_captain,
            'away_roster': away_roster,
            'away_score': game.away_score,
            'home_user': game.home_player,
            'home_captain': game.home_captain,
            'home_roster': home_roster,
            'home_score': game.home_score,
            'innings_played': game.innings_played,
            'innings_selected': game.innings_selected,
            'winner_incoming_elo': game.winner_incoming_elo,
            'loser_incoming_elo': game.loser_incoming_elo,
            'winner_result_elo': game.winner_result_elo,
            'loser_result_elo': game.loser_result_elo,
            'game_mode': game.tag_set
        }
        if include_linescore:
            game_dict['linescore'] = linescores.get(game.game_id, [[], []])
        if include_scoring_plays:
            game_dict['scoring_plays'] = scoring_plays_by_game.get(game.game_id, [])
        games.append(game_dict)

    return {'games': games}
