from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, RioUser, Character, Game, CharacterGameSummary, Tag, Event, TagSet, PitchSummary, ContactSummary, CharacterPositionSummary, FieldingSummary
from ..consts import *
from ..util import *
from sqlalchemy import select, func, case, text
from sqlalchemy.orm import aliased
import time
import datetime
from .stats.pitcher_wins import calculate_pitcher_wins_for_games
from .stats.runs_scored import calculate_runs_scored_for_games
from .games import get_game_ids
from ..utils.db_helpers import sanitize_int_list, resolve_names

# === Parameterized Grouping Configuration ===
# Universal grouping dimensions that apply to all stat types (Batting, Pitching, Fielding, Misc)
# Stat-specific dimensions (e.g., by_swing for Batting) are handled separately in their respective functions
#
# To add a new universal grouping dimension (e.g., by_position, by_team):
# 1. Add new entry to GROUPING_DIMENSIONS config below
# 2. Add dimension name to GROUPING_ORDER list (order determines nesting depth)
# 3. Add to active_dimensions dict in endpoint_detailed_stats() where request args are parsed
#    Example: 'position': (request.args.get('by_position') == '1')
# That's it! The dimension automatically flows through all query functions and update_detailed_stats_dict

# Order of dimensions in the nested dict structure: game → user → roster_order → char → stat_type → [batting_hand|fielding_hand|swing]
# Note: batting_hand, fielding_hand, and swing are stat-specific and nest INSIDE stat_type, not before it
GROUPING_ORDER = ['game', 'user', 'roster_order', 'char', 'batting_hand', 'fielding_hand']

# Config field descriptions:
# - select_cols: SQLAlchemy column expressions to include in SELECT clause (e.g., Character.name.label('char_name'))
# - group_cols: SQLAlchemy columns for GROUP BY clause (must match select_cols for aggregation to work)
# - path_key: Result row attribute name whose value becomes a dict key in the nested structure
#             (e.g., 'char_name' → result_row.char_name = "Mario" → nested dict key: {"Mario": {...}})
# - data_keys_to_remove: Keys to remove from stat data after using them for path navigation
#                        (prevents duplication - "Mario" is a dict key, so remove from stat values)
# - stat_specific: (optional) List of stat types this dimension applies to (if omitted, applies to all)

GROUPING_DIMENSIONS = {
    'user': {
        'select_cols': [RioUser.username.label('username')],
        'group_cols': [RioUser.username],
        'path_key': 'username',
        'data_keys_to_remove': ['username', 'user_id'],
    },
    'char': {
        'select_cols': [
            Character.char_id.label('char_id'),
            Character.name.label('char_name')
        ],
        'group_cols': [Character.char_id, Character.name],
        'path_key': 'char_name',
        'data_keys_to_remove': ['char_name', 'char_id'],
    },
    'game': {
        'select_cols': [CharacterGameSummary.game_id.label('game_id')],
        'group_cols': [CharacterGameSummary.game_id],
        'path_key': 'game_id',
        'data_keys_to_remove': ['game_id'],
    },
    'roster_order': {
        'select_cols': [CharacterGameSummary.roster_loc.label('roster_loc')],
        'group_cols': [CharacterGameSummary.roster_loc],
        'path_key': 'roster_loc',
        'data_keys_to_remove': ['roster_loc'],
    },
    'batting_hand': {
        'select_cols': [CharacterGameSummary.batting_hand.label('batting_hand')],
        'group_cols': [CharacterGameSummary.batting_hand],
        'path_key': 'batting_hand',
        'data_keys_to_remove': ['batting_hand'],
        'stat_specific': ['Batting'],  # Only applies to batting stats
    },
    'fielding_hand': {
        'select_cols': [CharacterGameSummary.fielding_hand.label('fielding_hand')],
        'group_cols': [CharacterGameSummary.fielding_hand],
        'path_key': 'fielding_hand',
        'data_keys_to_remove': ['fielding_hand'],
        'stat_specific': ['Pitching'],  # Only applies to pitching stats
    },
}

def _build_base_query_components(active_dimensions, game_ids, user_ids, char_ids, stat_type=None):
    """
    Build common select_cols, group_cols, and filters for stat queries.

    This extracts the repetitive setup logic shared across all stat query functions.
    Uses GROUPING_DIMENSIONS config to dynamically build query components based on grouping flags.

    Args:
        active_dimensions: Dict of dimension_name -> bool (e.g., {'user': True, 'char': False})
        game_ids: Set of game IDs to filter by (required)
        user_ids: Set of user IDs to filter by (optional)
        char_ids: Set of character IDs to filter by (optional)
        stat_type: Optional stat type ('Batting', 'Pitching', 'Fielding', 'Misc') for stat-specific dimensions

    Returns:
        tuple: (select_cols, group_cols, filters) ready to use in SQLAlchemy queries
    """
    select_cols = []
    group_cols = []

    # Build select and group columns based on active grouping dimensions
    # Iterate through dimensions in defined order
    for dim_name in GROUPING_ORDER:
        if active_dimensions.get(dim_name):
            config = GROUPING_DIMENSIONS[dim_name]
            # Skip stat-specific dimensions if stat_type doesn't match or isn't provided
            if 'stat_specific' in config:
                if stat_type is None or stat_type not in config['stat_specific']:
                    continue
            select_cols.extend(config['select_cols'])
            group_cols.extend(config['group_cols'])

    # Build filters - game_ids is always present
    filters = [CharacterGameSummary.game_id.in_(game_ids)]

    if user_ids:
        filters.append(CharacterGameSummary.user_id.in_(user_ids))
    if char_ids:
        filters.append(CharacterGameSummary.char_id.in_(char_ids))

    return select_cols, group_cols, filters

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



