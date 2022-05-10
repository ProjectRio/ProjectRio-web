from flask import request, jsonify, abort
from flask import current_app as app
from ...models import db, RioUser, Game
from ...helper_functions import calculate_era

'''
@ Description: Returns box score data
@ Params:
    - game_id
    - one or two 'username' fields, recent=1
@ Output:
    - json of game data needed to display a box score
@ URL examples: 
    - /box_score/?game_id=12345678
    - /box_score/?vs_username=user1&recent=1
    - /box_score/?vs_username=user1&vs_username=user2&recent=1
'''
# === Box Score ===
@app.route('/box_score/', methods = ['GET'])
def box_score():
    if request.args.get('game_id') is not None:
        game_id = request.args.get('game_id', type=int)
        game = Game.query.filter_by(game_id=game_id).first()
        if game is None:
            abort(400, 'Invalid game_id')

        away_username = RioUser.query.filter_by(id=game.away_player_id).first().username
        home_username = RioUser.query.filter_by(id=game.home_player_id).first().username

    else:
        abort(400, 'Must provide game_id')
    # elif request.args.get('vs_username') is not None:
    #     home_user = RioUser.query.filter_by(username_lowercase=)

    #     if request.args.get('recent') is None:
    #         abort(400, 'Must add recent=1 to url')
    #     game = endpoint_games()
    #     if game is None:
    #         abort(400, 'No corresponding game found')
    # else:
    #     abort(400, 'Provide a game_id or username and recent=1 url parameters')
    
    box_score = {
        "stadium_id": game.stadium_id,
        "innings_selected": game.innings_selected,
        "innings_played": game.innings_played,
        "date_time_start": game.date_time_start,
        "date_time_end": game.date_time_end,
        "average_ping": game.average_ping,
        "lag_spikes": game.lag_spikes,
        "version": game.version,
        "tags": [],
        'away': {
            'player': away_username,
            'runs': game.away_score,
            'hits': 0,
            'line_score': [],
            'lob': [],
            'rlisp': [],
            'pitchers': [],
            'batters': [],
            'character': {},
            'captain': str()
        },
        'home': {
            'player': home_username,
            'runs': game.home_score,
            'hits': 0,
            'line_score': [],
            'lob': [],
            'rlisp': [],
            'pitchers': [],
            'batters': [],
            'character': {},
            'captain': str()
        }
    }

    # NEED TO FIX SUM cases for event runner (pitch_result right?)
    event_query = (
        'SELECT \n'
        'event.inning AS inning, \n'
        'event.half_inning AS half_inning, \n'
        'MAX(event.away_score) AS away_score, \n'
        'MAX(event.home_score) AS home_score, \n'
        'SUM(CASE WHEN contact_summary.type_of_contact IN (0,1,2) THEN 1 ELSE 0 END) AS hits, \n'
        'SUM(CASE WHEN event.runner_on_1 IS NOT NULL AND event.outs = 2 AND pitch_summary.pitch_result IN (4,6) THEN 1 ELSE 0 END) AS runner_on_1, \n'
        'SUM(CASE WHEN event.runner_on_2 IS NOT NULL AND event.outs = 2 AND pitch_summary.pitch_result IN (4,6) THEN 1 ELSE 0 END) AS runner_on_2, \n'
        'SUM(CASE WHEN event.runner_on_3 IS NOT NULL AND event.outs = 2 AND pitch_summary.pitch_result IN (4,6) THEN 1 ELSE 0 END) AS runner_on_3 \n'
        'FROM game \n'
        'LEFT JOIN event ON game.game_id = event.game_id \n'
        'JOIN pitch_summary ON pitch_summary.id = event.pitch_summary_id \n'
        'JOIN contact_summary ON contact_summary.id = pitch_summary.contact_summary_id \n'
        f'WHERE game.game_id = {game.game_id} \n'
        'GROUP BY inning, half_inning \n'
        'ORDER BY inning, half_inning \n'
    )
    game_data = db.session.execute(event_query).all()
    for row in game_data:
        if row.half_inning == 0:
            box_score['away']['hits'] += row.hits
            box_score['away']['line_score'].append(row.away_score)
        else:
            box_score['home']['hits'] += row.hits
            box_score['home']['line_score'].append(row.home_score)
    
    character_stats_query = (
        "SELECT \n"
        # General Info
        "character.name AS name, \n"
        "character_game_summary.team_id AS team_id, \n"
        "character_game_summary.captain AS captain, \n"
        "character_game_summary.fielding_hand AS fielding_hand, \n"
        "character_game_summary.batting_hand AS batting_hand, \n"
        "character_game_summary.was_pitcher AS was_pitcher, \n"
        # Pitching Stats
        "character_game_summary.batters_faced AS batters_faced, \n"
        "character_game_summary.runs_allowed AS runs_allowed, \n"
        "character_game_summary.earned_runs AS earned_runs, \n"
        "character_game_summary.batters_walked AS batters_walked, \n"
        "character_game_summary.batters_hit AS batters_hit, \n"
        "character_game_summary.hits_allowed AS hits_allowed, \n"
        "character_game_summary.homeruns_allowed AS homeruns_allowed, \n"
        "character_game_summary.pitches_thrown AS pitches_thrown, \n"
        "character_game_summary.strikeouts_pitched AS strikeouts_pitched, \n"
        "character_game_summary.star_pitches_thrown AS star_pitches_thrown, \n"
        "character_game_summary.outs_pitched AS outs_pitched, \n"
        # "character_game_summary.big_plays AS big_plays, \n"
        # Batting Stats
        "character_game_summary.at_bats AS at_bats, \n"
        "character_game_summary.plate_appearances, \n"
        "character_game_summary.hits AS hits, \n"
        "character_game_summary.singles AS singles, \n"
        "character_game_summary.doubles AS doubles, \n"
        "character_game_summary.triples AS triples, \n"
        "character_game_summary.homeruns AS homeruns, \n"
        "character_game_summary.successful_bunts AS successful_bunts, \n"
        "character_game_summary.sac_flys AS sac_flys, \n"
        "character_game_summary.strikeouts AS strikeouts, \n"
        "character_game_summary.walks_bb AS walks_bb, \n"
        "character_game_summary.walks_hit AS walks_hit, \n"
        "character_game_summary.rbi AS rbi, \n"
        "character_game_summary.bases_stolen AS bases_stolen, \n"
        "character_game_summary.star_hits AS star_hits, \n"
        # Star Stats
        "character_game_summary.offensive_star_swings AS offensive_star_swings, \n"
        "character_game_summary.offensive_stars_used AS offensive_stars_used, \n"
        "character_game_summary.offensive_stars_put_in_play AS offensive_stars_put_in_play, \n"
        "character_game_summary.offensive_star_successes AS offensive_star_successes, \n"
        "character_game_summary.offensive_star_chances AS offensive_star_chances, \n"
        "character_game_summary.offensive_star_chances_won AS offensive_star_chances_won, \n"
        "character_game_summary.defensive_star_pitches AS defensive_star_pitches, \n"
        "character_game_summary.defensive_stars_used AS defensive_stars_used, \n"
        "character_game_summary.defensive_star_successes AS defensive_star_successes, \n"
        "character_game_summary.defensive_star_chances AS defensive_star_chances, \n"
        "character_game_summary.defensive_star_chances_won AS defensive_star_chances_won, \n"
        # Positions
        "character_position_summary.pitches_at_p AS pitches_at_p, \n"
        "character_position_summary.pitches_at_c AS pitches_at_c, \n"
        "character_position_summary.pitches_at_1b AS pitches_at_1b, \n"
        "character_position_summary.pitches_at_2b AS pitches_at_2b, \n"
        "character_position_summary.pitches_at_3b AS pitches_at_3b, \n"
        "character_position_summary.pitches_at_ss AS pitches_at_ss, \n"
        "character_position_summary.pitches_at_lf AS pitches_at_lf, \n"
        "character_position_summary.pitches_at_cf AS pitches_at_cf, \n"
        "character_position_summary.pitches_at_rf AS pitches_at_rf \n"
        "FROM character_game_summary \n"
        "LEFT JOIN character ON character_game_summary.char_id = character.char_id \n"
        "LEFT JOIN character_position_summary ON character_game_summary.character_position_summary_id = character_position_summary.id \n"
        f"WHERE character_game_summary.game_id = {game.game_id} \n"
    )
    character_data = db.session.execute(character_stats_query).all()
    positions = ['p', 'c', '1b', '2b', '3b', 'ss', 'lf', 'cf', 'rf']

    for character in character_data:
        # Get Team as a String for sorting data
        team = "away" if character.team_id == 0 else 'home'

        # Find primary position and plays at that position to add to character dicts
        primary_position = str()
        plays_at_primary_position = 0
        for position in positions:
            if plays_at_primary_position < character['pitches_at_' + position]:
                primary_position = position
                plays_at_primary_position = character['pitches_at_' + position]

        if character.was_pitcher:
            box_score[team]['pitchers'].append(character.name)
        
        if character.at_bats != 0:
            box_score[team]['batters'].append(character.name)

        if character.captain:
            box_score[team]['captain'] = character.name

        # box_score[team]['character'][character.name] = {}
        box_score[team]['character'][character.name] = {
            'primary_position': primary_position,
            'plays_at_primary_position': plays_at_primary_position,
            'batting_hand': character.batting_hand,
            'fielding_hand': character.fielding_hand,
            # Pitching Stats
            'batters_faced': character.batters_faced,
            'runs_allowed': character.runs_allowed,
            'earned_runs': character.earned_runs,
            'batters_walked': character.batters_walked,
            'batters_hit': character.batters_hit,
            'hits_allowed': character.hits_allowed,
            'homeruns_allowed': character.homeruns_allowed,
            'pitches_thrown': character.pitches_thrown,
            'strikeouts_pitched': character.strikeouts_pitched,
            'star_pitches_thrown': character.star_pitches_thrown,
            'outs_pitched': character.outs_pitched,
            # Batting Stats
            'at_bats': character.at_bats,
            'plate_appearances': character.plate_appearances,
            'hits': character.hits,
            'singles': character.singles,
            'doubles': character.doubles,
            'triples': character.triples,
            'homeruns': character.homeruns,
            'successful_bunts': character.successful_bunts,
            'sac_flys': character.sac_flys,
            'strikeouts': character.strikeouts,
            'walks_bb': character.walks_bb,
            'walks_hit': character.walks_hit,
            'rbi': character.rbi,
            'bases_stolen': character.bases_stolen,
            'star_hits': character.star_hits,
            # Calculated Stats
            'era': calculate_era(character.runs_allowed, character.outs_pitched),
            'batting_average': character.hits/character.at_bats,
            'obp': (character.hits + character.walks_bb + character.walks_hit)/(character.at_bats + character.walks_bb + character.walks_hit),
            'slg': (character.singles + (character.doubles * 2) + (character.triples * 3) + (character.homeruns * 4))/character.at_bats,
            'innings_pitched': character.outs_pitched/3,
            # Offensive/Defensive Stars
            'offensive_star_swings' : character.offensive_star_swings,
            'offensive_stars_used' : character.offensive_stars_used,
            'offensive_stars_put_in_play' : character.offensive_stars_put_in_play,
            'offensive_star_successes' : character.offensive_star_successes,
            'offensive_star_chances' : character.offensive_star_chances,
            'offensive_star_chances_won' : character.offensive_star_chances_won,
            'defensive_star_pitches' : character.defensive_star_pitches,
            'defensive_stars_used' : character.defensive_stars_used,
            'defensive_star_successes' : character.defensive_star_successes,
            'defensive_star_chances' : character.defensive_star_chances,
            'defensive_star_chances_won' : character.defensive_star_chances_won,
        }
        box_score[team]['character'][character.name]['ops'] = box_score[team]['character'][character.name]["obp"] + box_score[team]['character'][character.name]["slg"]

        if box_score[team]['character'][character.name]['innings_pitched'] == 0:
            box_score[team]['character'][character.name]['whip'] = 0
        else:
            box_score[team]['character'][character.name]['whip'] = (box_score[team]['character'][character.name]['batters_walked'] + box_score[team]['character'][character.name]['hits_allowed']) / box_score[team]['character'][character.name]['innings_pitched']
    
    return box_score
