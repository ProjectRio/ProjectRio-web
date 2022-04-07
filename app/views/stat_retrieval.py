from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, User, Character, Game, ChemistryTable, Tag, GameTag
from ..consts import *

import time
import datetime

import pprint
import itertools

# == Helper functions for SQL query formatting
# Returns tuple in SQL ready string and a bool to indicate if query is empty
def format_tuple_for_SQL(in_tuple, none_on_empty=False):
    sql_tuple = "(" + ",".join(repr(v) for v in in_tuple) + ")"
    
    return (sql_tuple, (len(in_tuple) == 0))

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
    recent_games = endpoint_games()

    # Returns JSON with user stats for ranked normal, ranked superstar, unranked normal, unranked superstar, and sum total
    user_totals = get_user_profile_totals(user_to_query.id)

    # These will be changed later, but currently they get TOP pitchers, hitters, and captains using a dynamically crafted query
    char_query = create_query(user_to_query.id, cCharacters)
    captain_query = create_query(user_to_query.id, cCaptains)
    char_totals = get_per_char_totals(user_to_query.id, char_query)
    captain_totals = get_captain_totals(user_to_query.id, captain_query)

    return {
        "recent_games": recent_games,
        "username": user_to_query.username,
        "user_totals": user_totals,
        "top_characters": char_totals,
        "top_captains": captain_totals,
    }

def get_user_profile_totals(user_id):
    game_ids_by_type_query = (
        'SELECT '
        'game.game_id AS game_id, '
        'SUM(CASE WHEN game_tag.tag_id = 1 THEN 1 END) AS ranked, ' 
        'SUM(CASE WHEN game_tag.tag_id = 2 THEN 1 END) AS unranked, '
        'SUM(CASE WHEN game_tag.tag_id = 3 THEN 1 END) AS superstar, '
        'SUM(CASE WHEN game_tag.tag_id = 4 THEN 1 END) AS normal '
        'FROM user '
        'LEFT JOIN game ON user.id = game.home_player_id OR user.id = game.away_player_id '
        'LEFT JOIN game_tag ON game.game_id = game_tag.game_id '
        f'WHERE user.id = {user_id} '
        'GROUP BY game.game_id '
    )
    games_by_type = db.session.execute(game_ids_by_type_query).all()
    
    # Sort games according to their corresponding tags, we will use these later to get totals per tag combination
    ranked_normal = []
    ranked_superstar = []
    unranked_normal = []
    unranked_superstar = []
    for game in games_by_type:
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

    # Join game type arrays into strings separated by commas in order to mimic a tuple for SQL IN statements
    ranked_normal_game_ids_string = ', '.join(ranked_normal)
    ranked_superstar_game_ids_string = ', '.join(ranked_superstar)
    unranked_normal_game_ids_string = ', '.join(unranked_normal)
    unranked_superstar_game_ids_string = ', '.join(unranked_superstar)

    sum_games_by_type_query = (
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
        'LEFT JOIN character_game_summary ON game.game_id = character_game_summary.game_id '
        f'WHERE character_game_summary.user_id = {user_id} '
        'GROUP BY character_game_summary.user_id, type'
    )

    summed_games_by_type = db.session.execute(sum_games_by_type_query).all()

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

    for sum in summed_games_by_type:
        user_totals['all']['losses'] += sum.losses
        user_totals['all']['wins'] += sum.wins
        user_totals['all']['runs_allowed'] += sum.runs_allowed
        user_totals['all']['outs_pitched'] += sum.outs_pitched
        user_totals['all']['hits'] += sum.hits
        user_totals['all']['at_bats'] += sum.at_bats
        user_totals['all']['walks_bb'] += sum.walks_bb
        user_totals['all']['walks_hit'] += sum.walks_hit
        user_totals['all']['rbi'] += sum.rbi
        user_totals['all']['singles'] += sum.singles
        user_totals['all']['doubles'] += sum.doubles
        user_totals['all']['triples'] += sum.triples
        user_totals['all']['homeruns'] += sum.homeruns
        
        key = str()
        if sum.type == 1:
            key = 'ranked_normal'
        elif sum.type == 2:
            key = 'ranked_superstar'
        elif sum.type == 3:
            key = 'unranked_normal'
        elif sum.type == 4:
            key = 'unranked_superstar'
        
        user_totals[key] = {
            'losses': sum.losses,
            'wins': sum.wins,
            'homeruns': sum.homeruns,
            'batting_average': sum.hits/sum.at_bats,
            'obp': (sum.hits + sum.walks_bb + sum.walks_hit)/(sum.at_bats + sum.walks_bb + sum.walks_hit),
            'slg': (sum.singles + (sum.doubles * 2) + (sum.triples * 3) + (sum.homeruns * 4))/sum.at_bats,
            'rbi': sum.rbi,
            'era': calculate_era(sum.runs_allowed, sum.outs_pitched)
        }

    user_totals['all']['batting_average'] = user_totals['all']['hits']/user_totals['all']['at_bats']
    user_totals['all']['obp'] = (user_totals['all']['hits'] + user_totals['all']['walks_bb'] + user_totals['all']['walks_hit']) / (user_totals['all']['at_bats'] + user_totals['all']['walks_bb'] + user_totals['all']['walks_hit'])
    user_totals['all']['slg'] = (user_totals['all']['singles'] + (user_totals['all']['doubles'] * 2) + (user_totals['all']['triples'] * 3) + (user_totals['all']['homeruns'] * 4))/user_totals['all']['at_bats']
    user_totals['all']['era'] = calculate_era(user_totals['all']['runs_allowed'], user_totals['all']['outs_pitched'])
    return user_totals

