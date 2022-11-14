from flask import request, jsonify, abort
from flask import current_app as app
from ..models import db, Game, Event, RioUser, CharacterGameSummary
from .stat_retrieval import endpoint_games, endpoint_event
from ..util import format_tuple_for_SQL, sanatize_ints
import json
import itertools


# == Function to recreate a stat file ==
'''
@Endpoint: Recreate Stat File
@Description: Used to build a close match for a submitted game. Primary uses: debugging
@Params:
    - game_id: the id of the game to be recreated
'''
@app.route("/recreate_stat_file/", methods=["GET"])
def recreate_stat_file():
  if request.args.get("game_id") is not None:
    try:
      game_id = request.args.get("game_id")
      game = Game.query.filter_by(game_id=game_id).first()
      away_player = RioUser.query.filter_by(id=game.away_player_id).first()
      home_player = RioUser.query.filter_by(id=game.home_player_id).first()
    except:
      abort(400, 'Invalid game_id')
  else:
    abort(400, 'Provide a valid game_id')

  character_game_summary_query = (
    "SELECT \n"
    "character_game_summary.team_id, \n"
    "character_game_summary.roster_loc, \n"
    "character_game_summary.char_id, \n"
    "character_game_summary.superstar, \n"
    "character_game_summary.captain, \n"
    "character_game_summary.fielding_hand, \n"
    "character_game_summary.batting_hand, \n"
    "character_game_summary.batters_faced, \n"
    "character_game_summary.runs_allowed, \n"
    "character_game_summary.earned_runs, \n"
    "character_game_summary.batters_walked, \n"
    "character_game_summary.batters_hit, \n"
    "character_game_summary.hits_allowed, \n"
    "character_game_summary.homeruns_allowed, \n"
    "character_game_summary.pitches_thrown, \n"
    "character_game_summary.stamina, \n"
    "character_game_summary.was_pitcher, \n"
    "character_game_summary.strikeouts_pitched, \n"
    "character_game_summary.star_pitches_thrown, \n"
    "character_game_summary.big_plays, \n"
    "character_game_summary.outs_pitched, \n"
    "character_game_summary.at_bats, \n"
    "character_game_summary.plate_appearances, \n"
    "character_game_summary.hits, \n"
    "character_game_summary.singles, \n"
    "character_game_summary.doubles, \n"
    "character_game_summary.triples, \n"
    "character_game_summary.homeruns, \n"
    "character_game_summary.successful_bunts, \n"
    "character_game_summary.sac_flys, \n"
    "character_game_summary.strikeouts, \n"
    "character_game_summary.walks_bb, \n"
    "character_game_summary.walks_hit, \n"
    "character_game_summary.rbi, \n"
    "character_game_summary.bases_stolen, \n"
    "character_game_summary.star_hits, \n"
    "character_position_summary.pitches_at_p, \n"
    "character_position_summary.pitches_at_c, \n"
    "character_position_summary.pitches_at_1b, \n"
    "character_position_summary.pitches_at_2b, \n"
    "character_position_summary.pitches_at_3b, \n"
    "character_position_summary.pitches_at_ss, \n"
    "character_position_summary.pitches_at_lf, \n"
    "character_position_summary.pitches_at_cf, \n"
    "character_position_summary.pitches_at_rf, \n"
    "character_position_summary.batter_outs_at_p, \n"
    "character_position_summary.batter_outs_at_c, \n"
    "character_position_summary.batter_outs_at_1b, \n"
    "character_position_summary.batter_outs_at_2b, \n"
    "character_position_summary.batter_outs_at_3b, \n"
    "character_position_summary.batter_outs_at_ss, \n"
    "character_position_summary.batter_outs_at_lf, \n"
    "character_position_summary.batter_outs_at_cf, \n"
    "character_position_summary.batter_outs_at_rf, \n"
    "character_position_summary.outs_at_p, \n"
    "character_position_summary.outs_at_c, \n"
    "character_position_summary.outs_at_1b, \n"
    "character_position_summary.outs_at_2b, \n"
    "character_position_summary.outs_at_3b, \n"
    "character_position_summary.outs_at_ss, \n"
    "character_position_summary.outs_at_lf, \n"
    "character_position_summary.outs_at_cf, \n"
    "character_position_summary.outs_at_rf \n"
    "FROM character_game_summary "
    "JOIN character_position_summary ON character_game_summary.character_position_summary_id = character_position_summary.id \n"
    f"WHERE character_game_summary.game_id = {game.game_id}"
  )
  character_game_summaries = db.session.execute(character_game_summary_query).all()

  character_game_stats = {}
  for cgs in character_game_summaries:
    pitches_per_position = {}
    if cgs.pitches_at_p: 
      pitches_per_position["P"] = cgs.pitches_at_p
    if cgs.pitches_at_c:
      pitches_per_position["C"] = cgs.pitches_at_c
    if cgs.pitches_at_1b:
      pitches_per_position["1B"] = cgs.pitches_at_1b
    if cgs.pitches_at_2b:
      pitches_per_position["2B"] = cgs.pitches_at_2b
    if cgs.pitches_at_3b:
      pitches_per_position["3B"] = cgs.pitches_at_3b
    if cgs.pitches_at_ss:
      pitches_per_position["SS"] = cgs.pitches_at_ss
    if cgs.pitches_at_lf:
      pitches_per_position["LF"] = cgs.pitches_at_lf
    if cgs.pitches_at_cf:
      pitches_per_position["CF"] = cgs.pitches_at_cf
    if cgs.pitches_at_rf:
      pitches_per_position["RF"] = cgs.pitches_at_rf

    batter_outs_per_position = {}
    if cgs.batter_outs_at_p: 
      batter_outs_per_position["P"] = cgs.batter_outs_at_p
    if cgs.batter_outs_at_c:
      batter_outs_per_position["C"] = cgs.batter_outs_at_c
    if cgs.batter_outs_at_1b:
      batter_outs_per_position["1B"] = cgs.batter_outs_at_1b
    if cgs.batter_outs_at_2b:
      batter_outs_per_position["2B"] = cgs.batter_outs_at_2b
    if cgs.batter_outs_at_3b:
      batter_outs_per_position["3B"] = cgs.batter_outs_at_3b
    if cgs.batter_outs_at_ss:
      batter_outs_per_position["SS"] = cgs.batter_outs_at_ss
    if cgs.batter_outs_at_lf:
      batter_outs_per_position["LF"] = cgs.batter_outs_at_lf
    if cgs.batter_outs_at_cf:
      batter_outs_per_position["CF"] = cgs.batter_outs_at_cf
    if cgs.batter_outs_at_rf:
      batter_outs_per_position["RF"] = cgs.batter_outs_at_rf

    outs_per_position = {}
    if cgs.outs_at_p: 
      outs_per_position["P"] = cgs.outs_at_p
    if cgs.outs_at_c:
      outs_per_position["C"] = cgs.outs_at_c
    if cgs.outs_at_1b:
      outs_per_position["1B"] = cgs.outs_at_1b
    if cgs.outs_at_2b:
      outs_per_position["2B"] = cgs.outs_at_2b
    if cgs.outs_at_3b:
      outs_per_position["3B"] = cgs.outs_at_3b
    if cgs.outs_at_ss:
      outs_per_position["SS"] = cgs.outs_at_ss
    if cgs.outs_at_lf:
      outs_per_position["LF"] = cgs.outs_at_lf
    if cgs.outs_at_cf:
      outs_per_position["CF"] = cgs.outs_at_cf
    if cgs.outs_at_rf:
      outs_per_position["RF"] = cgs.outs_at_rf

    character_game_stats[f"Team {cgs.team_id} Roster {cgs.roster_loc}"] = {
      "Team": cgs.team_id,
      "RosterID": cgs.roster_loc,
      "CharID": cgs.char_id,
      "Superstar": cgs.superstar,
      "Captain": cgs.captain,
      "Fielding Hand": cgs.fielding_hand,
      "Batting Hand": cgs.batting_hand,
      "Defensive Stats": {
        "Batters Faced": cgs.batters_faced,
        "Runs Allowed": cgs.runs_allowed,
        "Earned Runs": cgs.earned_runs,
        "Batters Walked": cgs.batters_walked,
        "Batters Hit": cgs.batters_hit,
        "Hits Allowed": cgs.hits_allowed,
        "HRs Allowed": cgs.homeruns_allowed,
        "Pitches Thrown": cgs.pitches_thrown,
        "Stamina": cgs.stamina,
        "Was Pitcher": cgs.was_pitcher,
        "Strikeouts": cgs.strikeouts_pitched,
        "Star Pitches Thrown": cgs.star_pitches_thrown,
        "Big Plays": cgs.big_plays,
        "Outs Pitched": cgs.outs_pitched,
        "Pitches Per Position": [pitches_per_position],
        "Batter Outs Per Position": [outs_per_position],
        "Outs Per Position": [outs_per_position]
      },
      "Offensive Stats": {
        "At Bats": cgs.at_bats,
        "Hits": cgs.hits,
        "Singles": cgs.singles,
        "Doubles": cgs.doubles,
        "Triples": cgs.triples,
        "Homeruns": cgs.homeruns,
        "Successful Bunts": cgs.successful_bunts,
        "Sac Flys": cgs.sac_flys,
        "Strikeouts": cgs.strikeouts,
        "Walks (4 Balls)": cgs.walks_bb,
        "Walks (Hit)": cgs.walks_hit,
        "RBI": cgs.rbi,
        "Bases Stolen": cgs.bases_stolen,
        "Star Hits": cgs.star_hits
      }
    }

  event_query = build_events_query(True, game.game_id)
  events = db.session.execute(event_query).all()
  event_list = list()
  for event in events:
    event_data = event_data = parse_event_data(event)
    event_list.append(event_data)

  json_stat_file = {
    "GameId": game.game_id,
    "Date - Start": game.date_time_start,
    "Date - End": game.date_time_end,
    "Ranked": game.ranked,
    "Netplay": game.netplay,
    "StadiumID": game.stadium_id,
    "Away Player": away_player.username,
    "Home Player": home_player.username,
    "Away Score": game.away_score,
    "Home Score": game.home_score,
    "Innings Selected": game.innings_selected,
    "Innings Played": game.innings_played,
    "Quitter Team": game.quitter,
    "Average Ping": game.average_ping,
    "Lag Spikes": game.lag_spikes,
    "Version": game.version,
    "Character Game Stats": character_game_stats,
    "Events": event_list
  }

  return json_stat_file



