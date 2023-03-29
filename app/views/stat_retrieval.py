from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, RioUser, Character, Game, ChemistryTable, Tag, Event
from ..consts import *
from ..util import *
import pprint
import time
import datetime
import itertools

@app.route('/characters/', methods = ['GET'])
def get_characters():
    characters = []
    
    character_names = request.args.getlist('name')
    if character_names:
        try:
            character_names_lowercase = tuple([name.lower() for name in character_names])
            character_rows = db.session.query(Character).filter(Character.name_lowercase.in_(character_names_lowercase)).all()
        except:
            abort(400, 'Invalid Character name')
    else:
        character_rows = Character.query.all()

    for character in character_rows:
        characters.append(character.to_dict())

    return {
        'characters': characters
        }

# Helpers for detailed stats
def build_where_statement(game_ids, char_ids, user_ids):
    game_id_string, game_empty = format_tuple_for_SQL(game_ids)
    char_string, char_empty = format_tuple_for_SQL(char_ids)
    user_id_string, user_empty = format_tuple_for_SQL(user_ids)

    #If at least one group is populated produce the WHERE statement
    where_statement = ''
    if not (game_empty and user_empty and char_empty):
        where_statement = 'WHERE '
        other_conditions = False
        if (not game_empty):
            other_conditions = True
            where_statement += f"character_game_summary.game_id IN {game_id_string} \n"
        if (not user_empty):
            if (other_conditions):
                where_statement += 'AND '
            other_conditions = True
            where_statement += f"character_game_summary.user_id IN {user_id_string} \n"
        if (not char_empty):
            if (other_conditions):
                where_statement += 'AND '
            other_conditions = True
            where_statement += f"character_game_summary.char_id IN {char_string} \n"
    return where_statement

def sanitize_int_list(int_list, error_msg, upper_bound, lower_bound = 0):
    if int_list == None or len(int_list) == 0:
        return [], ''
    try:
        for index, item in enumerate(int_list):
            sanitized_id = int(int_list[index])
            if sanitized_id in range (lower_bound,upper_bound):
                int_list[index] = sanitized_id
            else:
                return None, error_msg
        return int_list, ''
    except:
        return None, error_msg