def create_query(user_id, query_subject):
    left_join_character_statement = str()
    group_by_statement = str()
    character_name_statement = str()
    where_captain_statement = str()

    # Construct query to return 1 row for every character or 1 row with totals from all characters
    if query_subject is cCharacters:
        left_join_character_statement = 'LEFT JOIN character ON character_game_summary.char_id = character.char_id '
        group_by_statement = 'GROUP BY character_game_summary.char_id'
        character_name_statement = 'character.name as name, '
    elif query_subject is cCaptains:
        left_join_character_statement = 'LEFT JOIN character ON character_game_summary.char_id = character.char_id '
        group_by_statement = 'GROUP BY character_game_summary.char_id'
        character_name_statement = 'character.name as name, '
        where_captain_statement = 'AND character_game_summary.captain = 1 '

    query = (
        'SELECT '
        f'{character_name_statement}'
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
        'LEFT JOIN game ON character_game_summary.game_id = game.game_id '
        f'{left_join_character_statement}'
        f'WHERE character_game_summary.user_id = {user_id} '
        f'{where_captain_statement}'
        f'{group_by_statement}'
    )
    
    return query

# Returns list of the top 3 Captains and summary stats according to their winrate
def get_captain_totals(user_id, query):
    result = db.session.execute(query).all()

    sorted_captains = sorted(result, key=lambda captain: captain.wins/captain.games, reverse=True)[0:3]

    top_captains = []
    for captain in sorted_captains: 
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
def get_per_char_totals(user_id, query):
    result = db.session.execute(query).all()

    # Get top 6 batter by rbi where they have more than 20 at bats
    batters = sorted(result, key=lambda batter: batter.rbi, reverse=True)
    top_batters = [batter.name for batter in batters if batter.at_bats > 20][0:6]

    # Get top 6 pitchers by era where they have more than 135 outs pitched
    pitchers = sorted(result, key=lambda pitcher: calculate_era(pitcher.runs_allowed, pitcher.outs_pitched))
    top_pitchers = [pitcher.name for pitcher in pitchers if pitcher.outs_pitched > 135][0:6]

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


