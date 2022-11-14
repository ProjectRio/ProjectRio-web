from flask import request, abort
from flask import current_app as app
from ...models import db, RioUser
from ...util import calculate_era

# API Request URL example: /profile/stats/?recent=10&username=demouser1
'''
    @ Description: Returns a player overview
    @ Params:
        - recent - Int of number of games
        - username - list of users who appear in games to retreive
    @ Output:
        - N most recent games
        - N username
        - user totals (split into ranked normal, ranked superstar, unranked normal, unranked superstar, all)
        - top batters (split into ranked normal ranked superstar, unranked normal, unranked superstar, all)
        - top pitchers (split into ranked normal ranked superstar, unranked normal, unranked superstar, all)
        - top captains (split into ranked normal ranked superstar, unranked normal, unranked superstar, all)
    @ URL example: http://127.0.0.1:5000/profile/stats/?recent=5&username=demOuser4
'''
@app.route('/user_summary/', methods = ['GET'])
def user_stats():
    # # Get User row
    username = request.args.get('username')
    in_username_lowercase = username.lower()
    user_to_query = RioUser.query.filter_by(username_lowercase=in_username_lowercase).first()

    # If user doesn't exist, abort
    if not user_to_query:
        return abort(408, description='User does not exist')

    # returns tuples of game_ids for ranked_normals, ranked_superstar, unranked_normals, unranked_superstar games
    by_types_case_statement = get_users_sorted_games(user_to_query.id)

    # Returns JSON with user stats for ranked normal, ranked superstar, unranked normal, unranked superstar, and sum total
    user_totals = get_user_profile_totals(user_to_query.id, by_types_case_statement)

    # Returns JSON with top 6 pitchers by era, top 6 batters by rbi for ranked normals, ranked superstars, unranked normals, unranked superstars
    char_totals = get_top_pitchers_and_batters(user_to_query.id, by_types_case_statement)

    # Returns JSON of top 3 captains by winrate for ranked normals, ranked superstars, unranked normals, unranked superstars
    captain_totals = get_top_captains(user_to_query.id, by_types_case_statement)

    return {
        "username": user_to_query.username,
        "user_totals": user_totals,
        "top_batters": char_totals['batters'],
        "top_pitchers": char_totals['pitchers'],
        "top_captains": captain_totals,
    }

def get_users_sorted_games(user_id):
    query = (
        'SELECT \n'
        'game.game_id AS game_id, \n'
        'SUM(CASE WHEN game_tag.tag_id = 1 THEN 1 END) AS ranked, \n' 
        'SUM(CASE WHEN game_tag.tag_id = 2 THEN 1 END) AS unranked, \n'
        'SUM(CASE WHEN game_tag.tag_id = 3 THEN 1 END) AS superstar, \n'
        'SUM(CASE WHEN game_tag.tag_id = 4 THEN 1 END) AS normal \n'
        'FROM rio_user \n'
        'JOIN game ON rio_user.id = game.home_player_id OR rio_user.id = game.away_player_id \n'
        'JOIN game_tag ON game.game_id = game_tag.game_id \n'
        f'WHERE rio_user.id = {user_id} \n'
        'GROUP BY game.game_id \n'
    )
    games = db.session.execute(query).all()

    # Sort games according to their tags (Ranked, Unranked, Normal, Superstar)
    ranked_normal = []
    ranked_superstar = []
    unranked_normal = []
    unranked_superstar = []
    for game in games:
        if game.ranked == 1:
            if game.normal == 1:
                ranked_normal.append(str(game.game_id))
            elif game.superstar == 1:
                ranked_superstar.append(str(game.game_id))
        elif game.unranked == 1:
            if game.normal == 1:
                unranked_normal.append(str(game.game_id))
            elif game.superstar == 1:
                unranked_superstar.append(str(game.game_id))

    case_statement = ""
    when_game_id_in_statement = ""
    when_game_id_in_statement += f"WHEN game.game_id IN ({', '.join(ranked_normal)}) THEN 1 " if len(ranked_normal) > 0 else ""
    when_game_id_in_statement += f"WHEN game.game_id IN ({','.join(ranked_superstar)}) THEN 2 " if len(ranked_superstar) > 0 else ""
    when_game_id_in_statement += f"WHEN game.game_id IN ({', '.join(unranked_normal)}) THEN 3 " if len(unranked_normal) > 0 else ""
    when_game_id_in_statement += f"WHEN game.game_id IN ({', '.join(unranked_superstar)}) THEN 3 " if len(unranked_superstar) > 0 else ""
    if when_game_id_in_statement:
        case_statement = f"CASE {when_game_id_in_statement} END as type, "

    return case_statement