'''
@ Description: Returns games that fit the parameters
@ Params:
    - tag - list of tags to filter by
    - exclude_tag - List of tags to exclude from search
    - start_time - Unix time. Provides the lower (older) end of the range of games to retreive.
    - end_time - Unix time. Provides the lower (older) end of the range of games to retreive. Defaults to now (time of query).
    - username - list of users who appear in games to retreive
    - vs_username - list of users who MUST also appear in the game along with users
    - exclude_username - list of users to NOT include in query results
    - captain - captain name to appear in games to retrieve
    - vs_captain - captain name who MUST appear in game along with captain
    - exclude_captian -  captain name to EXLCUDE from results
    - limit_games - Int of number of games || False to return all

@ Output:
    - List of games and highlevel info based on flags

@ URL example: http://127.0.0.1:5000/games/?limit=5&username=demOuser4&username=demouser1&username=demouser5
'''
@app.route('/games/', methods = ['GET'])
def endpoint_games(called_internally=False):
    # === validate passed parameters ===
    try:
        # Check if tags are valid and get a list of corresponding ids
        tags = request.args.getlist('tag')
        tags_lowercase = tuple([lower_and_remove_nonalphanumeric(tag) for tag in tags])
        tag_rows = db.session.query(Tag).filter(Tag.name_lowercase.in_(tags_lowercase)).all()
        include_tag_ids = tuple([str(tag.id) for tag in tag_rows])
        if len(include_tag_ids) != len(tags):
            abort(400)

        # Check if exclude_tags are valid and get a list of corresponding ids
        exclude_tags = request.args.getlist('exclude_tag')
        exclude_tags_lowercase = tuple([lower_and_remove_nonalphanumeric(exclude_tag) for exclude_tag in exclude_tags])
        exclude_tag_rows = db.session.query(Tag).filter(Tag.name_lowercase.in_(exclude_tags_lowercase)).all()
        exclude_tag_ids = tuple([str(exclude_tag.id) for exclude_tag in exclude_tag_rows])
        if len(exclude_tag_ids) != len(exclude_tags):
            abort(400)

        #Get user ids from list of users
        usernames = request.args.getlist('username')
        usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(usernames_lowercase)).all()
        # using list comprehension
        list_of_user_id = list(itertools.chain(*list_of_user_id_tuples))
        tuple_user_ids = tuple(list_of_user_id)
        if len(usernames) != len(list_of_user_id_tuples):
            abort(400)

        #Get user ids from list of users
        vs_usernames = request.args.getlist('vs_username')
        vs_usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in vs_usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_vs_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(vs_usernames_lowercase)).all()
        # using list comprehension
        list_of_vs_user_id = list(itertools.chain(*list_of_vs_user_id_tuples))
        tuple_vs_user_ids = tuple(list_of_vs_user_id)

        #Get user ids from list of users
        exclude_usernames = request.args.getlist('exclude_username')
        exclude_usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in exclude_usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_exclude_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(exclude_usernames_lowercase)).all()
        # using list comprehension
        list_of_exclude_user_id = list(itertools.chain(*list_of_exclude_user_id_tuples))
        tuple_exclude_user_ids = tuple(list_of_exclude_user_id)

        #Get captain ids from Captain
        captains = request.args.getlist('captain')
        captains_lowercase = tuple([captain.lower() for captain in captains])
        list_of_captain_id_tuples = db.session.query(Character.char_id).filter(Character.name_lowercase.in_(captains_lowercase)).all()
        list_of_captain_ids = list(itertools.chain(*list_of_captain_id_tuples))
        tuple_captain_ids = tuple(list_of_captain_ids)

        vs_captains = request.args.getlist('vs_captain')
        vs_captains_lowercase = tuple([vs_captain.lower() for vs_captain in vs_captains])
        list_of_vs_captain_id_tuples = db.session.query(Character.char_id).filter(Character.name_lowercase.in_(vs_captains_lowercase)).all()
        list_of_vs_captain_ids = list(itertools.chain(*list_of_vs_captain_id_tuples))
        tuple_vs_captain_ids = tuple(list_of_vs_captain_ids)
        
        exclude_captains = request.args.getlist('exclude_captain')
        exclude_captains_lowercase = tuple([exclude_captain.lower() for exclude_captain in exclude_captains])
        list_of_exclude_captain_id_tuples = db.session.query(Character.char_id).filter(Character.name_lowercase.in_(exclude_captains_lowercase)).all()
        list_of_exclude_captain_ids =list(itertools.chain(*list_of_exclude_captain_id_tuples))
        tuple_exclude_captain_ids = tuple(list_of_exclude_captain_ids)

        limit = int()
        try:
            if request.args.get('limit_games') is None:
                limit = None if called_internally else 50
            elif request.args.get('limit_games') in ['False', 'false', 'f']:
                limit = None
            else:
                limit = int(request.args.get('limit_games'))
        except:
            abort(400, 'Invalid Limit provided')

    except:
       return abort(400, 'Invalid Username, Captain, or Tag')


    # Build WHERE statement
    where_statement = 'WHERE '

    #Get and validate start_time and end_time parameters from URL
    start_time_unix = 1
    if (request.args.get('start_time') != None):
        try:
            start_time = request.args.get('start_time')
            start_time_unix = int(start_time)
        except:
            return abort(408, 'Invalid start time format')
    
    end_time_unix = 0
    if (request.args.get('end_time') != None):
        try:
            end_time = request.args.get('end_time')
            end_time_unix = int(end_time)
        except:
            return abort(408, 'Invalid end time format')

    # Add start and end_time parameters to WHERE statement
    where_statement += f"game.date_time_start > {start_time_unix} \n"
    if (end_time_unix != 0):
        where_statement += f"AND game.date_time_end < {end_time_unix} \n"


    # === Set dynamic query values ===
    # count_matching_tags = f"SUM(CASE WHEN game_tag.tag_id IN ({', '.join(tag_ids)}) THEN 1 ELSE 0 END) AS having_tag_count \n" if len(tag_ids) > 0 else ""
    # count_matching_exclude_tags = f"SUM(CASE WHEN game_tag.tag_id IN ({', '.join(exclude_tag_ids)}) THEN 1 ELSE 0 END) AS exclude_tag_count \n" if len(exclude_tag_ids) > 0 else ""
    # having_matching_tags =  f'having_tag_count = {len(tag_ids)} ' if count_matching_tags != "" else ""
    # having_exclude_tags = f'exclude_tag_count = 0' if count_matching_exclude_tags != "" else ""
    
    # with_tags = str()
    # where_tags = str()
    # if count_matching_tags != "" or count_matching_exclude_tags != "":
    #     with_tags = (
    #         'WITH game_id_and_tag_counts AS ( \n'
    #         '   SELECT \n' 
    #         '       game_id, \n'
    #                 f'{count_matching_tags}'
    #                 f'{", " if count_matching_tags != "" and count_matching_exclude_tags != "" else ""}'
    #                 f'{count_matching_exclude_tags}'
    #         '   FROM game_tag \n'
    #         '   GROUP BY game_id \n'
    #         ')  \n'
    #     )
    #     where_tags = (
    #         'AND game.game_id IN ( \n'
    #         '  SELECT game_id  \n'
    #         '  FROM game_id_and_tag_counts \n'
    #         '  WHERE ' 
    #         f'{having_matching_tags}'
    #         f'{" AND " if count_matching_tags != "" and count_matching_exclude_tags != "" else ""}'
    #         f'{having_exclude_tags}'
    #         '\n)\n '
    #     )
    #     where_statement += where_tags



    #Build User strings
    user_id_string, user_empty = format_tuple_for_SQL(tuple_user_ids)
    vs_user_id_string, vs_user_empty = format_tuple_for_SQL(tuple_vs_user_ids)
    exclude_user_id_string, exclude_user_empty = format_tuple_for_SQL(tuple_exclude_user_ids)

    if (not user_empty):
        where_statement += f"AND (game.away_player_id IN {user_id_string} OR game.home_player_id IN {user_id_string}) \n"
    if (not vs_user_empty):
        where_statement += f"AND (game.away_player_id IN {vs_user_id_string} OR game.home_player_id IN {vs_user_id_string}) \n"
    if (not exclude_user_empty):
        where_statement += f"AND game.away_player_id NOT IN {exclude_user_id_string} AND game.home_player_id NOT IN {exclude_user_id_string} \n"

    #Build captain strings
    captain_id_string, captain_empty = format_tuple_for_SQL(tuple_captain_ids)
    vs_captain_id_string, vs_captain_empty = format_tuple_for_SQL(tuple_vs_captain_ids)
    exclude_captain_id_string, exclude_captain_empty = format_tuple_for_SQL(tuple_exclude_captain_ids)

    if (not captain_empty):
        where_statement += f"AND (away_captain.char_id IN {captain_id_string} OR home_captain.char_id IN {captain_id_string}) \n"
    if (not vs_captain_empty):
        where_statement += f"AND (away_captain.char_id IN {vs_captain_id_string} OR home_captain.char_id IN {vs_captain_id_string}) \n"
    if (not exclude_captain_empty):
        where_statement += f"AND away_captain.char_id NOT IN {exclude_captain_id_string} AND home_captain.char_id NOT IN {exclude_captain_id_string} \n"

    #Build Tag strings
    include_tag_id_string, include_tag_empty = format_tuple_for_SQL(include_tag_ids)
    exclude_tag_id_string, exclude_tag_empty = format_tuple_for_SQL(exclude_tag_ids)
    if (not include_tag_empty):
        where_statement += f"AND tag.id IN {include_tag_id_string} \n"
    if (not exclude_tag_empty):
        where_statement += f"AND tag.id NOT IN {exclude_tag_id_string} \n"


    # === Construct query === 
    query = (
        'SELECT game.game_id, \n'
        '   game.date_time_start AS date_time_start, \n'
        '   game.date_time_end AS date_time_end, \n'
        '   game.away_score AS away_score, \n'
        '   game.home_score AS home_score, \n'
        '   game.innings_played AS innings_played, \n'
        '   game.innings_selected AS innings_selected, \n'
        '   away_player.username AS away_player, \n'
        '   home_player.username AS home_player, \n'
        '   away_captain.name AS away_captain, \n'
        '   home_captain.name AS home_captain, \n'
        '   game_history.tag_set_id AS tag_set \n'
        'FROM game \n'
        'LEFT JOIN game_history ON game.game_id = game_history.game_id \n'
        'LEFT JOIN tag_set ON game_history.tag_set_id = tag_set.id \n'
        'LEFT JOIN tag_set_tag AS tst ON tag_set.id = tst.tagset_id \n'
        'LEFT JOIN tag ON tst.tag_id = tag.id \n'
        'LEFT JOIN rio_user AS away_player ON game.away_player_id = away_player.id \n'
        'LEFT JOIN rio_user AS home_player ON game.home_player_id = home_player.id \n'
        'LEFT JOIN character_game_summary AS away_captain_cgs \n'
        '   ON game.game_id = away_captain_cgs.game_id \n'
        '   AND away_captain_cgs.user_id = away_player.id \n'
        '   AND away_captain_cgs.captain = True \n'
        'LEFT JOIN character_game_summary AS home_captain_cgs \n'
        '	ON game.game_id = home_captain_cgs.game_id \n'
        '   AND home_captain_cgs.user_id = home_player.id \n'
        '   AND home_captain_cgs.captain = True \n'
        'LEFT JOIN character AS away_captain ON away_captain_cgs.char_id = away_captain.char_id \n'
        'LEFT JOIN character AS home_captain ON home_captain_cgs.char_id = home_captain.char_id \n'
        f'{where_statement} \n'
        'GROUP BY game.game_id, away_player, home_player, away_captain, home_captain, tag_set \n'
        'ORDER BY game.date_time_start DESC \n'
        f"{('LIMIT ' + str(limit)) if limit != None else ''}"
    )

    print(query)

    results = db.session.execute(query).all()
    
    games = []
    game_ids = []
    if called_internally:
        for game in results:
            game_ids.append(game.game_id)
        return { "game_ids": game_ids }
    else:
        for game in results:
            game_ids.append(game.game_id)

            games.append({
                'Id': game.game_id,
                'date_time_start': game.date_time_start,
                'date_time_end': game.date_time_end,
                'Away User': game.away_player,
                'Away Captain': game.away_captain,
                'Away Score': game.away_score,
                'Home User': game.home_player,
                'Home Captain': game.home_captain,
                'Home Score': game.home_score,
                'Innings Played': game.innings_played,
                'Innings Selected': game.innings_selected,
                'Game Mode': game.tag_set
            })

        # If there are games with matching tags, get all additional tags they have
        # if game_ids:
        #     where_game_id = str()
        #     game_id_string, game_id_empty = format_list_for_SQL(game_ids)
        #     where_game_id = f'WHERE game_tag.game_id = {game_id_string} '

        #     tags_query = (
        #         'SELECT '
        #         'game_tag.game_id as game_id, '
        #         'game_tag.tag_id as tag_id, '
        #         'tag.name as name '
        #         'FROM game_tag '
        #         'LEFT JOIN tag ON game_tag.tag_id = tag.id '
        #         f'{where_game_id}'
        #         'GROUP BY game_id, tag_id, name'
        #     )

        #     tag_results = db.session.execute(tags_query).all()
        #     for tag in tag_results:
        #         for game in games:
        #             if game['Id'] == tag.game_id:
        #                 game['Tags'].append(tag.name)

        return {'games': games}