## === Detailed stats ===
'''
@ Description: Returns games that fit the parameters
@ Params:
    - tag - list of tags to filter by
    - exclude_tag - List of tags to exclude from search
    - start date - Unix time. Provides the lower (older) end of the range of games to retreive. Overrides recent
    - end_date - Unix time. Provides the lower (older) end of the range of games to retreive. Defaults to now (time of query). Overrides recent
    - username - list of users who appear in games to retreive
    - vs_username - list of users who MUST also appear in the game along with users
    - recent - Int of number of games

@ Output:
    - List of games and highlevel info based on flags

@ URL example: http://127.0.0.1:5000/games/?recent=5&username=demOuser4&username=demouser1&username=demouser5
'''
@app.route('/games/', methods = ['GET'])
def endpoint_games():
    # === validate passed parameters ===
    try:
        # Check if tags are valid and get a list of corresponding ids
        tags = request.args.getlist('tag')
        tags_lowercase = tuple([tag.lower() for tag in tags])
        tag_rows = db.session.query(Tag).filter(Tag.name_lowercase.in_(tags_lowercase)).all()
        tag_ids = tuple([tag.id for tag in tag_rows])
        if len(tag_ids) != len(tags):
            abort(400)

        # Check if exclude_tags are valid and get a list of corresponding ids
        exclude_tags = request.args.getlist('exclude_tag')
        exclude_tags_lowercase = tuple([exclude_tag.lower() for exclude_tag in exclude_tags])
        exclude_tag_rows = db.session.query(Tag).filter(Tag.name_lowercase.in_(exclude_tags_lowercase)).all()
        exclude_tag_ids = tuple([exclude_tag.id for exclude_tag in exclude_tag_rows])
        if len(exclude_tag_ids) != len(exclude_tags):
            abort(400)

        #Get user ids from list of users
        usernames = request.args.getlist('username')
        usernames_lowercase = tuple([username.lower() for username in usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_user_id_tuples = db.session.query(User.id).filter(User.username_lowercase.in_(usernames_lowercase)).all()
        # using list comprehension
        list_of_user_id = list(itertools.chain(*list_of_user_id_tuples))
        tuple_user_ids = tuple(list_of_user_id)

        #Get user ids from list of users
        vs_usernames = request.args.getlist('vs_username')
        vs_usernames_lowercase = tuple([username.lower() for username in vs_usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_vs_user_id_tuples = db.session.query(User.id).filter(User.username_lowercase.in_(vs_usernames_lowercase)).all()
        # using list comprehension
        list_of_vs_user_id = list(itertools.chain(*list_of_vs_user_id_tuples))
        tuple_vs_user_ids = tuple(list_of_vs_user_id)

        recent = int(request.args.get('recent')) if request.args.get('recent') is not None else None
    except:
       return abort(400, 'Invalid Username or Tag')


    # === Set dynamic query values ===

    #Build User strings
    user_id_string, user_empty = format_tuple_for_SQL(tuple_user_ids)
    vs_user_id_string, vs_user_empty = format_tuple_for_SQL(tuple_vs_user_ids)

    where_user_sql_statement = f"(game.away_player_id {'NOT' if user_empty else ''} IN {user_id_string} OR game.home_player_id {'NOT' if user_empty else ''} IN {user_id_string}) \n"
    where_vs_user_sql_statement = f"AND (game.away_player_id {'NOT' if vs_user_empty else ''} IN {vs_user_id_string} OR game.home_player_id {'NOT' if vs_user_empty else ''} IN {vs_user_id_string}) \n"

    #Build GameTime strings
    start_time_unix = 0
    if (request.args.get('start_time') != None):
        try:
            start_time = request.args.get('start_time')
            start_time_strs = start_time.split('-') #YYYY-MM-DD
            print(start_time_strs)
            dt = datetime.datetime(year=int(start_time_strs[0]), month=int(start_time_strs[1]), day=int(start_time_strs[2]))
            start_time_unix = round(time.mktime(dt.timetuple()))
        except:
            return abort(408, 'Invalid start time format')
    
    end_time_unix = 0
    if (request.args.get('end_time') != None):
        try:
            end_time = request.args.get('end_time')
            end_time_strs = end_time.split('-') #YYYY-MM-DD
            dt = datetime.datetime(year=int(end_time_strs[0]), month=int(end_time_strs[1]), day=int(end_time_strs[2]))
            end_time_unix = round(time.mktime(dt.timetuple()))
        except:
            return abort(408, 'Invalid end time format')
    
    #Set start time to now if its 0
    if (start_time_unix == 0):
        start_time_unix = round(time.time())
    where_start_time_sql_statement = f"AND game.date_time < {start_time_unix} \n" if start_time_unix != 0 else ''
    where_end_time_sql_statement = f"AND game.date_time > {end_time_unix} \n" if end_time_unix != 0 else ''
    
    tag_cases = str()
    having_tags = str()
    join_tags = str()
    group_by = str()
    if tags:
        join_tags = (
            'JOIN game_tag ON game.game_id = game_tag.game_id \n'
            'JOIN tag ON game_tag.tag_id = tag.id \n'
        )
        for index, tag_id in enumerate(tag_ids):
            tag_cases += f'SUM(CASE WHEN game_tag.tag_id = {tag_id} THEN 1 END) AS tag_{index}, '
            having_tags += f'HAVING tag_{index} ' if index == 0 else f'AND tag_{index} '

        group_by = 'GROUP BY game_tag.game_id'

    exclude_tag_cases = str()
    having_exclude_tags = str()

    if exclude_tags:
        if join_tags == "":
            join_tags = (
            'JOIN game_tag ON game.game_id = game_tag.game_id \n'
            'JOIN tag ON game_tag.tag_id = tag.id \n'
            )

        for index, exclude_tag_id in enumerate(exclude_tag_ids):
            exclude_tag_cases += f'SUM(CASE WHEN game_tag.tag_id = {exclude_tag_id} THEN 1 ELSE 0 END) AS exclude_tag_{index}, '

            if having_tags == "":
                having_exclude_tags += f'HAVING exclude_tag_{index} = 0' if index == 0 else f' AND exclude_tag_{index} = 0'
            else:
                having_exclude_tags += f' AND exclude_tag_{index} = 0'

        if group_by == "":
            group_by = 'GROUP BY game_tag.game_id'

    # === Construct query === 
    query = (
        'SELECT '
        'game.game_id AS game_id, \n'
        f'{tag_cases} \n'
        f'{exclude_tag_cases} \n'
        'game.date_time AS date_time, \n'
        'game.away_score AS away_score, \n'
        'game.home_score AS home_score, \n'
        'game.innings_played AS innings_played, \n'
        'game.innings_selected AS innings_selected, \n'
        'away_player.username AS away_player, \n'
        'home_player.username AS home_player, \n'
        'away_captain.name AS away_captain, \n'
        'home_captain.name AS home_captain \n'   
        'FROM game '
        f'{join_tags} '
        'JOIN user AS away_player ON game.away_player_id = away_player.id \n'
        'JOIN user AS home_player ON game.home_player_id = home_player.id \n'
        'JOIN character_game_summary AS away_captain_game_summary \n'
            'ON game.game_id = away_captain_game_summary.game_id \n'
            'AND away_captain_game_summary.user_id = away_player.id \n'
            'AND away_captain_game_summary.captain = True \n'
        'JOIN character_game_summary AS home_captain_game_summary \n'
            'ON game.game_id = home_captain_game_summary.game_id \n'
            'AND home_captain_game_summary.user_id = home_player.id \n'
            'AND home_captain_game_summary.captain = True \n'
        'JOIN character AS away_captain ON away_captain_game_summary.char_id = away_captain.char_id \n'
        'JOIN character AS home_captain ON home_captain_game_summary.char_id = home_captain.char_id \n'
        f'WHERE {where_user_sql_statement} {where_vs_user_sql_statement} {where_start_time_sql_statement} {where_end_time_sql_statement} '
        f'{group_by} \n'
        f'{having_tags} {having_exclude_tags} \n'
        f'ORDER BY game.date_time DESC \n'
        f"{('LIMIT ' + str(recent)) if recent != None else ''}" #Limit values if limit provided, otherwise return all
    )

    #print(query)

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
    list_of_games = endpoint_games()   # List of dicts of games we want data from and info about those games
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
        'JOIN event ON event.game_id = game.game_id '
        'JOIN pitch_summary AS pitch ON pitch.id = event.pitch_summary_id '
            'AND pitch.pitch_result = 6 ' #Pitch_result == 6 is contact TODO make constant
        'JOIN contact_summary AS contact ON contact.id = pitch.contact_summary_id '
        'JOIN character_game_summary AS batter ON batter.id = pitch.batter_id '
        'JOIN character ON character.char_id = batter.char_id ' #Not sure we actually need this
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

## === Detailed stats ===
'''
@ Description: Returns batting, pitching, fielding, and star stats on configurable levels
@ Params:
    - Username (list):  List of users to get stats for. All users if blank
    - Character (list): List of character ids to get stats for. All charas if blank
    - Games (list):     List of game ids to use. If not provided arguments for /games/ endpoint will be expected and used
    - by_user (bool):   When true stats will be organized by user. When false, all users will be 
                        combined
    - by_char (bool):   When true stats will be organized by character. When false, 
                        all characters will be combined
    - by_swing (bool):  When true batting stats will be organized by swing type (slap, charge, star). When false, 
                        all swings will be combined. Only considered for swings
    - exlude_nonfair:   Exlude foul and unknown hits from the return
    - Games parms:      All params for /games/ endpoint. Determines the games that will be considered
@ Output:
    - Output is variable based on the "by_XXX" flags. Helper function update_detailed_stats_dict builds and updates
      the large return dict at each step

@ URL example: http://127.0.0.1:5000/detailed_stats/?username=demouser1&character=1&by_swing=1
'''
@app.route('/detailed_stats/', methods = ['GET'])
def endpoint_detailed_stats():

    #Sanitize games params 
    try:
        list_of_game_ids = list() # Holds IDs for all the games we want data from
        if (len(request.args.getlist('games')) != 0):
            list_of_game_ids = [int(game_id) for game_id in request.args.getlist('games')]
            list_of_game_id_tuples = db.session.query(Game.game_id).filter(Game.game_id.in_(tuple(list_of_game_ids))).all()
            if (len(list_of_game_id_tuples) != len(list_of_game_ids)):
                return abort(408, description='Provided GameIDs not found')

        else:
            list_of_games = endpoint_games()   # List of dicts of games we want data from and info about those games
            for game_dict in list_of_games['games']:
                list_of_game_ids.append(game_dict['Id'])
    except:
        abort(408, description='Invalid GameID')

    # Sanitize character params
    try:
        list_of_char_ids = request.args.getlist('character')
        for index, char_id in enumerate(list_of_char_ids):
            sanitized_id = int(list_of_char_ids[index])
            if sanitized_id in range (0,55):
                list_of_char_ids[index] = sanitized_id
            else:
                return abort(400, description = "Char ID not in range")
    except:
        return abort(400, description="Invalid Char Id")


    tuple_of_game_ids = tuple(list_of_game_ids)
    tuple_char_ids = tuple(list_of_char_ids)
    group_by_user = (request.args.get('by_user') == '1')
    group_by_swing = (request.args.get('by_swing') == '1')
    group_by_char = (request.args.get('by_char') == '1')
    exclude_nonfair = (request.args.get('exclude_nonfair') == '1')

    usernames = request.args.getlist('username')
    usernames_lowercase = tuple([username.lower() for username in usernames])
    #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
    list_of_user_id_tuples = db.session.query(User.id).filter(User.username_lowercase.in_(usernames_lowercase)).all()
    # using list comprehension
    list_of_user_id = list(itertools.chain(*list_of_user_id_tuples))

    tuple_user_ids = tuple(list_of_user_id)

    #If we didn't find every user provided in the DB, abort
    if (len(tuple_user_ids) != len(usernames)):
        return abort(408, description='Provided Usernames no found')

    #If a char was provided that is not 0-54 abort
    invalid_chars=[i for i in tuple_char_ids if int(i) not in range(0,55)]
    if len(invalid_chars) > 0:
        return abort(408, description='Invalid provided characters')

    
    # Individual functions create queries to get their respective stats
    return_dict = {}
    batting_stats = query_detailed_batting_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char, group_by_swing, exclude_nonfair)
    pitching_stats = query_detailed_pitching_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)
    misc_stats = query_detailed_misc_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)
    fielding_stats = query_detailed_fielding_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)

    pprint.pprint(return_dict)

    return {
        'Stats': return_dict
    }