'''
@Endpoint: Events
@Description: Used to pick out events that fit the given params
@Params:
    - Game params:           Params for /games/ (tags/users/date/etc)
    - games:           [0-x],   games if not using the game endpoint params
    - pitcher_char:    [0-53],  pitcher char ids
    - batter_char:     [0-53],  batter char ids
    - fielder_char:    [0-53],  fielder char ids
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
    - home_score       [0-50],  home score
    - away_score       [0-50],  away score
    - star_chance      [0-1],   bool for star chance
    - users_as_batter  [0-1],   bool if you want to only get the events for the given users when they are the batter
    - users_as_pitcher [0-1],   bool if you want to only get the events for the given users when they are the pitcher
    - final_result     [0-16],  value for the final result of the event
    - limit_events            int or False, value to limit the events
'''
def _parse_event_args(args):
    if len(args.getlist('games')) != 0:
        try:
            list_of_game_ids = [int(game_id) for game_id in args.getlist('games')]
        except ValueError:
            abort(400, description='Invalid GameID')
        existing_ids = db.session.execute(
            select(Game.game_id).where(Game.game_id.in_(list_of_game_ids))
        ).scalars().all()
        if len(existing_ids) != len(list_of_game_ids):
            abort(404, description='Provided GameIDs not found')
    else:
        list_of_game_ids = get_game_ids(args, limit=None)

    list_of_batter_user_ids = []
    list_of_pitcher_user_ids = []

    vs_user_ids = resolve_names(args.getlist('vs_username'), RioUser.id, RioUser.username_lowercase,
                                'vs_username(s)', transform=lower_and_remove_nonalphanumeric)
    user_ids = resolve_names(args.getlist('username'), RioUser.id, RioUser.username_lowercase,
                             'username(s)', transform=lower_and_remove_nonalphanumeric)

    for uid_list in [vs_user_ids, user_ids]:
        if args.get('users_as_batter') == "1":
            list_of_batter_user_ids += uid_list
        if args.get('users_as_pitcher') == "1":
            list_of_pitcher_user_ids += uid_list

    int_params = [
        ('pitcher_char',  cMAX_CHAR_ID),
        ('batter_char',   cMAX_CHAR_ID),
        ('contact',       cMAX_CONTACT_TYPES),
        ('swing',         len(cTYPE_OF_SWING)),
        ('pitch',         len(cTYPE_OF_SWING)),
        ('chem_link',     cMAX_CHEM_LINKS),
        ('batter_hand',   len(cHANDEDNESS)),
        ('pitcher_hand',  len(cHANDEDNESS)),
        ('fielder_char',  cMAX_CHAR_ID),
        ('fielder_pos',   cMAX_FIELDER_POS),
        ('inning',        cMAX_INNING),
        ('half_inning',   len(cHANDEDNESS)),
        ('balls',         cMAX_BALLS),
        ('strikes',       cMAX_STRIKES),
        ('outs',          cMAX_OUTS),
        ('home_score',    cMAX_SCORE),
        ('away_score',    cMAX_SCORE),
        ('final_result',  cMAX_FINAL_RESULT),
    ]

    parsed = {
        'game_ids':         list_of_game_ids,
        'batter_user_ids':  list_of_batter_user_ids,
        'pitcher_user_ids': list_of_pitcher_user_ids,
        'star_chance':      [1] if args.get('star_chance') == '1' else [],
    }

    for param, max_val in int_params:
        values, error = sanitize_int_list(args.getlist(param), f'Invalid {param}', max_val)
        if values is None:
            abort(400, description=error)
        parsed[param] = values

    return parsed


def _build_event_filters(parsed):
    batter   = aliased(CharacterGameSummary)
    pitcher  = aliased(CharacterGameSummary)
    fielder  = aliased(CharacterGameSummary)
    pitch    = aliased(PitchSummary)
    contact  = aliased(ContactSummary)
    fielding = aliased(FieldingSummary)

    # (values, column expression, null_sentinel)
    # Empty value lists are skipped entirely (no predicate added).
    where_specs = [
        (parsed['game_ids'],        Event.game_id,           ),
        (parsed['pitcher_char'],    pitcher.char_id,         ),
        (parsed['batter_char'],     batter.char_id,          ),
        (parsed['swing'],           pitch.type_of_swing,     ),
       #(parsed['pitch'],           pitch.type_of_swing,     ) #This one needs a DB rework. Manually add later
        (parsed['chem_link'],       Event.chem_links_ob,     ),
        (parsed['batter_hand'],     batter.batting_hand,     ),
        (parsed['pitcher_hand'],    pitcher.fielding_hand,   ),
        (parsed['fielder_char'],    fielder.char_id,         ),
        (parsed['fielder_pos'],     fielding.position,       ),
        (parsed['inning'],          Event.inning,            ),
        (parsed['half_inning'],     Event.half_inning,       ),
        (parsed['balls'],           Event.balls,             ),
        (parsed['strikes'],         Event.strikes,           ),
        (parsed['outs'],            Event.outs,              ),
        (parsed['home_score'],      Event.home_score,        ),
        (parsed['away_score'],      Event.away_score,        ),
        (parsed['star_chance'],     Event.star_chance,       ),
        (parsed['batter_user_ids'], batter.user_id,          ),
        (parsed['pitcher_user_ids'],pitcher.user_id,         ),
        (parsed['final_result'],    Event.result_of_ab,      ),
    ]

    filters = []
    for values, column in where_specs:
        if not values:
            continue
        filters.append(column.in_(values))

    # TODO: contact=5 is a sentinel for "no contact" (miss/foul), stored as NULL in the DB.
    #       Fix by storing an explicit contact type value instead of NULL, with a migration +
    #       emulator upload change. That would let this be a plain filter like all others.
    contact_vals = parsed['contact']
    if contact_vals:
        no_contact = 5 in contact_vals
        real_vals  = [v for v in contact_vals if v != 5]
        if real_vals and no_contact:
            filters.append(contact.type_of_contact.in_(real_vals) | contact.type_of_contact.is_(None))
        elif no_contact:
            filters.append(contact.type_of_contact.is_(None))
        else:
            filters.append(contact.type_of_contact.in_(real_vals))

    aliases = {
        'batter': batter,
        'pitcher': pitcher,
        'fielder': fielder,
        'pitch': pitch,
        'contact': contact,
        'fielding': fielding,
    }

    return filters, aliases