# == Functions to return coordinates for graphing ==
'''
@Endpoint: Events
@Description: Used to pick out events that fit the given params
@Params:
    - Game params:           Params for /games/ (tags/users/date/etc)
    - games:           [0-x],   games if not using the game endpoint params
    - pitcher_char:    [0-54],  pitcher char ids
    - batter_char:     [0-54],  batter char ids
    - fielder_char:    [0-54],  fielder char ids
    - fielder_pos:     [0-54],  fielder pos
    - contact:         [0-5],   contact types (0-4: in-game values, 5: no contact)
    - swing:           [0-4],   swing types ()
    - pitch:           [0-4],   pitch types (TODO)
    - chem_link:       [0-4],   chemistry on base values
    - pitcher_hand:    [0-1],   pitchers handedness ()
    - batter_hand:     [0-1],   batters handedness ()
    - inning:          [0-50],  innings to collect from
    - half_inning:     [0-1],   half inning to collect from
    - balls:           [0-3],   balls
    - strikes:         [0-2],   strikes
    - outs:            [0-2],   outs
    - star_chance      [0-1],   bool for star chance
    - users_as_batter  [0-1],   bool if you want to only get the events for the given users when they are the batter
    - users_as_pitcher [0-1],   bool if you want to only get the events for the given users when they are the pitcher
    - final_result     [0-16],  value for the final result of the event
    - limit_events            int or False, value to limit the events
'''
@app.route('/events/', methods = ['GET'])
def endpoint_event(called_internally=False):
    # === Construct query === 
    #Sanitize games params 
    try:
        list_of_game_ids = list() # Holds IDs for all the games we want data from
        if (len(request.args.getlist('games')) != 0):
            list_of_game_ids = [int(game_id) for game_id in request.args.getlist('games')]
            list_of_game_id_tuples = db.session.query(Game.game_id).filter(Game.game_id.in_(tuple(list_of_game_ids))).all()
            if (len(list_of_game_id_tuples) != len(list_of_game_ids)):
                return abort(408, description='Provided GameIDs not found')

        else:
            games = endpoint_games(True)   # List of dicts of games we want data from and info about those games
            print(games)
            for game_id in games['game_ids']:
                list_of_game_ids.append(game_id)
    except:
        return abort(408, description='Invalid GameID')

    
    list_of_batter_user_ids = []
    list_of_pitcher_user_ids = []
    if ( request.args.getlist('username') != None or request.args.getlist('vs_username') != None ):
        #Get user ids from list of users
        vs_usernames = request.args.getlist('vs_username')
        vs_usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in vs_usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_vs_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(vs_usernames_lowercase)).all()
        # using list comprehension
        list_of_vs_user_id = list(itertools.chain(*list_of_vs_user_id_tuples))
        if (request.args.get('users_as_batter') == "1"):
            list_of_batter_user_ids += list_of_vs_user_id
        if (request.args.get('users_as_pitcher') == "1"):
            list_of_pitcher_user_ids += list_of_vs_user_id

        #Get user ids from list of users
        usernames = request.args.getlist('username')
        usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in usernames])
        #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
        list_of_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(usernames_lowercase)).all()
        # using list comprehension
        list_of_user_id = list(itertools.chain(*list_of_user_id_tuples))
        if (request.args.get('users_as_batter') == "1"):
            list_of_batter_user_ids += list_of_user_id
        if (request.args.get('users_as_pitcher') == "1"):
            list_of_pitcher_user_ids += list_of_user_id

    # Pitcher Char Id
    list_of_pitcher_char_ids, error = sanitize_int_list(request.args.getlist('pitcher_char'), "Pitcher Char ID not in range", 55)
    if list_of_pitcher_char_ids == None:
        return abort(400, description = error)

    # Batter Char Id
    list_of_batter_char_ids, error = sanitize_int_list(request.args.getlist('batter_char'), "Batter Char ID not in range", 55)
    if list_of_batter_char_ids == None:
        return abort(400, description = error)

    #Contact Type
    list_of_contact, error = sanitize_int_list(request.args.getlist('contact'), "Contact Type not in range", 6)
    if list_of_contact == None:
        return abort(400, description = error)
    
    #Swing Type
    list_of_swings, error = sanitize_int_list(request.args.getlist('swing'), "Swing Type not in range", 5)
    if list_of_swings == None:
        return abort(400, description = error)

    #Pitch Type - 0,1,2,3,4 (curve, slider, perfect charge, changeup, star swing)
    list_of_pitches, error = sanitize_int_list(request.args.getlist('pitch'), "Pitch Type not in range", 5)
    if list_of_pitches == None:
        return abort(400, description = error)

    #Chem Links
    list_of_chem, error = sanitize_int_list(request.args.getlist('chem_link'), "Chem Links not in range", 4)
    if list_of_chem == None:
        return abort(400, description = error)

    #Batter Handedness
    list_of_bh, error = sanitize_int_list(request.args.getlist('batter_hand'), "Batter hand not in range", 2)
    if list_of_bh == None:
        return abort(400, description = error)

    #Pitcher Handedness
    list_of_ph, error = sanitize_int_list(request.args.getlist('pitcher_hand'), "Batter hand not in range", 2)
    if list_of_ph == None:
        return abort(400, description = error)

    #Fielder Id
    list_of_fielder_char_ids, error = sanitize_int_list(request.args.getlist('fielder_char'), "Fielder Char ID not in range", 55)
    if list_of_fielder_char_ids == None:
        return abort(400, description = error)

    #Fielder Pos
    list_of_fielder_pos, error = sanitize_int_list(request.args.getlist('fielder_pos'), "Fielder position not in range", 9)
    if list_of_fielder_pos == None:
        return abort(400, description = error)

    #Inning list
    list_of_innings, error = sanitize_int_list(request.args.getlist('innings'), "Innings not in range", 50)
    if list_of_innings == None:
        return abort(400, description = error)

    #Half Inning list
    list_of_half_inning, error = sanitize_int_list(request.args.getlist('half_inning'), "Half Inning not in range", 2)
    if list_of_half_inning == None:
        return abort(400, description = error)

    #Strike list
    list_of_balls, error = sanitize_int_list(request.args.getlist('balls'), "Balls not in range", 4)
    if list_of_balls == None:
        return abort(400, description = error)

    #Strike list
    list_of_strikes, error = sanitize_int_list(request.args.getlist('strikes'), "Strikes not in range", 3)
    if list_of_strikes == None:
        return abort(400, description = error)

    #Outs list
    list_of_outs, error = sanitize_int_list(request.args.getlist('outs'), "Outs not in range", 3)
    if list_of_outs == None:
        return abort(400, description = error)
    
    #Final result
    list_of_results, error = sanitize_int_list(request.args.getlist('final_result'), "Final result not in range", 17)
    if list_of_results == None:
        return abort(400, description = error)

    star_chance_flag = [1] if (request.args.get('star_chance') == '1') else []

    #list of args, the attribute to select from, null value
    where_list = [
        (list_of_game_ids, 'event.game_id', None),
        (list_of_pitcher_char_ids, 'pitcher.char_id', None),
        (list_of_batter_char_ids, 'batter.char_id', None),
        (list_of_contact, 'contact.type_of_contact', 5),
        (list_of_swings, 'pitch.type_of_swing', None),
       #(list_of_pitches, 'pitch.type_of_swing', None) #This one needs a DB rework. Manually add later
        (list_of_chem, 'event.chem_links_ob', None),
        (list_of_bh, 'batter.batting_hand', None),
        (list_of_ph, 'pitcher.fielding_hand', None),
        (list_of_fielder_char_ids, 'fielder.char_id', None),
        (list_of_fielder_pos, 'fielder.position', None),
        (list_of_innings, 'event.inning', None),
        (list_of_half_inning, 'event.half_inning', None),
        (list_of_balls, 'event.balls', None),
        (list_of_strikes, 'event.strikes', None),
        (list_of_outs, 'event.outs', None),
        (star_chance_flag, 'event.star_chance', None),
        (star_chance_flag, 'event.star_chance', None),
        (list_of_batter_user_ids, 'batter.user_id', None),
        (list_of_pitcher_user_ids, 'pitcher.user_id', None),
        (list_of_results, 'event.result_of_ab', None)
    ]

    #Go through all of the lists from the args
    #If they are empty, skip entire list, do not add to the statement
    #If not empty, use the SQL provided in tuple[1] to write a where statement and append it
    #Grab NULL values for column if tuple[3] is provided and also present in the list
    def build_where_statement(where_list):
        where_statement = 'WHERE ('
        and_needed = False
        for item in where_list:
            formatted_tuple, empty = format_list_for_SQL(item[0])
            if empty:
                continue
            if and_needed:
                where_statement += 'AND '
            #Check if there are values that will represent null (contact=5 is not a real value, but its used to represent 'no contact' AKA null in the table)
            null_statement = ''
            if ((item[2] != None) and (item[2] in item[0])):
                null_statement = f' OR {item[1]} IS NULL'
            where_statement += f'({item[1]} IN {formatted_tuple}{null_statement})\n'
            and_needed = True
        where_statement += ')'
        #If we have at least a single where statement, return it
        if and_needed:
            return where_statement
        return ''

    where_statement = build_where_statement(where_list)

    columns_statement = 'event.game_id AS game_id, \n event.event_num AS event_num, \n' if not called_internally else ''

    limit_statement = ''
    default_limit = 1000
    max_limit     = 150000
    if (request.args.get('limit_events') != None):
        try:
            limit = int(request.args.get('limit_events')) if int(request.args.get('limit_events')) <= max_limit else max_limit
            limit_statement = f' LIMIT {limit}'
        except:
            if request.args.get('limit_events') in ["false", "False", "F", "f"]:
                limit_statement = f' LIMIT {max_limit}'
            elif request.args.get('limit_events') in ["true", "True", "T", "t"]:
                limit_statement = f' LIMIT {default_limit}'
            else:
                return abort(400, description = "Invalid event_limit")
    else:
        limit_statement = '' if called_internally else f' LIMIT {default_limit}'

    query = (
        'SELECT \n'
        f'{columns_statement}'
        'event.id AS event_id \n'
        'FROM event \n'
        'JOIN pitch_summary AS pitch ON event.pitch_summary_id = pitch.id \n'
        'LEFT JOIN contact_summary AS contact ON pitch.contact_summary_id = contact.id \n'       #Contact gets a left joiin for misses
        'LEFT JOIN fielding_summary AS fielding ON contact.fielding_summary_id = fielding.id \n' #Fielding gets a left joiin for HRs and misses
        'JOIN character_game_summary AS batter ON event.batter_id = batter.id \n'
        'JOIN character_game_summary AS pitcher ON event.pitcher_id = pitcher.id \n'
        'LEFT JOIN character_game_summary AS fielder ON fielding.fielder_character_game_summary_id = fielder.id \n'
       f'{where_statement}'
       f'{limit_statement}'
    )

    print(query)

    result = db.session.execute(query).all()

    if called_internally:
        events = []
        for entry in result:
            events.append(entry.event_id )
        events = { 'Events': events }
    else:
        events = {}
        for entry in result:
            if entry.game_id not in events:
                events[entry.game_id] = {}
            events[entry.game_id][entry.event_num] = entry.event_id
        
    return events