def query_detailed_batting_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False, group_by_swing=False, exclude_nonfair=False):

    game_id_string, game_empty = format_tuple_for_SQL(game_ids)
    char_string, char_empty = format_tuple_for_SQL(char_ids)
    user_id_string, user_empty = format_tuple_for_SQL(user_ids)

    by_user = 'character_game_summary.user_id' if group_by_user else ''
    by_char = 'character_game_summary.char_id' if group_by_char else ''
    by_swing = 'pitch_summary.type_of_swing' if group_by_swing else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char, by_swing]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    query = (
        'SELECT \n'
        'user.id AS user_id, \n'
        'user.username AS username, \n'
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'pitch_summary.type_of_swing AS type_of_swing, \n'
        'COUNT(CASE WHEN pitch_summary.pitch_result = 1 THEN 1 ELSE NULL END) AS walks_bb, \n'
        'COUNT(CASE WHEN pitch_summary.pitch_result = 0 THEN 1 ELSE NULL END) AS walks_hit, \n'
        'COUNT(CASE WHEN contact_summary.primary_result = 0 THEN 1 ELSE NULL END) AS outs, \n'
        'COUNT(CASE WHEN contact_summary.primary_result = 1 THEN 1 ELSE NULL END) AS foul_hits, \n'
        'COUNT(CASE WHEN contact_summary.primary_result = 2 THEN 1 ELSE NULL END) AS fair_hits, \n'
        'COUNT(CASE WHEN contact_summary.primary_result = 3 THEN 1 ELSE NULL END) AS unknown_hits, \n'
        'COUNT(CASE WHEN (contact_summary.type_of_contact = 0 OR contact_summary.type_of_contact = 4) THEN 1 ELSE NULL END) AS sour_hits, '
        'COUNT(CASE WHEN (contact_summary.type_of_contact = 1 OR contact_summary.type_of_contact = 3) THEN 1 ELSE NULL END) AS nice_hits, '
        'COUNT(CASE WHEN contact_summary.type_of_contact = 2 THEN 1 ELSE NULL END) AS perfect_hits, '
        'COUNT(CASE WHEN contact_summary.secondary_result = 7 THEN 1 ELSE NULL END) AS singles, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 8 THEN 1 ELSE NULL END) AS doubles, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 9 THEN 1 ELSE NULL END) AS triples, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 10 THEN 1 ELSE NULL END) AS homeruns, \n'
        'COUNT(CASE WHEN contact_summary.multi_out = 1 THEN 1 ELSE NULL END) AS multi_out, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 14 THEN 1 ELSE NULL END) AS sacflys, \n'
        'COUNT(CASE WHEN event.result_of_ab != 0 THEN 1 ELSE NULL END) AS plate_appearances \n'
        #'SUM(ABS(contact_summary.ball_x_pos)) AS ball_x_pos_total, '
        #'SUM(ABS(contact_summary.ball_z_pos)) AS ball_z_pos_total '
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN pitch_summary ON pitch_summary.id = event.pitch_summary_id \n'
        '   AND pitch_summary.type_of_swing != 4 \n'
        'JOIN contact_summary ON pitch_summary.contact_summary_id = contact_summary.id \n'
       f"   {'AND contact_summary.primary_result != 1 AND contact_summary.primary_result != 3' if exclude_nonfair else ''} \n"
        'JOIN event ON character_game_summary.id = event.batter_id \n'
        'JOIN user ON character_game_summary.user_id = user.id \n'
       f"   WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"{group_by_statement}"
    )

    results = db.session.execute(query).all()

    batting_stats = {}
    for result_row in results:
        update_detailed_stats_dict(stat_dict, 'Batting', result_row, group_by_user, group_by_char, group_by_swing)

    return batting_stats