def _build_event_stmt(filters, aliases, columns):
    batter   = aliases['batter']
    pitcher  = aliases['pitcher']
    fielder  = aliases['fielder']
    pitch    = aliases['pitch']
    contact  = aliases['contact']
    fielding = aliases['fielding']

    stmt = (
        select(*columns)
        .select_from(Event)
        .join(pitch,    Event.pitch_summary_id == pitch.id)
        .outerjoin(contact,  pitch.contact_summary_id == contact.id)        # Contact left-joined for misses
        .outerjoin(fielding, contact.fielding_summary_id == fielding.id)    # Fielding left-joined for HRs and misses
        .join(batter,   Event.batter_id == batter.id)
        .join(pitcher,  Event.pitcher_id == pitcher.id)
        .outerjoin(fielder, fielding.fielder_character_game_summary_id == fielder.id)
    )
    if filters:
        stmt = stmt.where(*filters)
    return stmt


def get_event_ids(args, limit=None):
    """Return a flat list of event IDs matching the given query args.

    Args:
        args: request.args (or any MultiDict with the same interface)
        limit: max events to return; None means no limit

    Returns:
        List of event IDs matching the filters.
    """
    parsed = _parse_event_args(args)
    filters, aliases = _build_event_filters(parsed)
    stmt = _build_event_stmt(filters, aliases, [Event.id.label('event_id')])
    if limit is not None:
        stmt = stmt.limit(limit)
    return [row.event_id for row in db.session.execute(stmt).all()]


@app.route('/events/', methods = ['GET'])
def endpoint_event():
    parsed = _parse_event_args(request.args)
    filters, aliases = _build_event_filters(parsed)

    default_limit = 1000
    max_limit     = 150000
    limit_raw = request.args.get('limit_events')
    if limit_raw is not None:
        try:
            limit_value = min(int(limit_raw), max_limit)
        except ValueError:
            abort(400, description="limit_events must be an integer")
    else:
        limit_value = default_limit

    columns = [
        Event.game_id.label('game_id'),
        Event.event_num.label('event_num'),
        Event.id.label('event_id'),
    ]
    stmt = _build_event_stmt(filters, aliases, columns)
    if limit_value is not None:
        stmt = stmt.limit(limit_value)

    events = {}
    for entry in db.session.execute(stmt).all():
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
#             list_of_event_ids = get_event_ids(request.args)
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
            list_of_event_ids = get_event_ids(request.args)
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
        'contact.ball_power AS ball_power, \n'
        'contact.ball_horiz_angle AS ball_horiz_angle, \n'
        'contact.ball_vert_angle AS ball_vert_angle, \n'
        'contact.contact_absolute AS contact_absolute, \n'
        'contact.contact_quality AS contact_quality, \n'
        'contact.rng1 AS rng1, \n'
        'contact.rng2 AS rng2, \n'
        'contact.rng3 AS rng3, \n'
        'contact.ball_x_velocity AS ball_x_velocity, \n'
        'contact.ball_y_velocity AS ball_y_velocity, \n'
        'contact.ball_z_velocity AS ball_z_velocity, \n'
        'contact.ball_x_contact_pos AS ball_x_contact_pos, \n'
        'contact.ball_z_contact_pos AS ball_z_contact_pos, \n'
        'contact.ball_x_landing_pos AS ball_x_landing_pos, \n'
        'contact.ball_y_landing_pos AS ball_y_landing_pos, \n'
        'contact.ball_z_landing_pos AS ball_z_landing_pos, \n'
        'contact.ball_max_height AS ball_max_height, \n'
        'contact.ball_hang_time AS ball_hang_time, \n'
        'contact.input_direction_stick AS stick_input, \n'
        'contact.charge_power_up AS charge_power_up, \n'
        'contact.charge_power_down AS charge_power_down, \n'
        'contact.frame_of_swing_upon_contact AS frame_of_swing, \n'
        'pitch.pitch_type, \n'
        'pitch.charge_pitch_type, \n'
        'pitch.type_of_swing, \n'
        'contact.type_of_contact, \n'
        'pitch.bat_x_contact_pos, \n'
        'pitch.bat_z_contact_pos, \n'
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
            list_of_event_ids = get_event_ids(request.args)
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
#             list_of_event_ids = get_event_ids(request.args)
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

@ URL example: http://127.0.0.1:5000/stats/?username=demouser1&character=1&by_swing=1

