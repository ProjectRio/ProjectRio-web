from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, User, Character, Game, ChemistryTable, Tag, GameTag
from ..consts import *
import pprint


@app.route('/characters/', methods = ['GET'])
def get_characters():
    characters = []
    for character in Character.query.all():
        characters.append(character.to_dict())

    return {
        'characters': characters
        }

# API Request URL example: /profile/stats/?recent=10&username=demouser1
@app.route('/profile/stats/', methods = ['GET'])
@jwt_required(optional=True)
def user_stats():
    # # Use JSON Web Token to get username if user is logged in
    # logged_in_user = get_jwt_identity()
    
    # # Get User row
    username = request.args.get('username')
    in_username_lowercase = username.lower()
    user_to_query = User.query.filter_by(username_lowercase=in_username_lowercase).first()

    # If user doesn't exist, abort
    if not user_to_query:
        return abort(408, description='User does not exist')

    # if user_to_query.private and user_to_query.username != logged_in_user:
    #     return {
    #         'private': True,
    #         'username': user_to_query.username
    #     }

    # if not user_to_query.private or user_to_query.username == logged_in_user:
    # Returns dict with most 10 recent games for the user and summary data
    recent_games = games()

    sorted_user_games = get_users_sorted_games(user_to_query.id)

    # Returns JSON with user stats for ranked normal, ranked superstar, unranked normal, unranked superstar, and sum total
    user_totals = get_user_profile_totals(user_to_query.id, sorted_user_games)

    # Returns JSON with top 6 pitchers, top 6 batters, and corresponding stats
    char_totals = get_top_pitchers_and_batters(user_to_query.id)

    # Returns JSON of top 3 captains by winrate with corresponding stats
    captain_totals = get_captain_totals(user_to_query.id)
    captains_by_tags = top_captains_for_tags(user_to_query.id, sorted_user_games)

    return {
        "recent_games": recent_games,
        "username": user_to_query.username,
        "user_totals": user_totals,
        "top_characters": char_totals,
        "top_captains": captain_totals,
    }