def query_detailed_pitching_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False):

    game_id_string, game_empty = format_tuple_for_SQL(game_ids, True)
    char_string, char_empty = format_tuple_for_SQL(char_ids, True)
    user_id_string, user_empty = format_tuple_for_SQL(user_ids)

    by_user = 'character_game_summary.user_id' if group_by_user else ''
    by_char = 'character_game_summary.char_id' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    pitching_summary_query = (
        'SELECT '
        'user.username AS username, \n' 
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'SUM(character_game_summary.batters_faced) AS batters_faced, \n'
        'SUM(character_game_summary.runs_allowed) AS runs_allowed, \n'
        'SUM(character_game_summary.hits_allowed) AS hits_allowed, \n'
        'SUM(character_game_summary.strikeouts_pitched) AS strikeouts_pitched, \n'
        'SUM(character_game_summary.star_pitches_thrown) AS star_pitches_thrown, \n'
        'SUM(character_game_summary.outs_pitched) AS outs_pitched, \n'
        'SUM(character_game_summary.pitches_thrown) AS total_pitches \n'
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN user ON user.id = character_game_summary.user_id \n'
        f"WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"{group_by_statement}"
    )

    pitch_breakdown_query = (
        'SELECT '
        'user.username AS username, \n' 
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'COUNT(CASE WHEN pitch_summary.pitch_result < 2 THEN 1 ELSE NULL END) AS walks, \n'
        'COUNT(CASE WHEN pitch_summary.pitch_result = 2 THEN 1 ELSE NULL END) AS balls, \n'
        'COUNT(CASE WHEN (pitch_summary.pitch_result = 3 OR pitch_summary.pitch_result = 4 OR pitch_summary.pitch_result = 5) THEN 1 ELSE NULL END) AS strikes \n'
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN event ON character_game_summary.id = event.pitcher_id \n'
        'JOIN pitch_summary ON pitch_summary.id = event.pitch_summary_id \n'
        'JOIN user ON user.id = character_game_summary.user_id \n'
        f"WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"{group_by_statement}"
    )

    pitching_summary_results = db.session.execute(pitching_summary_query).all()
    pitch_breakdown_results = db.session.execute(pitch_breakdown_query).all()
    for result_row in pitching_summary_results:
        update_detailed_stats_dict(stat_dict, 'Pitching', result_row, group_by_user, group_by_char)
    for result_row in pitch_breakdown_results:
        update_detailed_stats_dict(stat_dict, 'Pitching', result_row, group_by_user, group_by_char)
    return