# @app.route('/plate_data/', methods = ['GET'])
# def endpoint_plate_data():
#     #Sanitize games params 
#     try:
#         list_of_event_ids = list() # Holds IDs for all the events we want data from
#         if (len(request.args.getlist('events')) != 0):
#             list_of_event_ids = [int(game_id) for game_id in request.args.getlist('events')]
#             list_of_event_id_tuples = db.session.query(Event.id).filter(Event.id.in_(tuple(list_of_event_ids))).all()
#             if (len(list_of_event_id_tuples) != len(list_of_event_ids)):
#                 return abort(408, description='Provided Events not found')

#         else:
#             list_of_event_ids = endpoint_event(True)['Events']   # List of dicts of games we want data from and info about those games
#     except:
#         return abort(408, description='Invalid GameID')

#     event_id_string, event_empty = format_list_for_SQL(list_of_event_ids)

#     if event_empty:
#         return {}

#     query = (
#         'SELECT \n'
#         'event.game_id AS game_id, \n'
#         'event.id AS event_id, \n'
#         'event.result_of_ab AS final_result, \n'
#         'batter.char_id AS batter_char_id, \n'
#         'pitcher.char_id AS pitcher_char_id, \n'
#         'pitcher_user.username AS pitcher_username, \n'
#         'batter_user.username AS batter_username, \n'
#         'batter.batting_hand, \n'
#         'pitcher.fielding_hand, \n'
#         'pitch.pitch_ball_x_pos, \n'
#         'pitch.pitch_ball_z_pos, \n'
#         'pitch.pitch_batter_x_pos, \n'
#         'pitch.pitch_batter_z_pos, \n'
#         'pitch.type_of_swing, \n'
#         'contact.type_of_contact, \n'
#         'pitch.pitch_result\n'
#         'FROM event \n'
#         'JOIN pitch_summary AS pitch ON event.pitch_summary_id = pitch.id \n'
#         'LEFT JOIN contact_summary AS contact ON pitch.contact_summary_id = contact.id \n'       #Contact gets a left joiin for misses
#         'JOIN character_game_summary AS batter ON event.batter_id = batter.id \n'
#         'JOIN character_game_summary AS pitcher ON event.pitcher_id = pitcher.id \n'
#         'JOIN rio_user AS pitcher_user ON pitcher.user_id = pitcher_user.id \n'
#         'JOIN rio_user AS batter_user ON batter.user_id = batter_user.id \n'
#        f'WHERE event.id IN {event_id_string}'
#     )