def get_users_sorted_games(user_id):
    query = (
        'SELECT '
        'game.game_id AS game_id, '
        'SUM(CASE WHEN game_tag.tag_id = 1 THEN 1 END) AS ranked, ' 
        'SUM(CASE WHEN game_tag.tag_id = 2 THEN 1 END) AS unranked, '
        'SUM(CASE WHEN game_tag.tag_id = 3 THEN 1 END) AS superstar, '
        'SUM(CASE WHEN game_tag.tag_id = 4 THEN 1 END) AS normal '
        'FROM user '
        'JOIN game ON user.id = game.home_player_id OR user.id = game.away_player_id '
        'JOIN game_tag ON game.game_id = game_tag.game_id '
        f'WHERE user.id = {user_id} '
        'GROUP BY game.game_id '
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

    return {
        'ranked_normal': ranked_normal,
        'ranked_superstar': ranked_superstar,
        'unranked_normal': unranked_normal,
        'unranked_superstar': unranked_superstar
    }

def top_captains_for_tags(user_id, games):
    # Join game type arrays into strings separated by commas in order to mimic a tuple for SQL IN statements
    ranked_normal_game_ids_string = ', '.join(games['ranked_normal'])
    ranked_superstar_game_ids_string = ', '.join(games['ranked_superstar'])
    unranked_normal_game_ids_string = ', '.join(games['unranked_normal'])
    unranked_superstar_game_ids_string = ', '.join(games['unranked_superstar'])

    query = (
        'SELECT '
        'character.name AS name, '
        f'CASE WHEN game.game_id IN ({ranked_normal_game_ids_string}) THEN 1 '
            f'WHEN game.game_id IN ({ranked_superstar_game_ids_string}) THEN 2 '
            f'WHEN game.game_id IN ({unranked_normal_game_ids_string}) THEN 3 '
            f'WHEN game.game_id IN ({unranked_superstar_game_ids_string}) THEN 4 '
            'END as type, '
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
        'AND character_game_summary.captain = 1 '
        'GROUP BY character_game_summary.char_id, type'
    )

    summed_captains_by_type = db.session.execute(query).all()
    captains = {
        'ranked_normal': [],
        'ranked_superstar': [],
        'unranked_normal': [],
        'unranked_superstar': []
    }

    for captain in summed_captains_by_type:
        key = str()
        if captain.type == 1:
            key = 'ranked_normal'
        elif captain.type == 2:
            key = 'ranked_superstar'
        elif captain.type == 3:
            key = 'unranked_normal'
        elif captain.type == 4:
            key = 'unranked_superstar'

        captains[key].append({
                "name": captain.name,
                "wins": captain.wins,
                "losses": captain.losses,
                "homeruns": captain.homeruns,
                "batting_average": captain.hits/captain.at_bats,
                "obp": (captain.hits + captain.walks_bb + captain.walks_hit)/(captain.at_bats + captain.walks_bb + captain.walks_hit),
                "rbi": captain.rbi,
                "slg": (captain.singles + (captain.doubles * 2) + (captain.triples * 3) + (captain.homeruns * 4))/captain.at_bats,
                "era": calculate_era(captain.runs_allowed, captain.outs_pitched),
            })

    return captains


def get_user_profile_totals(user_id, games):
    # Join game type arrays into strings separated by commas in order to mimic a tuple for SQL IN statements
    ranked_normal_game_ids_string = ', '.join(games['ranked_normal'])
    ranked_superstar_game_ids_string = ', '.join(games['ranked_superstar'])
    unranked_normal_game_ids_string = ', '.join(games['unranked_normal'])
    unranked_superstar_game_ids_string = ', '.join(games['unranked_superstar'])

    query = (
        'SELECT '
        f'CASE WHEN game.game_id IN ({ranked_normal_game_ids_string}) THEN 1 '
            f'WHEN game.game_id IN ({ranked_superstar_game_ids_string}) THEN 2 '
            f'WHEN game.game_id IN ({unranked_normal_game_ids_string}) THEN 3 '
            f'WHEN game.game_id IN ({unranked_superstar_game_ids_string}) THEN 4 '
            'END as type, '
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

# Returns list of the top 3 Captains by winrate with 5 or more games and their stats
def get_captain_totals(user_id):
    query = (
        'SELECT '
        'character.name as name, '
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
        'COUNT(character_game_summary.game_id) AS games, '
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
        'AND character_game_summary.captain = 1 '
        'GROUP BY character_game_summary.char_id'
    )

    result = db.session.execute(query).all()

    captains = sorted(result, key=lambda captain: captain.wins/captain.games, reverse=True)
    top_captains = []
    for captain in captains: 
        if captain.games >= 5 and len(top_captains) < 3:
            top_captains.append({
                "name": captain.name,
                "wins": captain.wins,
                "losses": captain.losses,
                "homeruns": captain.homeruns,
                "batting_average": captain.hits/captain.at_bats,
                "obp": (captain.hits + captain.walks_bb + captain.walks_hit)/(captain.at_bats + captain.walks_bb + captain.walks_hit),
                "rbi": captain.rbi,
                "slg": (captain.singles + (captain.doubles * 2) + (captain.triples * 3) + (captain.homeruns * 4))/captain.at_bats,
                "era": calculate_era(captain.runs_allowed, captain.outs_pitched),
            })

    return top_captains

# Returns the top 6 batters and pitchers according to rbi and era, along with their summary stats. (Summary stats are kept seperate to reduce possible duplication)
def get_top_pitchers_and_batters(user_id):
    query = (
        'SELECT '
        'character.name as name, '
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
        'COUNT(character_game_summary.game_id) AS games, '
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
        'GROUP BY character_game_summary.char_id'
    )

    result = db.session.execute(query).all()

    # Get top 6 batter by rbi where they have more than 20 at bats
    batters = sorted(result, key=lambda batter: batter.rbi, reverse=True)
    top_batters = [batter.name for batter in batters if batter.at_bats > 10][0:6]

    # Get top 6 pitchers by era where they have more than 135 outs pitched
    pitchers = sorted(result, key=lambda pitcher: calculate_era(pitcher.runs_allowed, pitcher.outs_pitched))
    top_pitchers = [pitcher.name for pitcher in pitchers if pitcher.outs_pitched > 60][0:6]

    top_characters = {
        "top_pitchers": top_pitchers,
        "top_batters": top_batters,
        "character_values": {}
    }
    for row in result:
        if row.name in top_batters or row.name in top_pitchers:
            top_characters["character_values"][row.name] = {
                "games": row.games,
                "wins": row.wins,
                "losses": row.losses,
                "homeruns": row.homeruns,
                "batting_average": row.hits/row.at_bats,
                "obp": (row.hits + row.walks_bb + row.walks_hit)/(row.at_bats + row.walks_bb + row.walks_hit),
                "rbi": row.rbi,
                "slg": (row.singles + (row.doubles * 2) + (row.triples * 3) + (row.homeruns * 4))/row.at_bats,
                "era": calculate_era(row.runs_allowed, row.outs_pitched),
            }
    
    return top_characters

def calculate_era(runs_allowed, outs_pitched):
    if outs_pitched == 0 and runs_allowed > 0:
        return -abs(runs_allowed)
    elif outs_pitched > 0:
        return runs_allowed/(outs_pitched/3)
    else:
        return 0



# URL example: http://127.0.0.1:5000/games/?recent=5&username=demOuser4&username=demouser1&username=demouser5&tag=ranked&vs=True
@app.route('/games/', methods = ['GET'])
def games():
    # === validate passed parameters ===
    try:
        # Check if tags are valid and get a list of corresponding ids
        tags = request.args.getlist('tag')
        tags_lowercase = tuple([tag.lower() for tag in tags])
        tag_rows = db.session.query(Tag).filter(Tag.name_lowercase.in_(tags_lowercase)).all()
        tag_ids = tuple([tag.id for tag in tag_rows])
        if len(tag_ids) != len(tags):
            abort(400)
        
        # Check if usernames are valid and get array of corresponding ids
        usernames = request.args.getlist('username')
        usernames_lowercase = tuple([username.lower() for username in usernames])
        users = db.session.query(User).filter(User.username_lowercase.in_(usernames_lowercase)).all() 
        if len(usernames) != len(users):
            abort(400)

        # If true, returned values will return games that contain the first passed username when playing against other provided usernames
        vs = True if request.args.get('vs') == 'True' else False

        user_id_list = []
        for index, user in enumerate(users):
            # primary_user_id is theid of the first username provided in the url, it is used when querying
            # for games that must contain that username paired with n number of other provided usernames
            if vs == True and user.username_lowercase == usernames_lowercase[0]:
                primary_user_id = user.id
            user_id_list.append(user.id)
        user_ids = tuple(user_id_list)

        recent = int(request.args.get('recent')) if request.args.get('recent') is not None else None
    except:
       return abort(400, 'Invalid Username or Tag')


    # === Set dynamic query values ===
    limit = str()
    order_by = str()
    if (recent == None):
        limit = ''
        order_by = ''
    else:
        limit = 'LIMIT {}'.format(recent)
        order_by = 'ORDER BY game.date_time DESC '

    where_user = str()
    if user_ids:
        if len(user_ids) > 1:
            if vs == True:
                where_user = (
                    f'WHERE (game.away_player_id = {primary_user_id} AND game.home_player_id IN {user_ids}) '
                    f'OR (game.home_player_id = {primary_user_id} AND game.away_player_id IN {user_ids})'
                )
            else:
                where_user = f'WHERE (game.away_player_id IN {user_ids} OR game.home_player_id IN {user_ids})'
        else:
            where_user = f'WHERE (game.away_player_id = {user_ids[0]} OR game.home_player_id = {user_ids[0]})'
    else:
        where_user = ''

    tag_cases = str()
    having_tags = str()
    join_tags = str()
    group_by = str()
    if tags:
        join_tags = (
            'LEFT JOIN game_tag ON game.game_id = game_tag.game_id '
            'LEFT JOIN tag ON game_tag.tag_id = tag.id '
        )
        for index, tag_id in enumerate(tag_ids):
            tag_cases += f'SUM(CASE WHEN game_tag.tag_id = {tag_id} THEN 1 END) AS tag_{index}, '
            having_tags += f'HAVING tag_{index} ' if index == 0 else f'AND tag_{index} '

        group_by = 'GROUP BY game_tag.game_id'


    # === Construct query === 
    query = (
        'SELECT '
        'game.game_id AS game_id, '
        f'{tag_cases}'
        'game.date_time AS date_time, '
        'game.away_score AS away_score, '
        'game.home_score AS home_score, '
        'game.innings_played AS innings_played, '
        'game.innings_selected AS innings_selected, '
        'away_player.username AS away_player, '
        'home_player.username AS home_player, '
        'away_captain.name AS away_captain, '
        'home_captain.name AS home_captain '   
        'FROM game '
        f'{join_tags} '
        'LEFT JOIN user AS away_player ON game.away_player_id = away_player.id '
        'LEFT JOIN user AS home_player ON game.home_player_id = home_player.id '
        'LEFT JOIN character_game_summary AS away_character_game_summary '
            'ON game.game_id = away_character_game_summary.game_id '
            'AND away_character_game_summary.user_id = away_player.id '
            'AND away_character_game_summary.captain = True '
        'LEFT JOIN character_game_summary AS home_character_game_summary '
            'ON game.game_id = home_character_game_summary.game_id '
            'AND home_character_game_summary.user_id = home_player.id '
            'AND home_character_game_summary.captain = True '
        'LEFT JOIN character AS away_captain ON away_character_game_summary.char_id = away_captain.char_id '
        'LEFT JOIN character AS home_captain ON home_character_game_summary.char_id = home_captain.char_id '
        f'{where_user} '
        f'{group_by} '
        f'{having_tags} '
        f'{order_by}'
        f'{limit}'
    )

    results = db.session.execute(query).all()
    
    games = []
    game_ids = []
    for game in results:
        game_ids.append(game.game_id)

        games.append({
            'Id': game.game_id,
            'Datetime': game.date_time,
            'Away User': game.away_player,
            'Away Captain': game.away_captain,
            'Away Score': game.away_score,
            'Home User': game.home_player,
            'Home Captain': game.home_captain,
            'Home Score': game.home_score,
            'Innings Played': game.innings_played,
            'Innings Selected': game.innings_selected,
            'Tags': []
        })



    # If there are games with matching tags, get all additional tags they have
    if game_ids:
        where_game_id = str()
        if len(game_ids) == 1:
            where_game_id = f'WHERE game_tag.game_id = {game_ids[0]} '
        else:
            where_game_id = f'WHERE game_tag.game_id IN {tuple(game_ids)} '

        tags_query = (
            'SELECT '
            'game_tag.game_id as game_id, '
            'game_tag.tag_id as tag_id, '
            'tag.name as name '
            'FROM game_tag '
            'LEFT JOIN tag ON game_tag.tag_id = tag.id '
            f'{where_game_id}'
            'GROUP BY game_id, tag_id'
        )

        tag_results = db.session.execute(tags_query).all()
        for tag in tag_results:
            for game in games:
                if game['Id'] == tag.game_id:
                    game['Tags'].append(tag.name)

    return {'games': games}



# == Functions to return coordinates for graphing ==
'''
    - Game params (args): Same params as games. Use to get games with proper tags/users/etc
    - Char Id (list):     List of characters to get coordinates for
    - TypeOfHit (list):   List of contact types to get data for
    - TypeOfSwing (list): List of swing types to get data for
    - Hand (list):        List of batterhands

'''
@app.route('/batter_position_data/', methods = ['GET'])
def endpoint_batter_position():

        # === Construct query === 
    list_of_games = games()   # List of dicts of games we want data from and info about those games
    list_of_game_ids = list() # Holds IDs for all the games we want data from

    print(list_of_games)
    for game_dict in list_of_games['games']:
        list_of_game_ids.append(game_dict['Id'])

    list_of_game_ids = tuple(list_of_game_ids)
    print(list_of_game_ids)


    #Get list of game_ids from list_of_games

    # Apply filters
    #   WHERE batter.hand in input_hand
    #   WHERE contact.type_of_contact in input_typeofcontact
    #   WHERE pitch.type_of_swing in input_typeofswing
    #   WHERE character.char_id in input_char_ids
    query = (
        'SELECT '
        'game.game_id AS game_id, '
        'event.id AS event_id, '
        'character.char_id AS char_id, '
        'contact.batter_x_pos_upon_hit AS batter_x_pos, '
        'contact.batter_z_pos_upon_hit AS batter_z_pos, '
        'contact.ball_x_pos_upon_hit AS ball_x_pos, '
        'contact.ball_z_pos_upon_hit AS ball_z_pos, '
        'contact.type_of_contact AS type_of_contact, '
        'pitch.pitch_result AS pitch_result, '
        'pitch.type_of_swing AS type_of_swing '
        'FROM game '
        'LEFT JOIN event ON event.game_id = game.game_id '
        'LEFT JOIN pitch_summary AS pitch ON pitch.id = event.pitch_summary_id '
            'AND pitch.pitch_result = 6 ' #Pitch_result == 6 is contact TODO make constant
        'LEFT JOIN contact_summary AS contact ON contact.id = pitch.contact_summary_id '
        'LEFT JOIN character_game_summary AS batter ON batter.id = pitch.batter_id '
        'LEFT JOIN character ON character.char_id = batter.char_id ' #Not sure we actually need this
       f'WHERE (game.game_id IN {list_of_game_ids}) '
    )

    print(query)

    result = db.session.execute(query).all()
    print(result)
    for entry in result:
        print(entry._asdict())

    #Format output data and return
    '''
    Format:
        {
            "Batter Character ID": 0-53,
            "Ball upon hit X position": float,
            "Ball upon hit Z position": float,
            "Batter upon hit X position": float,
            "Batter upon hit Z position": float,
            "Batter hand": bool
            "Type of contact": left-sour, left-nice, perfect...
            "Type of swing": slap, star, charge
        }
    '''


# URL example: http://127.0.0.1:5000/user_character_stats/?username=demouser1&character=mario
# UNDER CONSTRUCTION
@app.route('/user_character_stats/', methods = ['GET'])
def get_user_character_stats():
    # verify username
    in_username = request.args.get('username')
    in_username_lowercase = in_username.lower()
    user = User.query.filter_by(username_lowercase=in_username_lowercase).first()

    if not user:
        return abort(408, description='User does not exist')

    user_id = user.id

    # verify character
    in_char_name = request.args.get('character')
    in_char_name_lowercase = in_char_name.lower()
    character = Character.query.filter_by(name_lowercase=in_char_name_lowercase).first()

    if not character:
        return abort(408, description='Character does not exist')

    char_id = character.char_id
    
    # batting_stats = get_batting_stats(user_id, char_id)
    pitching_and_fielding_stats = get_pitching_and_fielding_stats(user_id, char_id)

    return {
        'Batting Stats': batting_stats,
        "Pitching Stats": pitching_and_fielding_stats,
        "Fielding Stats": pitching_and_fielding_stats,
    }

def get_batting_stats(user_id, char_id):
    query = (
        'SELECT '
        'character.name AS name, '
        'character_game_summary.char_id AS char_id, '
        'pitch_summary.type_of_swing AS type_of_swing, '
        # 'COUNT(CASE WHEN pitch_summary.pitch_result = 'WALK_BB' AS 1 ELSE NULL END) AS walks_bb, '
        # 'COUNT(CASE WHEN pitch_summary.pitch_result = 'WALKS_HIT' AS 1 ELSE NULL END) AS walks_hit, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_primary = 'OUT' AS 1 ELSE NULL END) AS outs, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_primary = 'FOUL' AS 1 ELSE NULL END) AS foul_hits, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_primary = 'FAIR' AS 1 ELSE NULL END) AS fair_hits, '
        # 'COUNT(CASE WHEN contact_summary.type_of_contact = 'SOUR' AS 1 ELSE NULL END) AS sour_hits, '
        # 'COUNT(CASE WHEN contact_summary.type_of_contact = 'NICE' AS 1 ELSE NULL END) AS nice_hits, '
        # 'COUNT(CASE WHEN contact_summary.type_of_contact = 'PERFECT' AS 1 ELSE NULL END) AS perfect_hits, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'SINGLE' AS 1 ELSE NULL END) AS singles, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'DOUBLE' AS 1 ELSE NULL END) AS doubles, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'TRIPLE' AS 1 ELSE NULL END) AS triples, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'HOMERUN' AS 1 ELSE NULL END) AS homeruns, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'DOUBLE PLAY' AS 1 ELSE NULL END) AS double_plays, '
        # 'COUNT(CASE WHEN contact_summary.contact_result_secondary = 'SACFLY' AS 1 ELSE NULL END) AS sacflys, '
        'SUM(ABS(contact_summary.ball_x_pos)) AS ball_x_pos_total, '
        'SUM(ABS(contact_summary.ball_z_pos)) AS ball_z_pos_total, '
        'FROM character_game_summary '
        'LEFT JOIN character ON character_game_summary.char_id = character.char_id '
        'LEFT JOIN pitch_summary ON character_game_summary.id = pitch_summary.batter_id '
        'LEFT JOIN contact_summary ON pitch_summary.contact_summary_id = contact_summary.id '
        'WHERE character_game_summary.user_id = {user_id} '
        'AND character_game_summary.char_id = {char_id} '
        'GROUP BY character_game_summary.char_id, pitch_summary.type_of_swing '
    )

    results = db.session.execute(query).all()

    batting_stats = {}
    for character in results:
        batting_stats[character.name] = {
            'insert stats here': 'insert stats here'
        }

    return batting_stats

def get_pitching_and_fielding_stats(user_id, char_id):
    query = (
        'SELECT '
        'SUM(batters_faced) AS batters_faced, '
        'SUM(earned_runs) AS earned_runs, '
        'SUM(runs_allowed) AS runs_allowed, '
        'SUM(hits_allowed) AS hits_allowed, '
        'SUM(strikeouts_pitched) AS strikeouts_pitched, '
        'SUM(star_pitches_thrown) AS star_pitches_thrown, '
        'SUM(defensive_star_successes) AS defensive_star_successes, '
        'SUM(outs_pitched) AS outs_pitched, '
        'SUM(offensive_stars_used) AS offensive_stars_used, '
        'SUM(defensive_stars_used) AS defensive_stars_used, '
        'SUM(offensive_star_chances_won) AS offensive_star_chances_won, '
        'SUM(deffensive_star_chances_won) AS defensive_star_chances_won, '
        'SUM(total_pitches) AS total_pitches, '
        # Insert other stats once questions addressed
        'FROM character_game_summary '
        'WHERE character_game_summary.user_id = {user_id} '
        'GROUP BY character_game_summary.char_id'
    )

    results = db.session.execute(query).all()
    pitching_and_fielding_stats = {}
    for character in results:
        pitching_and_fielding_stats[character.name] = {
            'insert stats here': 'insert stats here'
        }

    return pitching_and_fielding_stats