'''
@Endpoint: Recreate Events
@Description: Used to recreate events from submitted stat files. Primary usage: debugging
@Params:
    - event_ids: event ids to recreate
'''
@app.route("/recreate_events/", methods=["GET"])
def recreate_events():
  if request.args.get("event_ids") is not None:
    try:
      event_ids = sanatize_ints(request.args.get("event_ids"))
      list_of_event_id_tuples = db.session.query(Event.id).filter(Event.id.in_(event_ids)).all()
      list_of_event_ids = list(itertools.chain(*list_of_event_id_tuples))
      tuple_event_ids = tuple(list_of_event_ids)
      SQL_formatted_event_ids, tuple_is_empty = format_tuple_for_SQL(tuple_event_ids)
    except:
      abort(400, 'Invalid event id')
  else:
    abort(400, 'Provide at least one event id')

  event_query = build_events_query(False, SQL_formatted_event_ids)
  events = db.session.execute(event_query).all()
  event_dict = {}
  for event in events:
    event_data = parse_event_data(event)
    if event.game_id in event_dict:
      event_dict[event.game_id][event.event_num] = event_data
    else:
      event_dict[event.game_id] = {
        event.event_num: event_data
      }
  return event_dict


def build_events_query(filter_by_game_id, where_statement_in_values):
  where_statement = str()
  limit_statement = str()
  if filter_by_game_id:
    where_statement = f"WHERE event.game_id = {where_statement_in_values} "
  else:
    where_statement = f"WHERE event.id IN {where_statement_in_values} "
    limit_statement = "LIMIT 1000"

  event_query = (
    "SELECT "
    "event.game_id, \n"
    "event.id, \n"
    "event.event_num, \n"
    "event.inning, \n"
    "event.half_inning, \n"
    "event.away_score, \n"
    "event.home_score, \n"
    "event.balls, \n"
    "event.strikes, \n"
    "event.outs, \n"
    "event.star_chance, \n"
    "event.away_stars, \n"
    "event.home_stars, \n"
    "event.pitcher_stamina, \n"
    "event.chem_links_ob, \n"
    "event.result_rbi, \n"
    "event.result_of_ab, \n"
    "pitcher.char_id AS pitcher, \n"
    "pitcher.id AS pitcher_cgs_id, \n"
    "batter.char_id AS batter, \n"
    "batter.id AS batter_cgs_id, \n"
    "catcher.char_id AS catcher, \n"
    "catcher.id AS catcher_cgs_id, \n"
    "runner_cgs.char_id AS runner_char_id, \n"
    "runner_batter.initial_base AS runner_batter_initial_base, \n"
    "runner_batter.result_base AS runner_batter_result_base, \n"
    "runner_batter.out_type AS runner_batter_out_type, \n"
    "runner_batter.out_location AS runner_batter_out_location, \n"
    "runner_batter.steal AS runner_batter_steal, \n"
    "runner_1b.initial_base AS runner_1b_initial_base, \n"
    "runner_1b.result_base AS runner_1b_result_base, \n"
    "runner_1b.out_type AS runner_1b_out_type, \n"
    "runner_1b.out_location AS runner_1b_out_location, \n"
    "runner_1b.steal AS runner_1b_steal, \n"
    "runner_1b.runner_character_game_summary_id AS runner_1b_cgs_id, \n"
    "b1_cgs.char_id AS runner_1b_char_id, \n"
    "runner_2b.initial_base AS runner_2b_initial_base, \n"
    "runner_2b.result_base AS runner_2b_result_base, \n"
    "runner_2b.out_type AS runner_2b_out_type, \n"
    "runner_2b.out_location AS runner_2b_out_location, \n"
    "runner_2b.steal AS runner_2b_steal, \n"
    "runner_2b.runner_character_game_summary_id AS runner_2b_cgs_id, \n"
    "b2_cgs.char_id AS runner_2b_char_id, \n"
    "runner_3b.initial_base AS runner_3b_initial_base, \n"
    "runner_3b.result_base AS runner_3b_result_base, \n"
    "runner_3b.out_type AS runner_3b_out_type, \n"
    "runner_3b.out_location AS runner_3b_out_location, \n"
    "runner_3b.steal AS runner_3b_steal, \n"
    "runner_3b.runner_character_game_summary_id AS runner_3b_cgs_id, \n"
    "b3_cgs.char_id AS runner_3b_char_id, \n"
    "pitch_summary.pitch_type, \n"
    "pitch_summary.charge_pitch_type, \n"
    "pitch_summary.star_pitch, \n"
    "pitch_summary.pitch_speed, \n"
    "pitch_summary.pitch_ball_x_pos, \n"
    "pitch_summary.pitch_ball_z_pos, \n"
    "pitch_summary.pitch_batter_x_pos, \n"
    "pitch_summary.pitch_batter_z_pos, \n"
    "pitch_summary.pitch_result, \n"
    "pitch_summary.type_of_swing, \n"
    "contact_summary.type_of_contact, \n"
    "contact_summary.charge_power_up, \n"
    "contact_summary.charge_power_down, \n"
    "contact_summary.star_swing_five_star, \n"
    "contact_summary.input_direction, \n"
    "contact_summary.input_direction_stick, \n"
    "contact_summary.frame_of_swing_upon_contact, \n"
    "contact_summary.ball_angle, \n"
    "contact_summary.ball_horiz_power, \n"
    "contact_summary.ball_vert_power, \n"
    "contact_summary.ball_x_velocity, \n"
    "contact_summary.ball_y_velocity, \n"
    "contact_summary.ball_z_velocity, \n"
    "contact_summary.ball_x_pos, \n"
    "contact_summary.ball_y_pos, \n"
    "contact_summary.ball_z_pos, \n"
    "contact_summary.ball_max_height, \n"
    "contact_summary.multi_out, \n"
    "contact_summary.primary_result, \n"
    "contact_summary.secondary_result, \n"
    "fielder_cgs.char_id AS fielder, \n"
    "fielding_summary.position, \n"
    "fielding_summary.action, \n"
    "fielding_summary.jump, \n"
    "fielding_summary.bobble, \n"
    "fielding_summary.swap, \n"
    "fielding_summary.manual_select, \n"
    "fielding_summary.fielder_x_pos, \n"
    "fielding_summary.fielder_y_pos, \n"
    "fielding_summary.fielder_z_pos \n"
    "FROM event \n"
    "LEFT JOIN character_game_summary AS pitcher ON event.pitcher_id = pitcher.id \n"
    "LEFT JOIN character_game_summary AS catcher ON event.catcher_id = catcher.id \n"
    "LEFT JOIN character_game_summary AS batter ON event.batter_id = batter.id \n"
    "LEFT JOIN runner AS runner_batter ON event.runner_on_0 = runner_batter.id \n"
    "LEFT JOIN character_game_summary AS runner_cgs ON runner_batter.runner_character_game_summary_id = runner_cgs.id \n"
    "LEFT JOIN runner AS runner_1b ON event.runner_on_1 = runner_1b.id \n"
    "LEFT JOIN character_game_summary AS b1_cgs ON runner_1b.runner_character_game_summary_id = b1_cgs.id \n"
    "LEFT JOIN runner AS runner_2b ON event.runner_on_2 = runner_2b.id \n"
    "LEFT JOIN character_game_summary AS b2_cgs ON runner_2b.runner_character_game_summary_id = b2_cgs.id \n"
    "LEFT JOIN runner AS runner_3b ON event.runner_on_3 = runner_3b.id \n"
    "LEFT JOIN character_game_summary AS b3_cgs ON runner_3b.runner_character_game_summary_id = b3_cgs.id \n"
    "LEFT JOIN pitch_summary ON event.pitch_summary_id = pitch_summary.id \n"
    "LEFT JOIN contact_summary ON pitch_summary.contact_summary_id = contact_summary.id \n"
    "LEFT JOIN fielding_summary ON contact_summary.fielding_summary_id = fielding_summary.id \n"
    "LEFT JOIN character_game_summary AS fielder_cgs ON fielding_summary.fielder_character_game_summary_id = fielder_cgs.id \n"
    f"{where_statement} "
    "ORDER BY event.event_num "
    f"{limit_statement}"
  )

  return event_query