#     print(query)

#     result = db.session.execute(query).all()

#     data = []
#     for entry in result:
#         data.append(entry._asdict())
#     return {
#         'Data': data
#     }

@app.route('/landing_data/', methods = ['GET'])
def endpoint_landing_data():
    #Sanitize games params 
    try:
        list_of_event_ids = list() # Holds IDs for all the events we want data from
        if (len(request.args.getlist('events')) != 0):
            list_of_event_ids = [int(game_id) for game_id in request.args.getlist('events')]
            list_of_event_id_tuples = db.session.query(Event.id).filter(Event.id.in_(tuple(list_of_event_ids))).all()
            if (len(list_of_event_id_tuples) != len(list_of_event_ids)):
                return abort(408, description='Provided Events not found')

        else:
            list_of_event_ids = endpoint_event(True)['Events']   # List of dicts of games we want data from and info about those games
    except:
        return abort(408, description='Invalid GameID')

    event_id_string, event_empty = format_list_for_SQL(list_of_event_ids)

    if event_empty:
        return {}

    query = (
        'SELECT \n'
        'event.game_id AS game_id, \n'
        'event.event_num AS event_num, \n'
        'event.result_of_ab AS final_result, \n'
        'event.chem_links_ob AS chem_links_ob, \n'
        'batter.char_id AS batter_char_id, \n'
        'pitcher.char_id AS pitcher_char_id, \n'
        'fielder.char_id AS fielder_char_id, \n'
        'pitcher_user.username AS pitcher_username, \n'
        'batter_user.username AS batter_username, \n'
        'batter.batting_hand, \n'
        'pitcher.fielding_hand, \n'
        'contact.ball_power AS ball_power '
        'contact.ball_horiz_angle AS ball_horiz_angle '
        'contact.ball_vert_angle AS ball_vert_angle '
        'contact.contact_absolute AS contact_absolute '
        'contact.contact_quality AS contact_quality '
        'contact.rng1 AS rng1 '
        'contact.rng2 AS rng2 '
        'contact.rng3 AS rng3 '
        'contact.ball_x_velocity AS ball_x_velocity '
        'contact.ball_y_velocity AS ball_y_velocity '
        'contact.ball_z_velocity AS ball_z_velocity '
        'contact.ball_x_contact_pos AS ball_x_contact_pos '
        'contact.ball_y_contact_pos AS ball_y_contact_pos '
        'contact.ball_z_contact_pos AS ball_z_contact_pos '
        'contact.bat_x_contact_pos AS bat_x_contact_pos '
        'contact.bat_y_contact_pos AS bat_y_contact_pos '
        'contact.bat_z_contact_pos AS bat_z_contact_pos '
        'contact.ball_x_landing_pos AS ball_x_landing_pos '
        'contact.ball_y_landing_pos AS ball_y_landing_pos '
        'contact.ball_z_landing_pos AS ball_z_landing_pos '
        'contact.ball_max_height AS ball_max_height, \n'
        'contact.input_direction_stick AS stick_input, \n'
        'contact.charge_power_up AS charge_power_up, \n'
        'contact.charge_power_down AS charge_power_down, \n'
        'contact.frame_of_swing_upon_contact AS frame_of_swing, \n'
        'pitch.type_of_swing, \n'
        'contact.type_of_contact, \n'
        #Add decoded action
        'fielding.position AS fielder_position, \n'
        'fielding.fielder_x_pos AS fielder_x_pos, \n'
        'fielding.fielder_y_pos AS fielder_y_pos, \n'
        'fielding.fielder_z_pos AS fielder_z_pos, \n'
        'fielding.jump AS fielder_jump, \n'
        'fielding.manual_select AS manual_select_state \n'
        'FROM event \n'
        'JOIN pitch_summary AS pitch ON event.pitch_summary_id = pitch.id \n'
        'JOIN contact_summary AS contact ON pitch.contact_summary_id = contact.id \n'
        'LEFT JOIN fielding_summary AS fielding ON contact.fielding_summary_id = fielding.id \n'
        'JOIN character_game_summary AS batter ON event.batter_id = batter.id \n'
        'JOIN character_game_summary AS pitcher ON event.pitcher_id = pitcher.id \n'
        'LEFT JOIN character_game_summary AS fielder ON fielding.fielder_character_game_summary_id = fielder.id \n'
        'JOIN rio_user AS pitcher_user ON pitcher.user_id = pitcher_user.id \n'
        'JOIN rio_user AS batter_user ON batter.user_id = batter_user.id \n'
       f'WHERE event.id IN {event_id_string}'
    )

    print(query)

    result = db.session.execute(query).all()

    data = []
    for entry in result:
        data.append(entry._asdict())
    return {
        'Data': data
    }