def query_detailed_misc_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False):
    game_id_string, game_empty = format_tuple_for_SQL(game_ids, True)
    char_string, char_empty = format_tuple_for_SQL(char_ids, True)
    user_id_string, user_empty = format_tuple_for_SQL(user_ids)

    by_user = 'character_game_summary.user_id' if group_by_user else ''
    by_char = 'character_game_summary.char_id' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    query = (
        'SELECT '
        'user.username AS username, \n' 
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'SUM(CASE WHEN game.away_score > game.home_score AND game.away_player_id = user.id THEN 1 ELSE 0 END) AS away_wins, \n'
        'SUM(CASE WHEN game.away_score < game.home_score AND game.away_player_id = user.id THEN 1 ELSE 0 END) AS away_loses, \n'
        'SUM(CASE WHEN game.home_score > game.away_score AND game.home_player_id = user.id THEN 1 ELSE 0 END) AS home_wins, \n'
        'SUM(CASE WHEN game.home_score < game.away_score AND game.home_player_id = user.id THEN 1 ELSE 0 END) AS home_loses, \n'      
        'SUM(character_game_summary.defensive_star_successes) AS defensive_star_successes, \n'
        'SUM(character_game_summary.defensive_star_chances) AS defensive_star_chances, \n'
        'SUM(character_game_summary.defensive_star_chances_won) AS defensive_star_chances_won, \n'
        'SUM(character_game_summary.offensive_stars_put_in_play) AS offensive_stars_put_in_play, \n'
        'SUM(character_game_summary.offensive_star_successes) AS offensive_star_successes, \n'
        'SUM(character_game_summary.offensive_star_chances) AS offensive_star_chances, \n'
        'SUM(character_game_summary.offensive_star_chances_won) AS offensive_star_chances_won \n'
        'FROM game \n'
        'JOIN character_game_summary ON character_game_summary.game_id = game.game_id \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN user ON user.id = character_game_summary.user_id \n'
        f"WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"{group_by_statement}"
    )

    results = db.session.execute(query).all()
    for result_row in results:
        update_detailed_stats_dict(stat_dict, 'Misc', result_row, group_by_user, group_by_char)

    return