def parse_event_data(event):
  event_data = {
    "Event Num": event.event_num,
    "Event ID": event.id,
    "Inning": event.inning,
    "Half Inning": event.half_inning,
    "Away Score": event.away_score,
    "Home Score": event.home_score,
    "Balls": event.balls,
    "Strikes": event.strikes,
    "Outs": event.outs,
    "Star Chance": event.star_chance,
    "Away Stars": event.away_stars,
    "Home Stars": event.home_stars,
    "Pitcher Stamina": event.pitcher_stamina,
    "Chemistry Links on Base": event.chem_links_ob,
    "Pitcher CGS Id": event.pitcher_cgs_id,
    "Batter CGS Id": event.batter_cgs_id,
    "Catcher CGS Id": event.catcher_cgs_id,
    "Pitcher": event.pitcher,
    "Batter": event.batter,
    "Catcher": event.catcher,
    "RBI": event.result_rbi,
    "Result of AB": event.result_of_ab
  }

  # check if event has a batter
  if event.runner_batter_initial_base:
    event_data["Runner Batter"] = {
      "Runner Char Id": event.batter,
      "Runner Initial Base": event.runner_batter_initial_base,
      "Runner Result Base": event.runner_batter_result_base,
      "Out Type": event.runner_batter_out_type,
      "Out Location": event.runner_batter_out_location,
      "Steal": event.runner_batter_steal
    }
  # check if event has a runner on 1b
  if event.runner_1b_initial_base:
    event_data["Runner 1B"] = {
      "Runner Char Id": event.runner_1b_char_id,
      "Runner Initial Base": event.runner_1b_initial_base,
      "Runner Result Base": event.runner_1b_result_base,
      "Out Type": event.runner_1b_out_type,
      "Out Location": event.runner_1b_out_location,
      "Steal": event.runner_1b_steal
    }
  # check if event has a runner on 2b
  if event.runner_2b_initial_base:
    event_data["Runner 2B"] = {
      "Runner Char Id": event.runner_2b_char_id,
      "Runner Initial Base": event.runner_2b_initial_base,
      "Runner Result Base": event.runner_2b_result_base,
      "Out Type": event.runner_2b_out_type,
      "Out Location": event.runner_2b_out_location,
      "Steal": event.runner_2b_steal
    }
  # check if event has a runner on 3b
  if event.runner_3b_initial_base:
    event_data["Runner 3B"] = {
      "Runner Char Id": event.runner_3b_char_id,
      "Runner Initial Base": event.runner_3b_initial_base,
      "Runner Result Base": event.runner_3b_result_base,
      "Out Type": event.runner_3b_out_type,
      "Out Location": event.runner_3b_out_location,
      "Steal": event.runner_3b_steal
    }
  
  if event.type_of_contact:
    event_data["Pitch"] = {
      "Pitcher Team Id": event.half_inning,
      "Pitcher Char Id": event.pitcher,
      "Pitch Type": event.pitch_type,
      "Charge Type": event.charge_pitch_type,
      "Star Pitch": event.star_pitch,
      "Pitch Speed": event.pitch_speed,
      "Pitch Result": event.pitch_result,
      "Type of Swing": event.type_of_swing,
    }

    if event.type_of_contact:
      event_data["Pitch"]["Contact"] = {
        "Type of Contact": event.type_of_contact,
        "Charge Power Up": event.charge_power_up,
        "Charge Power Down": event.charge_power_down,
        "Star Swing Five-Star": event.star_swing_five_star,
        "Input Direction - Push/Pull": event.input_direction,
        "Input Direction - Stick": event.input_direction_stick,
        "Frame of Swing Upon Contact": event.frame_of_swing_upon_contact,
        "Ball Angle": event.ball_angle,
        "Ball Vertical Power": event.ball_vert_power,
        "Ball Horizontal Power": event.ball_horiz_power,
        "Ball Velocity - X": event.ball_x_velocity,
        "Ball Velocity - Y": event.ball_y_velocity,
        "Ball Velocity - Z": event.ball_z_velocity,
        "Ball Landing Position - X": event.ball_x_pos,
        "Ball Landing Position - Y": event.ball_y_pos,
        "Ball Landing Position - Z": event.ball_z_pos,
        "Ball Max Height": event.ball_max_height,
        "Ball Position - X": event.pitch_ball_x_pos,
        "Ball Position - Z": event.pitch_ball_z_pos,
        "Batter Position Upon Contact - X": event.pitch_batter_x_pos,
        "Batter Position Upon Contact - Z": event.pitch_batter_z_pos,
        "Multi-out": event.multi_out,
        "Contact Result - Primary": event.primary_result,
        "Contact Result - Secondary": event.secondary_result,
      }

      if event.position:
        event_data["Pitch"]["Contact"]["First Fielder"] = {
          "Fielder Position": event.position,
          "Fielder Character": event.fielder,
          "Fielder Action": event.action,
          "Fielder Jump": event.jump,
          "Fielder Swap": event.swap,
          "Fielder Manual Selected": event.manual_select,
          "Fielder Position - X": event.fielder_x_pos,
          "Fielder Position - Y": event.fielder_y_pos,
          "Fielder Position - Z": event.fielder_z_pos,
          "Fielder Bobble": event.bobble
        }

  return event_data