def get_top_captains(user_id, by_types_case_statement):
    query = (
        'SELECT '
        'character.name AS name, '
        f'{by_types_case_statement}'
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score > game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score > game.away_score THEN 1 '
            'ELSE 0 '
            'END) AS wins, '
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score < game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score < game.away_score THEN 1 '
            'ELSE 0 '
            'END) AS losses, '
        'SUM(character_game_summary.runs_allowed) AS runs_allowed, '
        'SUM(character_game_summary.outs_pitched) AS outs_pitched, '
        'SUM(character_game_summary.hits) AS hits, '
        'SUM(character_game_summary.at_bats) AS at_bats, '
        'SUM(character_game_summary.walks_bb) AS walks_bb, '
        'SUM(character_game_summary.walks_hit) AS walks_hit, '
        'SUM(character_game_summary.rbi) AS rbi, '
        'SUM(character_game_summary.singles) AS singles, '
        'SUM(character_game_summary.doubles) AS doubles, '
        'SUM(character_game_summary.triples) AS triples, '
        'SUM(character_game_summary.homeruns) AS homeruns '
        'FROM character_game_summary '
        'JOIN game ON character_game_summary.game_id = game.game_id '
        'JOIN character ON character_game_summary.char_id = character.char_id '        
        f'WHERE character_game_summary.user_id = {user_id} '
        'AND character_game_summary.captain '
        'GROUP BY character.name, type'
    )

    summed_captains_by_tags = db.session.execute(query).all()

    captains_ranked_normal = []
    captains_ranked_superstar = []
    captains_unranked_normal = []
    captains_unranked_superstar = []
    for captain in summed_captains_by_tags:
        if captain.wins + captain.losses >= 5:
            stats = {
                "name": captain.name,
                "wins": captain.wins,
                "losses": captain.losses,
                "homeruns": captain.homeruns,
                "batting_average": captain.hits/captain.at_bats,
                "obp": (captain.hits + captain.walks_bb + captain.walks_hit)/(captain.at_bats + captain.walks_bb + captain.walks_hit),
                "rbi": captain.rbi,
                "slg": (captain.singles + (captain.doubles * 2) + (captain.triples * 3) + (captain.homeruns * 4))/captain.at_bats,
                "era": calculate_era(captain.runs_allowed, captain.outs_pitched),
            }

            if captain.type == 1:
                captains_ranked_normal.append(stats)
            elif captain.type == 2:
                captains_ranked_superstar.append(stats)
            elif captain.type == 3:
                captains_unranked_normal.append(stats)
            elif captain.type == 4:
                captains_unranked_superstar.append(stats)

    
    sorted_captains = {
        'ranked_normal': sorted(captains_ranked_normal, key=lambda captain: captain['wins']/(captain['wins'] + captain['losses']), reverse=True)[0:3],
        'ranked_superstar': sorted(captains_ranked_superstar, key=lambda captain: captain['wins']/(captain['wins'] + captain['losses']), reverse=True)[0:3],
        'unranked_normal': sorted(captains_unranked_normal, key=lambda captain: captain['wins']/(captain['wins'] + captain['losses']), reverse=True)[0:3],
        'unranked_superstar': sorted(captains_unranked_superstar, key=lambda captain: captain['wins']/(captain['wins'] + captain['losses']), reverse=True)[0:3]
    }

    return sorted_captains