# == Functions to return coordinates for graphing ==
'''
@Endpoint: Star_chances
@Description: Return number of star chances per game or per inning
@Params:
    - Game params:           Params for /games/ (tags/users/date/etc)
    - Event params:
    - by_inning:      [bool] Show breakdown by inning instead of by game
'''
@app.route('/star_chances/', methods = ['GET'])
def endpoint_star_chances():
    #Sanitize games params 
    try:
        list_of_event_ids = list() # Holds IDs for all the events we want data from
        if (len(request.args.getlist('events')) != 0):
            list_of_event_ids = [int(game_id) for game_id in request.args.getlist('events')]
            list_of_event_id_tuples = db.session.query(Event.id).filter(Event.id.in_(tuple(list_of_event_ids))).all()
            if (len(list_of_event_id_tuples) != len(list_of_event_ids)):
                return abort(408, description='Provided Events not found')

        else:
            list_of_event_ids = endpoint_event(True)['Events']   # List of dicts of games we want data from and info about those games
    except:
        return abort(408, description='Invalid GameID')

    event_id_string, event_empty = format_list_for_SQL(list_of_event_ids)

    if event_empty:
        return {}

    select_statement = ''
    group_by_statement = ''
    if request.args.get('by_inning') in ["true", "True", "T", "t"]:
        select_statement = (
            'event.inning AS inning, \n'
            'event.half_inning AS half_inning, \n'
        )
        group_by_statement = 'GROUP BY event.inning, event.half_inning'

    query = (
        'SELECT \n'
       f'{select_statement}' 
        'COUNT(CASE WHEN (event.runner_on_1 IS NULL AND event.runner_on_2 IS NULL \n'
        '                 AND event.runner_on_3 IS NULL AND event.event_num != 0'
        '                 AND (event.away_stars < 5 OR event.home_stars < 5)) THEN 1 ELSE NULL END) AS eligible_event, \n'
        'COUNT(CASE WHEN (event.star_chance = 1 AND event.result_of_ab > 0) THEN 1 ELSE NULL END) AS star_chances, \n'
        'COUNT(CASE WHEN (event.result_of_ab > 0) THEN 1 ELSE NULL END) AS total_events, \n'
        'COUNT(CASE WHEN (event.star_chance = 1 AND event.result_of_ab >= 1 AND event.result_of_ab <= 6 AND event.result_of_ab != 0) THEN 1 ELSE NULL END) AS pitcher_win, \n'
        'COUNT(CASE WHEN (event.star_chance = 1 AND event.result_of_ab >= 7) THEN 1 ELSE NULL END) AS batter_win, \n'
        'COUNT ( DISTINCT event.game_id ) AS games \n'
        'FROM event \n'
       f'WHERE event.id IN {event_id_string} and event.result_of_ab != 0 \n'
       f'{group_by_statement}'
    )

    print(query)

    result = db.session.execute(query).all()

    data = []
    for entry in result:
        data.append(entry._asdict())
    return {
        'Data': data
    }

# @app.route('/pitch_analysis/', methods = ['GET'])
# def endpoint_pitch_analysis():
#     #Sanitize games params 
#     try:
#         list_of_event_ids = list() # Holds IDs for all the events we want data from
#         if (len(request.args.getlist('events')) != 0):
#             list_of_event_ids = [int(game_id) for game_id in request.args.getlist('events')]
#             list_of_event_id_tuples = db.session.query(Event.id).filter(Event.id.in_(tuple(list_of_event_ids))).all()
#             if (len(list_of_event_id_tuples) != len(list_of_event_ids)):
#                 return abort(408, description='Provided Events not found')

#         else:
#             list_of_event_ids = endpoint_event(True)['Events']   # List of dicts of games we want data from and info about those games
#     except:
#         return abort(408, description='Invalid GameID')

#     event_id_string, event_empty = format_list_for_SQL(list_of_event_ids)

#     if event_empty:
#         return {}

#     query = (
#         'SELECT \n'
#         'event.balls AS count_balls, \n'
#         'event.strikes AS count_strikes, \n'
#         'event.outs AS count_outs, \n'
#         'COUNT (CASE WHEN (pitch.pitch_result >= 3 AND pitch.pitch_result <= 6) THEN 1 ELSE NULL END) AS result_strike_or_hit, \n' #Hittable
#         'COUNT (CASE WHEN (pitch.pitch_result = 0) THEN 1 ELSE NULL END) AS result_hbp, \n'
#         'COUNT (CASE WHEN (pitch.pitch_result = 1 OR pitch.pitch_result = 2) THEN 1 ELSE NULL END) AS result_ball \n'
#         'FROM event \n'
#         'JOIN pitch_summary AS pitch ON event.pitch_summary_id = pitch.id \n'
#        f'WHERE event.id IN {event_id_string} \n'
#         'GROUP BY count_balls, count_strikes, count_outs'
#     )

#     print(query)

#     result = db.session.execute(query).all()

#     data = []
#     for entry in result:
#         data.append(entry._asdict())
#     return {
#         'Data': data
#     }