def query_detailed_fielding_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False):

    game_id_string, game_empty = format_tuple_for_SQL(game_ids, True)
    char_string, char_empty = format_tuple_for_SQL(char_ids, True)
    user_id_string, user_empty = format_tuple_for_SQL(user_ids)

    by_user = 'character_game_summary.user_id' if group_by_user else ''
    by_char = 'character_game_summary.char_id' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    position_query = (
        'SELECT '
        'user.username AS username, \n' 
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'SUM(pitches_at_p) AS pitches_per_p, \n'
        'SUM(pitches_at_c) AS pitches_per_c, \n'
        'SUM(pitches_at_1b) AS pitches_per_1b, \n'
        'SUM(pitches_at_2b) AS pitches_per_2b, \n'
        'SUM(pitches_at_3b) AS pitches_per_3b, \n'
        'SUM(pitches_at_ss) AS pitches_per_ss, \n'
        'SUM(pitches_at_lf) AS pitches_per_lf, \n'
        'SUM(pitches_at_cf) AS pitches_per_cf, \n'
        'SUM(pitches_at_rf) AS pitches_per_rf, \n'
        'SUM(outs_at_p) AS outs_per_p, \n'
        'SUM(outs_at_c) AS outs_per_c, \n'
        'SUM(outs_at_1b) AS outs_per_1b, \n'
        'SUM(outs_at_2b) AS outs_per_2b, \n'
        'SUM(outs_at_3b) AS outs_per_3b, \n'
        'SUM(outs_at_ss) AS outs_per_ss, \n'
        'SUM(outs_at_lf) AS outs_per_lf, \n'
        'SUM(outs_at_cf) AS outs_per_cf, \n'
        'SUM(outs_at_rf) AS outs_per_rf \n'
        #SUM( Insert other stats once questions addressed
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN character_position_summary ON character_position_summary.id = character_game_summary.character_position_summary_id \n'
        'JOIN user ON user.id = character_game_summary.user_id \n'
       f"WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"{group_by_statement}"
    )

    fielding_query = (
        'SELECT '
        'user.username AS username, \n' 
        'character_game_summary.char_id AS char_id, \n'
        'character.name AS char_name, \n'
        'COUNT(CASE WHEN fielding_summary.action = 1 THEN 1 ELSE NULL END) AS jump_catches, \n'
        'COUNT(CASE WHEN fielding_summary.action = 2 THEN 1 ELSE NULL END) AS diving_catches, \n'
        'COUNT(CASE WHEN fielding_summary.action = 3 THEN 1 ELSE NULL END) AS wall_jumps, \n'
        'SUM(fielding_summary.swap) AS swap_successes, \n'
        'COUNT(CASE WHEN fielding_summary.bobble != 0 THEN 1 ELSE NULL END) AS bobbles \n'
        #SUM( Insert other stats once questions addressed
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN fielding_summary ON fielding_summary.fielder_character_game_summary_id = character_game_summary.id \n'
        'JOIN user ON user.id = character_game_summary.user_id \n'
       f"WHERE character_game_summary.game_id {'NOT' if game_empty else ''} IN {game_id_string} \n"
       f"   AND character_game_summary.user_id {'NOT' if user_empty else ''} IN {user_id_string} \n"
       f"   AND character_game_summary.char_id {'NOT' if char_empty else ''} IN {char_string} \n"
       f"{group_by_statement}"
    )

    position_results = db.session.execute(position_query).all()
    fielding_results = db.session.execute(fielding_query).all()
    for result_row in position_results:
        update_detailed_stats_dict(stat_dict, 'Fielding', result_row, group_by_user, group_by_char)
    for result_row in fielding_results:
        update_detailed_stats_dict(stat_dict, 'Fielding', result_row, group_by_user, group_by_char)
    return