def get_user_profile_totals(user_id, by_types_case_statement):
    query = (
        'SELECT '
        f'{by_types_case_statement}'
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score > game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score > game.away_score THEN 1 '
            'ELSE 0 '
            'END)/9 AS wins, '
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score < game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score < game.away_score THEN 1 '
            'ELSE 0 '
            'END)/9 AS losses, '
        'SUM(character_game_summary.runs_allowed) AS runs_allowed, '
        'SUM(character_game_summary.outs_pitched) AS outs_pitched, '
        'SUM(character_game_summary.hits) AS hits, '
        'SUM(character_game_summary.at_bats) AS at_bats, '
        'SUM(character_game_summary.walks_bb) AS walks_bb, '
        'SUM(character_game_summary.walks_hit) AS walks_hit, '
        'SUM(character_game_summary.rbi) AS rbi, '
        'SUM(character_game_summary.singles) AS singles, '
        'SUM(character_game_summary.doubles) AS doubles, '
        'SUM(character_game_summary.triples) AS triples, '
        'SUM(character_game_summary.homeruns) AS homeruns '
        'FROM game '
        'JOIN character_game_summary ON game.game_id = character_game_summary.game_id '
        f'WHERE character_game_summary.user_id = {user_id} '
        'GROUP BY character_game_summary.user_id, type'
    )

    summed_games_by_type = db.session.execute(query).all()

    user_totals = {
        'all': {
            'losses': 0,
            'wins': 0,
            'runs_allowed': 0,
            'outs_pitched': 0,
            'hits': 0,
            'at_bats': 0,
            'walks_bb': 0,
            'walks_hit': 0,
            'rbi': 0,
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'homeruns': 0,
        },
        'ranked_normal': {},
        'ranked_superstar': {},
        'unranked_normal': {},
        'unranked_superstar': {}
        }

    for summed_game in summed_games_by_type:
        user_totals['all']['losses'] += summed_game.losses
        user_totals['all']['wins'] += summed_game.wins
        user_totals['all']['runs_allowed'] += summed_game.runs_allowed
        user_totals['all']['outs_pitched'] += summed_game.outs_pitched
        user_totals['all']['hits'] += summed_game.hits
        user_totals['all']['at_bats'] += summed_game.at_bats
        user_totals['all']['walks_bb'] += summed_game.walks_bb
        user_totals['all']['walks_hit'] += summed_game.walks_hit
        user_totals['all']['rbi'] += summed_game.rbi
        user_totals['all']['singles'] += summed_game.singles
        user_totals['all']['doubles'] += summed_game.doubles
        user_totals['all']['triples'] += summed_game.triples
        user_totals['all']['homeruns'] += summed_game.homeruns
        
        key = str()
        if summed_game.type == 1:
            key = 'ranked_normal'
        elif summed_game.type == 2:
            key = 'ranked_superstar'
        elif summed_game.type == 3:
            key = 'unranked_normal'
        elif summed_game.type == 4:
            key = 'unranked_superstar'
        
        user_totals[key] = {
            'losses': summed_game.losses,
            'wins': summed_game.wins,
            'homeruns': summed_game.homeruns,
            'batting_average': summed_game.hits/summed_game.at_bats,
            'obp': (summed_game.hits + summed_game.walks_bb + summed_game.walks_hit)/(summed_game.at_bats + summed_game.walks_bb + summed_game.walks_hit),
            'slg': (summed_game.singles + (summed_game.doubles * 2) + (summed_game.triples * 3) + (summed_game.homeruns * 4))/summed_game.at_bats,
            'rbi': summed_game.rbi,
            'era': calculate_era(summed_game.runs_allowed, summed_game.outs_pitched)
        }

    user_totals['all']['batting_average'] = user_totals['all']['hits']/user_totals['all']['at_bats']
    user_totals['all']['obp'] = (user_totals['all']['hits'] + user_totals['all']['walks_bb'] + user_totals['all']['walks_hit']) / (user_totals['all']['at_bats'] + user_totals['all']['walks_bb'] + user_totals['all']['walks_hit'])
    user_totals['all']['slg'] = (user_totals['all']['singles'] + (user_totals['all']['doubles'] * 2) + (user_totals['all']['triples'] * 3) + (user_totals['all']['homeruns'] * 4))/user_totals['all']['at_bats']
    user_totals['all']['era'] = calculate_era(user_totals['all']['runs_allowed'], user_totals['all']['outs_pitched'])
    return user_totals