## === Detailed stats ===
'''
@ Endpoint: detailed_stats
@ Description: Returns batting, pitching, fielding, and star stats on configurable levels
@ Params:
    - Game params:                  Params for /games/ (tags/users/date/etc)
    - games:             [0-x],        game ids to use. If not provided arguments for /games/ endpoint will be expected and used
    - username:          [],           users to get stats for. All users if blank
    - char_id:           [0-54],       character ids to get stats for. All charas if blank
    - by_user:           [bool],       When true stats will be grouped by user. When false, all users will be separate
    - by_char:           [bool],       When true stats will be grouped by character. When false, all characters will be separate
    - by_swing:          [bool],       When true batting stats will be organized by swing type (slap, charge, star). When false, 
                                    all swings will be combined. Only considered for swings
    - exlude_nonfair:    [bool],       Exlude foul and unknown hits from the return
    - exclude_batting:   [bool],       Do not return stats from the batting section
    - exclude_pitching:  [bool],       Do not return stats from the pitching section
    - exclude_misc:      [bool],       Do not return stats from the misc section
    - exclude_fielding:  [bool],       Do not return stats from the fielding section
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
            games = endpoint_games(True)   # List of dicts of games we want data from and info about those games
            for game_id in games['game_ids']:
                list_of_game_ids.append(game_id)
    except:
        return abort(408, description='Invalid GameID')

    # Sanitize character params
    try:
        list_of_char_ids = request.args.getlist('char_id')
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

    #Stat exclussion flags
    exclude_batting_stats = (request.args.get('exclude_batting') == '1')
    exclude_pitching_stats = (request.args.get('exclude_pitching') == '1')
    exclude_misc_stats = (request.args.get('exclude_misc') == '1')
    exclude_fielding_stats = (request.args.get('exclude_fielding') == '1')

    usernames = request.args.getlist('username')
    usernames_lowercase = tuple([lower_and_remove_nonalphanumeric(username) for username in usernames])
    #List returns a list of user_ids, each in a tuple. Convert to list and return to tuple for SQL query
    list_of_user_id_tuples = db.session.query(RioUser.id).filter(RioUser.username_lowercase.in_(usernames_lowercase)).all()
    # using list comprehension
    list_of_user_id = list(itertools.chain(*list_of_user_id_tuples))

    tuple_user_ids = tuple(list_of_user_id)

    #If we didn't find every user provided in the DB, abort
    if (len(tuple_user_ids) != len(usernames)):
        return abort(408, description='Provided Usernames not found')

    #If a char was provided that is not 0-54 abort
    invalid_chars=[i for i in tuple_char_ids if int(i) not in range(0,55)]
    if len(invalid_chars) > 0:
        return abort(408, description='Invalid provided characters')

    
    # Individual functions create queries to get their respective stats
    return_dict = {}
    if (not exclude_batting_stats):
        batting_stats = query_detailed_batting_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char, group_by_swing, exclude_nonfair)
    if (not exclude_pitching_stats):
        pitching_stats = query_detailed_pitching_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)
    if (not exclude_misc_stats):
        misc_stats = query_detailed_misc_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)
    if (not exclude_fielding_stats):
        fielding_stats = query_detailed_fielding_stats(return_dict, tuple_of_game_ids, tuple_user_ids, tuple_char_ids, group_by_user, group_by_char)

    return {
        'Stats': return_dict
    }

def query_detailed_batting_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False, group_by_swing=False, exclude_nonfair=False):

    where_statement = build_where_statement(game_ids, char_ids, user_ids)

    by_user = 'character_game_summary.user_id, rio_user.username' if group_by_user else ''
    select_user = 'character_game_summary.user_id, \n rio_user.username AS username, \n' if group_by_user else ''

    by_char = 'character_game_summary.char_id, character.name' if group_by_char else ''
    select_char = 'character_game_summary.char_id AS char_id, \n character.name AS char_name, \n' if group_by_char else ''

    by_swing = 'pitch_summary.type_of_swing' if group_by_swing else ''
    select_swing = 'pitch_summary.type_of_swing AS type_of_swing, \n' if group_by_swing else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char, by_swing]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    contact_batting_query = (
        
        'SELECT \n'
        f"{select_user}"
        f"{select_char}"
        f"{select_swing}"
        'COUNT(CASE WHEN (contact_summary.primary_result = 0) THEN 1 ELSE NULL END) AS outs, \n'
        'COUNT(CASE WHEN contact_summary.primary_result = 1 THEN 1 ELSE NULL END) AS foul_hits, \n'
        'COUNT(CASE WHEN (contact_summary.primary_result = 2 OR contact_summary.primary_result = 3) THEN 1 ELSE NULL END) AS fair_hits, \n'
        'COUNT(CASE WHEN (contact_summary.type_of_contact = 0 OR contact_summary.type_of_contact = 4) THEN 1 ELSE NULL END) AS sour_hits, '
        'COUNT(CASE WHEN (contact_summary.type_of_contact = 1 OR contact_summary.type_of_contact = 3) THEN 1 ELSE NULL END) AS nice_hits, '
        'COUNT(CASE WHEN contact_summary.type_of_contact = 2 THEN 1 ELSE NULL END) AS perfect_hits, '
        'COUNT(CASE WHEN contact_summary.secondary_result = 7 THEN 1 ELSE NULL END) AS singles, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 8 THEN 1 ELSE NULL END) AS doubles, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 9 THEN 1 ELSE NULL END) AS triples, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 10 THEN 1 ELSE NULL END) AS homeruns, \n'
        'COUNT(CASE WHEN contact_summary.secondary_result = 14 THEN 1 ELSE NULL END) AS sacflys, \n'
        'COUNT(CASE WHEN event.result_of_ab = 1 THEN 1 ELSE NULL END) AS strikeouts, \n'
        'COUNT(CASE WHEN event.result_of_ab != 0 THEN 1 ELSE NULL END) AS plate_appearances, \n'
        'SUM(event.result_rbi) AS rbi '
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN event ON character_game_summary.id = event.batter_id \n'
        'JOIN pitch_summary ON pitch_summary.id = event.pitch_summary_id \n'
        'LEFT JOIN contact_summary ON pitch_summary.contact_summary_id = contact_summary.id \n'
       f"   {'AND contact_summary.primary_result != 1' if exclude_nonfair else ''} \n"
        'JOIN rio_user ON character_game_summary.user_id = rio_user.id \n'
       f"{where_statement}"
       f"{group_by_statement}"
    )

    print(contact_batting_query)

    #Redo groups, removing swing type
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    non_contact_batting_query = ( 
        'SELECT \n'
       f"{select_user}"
       f"{select_char}"
        'SUM(character_game_summary.walks_bb) AS summary_walks_bb, \n'
        'SUM(character_game_summary.walks_hit) AS summary_walks_hbp, \n'
        'SUM(character_game_summary.strikeouts) AS summary_strikeouts, \n'
        'SUM(character_game_summary.singles) AS summary_singles, \n'
        'SUM(character_game_summary.doubles) AS summary_doubles, \n'
        'SUM(character_game_summary.triples) AS summary_triples, \n'
        'SUM(character_game_summary.homeruns) AS summary_homeruns, \n'
        'SUM(character_game_summary.sac_flys) AS summary_sac_flys, \n'
        'SUM(character_game_summary.rbi) AS summary_rbi, \n'
        'SUM(character_game_summary.at_bats) AS summary_at_bats, \n'
        'SUM(character_game_summary.hits) AS summary_hits \n'
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN rio_user ON character_game_summary.user_id = rio_user.id \n'
       f"{where_statement}"
       f"{group_by_statement}"
    )
    contact_batting_results = db.session.execute(contact_batting_query).all()
    non_contact_batting_results = db.session.execute(non_contact_batting_query).all()

    batting_stats = {}
    for result_row in contact_batting_results:
        update_detailed_stats_dict(stat_dict, 'Batting', result_row, group_by_user, group_by_char, group_by_swing)
    for result_row in non_contact_batting_results:
        update_detailed_stats_dict(stat_dict, 'Batting', result_row, group_by_user, group_by_char)

    return batting_stats

def query_detailed_pitching_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False):

    where_statement = build_where_statement(game_ids, char_ids, user_ids)

    by_user = 'character_game_summary.user_id, rio_user.username' if group_by_user else ''
    select_user = 'character_game_summary.user_id, \n rio_user.username AS username, \n' if group_by_user else ''

    by_char = 'character_game_summary.char_id, character.name' if group_by_char else ''
    select_char = 'character_game_summary.char_id AS char_id, \n character.name AS char_name, \n' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    pitching_summary_query = (
        'SELECT '
        f"{select_user}"
        f"{select_char}"
        'SUM(character_game_summary.batters_faced) AS batters_faced, \n'
        'SUM(character_game_summary.runs_allowed) AS runs_allowed, \n'
        'SUM(character_game_summary.hits_allowed) AS hits_allowed, \n'
        'SUM(character_game_summary.strikeouts_pitched) AS strikeouts_pitched, \n'
        'SUM(character_game_summary.star_pitches_thrown) AS star_pitches_thrown, \n'
        'SUM(character_game_summary.outs_pitched) AS outs_pitched, \n'
        'SUM(character_game_summary.batters_walked) AS walks_bb, \n'
        'SUM(character_game_summary.batters_hit) AS walks_hbp, \n'
        'SUM(character_game_summary.pitches_thrown) AS total_pitches \n'
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN rio_user ON rio_user.id = character_game_summary.user_id \n'
       f"{where_statement}"
       f"{group_by_statement}"
    )

    pitch_breakdown_query = (
        'SELECT '
        f"{select_user}"
        f"{select_char}"
        'COUNT(CASE WHEN (pitch_summary.in_strikezone = false AND type_of_swing = 0) THEN 1 ELSE NULL END) AS balls, \n'
        'COUNT(CASE WHEN ('
            '(pitch_summary.in_strikezone = true AND pitch_summary.contact_summary_id = NULL) OR'
            '(pitch_summary.in_strikezone = false AND type_of_swing > 0)'
            ') THEN 1 ELSE NULL END) AS strikes \n'
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN event ON character_game_summary.id = event.pitcher_id \n'
        'JOIN pitch_summary ON pitch_summary.id = event.pitch_summary_id \n'
        'JOIN contact_summary ON contact_summary.id = pitch_summary.contact_summary_id \n'
        'JOIN rio_user ON rio_user.id = character_game_summary.user_id \n'
       f"{where_statement}"
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
    where_statement = build_where_statement(game_ids, char_ids, user_ids)

    by_user = 'character_game_summary.user_id, rio_user.username' if group_by_user else ''
    select_user = 'character_game_summary.user_id, \n rio_user.username AS username, \n' if group_by_user else ''

    by_char = 'character_game_summary.char_id, character.name' if group_by_char else ''
    select_char = 'character_game_summary.char_id AS char_id, \n character.name AS char_name, \n' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''

    query = (
        'SELECT '
       f"{select_user}"
       f"{select_char}"
       f"COUNT(*){'/9' if group_by_char != True else ''} AS game_appearances, \n "
       f"SUM(CASE WHEN game.away_score > game.home_score AND game.away_player_id = rio_user.id THEN 1 ELSE 0 END){'/9' if group_by_char != True else ''} AS away_wins, \n"
       f"SUM(CASE WHEN game.away_score < game.home_score AND game.away_player_id = rio_user.id THEN 1 ELSE 0 END){'/9' if group_by_char != True else ''} AS away_loses, \n"
       f"SUM(CASE WHEN game.home_score > game.away_score AND game.home_player_id = rio_user.id THEN 1 ELSE 0 END){'/9' if group_by_char != True else ''} AS home_wins, \n"
       f"SUM(CASE WHEN game.home_score < game.away_score AND game.home_player_id = rio_user.id THEN 1 ELSE 0 END){'/9' if group_by_char != True else ''} AS home_loses, \n"      
        'SUM(character_game_summary.defensive_star_successes) AS defensive_star_successes, \n'
        'SUM(character_game_summary.defensive_star_chances) AS defensive_star_chances, \n'
        'SUM(character_game_summary.defensive_star_chances_won) AS defensive_star_chances_won, \n'
        'SUM(character_game_summary.offensive_stars_put_in_play) AS offensive_stars_put_in_play, \n'
        'SUM(character_game_summary.offensive_star_successes) AS offensive_star_successes, \n'
        'SUM(character_game_summary.offensive_star_chances) AS offensive_star_chances, \n'
        'SUM(character_game_summary.offensive_star_chances_won) AS offensive_star_chances_won \n'
        'FROM character_game_summary \n'
        'JOIN game ON character_game_summary.game_id = game.game_id \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN rio_user ON rio_user.id = character_game_summary.user_id \n'
       f"{where_statement}"
       f"{group_by_statement}"
    )

    results = db.session.execute(query).all()
    for result_row in results:
        update_detailed_stats_dict(stat_dict, 'Misc', result_row, group_by_user, group_by_char)

    return

def query_detailed_fielding_stats(stat_dict, game_ids, user_ids, char_ids, group_by_user=False, group_by_char=False):

    where_statement = build_where_statement(game_ids, char_ids, user_ids)

    by_user = 'character_game_summary.user_id, rio_user.username' if group_by_user else ''
    select_user = 'character_game_summary.user_id, \n rio_user.username AS username, \n' if group_by_user else ''

    by_char = 'character_game_summary.char_id, character.name' if group_by_char else ''
    select_char = 'character_game_summary.char_id AS char_id, \n character.name AS char_name, \n' if group_by_char else ''

    # Build groupby statement by joining all the groups together. Empty statement if all groups are empty
    groups = ','.join(filter(None,[by_user, by_char]))
    group_by_statement = f"GROUP BY {groups} " if groups != '' else ''
    position_query = (
        'SELECT '
        f"{select_user}"
        f"{select_char}"
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
        'JOIN rio_user ON rio_user.id = character_game_summary.user_id \n'
       f"{where_statement}"
       f"{group_by_statement}"
    )

    fielding_query = (
        'SELECT '
        f"{select_user}"
        f"{select_char}"
        'COUNT(CASE WHEN fielding_summary.action = 1 THEN 1 ELSE NULL END) AS jump_catches, \n'
        'COUNT(CASE WHEN fielding_summary.action = 2 THEN 1 ELSE NULL END) AS diving_catches, \n'
        'COUNT(CASE WHEN fielding_summary.action = 3 THEN 1 ELSE NULL END) AS wall_jumps, \n'
        'SUM(CASE WHEN fielding_summary.swap = True THEN 1 ELSE 0 END) AS swap_successes, \n'
        'COUNT(CASE WHEN fielding_summary.bobble != 0 THEN 1 ELSE NULL END) AS bobbles \n'
        #SUM( Insert other stats once questions addressed
        'FROM character_game_summary \n'
        'JOIN character ON character_game_summary.char_id = character.char_id \n'
        'JOIN fielding_summary ON fielding_summary.fielder_character_game_summary_id = character_game_summary.id \n'
        'JOIN rio_user ON rio_user.id = character_game_summary.user_id \n'
       f"{where_statement}"
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
                pprint(result_row._asdict())
                
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
        elif cTYPE_OF_SWING[result_row.type_of_swing] in in_stat_dict[type_of_result]:
            print('ERROR: FOUND PREVIOUS SWING TYPE')
            
        in_stat_dict[type_of_result][cTYPE_OF_SWING[result_row.type_of_swing]].update(data_dict)

    #User=0, Char=0, Swing=0
    else:
        if type_of_result not in in_stat_dict:
            in_stat_dict[type_of_result] = {}
        in_stat_dict[type_of_result].update(data_dict)