def update_detailed_stats_dict(in_stat_dict, type_of_result, result_row, group_by_user=False, group_by_char=False, group_by_swing=False):
    
    #Transform SQLAlchemy result_row into a dict and remove extra fields
    data_dict = result_row._asdict()
    if ('username' in data_dict): data_dict.pop('username')
    if ('user_id' in data_dict): data_dict.pop('user_id')
    if ('char_name' in data_dict): data_dict.pop('char_name')
    if ('char_id' in data_dict): data_dict.pop('char_id')
    if ('type_of_swing' in data_dict): data_dict.pop('type_of_swing')

    if group_by_user:
        if result_row.username not in in_stat_dict:
            in_stat_dict[result_row.username] = {}

        USER_DICT = in_stat_dict[result_row.username]
    
        #User=1, Char=1, Swing=X
        if group_by_char:
            if result_row.char_name not in USER_DICT:
                USER_DICT[result_row.char_name] = {}

            CHAR_DICT = USER_DICT[result_row.char_name]

            #Look at result type
            if (type_of_result == 'Batting'):

                if type_of_result not in CHAR_DICT:
                    CHAR_DICT[type_of_result] = {}

                #User=1, Char=1, Swing=1
                if group_by_swing:
                    BATTING_DICT = CHAR_DICT[type_of_result]

                    if cTYPE_OF_SWING[result_row.type_of_swing] not in BATTING_DICT:
                        BATTING_DICT[cTYPE_OF_SWING[result_row.type_of_swing]] = {}
                    elif cTYPE_OF_SWING[result_row.type_of_swing] in BATTING_DICT:
                        print('ERROR: FOUND PREVIOUS SWING TYPE')
                        
                    BATTING_DICT[cTYPE_OF_SWING[result_row.type_of_swing]].update(data_dict)
                
                #User=1, Char=1, Swing=0
                else:
                    CHAR_DICT[type_of_result].update(data_dict)
            
            elif (type_of_result == 'Pitching' or type_of_result == 'Fielding' or type_of_result == 'Misc'):
                if type_of_result not in CHAR_DICT:
                    CHAR_DICT[type_of_result] = {}
                CHAR_DICT[type_of_result].update(data_dict)

        #User=1, Char=0, Swing=1
        elif group_by_swing and type_of_result == 'Batting':
            if type_of_result not in USER_DICT:
                    USER_DICT[type_of_result] = {}
            
            if cTYPE_OF_SWING[result_row.type_of_swing] not in USER_DICT[type_of_result]:
                USER_DICT[type_of_result][cTYPE_OF_SWING[result_row.type_of_swing]] = {}
            elif USER_DICT[cTYPE_OF_SWING[result_row.type_of_swing]]:
                print('ERROR: FOUND PREVIOUS SWING TYPE')
                
            USER_DICT[type_of_result][cTYPE_OF_SWING[result_row.type_of_swing]].update(data_dict)

        #User=1, Char=0, Swing=0 if batting
        else:
            if type_of_result not in USER_DICT:
                USER_DICT[type_of_result] = {}

            USER_DICT[type_of_result].update(data_dict)

    #User=0, Char=1, Swing=X
    elif group_by_char:
        if result_row.char_name not in in_stat_dict:
            in_stat_dict[result_row.char_name] = {}

        CHAR_DICT = in_stat_dict[result_row.char_name]

        #Look at result type
        if (type_of_result == 'Batting'):

            #Build batting
            if type_of_result not in CHAR_DICT:
                CHAR_DICT[type_of_result] = {}

            #User=0, Char=1, Swing=1
            if group_by_swing:
                BATTING_DICT = CHAR_DICT[type_of_result]

                if cTYPE_OF_SWING[result_row.type_of_swing] not in BATTING_DICT:
                    BATTING_DICT[cTYPE_OF_SWING[result_row.type_of_swing]] = {}
                elif cTYPE_OF_SWING[result_row.type_of_swing] in BATTING_DICT:
                    print('ERROR: FOUND PREVIOUS SWING TYPE')
                    
                BATTING_DICT[cTYPE_OF_SWING[result_row.type_of_swing]].update(data_dict)
            
            #User=0, Char=1, Swing=0
            else:
                CHAR_DICT[type_of_result].update(data_dict)

        elif (type_of_result == 'Pitching' or type_of_result == 'Fielding' or type_of_result == 'Misc'):
            if type_of_result not in CHAR_DICT:
                CHAR_DICT[type_of_result] = {}
            CHAR_DICT[type_of_result].update(data_dict)
    
    #User=0, Char=0, Swing=1
    elif group_by_swing and type_of_result == 'Batting':
        #Build batting
        if type_of_result not in in_stat_dict:
            in_stat_dict[type_of_result] = {}

        if cTYPE_OF_SWING[result_row.type_of_swing] not in in_stat_dict[type_of_result]:
            in_stat_dict[type_of_result][cTYPE_OF_SWING[result_row.type_of_swing]] = {}
        if cTYPE_OF_SWING[result_row.type_of_swing] in in_stat_dict[type_of_result]:
            print('ERROR: FOUND PREVIOUS SWING TYPE')
            
        in_stat_dict[type_of_result][cTYPE_OF_SWING[result_row.type_of_swing]].update(data_dict)

    #User=0, Char=0, Swing=0
    else:
        if type_of_result not in in_stat_dict:
            in_stat_dict[type_of_result] = {}
        in_stat_dict[type_of_result].update(data_dict)