# Returns the top 6 batters and pitchers according to rbi and era, along with their summary stats.
def get_top_pitchers_and_batters(user_id, by_types_case_statement):
    query = (
        'SELECT '
        'character.name AS name, '
        f'{by_types_case_statement}'
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score > game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score > game.away_score THEN 1 '
            'ELSE 0 '
            'END) AS wins, '
        'SUM(CASE '
            f'WHEN game.away_player_id = {user_id} AND game.away_score < game.home_score THEN 1 '
            f'WHEN game.home_player_id = {user_id} AND game.home_score < game.away_score THEN 1 '
            'ELSE 0 '
            'END) AS losses, '
        'SUM(character_game_summary.runs_allowed) AS runs_allowed, '
        'SUM(character_game_summary.outs_pitched) AS outs_pitched, '
        'SUM(character_game_summary.hits) AS hits, '
        'SUM(character_game_summary.at_bats) AS at_bats, '
        'SUM(character_game_summary.walks_bb) AS walks_bb, '
        'SUM(character_game_summary.walks_hit) AS walks_hit, '
        'SUM(character_game_summary.rbi) AS rbi, '
        'SUM(character_game_summary.singles) AS singles, '
        'SUM(character_game_summary.doubles) AS doubles, '
        'SUM(character_game_summary.triples) AS triples, '
        'SUM(character_game_summary.homeruns) AS homeruns '
        'FROM character_game_summary '
        'JOIN game ON character_game_summary.game_id = game.game_id '
        'JOIN character ON character_game_summary.char_id = character.char_id '        
        f'WHERE character_game_summary.user_id = {user_id} '
        'GROUP BY character.name, type'
    )

    summed_chars_by_tags = db.session.execute(query).all()

    pitchers = {
        'ranked_normal': [],
        'ranked_superstar': [],
        'unranked_normal': [],
        'unranked_superstar': []
    }
    batters = {
        'ranked_normal': [],
        'ranked_superstar': [],
        'unranked_normal': [],
        'unranked_superstar': []
    }
    for character in summed_chars_by_tags:
        key = str()
        if character.type == 1:
            key = 'ranked_normal'
        elif character.type == 2:
            key = 'ranked_superstar'
        elif character.type == 3:
            key = 'unranked_normal'
        elif character.type == 4:
            key = 'unranked_superstar'
        
        if character.outs_pitched >= 12:
            pitchers[key].append({
                "name": character.name,
                "wins": character.wins,
                "losses": character.losses,
                "homeruns": character.homeruns,
                "batting_average": character.hits/character.at_bats,
                "obp": (character.hits + character.walks_bb + character.walks_hit)/(character.at_bats + character.walks_bb + character.walks_hit),
                "rbi": character.rbi,
                "slg": (character.singles + (character.doubles * 2) + (character.triples * 3) + (character.homeruns * 4))/character.at_bats,
                "era": calculate_era(character.runs_allowed, character.outs_pitched),
            })

        if character.at_bats >= 5:
            batters[key].append({
                "name": character.name,
                "wins": character.wins,
                "losses": character.losses,
                "homeruns": character.homeruns,
                "batting_average": character.hits/character.at_bats,
                "obp": (character.hits + character.walks_bb + character.walks_hit)/(character.at_bats + character.walks_bb + character.walks_hit),
                "rbi": character.rbi,
                "slg": (character.singles + (character.doubles * 2) + (character.triples * 3) + (character.homeruns * 4))/character.at_bats,
                "era": calculate_era(character.runs_allowed, character.outs_pitched),
            })

    sorted_pitchers = {
        'ranked_normal': sorted(pitchers['ranked_normal'], key=lambda pitcher: pitcher['era'])[0:6],
        'ranked_superstar':sorted(pitchers['ranked_superstar'], key=lambda pitcher: pitcher['era'])[0:6],
        'unranked_normal': sorted(pitchers['unranked_normal'], key=lambda pitcher: pitcher['era'])[0:6],
        'unranked_superstar': sorted(pitchers['unranked_superstar'], key=lambda pitcher: pitcher['era'])[0:6],
    }

    sorted_batters = {
        'ranked_normal': sorted(batters['ranked_normal'], key=lambda batter: batter['rbi'], reverse=True)[0:6],
        'ranked_superstar': sorted(batters['ranked_superstar'], key=lambda batter: batter['rbi'], reverse=True)[0:6],
        'unranked_normal': sorted(batters['unranked_normal'], key=lambda batter: batter['rbi'], reverse=True)[0:6],
        'unranked_superstar': sorted(batters['unranked_superstar'], key=lambda batter: batter['rbi'], reverse=True)[0:6],
    }

    return {
        'pitchers': sorted_pitchers,
        'batters': sorted_batters,
    }