TODO: Add character name lookup
'''
@app.route('/stats/', methods = ['GET'])
def endpoint_detailed_stats():

    game_ids_param = request.args.getlist('games')
    if game_ids_param:
        try:
            game_ids = {int(game_id) for game_id in game_ids_param}
        except ValueError as e:
            abort(
                400,
                description=f"Invalid game ID (must be int): {e.args[0]}"
            )
        
        # Verify all game IDs exist in database
        stmt = select(Game.game_id).where(Game.game_id.in_(game_ids))
        existing_game_ids = set(db.session.execute(stmt).scalars().all())
        
        missing_ids = game_ids - existing_game_ids
        if missing_ids:
            return abort(404, description=f'Game IDs not found: {missing_ids}')
    else:
        game_ids = set(get_game_ids(request.args, limit=None))
        if not game_ids:
            return abort(404, description='No games found for provided parameters')

    # Sanitize character params
    char_id_param = request.args.getlist('char_id')
    char_ids = set()
    if char_id_param:
        try:
            char_ids = {int(char_id) for char_id in char_id_param}
        except ValueError as e:
            abort(
                400,
                description=f"Invalid Char ID (must be int): {e.args[0]}"
            )
        
        invalid_ids = {cid for cid in char_ids if not 0 <= cid <= 54}
        if invalid_ids:
            abort(400, description=f"Char IDs out of range (0-54): {invalid_ids}")

    # Parse grouping dimension flags - centralized location for adding new dimensions
    active_dimensions = {
        'user': (request.args.get('by_user') == '1'),
        'char': (request.args.get('by_char') == '1'),
        'game': (request.args.get('by_game') == '1'),
        'roster_order': (request.args.get('by_roster_order') == '1'),
        'batting_hand': (request.args.get('by_batting_hand') == '1'),
        'fielding_hand': (request.args.get('by_fielding_hand') == '1'),
    }

    # Stat-specific grouping flags (handled separately due to query complexity)
    group_by_swing = (request.args.get('by_swing') == '1')
    exclude_nonfair = (request.args.get('exclude_nonfair') == '1')
    include_pitcher_wins = (request.args.get('include_pitcher_wins') == '1')
    include_runs_scored = (request.args.get('include_runs_scored') == '1')

    # Stat exclusion flags
    exclude_batting_stats = (request.args.get('exclude_batting') == '1')
    exclude_pitching_stats = (request.args.get('exclude_pitching') == '1')
    exclude_misc_stats = (request.args.get('exclude_misc') == '1')
    exclude_fielding_stats = (request.args.get('exclude_fielding') == '1')

    usernames_param = request.args.getlist('username')
    user_ids = set()
    if usernames_param:
        usernames_normalized = set([lower_and_remove_nonalphanumeric(username) for username in usernames_param])

        stmt = select(RioUser.id, RioUser.username_lowercase).where(RioUser.username_lowercase.in_(usernames_normalized))
        results = db.session.execute(stmt).all()

        user_ids = set()
        found_usernames = set()
        for user_id, username in results:
            user_ids.add(user_id)
            found_usernames.add(username)

        missing_usernames = usernames_normalized - found_usernames
        if missing_usernames:
            return abort(404, description=f'Users not found: {missing_usernames}')

    # Individual functions create queries to get their respective stats
    return_dict = {}
    if (not exclude_batting_stats):
        batting_stats = query_detailed_batting_stats(return_dict, game_ids, user_ids, char_ids, active_dimensions, group_by_swing, exclude_nonfair, include_runs_scored)
    if (not exclude_pitching_stats):
        pitching_stats = query_detailed_pitching_stats(return_dict, game_ids, user_ids, char_ids, active_dimensions, include_pitcher_wins)
    if (not exclude_misc_stats):
        misc_stats = query_detailed_misc_stats(return_dict, game_ids, user_ids, char_ids, active_dimensions)
    if (not exclude_fielding_stats):
        fielding_stats = query_detailed_fielding_stats(return_dict, game_ids, user_ids, char_ids, active_dimensions)
    return {
        'Stats': return_dict
    }

def query_detailed_batting_stats(stat_dict, game_ids, user_ids, char_ids, active_dimensions, group_by_swing=False, exclude_nonfair=False, include_runs_scored=False):

    select_cols, group_cols, filters = _build_base_query_components(
        active_dimensions, game_ids, user_ids, char_ids, stat_type='Batting'
    )

    contact_join_condition = (PitchSummary.contact_summary_id == ContactSummary.id)
    if exclude_nonfair:
        contact_join_condition = contact_join_condition & (ContactSummary.primary_result != 1)

    non_contact_batting_query = (
        select(
            *select_cols,
            func.sum(CharacterGameSummary.walks_bb).label('summary_walks_bb'),
            func.sum(CharacterGameSummary.walks_hit).label('summary_walks_hbp'),
            func.sum(CharacterGameSummary.strikeouts).label('summary_strikeouts'),
            func.sum(CharacterGameSummary.singles).label('summary_singles'),
            func.sum(CharacterGameSummary.doubles).label('summary_doubles'),
            func.sum(CharacterGameSummary.triples).label('summary_triples'),
            func.sum(CharacterGameSummary.homeruns).label('summary_homeruns'),
            func.sum(CharacterGameSummary.sac_flys).label('summary_sac_flys'),
            func.sum(CharacterGameSummary.rbi).label('summary_rbi'),
            func.sum(CharacterGameSummary.at_bats).label('summary_at_bats'),
            func.sum(CharacterGameSummary.hits).label('summary_hits'),
            func.sum(CharacterGameSummary.star_hits).label('star_hits'),
            func.sum(CharacterGameSummary.bases_stolen).label('summary_bases_stolen')
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        non_contact_batting_query = non_contact_batting_query.group_by(*group_cols)

    # Stat-specific grouping: by_swing only applies to contact batting (not walks/HBP/strikeouts)
    # This is added AFTER non_contact query since non-contact events don't have swing data
    if group_by_swing:
        select_cols.append(PitchSummary.type_of_swing.label('type_of_swing'))
        group_cols.append(PitchSummary.type_of_swing)

    contact_batting_query = (
        select(
            *select_cols,
            func.count(case((ContactSummary.primary_result == 0, 1))).label('outs'),
            func.count(case((ContactSummary.primary_result == 1, 1))).label('foul_hits'),
            func.count(case(((ContactSummary.primary_result == 2) | (ContactSummary.primary_result == 3), 1))).label('fair_hits'),
            func.count(case(((ContactSummary.type_of_contact == 0) | (ContactSummary.type_of_contact == 4), 1))).label('sour_hits'),
            func.count(case(((ContactSummary.type_of_contact == 1) | (ContactSummary.type_of_contact == 3), 1))).label('nice_hits'),
            func.count(case((ContactSummary.type_of_contact == 2, 1))).label('perfect_hits'),
            func.count(case((ContactSummary.secondary_result == 7, 1))).label('singles'),
            func.count(case((ContactSummary.secondary_result == 8, 1))).label('doubles'),
            func.count(case((ContactSummary.secondary_result == 9, 1))).label('triples'),
            func.count(case((ContactSummary.secondary_result == 10, 1))).label('homeruns'),
            func.count(case((ContactSummary.secondary_result == 14, 1))).label('sacflys'),
            func.count(case((ContactSummary.secondary_result == 15, 1))).label('gidps'),
            func.count(case((Event.result_of_ab == 1, 1))).label('strikeouts'),
            func.count(case((Event.result_of_ab != 0, 1))).label('plate_appearances'),
            func.sum(Event.result_rbi).label('rbi'),
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(Event, CharacterGameSummary.id == Event.batter_id)
        .join(PitchSummary, PitchSummary.id == Event.pitch_summary_id)
        .outerjoin(ContactSummary, contact_join_condition)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        contact_batting_query = contact_batting_query.group_by(*group_cols)

    contact_batting_results = db.session.execute(contact_batting_query).all()
    non_contact_batting_results = db.session.execute(non_contact_batting_query).all()

    for result_row in contact_batting_results:
        update_detailed_stats_dict(stat_dict, 'Batting', result_row, active_dimensions, group_by_swing)
    for result_row in non_contact_batting_results:
        update_detailed_stats_dict(stat_dict, 'Batting', result_row, active_dimensions)

    # Add default runs_scored: 0 to all batting entries if requested
    if include_runs_scored:
        _add_default_to_stat_category(stat_dict, 'Batting', 'runs_scored', 0)

    # Optionally calculate runs scored (requires loading events and runners into memory)
    if include_runs_scored:

        # Build fresh select_cols and group_cols (not affected by group_by_swing)
        runs_select_cols, runs_group_cols, _ = _build_base_query_components(
            active_dimensions, game_ids, user_ids, char_ids, stat_type='Batting'
        )

        runs_by_cgs = calculate_runs_scored_for_games(list(game_ids))
        scoring_cgs_ids = list(runs_by_cgs.keys())

        if scoring_cgs_ids:
            runs_scored_query = (
                select(
                    *runs_select_cols,
                    func.count(CharacterGameSummary.id).label('runs_scored'),
                )
                .select_from(CharacterGameSummary)
                .join(Character, CharacterGameSummary.char_id == Character.char_id)
                .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
                .where(
                    CharacterGameSummary.id.in_(scoring_cgs_ids),
                    *filters
                )
            )

            if runs_group_cols:
                runs_scored_query = runs_scored_query.group_by(*runs_group_cols)

            runs_scored_results = db.session.execute(runs_scored_query).all()

            for result_row in runs_scored_results:
                update_detailed_stats_dict(stat_dict, 'Batting', result_row, active_dimensions)

    return

def query_detailed_pitching_stats(stat_dict, game_ids, user_ids, char_ids, active_dimensions, include_pitcher_wins=False):

    select_cols, group_cols, filters = _build_base_query_components(
        active_dimensions, game_ids, user_ids, char_ids, stat_type='Pitching'
    )

    pitching_summary_query = (
        select(
            *select_cols,
            func.sum(CharacterGameSummary.batters_faced).label('batters_faced'),
            func.sum(CharacterGameSummary.runs_allowed).label('runs_allowed'),
            func.sum(CharacterGameSummary.hits_allowed).label('hits_allowed'),
            func.sum(CharacterGameSummary.strikeouts_pitched).label('strikeouts_pitched'),
            func.sum(CharacterGameSummary.star_pitches_thrown).label('star_pitches_thrown'),
            func.sum(CharacterGameSummary.outs_pitched).label('outs_pitched'),
            func.sum(CharacterGameSummary.batters_walked).label('walks_bb'),
            func.sum(CharacterGameSummary.batters_hit).label('walks_hbp'),
            func.sum(CharacterGameSummary.pitches_thrown).label('total_pitches'),
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        pitching_summary_query = pitching_summary_query.group_by(*group_cols)

    pitch_breakdown_query = (
        select(
            *select_cols,
            func.count(case((
                (PitchSummary.in_strikezone == False) & (PitchSummary.type_of_swing == 0),
                1
            ))).label('balls'),
            func.count(case((
                ((PitchSummary.in_strikezone == True) & PitchSummary.contact_summary_id.is_(None)) |
                ((PitchSummary.in_strikezone == False) & (PitchSummary.type_of_swing > 0)),
                1
            ))).label('strikes'),
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(Event, CharacterGameSummary.id == Event.pitcher_id)
        .join(PitchSummary, PitchSummary.id == Event.pitch_summary_id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        pitch_breakdown_query = pitch_breakdown_query.group_by(*group_cols)

    pitching_summary_results = db.session.execute(pitching_summary_query).all()
    pitch_breakdown_results = db.session.execute(pitch_breakdown_query).all()

    for result_row in pitching_summary_results:
        update_detailed_stats_dict(stat_dict, 'Pitching', result_row, active_dimensions)
    for result_row in pitch_breakdown_results:
        update_detailed_stats_dict(stat_dict, 'Pitching', result_row, active_dimensions)

    # Add default pitcher_wins: 0 to all pitching entries if requested
    if include_pitcher_wins:
        _add_default_to_stat_category(stat_dict, 'Pitching', 'pitcher_wins', 0)

    # Optionally calculate pitcher wins (requires loading events into memory)
    if include_pitcher_wins:
        winning_pitcher_by_game = calculate_pitcher_wins_for_games(list(game_ids))
        winning_cgs_ids = list(winning_pitcher_by_game.values())

        if winning_cgs_ids:
            pitcher_wins_query = (
                select(
                    *select_cols,
                    func.count(CharacterGameSummary.id).label('pitcher_wins'),
                )
                .select_from(CharacterGameSummary)
                .join(Character, CharacterGameSummary.char_id == Character.char_id)
                .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
                .where(
                    CharacterGameSummary.id.in_(winning_cgs_ids),
                    *filters
                )
            )

            if group_cols:
                pitcher_wins_query = pitcher_wins_query.group_by(*group_cols)

            pitcher_wins_results = db.session.execute(pitcher_wins_query).all()

            for result_row in pitcher_wins_results:
                update_detailed_stats_dict(stat_dict, 'Pitching', result_row, active_dimensions)

    return

def query_detailed_misc_stats(stat_dict, game_ids, user_ids, char_ids, active_dimensions):

    select_cols, group_cols, filters = _build_base_query_components(
        active_dimensions, game_ids, user_ids, char_ids
    )

    # CharacterGameSummary stores 9 rows per game (one per character).
    # When filtering by specific chars: count "character-wins" (each char gets credit per win)
    # When viewing all chars: normalize to "games won" (avoid counting same game 9 times)
    # When grouping by_game or by_roster_order: each row is already per-character, no normalization needed
    if active_dimensions.get('char') or active_dimensions.get('roster_order'):
        divide_by = 1  # Each char gets separate row - no normalization needed
    elif active_dimensions.get('game') or len(char_ids) > 0:
        divide_by = 1  # Per-game grouping or char filter - no normalization needed
    else:
        divide_by = 9  # Normalize to games won (9 char-rows per game → 1 game)

    query = (
        select(
            *select_cols,
            (func.sum(case((
                (Game.away_score > Game.home_score) & (Game.away_player_id == RioUser.id),
                1
            ), else_=0)) / divide_by).label('away_wins'),
            (func.sum(case((
                (Game.away_score < Game.home_score) & (Game.away_player_id == RioUser.id),
                1
            ), else_=0)) / divide_by).label('away_loses'),
            (func.sum(case((
                (Game.home_score > Game.away_score) & (Game.home_player_id == RioUser.id),
                1
            ), else_=0)) / divide_by).label('home_wins'),
            (func.sum(case((
                (Game.home_score < Game.away_score) & (Game.home_player_id == RioUser.id),
                1
            ), else_=0)) / divide_by).label('home_loses'),
            (func.count() / divide_by).label('game_appearances'),
        )
        .select_from(CharacterGameSummary)
        .join(Game, CharacterGameSummary.game_id == Game.game_id)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        query = query.group_by(*group_cols)

    results = db.session.execute(query).all()
    for result_row in results:
        update_detailed_stats_dict(stat_dict, 'Misc', result_row, active_dimensions)

    return

def query_detailed_fielding_stats(stat_dict, game_ids, user_ids, char_ids, active_dimensions):

    select_cols, group_cols, filters = _build_base_query_components(
        active_dimensions, game_ids, user_ids, char_ids
    )

    position_query = (
        select(
            *select_cols,
            func.sum(CharacterPositionSummary.pitches_at_p).label('pitches_per_p'),
            func.sum(CharacterPositionSummary.pitches_at_c).label('pitches_per_c'),
            func.sum(CharacterPositionSummary.pitches_at_1b).label('pitches_per_1b'),
            func.sum(CharacterPositionSummary.pitches_at_2b).label('pitches_per_2b'),
            func.sum(CharacterPositionSummary.pitches_at_3b).label('pitches_per_3b'),
            func.sum(CharacterPositionSummary.pitches_at_ss).label('pitches_per_ss'),
            func.sum(CharacterPositionSummary.pitches_at_lf).label('pitches_per_lf'),
            func.sum(CharacterPositionSummary.pitches_at_cf).label('pitches_per_cf'),
            func.sum(CharacterPositionSummary.pitches_at_rf).label('pitches_per_rf'),
            func.sum(CharacterPositionSummary.outs_at_p).label('outs_per_p'),
            func.sum(CharacterPositionSummary.outs_at_c).label('outs_per_c'),
            func.sum(CharacterPositionSummary.outs_at_1b).label('outs_per_1b'),
            func.sum(CharacterPositionSummary.outs_at_2b).label('outs_per_2b'),
            func.sum(CharacterPositionSummary.outs_at_3b).label('outs_per_3b'),
            func.sum(CharacterPositionSummary.outs_at_ss).label('outs_per_ss'),
            func.sum(CharacterPositionSummary.outs_at_lf).label('outs_per_lf'),
            func.sum(CharacterPositionSummary.outs_at_cf).label('outs_per_cf'),
            func.sum(CharacterPositionSummary.outs_at_rf).label('outs_per_rf'),
            func.sum(CharacterGameSummary.big_plays).label('big_plays')
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(CharacterPositionSummary, CharacterPositionSummary.id == CharacterGameSummary.character_position_summary_id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        position_query = position_query.group_by(*group_cols)

    fielding_query = (
        select(
            *select_cols,
            func.count(case((FieldingSummary.action == 1, 1))).label('jump_catches'),
            func.count(case((FieldingSummary.action == 2, 1))).label('diving_catches'),
            func.count(case((FieldingSummary.action == 3, 1))).label('wall_jumps'),
            func.sum(case((FieldingSummary.swap == True, 1), else_=0)).label('swap_successes'),
            func.count(case((FieldingSummary.bobble != 0, 1))).label('bobbles'),
        )
        .select_from(CharacterGameSummary)
        .join(Character, CharacterGameSummary.char_id == Character.char_id)
        .join(FieldingSummary, FieldingSummary.fielder_character_game_summary_id == CharacterGameSummary.id)
        .join(RioUser, CharacterGameSummary.user_id == RioUser.id)
        .where(*filters)
    )

    if group_cols:
        fielding_query = fielding_query.group_by(*group_cols)

    position_results = db.session.execute(position_query).all()
    fielding_results = db.session.execute(fielding_query).all()
    for result_row in position_results:
        update_detailed_stats_dict(stat_dict, 'Fielding', result_row, active_dimensions)
    for result_row in fielding_results:
        update_detailed_stats_dict(stat_dict, 'Fielding', result_row, active_dimensions)
    return

def _add_default_to_stat_category(stat_dict, category, field_name, default_value):
    """
    Recursively adds a default field value to all entries in a stat category.

    This ensures fields like 'pitcher_wins' or 'runs_scored' appear as 0
    even when a player has no wins/runs, maintaining consistent response structure.

    Handles nested stat-specific groupings (e.g., handedness) inside the category.
    """
    def add_to_nested_dict(d):
        if isinstance(d, dict):
            # If this dict contains the category
            if category in d and isinstance(d[category], dict):
                category_dict = d[category]
                # Check if the category dict contains stat data or more nesting
                # If all values are dicts, it's nested (e.g., handedness grouping)
                # If it has non-dict values, it's the stat data level
                has_stat_data = any(not isinstance(v, dict) for v in category_dict.values())

                if has_stat_data:
                    # This is the stat data level - add the default here
                    if field_name not in category_dict:
                        category_dict[field_name] = default_value
                else:
                    # This is a grouping level (e.g., handedness) - recurse into it
                    for value in category_dict.values():
                        if isinstance(value, dict) and field_name not in value:
                            value[field_name] = default_value

            # Recurse into all nested dicts
            for value in d.values():
                if isinstance(value, dict):
                    add_to_nested_dict(value)

    add_to_nested_dict(stat_dict)


def update_detailed_stats_dict(in_stat_dict, type_of_result, result_row, active_dimensions, group_by_swing=False):
    """
    Update nested stat dictionary with result row data.

    Builds nested dict structure: [game_id]? → [username]? → [roster_loc]? → [char_name]? → type_of_result → [batting_hand|fielding_hand|swing]? → stat_data
    Uses GROUPING_DIMENSIONS config for universal dimensions, stat-specific dimensions nest inside type_of_result.

    Args:
        in_stat_dict: The dictionary to update (modified in place)
        type_of_result: The stat category ('Batting', 'Pitching', 'Fielding', 'Misc')
        result_row: SQLAlchemy result row containing stat data
        active_dimensions: Dict of dimension_name -> bool (e.g., {'user': True, 'char': False})
        group_by_swing: Whether swing grouping is active (Batting only, stat-specific)
    """
    # Extract stat data and build navigation path
    data_dict = result_row._asdict()
    path = []

    # Universal grouping dimensions (iterate through config in defined order)
    # Skip stat-specific dimensions (batting_hand, fielding_hand) - they go after type_of_result
    for dim_name in GROUPING_ORDER:
        if active_dimensions.get(dim_name):
            config = GROUPING_DIMENSIONS[dim_name]
            # Skip stat-specific dimensions - handled after type_of_result
            if 'stat_specific' in config:
                continue

            path_value = getattr(result_row, config['path_key'])
            path.append(path_value)
            for key in config['data_keys_to_remove']:
                data_dict.pop(key, None)

    # Always add type_of_result level (Batting/Pitching/Fielding/Misc)
    path.append(type_of_result)

    # Stat-specific grouping dimensions go AFTER type_of_result
    # batting_hand: only for Batting stats
    if active_dimensions.get('batting_hand') and type_of_result == 'Batting':
        batting_hand_name = cHANDEDNESS.get(result_row.batting_hand, 'Unknown')
        path.append(batting_hand_name)
        data_dict.pop('batting_hand', None)

    # fielding_hand: only for Pitching stats
    if active_dimensions.get('fielding_hand') and type_of_result == 'Pitching':
        fielding_hand_name = cHANDEDNESS.get(result_row.fielding_hand, 'Unknown')
        path.append(fielding_hand_name)
        data_dict.pop('fielding_hand', None)

    # by_swing: only for Batting stats
    if group_by_swing and type_of_result == 'Batting':
        swing_name = cTYPE_OF_SWING[result_row.type_of_swing]
        path.append(swing_name)
        data_dict.pop('type_of_swing', None)

    # Navigate to target dict, creating nested dicts as needed
    current_dict = in_stat_dict
    for key in path:
        if key not in current_dict:
            current_dict[key] = {}
        current_dict = current_dict[key]

    # Update final dict with stat data
    current_dict.update(data_dict)

@app.route('/stats/fix/', methods = ['GET'])
def fix_event_cgs_ids():
    all_games = Game.query.filter_by()
    game_count = 0
    for game in all_games:
        all_cgs = CharacterGameSummary.query.filter_by(game_id=game.game_id)
        cgs_dict = dict()
        cgs_dict[0] = {}
        cgs_dict[1] = {}
        cgs_by_id = dict()
        for cgs in all_cgs:
            cgs_dict[cgs.team_id][cgs.roster_loc] = cgs

            cgs_by_id[cgs.id] = cgs

        all_game_events = Event.query.filter_by(game_id=game.game_id)
        for event in all_game_events:
            #Fix pitcher_id
            pitcher_roster_loc = cgs_by_id[event.pitcher_id].roster_loc
            pitcher_team_id = 1-cgs_by_id[event.pitcher_id].team_id
            old_pitcher_id = event.pitcher_id
            event.pitcher_id = cgs_dict[pitcher_team_id][pitcher_roster_loc].id

            #Fix batter_id
            batter_roster_loc = cgs_by_id[event.batter_id].roster_loc
            batter_team_id = 1-cgs_by_id[event.batter_id].team_id
            old_batter_id = event.batter_id
            event.batter_id = cgs_dict[batter_team_id][batter_roster_loc].id

            print('Count: ', game_count, ' Game: ', game.game_id, ' Pitcher: ', old_pitcher_id, '->', event.pitcher_id, ' Batter: ', old_batter_id, '->', event.batter_id, sep="")

            #Fix catcher_id
            catcher_roster_loc = cgs_by_id[event.catcher_id].roster_loc
            catcher_team_id = 1-cgs_by_id[event.catcher_id].team_id
            event.catcher_id = cgs_dict[catcher_team_id][catcher_roster_loc].id
        game_count += 1

    db.session.commit()


@app.route('/ladder/games/', methods = ['GET'])
def endpoint_ladder_games():
    try:
        # Check if tags are valid and get a list of corresponding ids
        tag_sets = request.args.getlist('tag_set')
        tag_set_lowercase = tuple([lower_and_remove_nonalphanumeric(tag) for tag in tag_sets])
        tag_set_rows = db.session.query(TagSet).filter(TagSet.name_lowercase.in_(tag_set_lowercase)).all()
        tag_set_ids = tuple([str(tag_set.id) for tag_set in tag_set_rows])
        if len(tag_set_ids) != len(tag_sets):
            abort(400)
    except:
       return abort(400, 'Invalid TagSet')
    

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
    where_statement = f"WHERE game_history.date_created > {start_time_unix} \n"
    if (end_time_unix != 0):
        where_statement += f"AND game_history.date_created < {end_time_unix} \n"

    tag_set_id_string, include_tag_empty = format_tuple_for_SQL(tag_set_ids)
    if (not include_tag_empty):
        where_statement += f"AND game_history.tag_set_id IN {tag_set_id_string}"
    
    query = (
        'SELECT \n'
        '   game.game_id, \n'
        '   game.stadium_id AS stadium, \n'
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
        '   winner_rio_user.username AS winner_player, \n'
        '   loser_rio_user.username AS loser_player, \n'
        '   game_history.winner_incoming_elo AS winner_incoming_elo, \n'
        '   game_history.loser_incoming_elo AS loser_incoming_elo, \n'
        '   game_history.winner_result_elo AS winner_result_elo, \n'
        '   game_history.loser_result_elo AS loser_result_elo, \n'
        '   game_history.tag_set_id AS tag_set \n'
        'from game_history \n'
        'LEFT JOIN game ON game_history.game_id = game.game_id \n'
        'LEFT JOIN rio_user AS away_player ON game.away_player_id = away_player.id \n'
        'LEFT JOIN rio_user AS home_player ON game.home_player_id = home_player.id \n'
        'LEFT JOIN community_user AS winner_comm_user ON game_history.winner_comm_user_id = winner_comm_user.id \n'
        'LEFT JOIN community_user AS loser_comm_user ON game_history.loser_comm_user_id = loser_comm_user.id \n'
        'LEFT JOIN rio_user AS winner_rio_user ON winner_comm_user.user_id = winner_rio_user.id \n'
        'LEFT JOIN rio_user AS loser_rio_user ON loser_comm_user.user_id = loser_rio_user.id \n'
        'LEFT JOIN character_game_summary AS away_cgs  \n'
	    '    ON game.game_id = away_cgs.game_id  \n'
        '    AND away_cgs.user_id = away_player.id  \n'
        '    AND away_cgs.captain = True  \n'
        'LEFT JOIN character AS away_captain  \n'
        '    ON away_cgs.char_id = away_captain.char_id  \n'
        'LEFT JOIN character_game_summary AS home_cgs  \n'
	    '    ON game.game_id = home_cgs.game_id  \n'
        '    AND home_cgs.user_id = home_player.id  \n'
        '    AND home_cgs.captain = True  \n'
        'LEFT JOIN character AS home_captain  \n'
        '    ON home_cgs.char_id = home_captain.char_id \n'
        f"{where_statement} \n"
        'ORDER BY game_history.date_created DESC \n'
        'LIMIT 50'
    )

    results = db.session.execute(text(query)).all()

    games = []
    for game in results:
        games.append(dict(game._mapping))
    return {'games': games}
    