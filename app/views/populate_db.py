from flask import request, jsonify, abort
from flask import current_app as app
from ..models import db, User, Character, Game, CharacterGameSummary, CharacterPositionSummary, Event, Runner, PitchSummary, ContactSummary, FieldingSummary, ChemistryTable, Tag, GameTag
import json
from ..consts import *

# === Upload Game Data ===
@app.route('/upload_game_data/', methods = ['POST'])
def populate_db():
    # Boolean to check if a game has superstar tag
    is_superstar_game = False
    tags = []

    # Get players from db User table
    home_player = User.query.filter_by(username=request.json['Home Player']).first()
    away_player = User.query.filter_by(username=request.json['Away Player']).first()

    # Check if players exist
    if home_player is None or away_player is None:
        abort(400, 'Invalid Username')

    # Detect invalid games
    innings_selected = request.json['Innings Selected']
    innings_played = request.json['Innings Played']
    score_difference = abs(request.json['Home Score'] - request.json['Away Score'])
    is_valid = False if innings_played < innings_selected and score_difference < 10 else True

    game = Game(
        game_id = int(request.json['GameID'].replace(',', ''), 16),
        away_player_id = away_player.id,
        home_player_id = home_player.id,
        date_time = request.json['Date'],
        ranked = request.json['Ranked'],
        stadium_id = request.json['StadiumID'],
        away_score = request.json['Away Score'],
        home_score = request.json['Home Score'],
        innings_selected = request.json['Innings Selected'],
        innings_played = request.json['Innings Played'],
        quitter = request.json['Quitter Team'],
        valid = is_valid,
    )

    db.session.add(game)
    db.session.commit()

    # === Character Game Summary ===
    player_stats = request.json['Player Stats']
    teams = {
        'Home': [None] * 9,
        'Away': [None] * 9,
    }
    for character in player_stats:
        defensive_stats = character['Defensive Stats']
        offensive_stats = character['Offensive Stats']

        character_game_summary = CharacterGameSummary(
            game_id = game.game_id,
            team_id = 0 if character['Team'] == 'Home' else 1,
            char_id = character["Character"],
            user_id = home_player.id if character['Team'] == 'Home' else away_player.id,
            roster_loc = character['RosterID'],
            captain = character['Captain'],
            superstar = character['Superstar'],
            batters_faced = defensive_stats['Batters Faced'],
            runs_allowed = defensive_stats['Runs Allowed'],
            batters_walked = defensive_stats['Batters Walked'],
            batters_hit = defensive_stats['Batters Hit'],
            hits_allowed = defensive_stats['Hits Allowed'],
            homeruns_allowed = defensive_stats['HRs Allowed'],
            pitches_thrown = defensive_stats['Pitches Thrown'],
            stamina = defensive_stats['Stamina'],
            was_pitcher = defensive_stats['Was Pitcher'],
            strikeouts_pitched = defensive_stats['Strikeouts'],
            star_pitches_thrown = defensive_stats['Star Pitches Thrown'],
            big_plays = defensive_stats['Big Plays'],
            inning_appearances = defensive_stats['Inning Appearances'],
            outs_pitched = defensive_stats['Outs Pitched'],
            at_bats = offensive_stats['At Bats'],
            hits = offensive_stats['Hits'],
            singles = offensive_stats['Singles'],
            doubles = offensive_stats['Doubles'],
            triples = offensive_stats['Triples'],
            homeruns = offensive_stats['Homeruns'],
            strikeouts = offensive_stats['Strikeouts'],
            walks_bb = offensive_stats['Walks (4 Balls)'],
            walks_hit = offensive_stats['Walks (Hit)'],
            rbi = offensive_stats['RBI'],
            bases_stolen = offensive_stats['Bases Stolen'],
            star_hits = offensive_stats['Star Hits'],
            offensive_star_swings = 0,
            offensive_stars_used = 0,
            offensive_stars_put_in_play = 0,
            offensive_star_successes = 0,
            offensive_star_chances = 0,
            offensive_star_chances_won = 0,
            defensive_star_pitches = 0,
            defensive_stars_used = 0,
            defensive_star_successes = 0,
            defensive_star_chances = 0,
            defensive_star_chances_won = 0
        )

        db.session.add(character_game_summary)
        db.session.commit()

        teams[character['Team']][character['RosterID']] = character_game_summary
        
    for character in player_stats:

        # Update CharacterUserStats
        if character['Team'] == 'Home':
            batting_character_game_summary = teams['Home'][character['RosterID']]
        else: 
            batting_character_game_summary = teams['Away'][character['RosterID']]
         
        for pitch in character['Pitch Summary']:
            pitch_summary = PitchSummary(
                batter_id = teams[character['Team']][character['RosterID']].id,
                pitcher_id = teams['Home' if character['Team'] == 'Away' else 'Away'][pitch["Pitcher Roster Location"]].id,
                inning = pitch['Inning'],
                half_inning = pitch['Half Inning'],
                batter_score = pitch['Batter Score'],
                pitcher_score = pitch['Fielder Score'],
                balls = pitch['Balls'],
                strikes = pitch['Strikes'],
                outs = pitch['Outs'],
                runner_on_1 = pitch['Runners on Base'][2],
                runner_on_2 = pitch['Runners on Base'][1],
                runner_on_3 = pitch['Runners on Base'][0],
                chem_links_ob = pitch['Chemistry Links on Base'],
                star_chance = pitch['Star Chance'],
                batter_stars = pitch['Batter Stars'],
                pitcher_stars = pitch['Pitcher Stars'],
                pitcher_handedness = pitch['Pitcher Handedness'],
                pitch_type = pitch['Pitch Type'],
                charge_pitch_type = pitch['Charge Pitch Type'],
                star_pitch = pitch['Star Pitch'],
                pitch_speed = pitch['Pitch Speed'],
                type_of_swing = pitch['Type of Swing'],
                rbi = pitch['RBI'],
                num_outs = pitch['Number Outs During Play'],
                result_inferred = pitch['Final Result - Inferred'],
                result_game = pitch['Final Result - Game'],
            )


            strike_or_strikeout_or_foul = ((pitch['Final Result - Inferred'] == "Strike-looking")
                                        or (pitch['Final Result - Inferred'] == "Strike-swing")
                                        or (pitch['Final Result - Inferred'] == "Strike-bunting")
                                        or (pitch['Final Result - Inferred'] == "Foul")
                                        or (pitch['Final Result - Game'] == "1"))
            
            # Get pitchers user_char_stats
            if character['Team'] == 'Home':
                pitcher_character_game_summary = teams['Away'][pitch['Pitcher Roster Location']]
            else: 
                pitcher_character_game_summary = teams['Home'][pitch['Pitcher Roster Location']]
            
            # == Offensive Star Use ==
            star_swing = pitch['Type of Swing'] == 'Star'
            star_cost = 1
            is_captainable_char = Character.query.filter_by(char_id = batting_character_game_summary.char_id, captain=1).first()
            #Star hits/pitches cost two star for captain eligible characters that are not captains when contact is made
            if ((is_captainable_char is not None) and not batting_character_game_summary.captain and pitch['Contact Summary']):
                star_cost = 2
            batting_character_game_summary.offensive_star_swings += star_swing
            batting_character_game_summary.offensive_stars_used += star_swing * star_cost
            #Star landed and batter got on base
            if ((int(pitch['Final Result - Game']) in cPLAY_RESULT_SAFE.keys()) 
             or (int(pitch['Final Result - Game']) in cPLAY_RESULT_BUNT.keys() and pitch['Number Outs During Play'] == 0)):
                batting_character_game_summary.offensive_star_successes += star_swing
                batting_character_game_summary.offensive_star_chances_won += pitch['Star Chance']

            if (int(pitch['Final Result - Game']) in cPLAY_RESULT_OUT.keys()):
                pitcher_character_game_summary.defensive_star_chances_won += pitch['Star Chance']
                        
            batting_character_game_summary.offensive_stars_put_in_play += star_swing and not strike_or_strikeout_or_foul

            # == Defensive Star Use ==
            star_pitch = pitch['Star Pitch']
            star_cost = 1
            is_captainable_char = Character.query.filter_by(char_id = pitcher_character_game_summary.char_id, captain=1).first()
            #Star hits/pitches cost two star for captain eligible characters that are not captains
            if (is_captainable_char and not pitcher_character_game_summary.captain):
                star_cost = 2
            pitcher_character_game_summary.defensive_star_pitches += star_pitch
            pitcher_character_game_summary.defensive_stars_used += star_pitch * star_cost
            pitcher_character_game_summary.defensive_star_successes += int(star_pitch and strike_or_strikeout_or_foul)

            #Play is over, see if AB was a star chance
            if int(pitch['Final Result - Game']) not in cPLAY_RESULT_INVLD:
                batting_character_game_summary.offensive_star_chances += pitch['Star Chance']
                pitcher_character_game_summary.defensive_star_chances += pitch['Star Chance']

            db.session.add(pitch_summary)
            db.session.commit()

            # === Contact Summary === 
            if pitch['Contact Summary']:
                contact_summary = ContactSummary(
                    pitchsummary_id = pitch_summary.id,
                    type_of_contact = pitch['Contact Summary'][0]['Type of Contact'],
                    charge_power_up = pitch['Contact Summary'][0]['Charge Power Up'],
                    charge_power_down = pitch['Contact Summary'][0]['Charge Power Down'],
                    star_swing_five_star = pitch['Contact Summary'][0]['Star Swing Five-Star'],
                    input_direction = pitch['Contact Summary'][0]['Input Direction'],
                    batter_handedness = pitch['Batter Handedness'],
                    ball_angle = pitch['Contact Summary'][0]['Ball Angle'],
                    ball_horiz_power = pitch['Contact Summary'][0]['Ball Horizontal Power'],
                    ball_vert_power = pitch['Contact Summary'][0]['Ball Vertical Power'],
                    ball_x_velocity = pitch['Contact Summary'][0]['Ball Velocity - X'],
                    ball_y_velocity = pitch['Contact Summary'][0]['Ball Velocity - Y'],
                    ball_z_velocity = pitch['Contact Summary'][0]['Ball Velocity - Z'],
                    ball_x_pos = pitch['Contact Summary'][0]['Ball Acceleration - X'],
                    ball_y_pos = pitch['Contact Summary'][0]['Ball Acceleration - Y'],
                    ball_z_pos = pitch['Contact Summary'][0]['Ball Acceleration - Z'],
                    ball_x_pos_upon_hit = pitch['Contact Summary'][0]['Ball Position Upon Contact - X'],
                    ball_y_pos_upon_hit = pitch['Contact Summary'][0]['Ball Position Upon Contact - Y'],
                )

                db.session.add(contact_summary)
                db.session.commit()

                # === Fielding Summary ===
                if pitch['Contact Summary'][0]['Fielding Summary']:
                    fielder_roster_location = pitch['Contact Summary'][0]['Fielding Summary'][0]['Fielder Roster Location']
                    fielder_team = 'Home' if character['Team'] == 'Away' else 'Away'

                    fielding_summary = FieldingSummary(
                        contact_summary_id = contact_summary.id,
                        fielder_character_game_summary_id = teams[fielder_team][fielder_roster_location].id,
                        position = pitch['Contact Summary'][0]['Fielding Summary'][0]['Fielder Position'],
                    )
                    db.session.add(fielding_summary)
                    
                db.session.commit()

        # Check if its a superstar game or not
        if character['Superstar'] == True:
            is_superstar_game == True 

    if game.ranked == True:
        tags.append('Ranked')
    else:
        tags.append('Unranked')

    if is_superstar_game == True:
        tags.append('Superstar')
    else:
        tags.append('Normal')
    
    for name in tags:
        tag = Tag.query.filter_by(name=name).first()
        if tag:
            game_tag = GameTag(
                game_id = game.game_id,
                tag_id = tag.id
            )
            db.session.add(game_tag)

    db.session.commit()
    return 'Successfully added...\n'


@app.route('/populate_db/', methods=['POST'])
def populate_db2():
    tags = []

    # Boolean used to assign a GameTag after creating CharacterGameSummary rows
    is_superstar_game = False
    
    # Get players from db User table
    home_player = User.query.filter_by(username=request.json['Home Player']).first()
    away_player = User.query.filter_by(username=request.json['Away Player']).first()

    # Check if players exist
    if home_player is None or away_player is None:
        abort(400, 'Invalid Username')

    # Detect invalid games
    innings_selected = request.json['Innings Selected']
    innings_played = request.json['Innings Played']
    score_difference = abs(request.json['Home Score'] - request.json['Away Score'])
    is_valid = False if innings_played < innings_selected and score_difference < 10 else True

    game = Game(
        game_id = int(request.json['GameID'].replace(',', ''), 16),
        away_player_id = away_player.id,
        home_player_id = home_player.id,
        date_time = request.json['Date'],
        ranked = request.json['Ranked'],
        stadium_id = request.json['StadiumID'],
        away_score = request.json['Away Score'],
        home_score = request.json['Home Score'],
        innings_selected = request.json['Innings Selected'],
        innings_played = request.json['Innings Played'],
        quitter = request.json['Quitter Team'],
        valid = is_valid,
        average_ping = request.json['Average Ping'],
        lag_spikes = request.json['Lag Spikes'],
    )

    db.session.add(game)
    db.session.commit()


    # ======= Character Game Summary =======
    teams = {
        'Home': [None] * 9,
        'Away': [None] * 9,
    }
    character_game_stats = request.json['Character Game Stats']
    characters = [character_game_stats['Team 0 Roster 0'], character_game_stats['Team 0 Roster 1'], character_game_stats['Team 0 Roster 2'], character_game_stats['Team 0 Roster 3'], character_game_stats['Team 0 Roster 4'], character_game_stats['Team 0 Roster 5'], character_game_stats['Team 0 Roster 6'], character_game_stats['Team 0 Roster 7'], character_game_stats['Team 0 Roster 8'], character_game_stats['Team 1 Roster 0'], character_game_stats['Team 1 Roster 1'], character_game_stats['Team 1 Roster 2'], character_game_stats['Team 1 Roster 3'], character_game_stats['Team 1 Roster 4'], character_game_stats['Team 1 Roster 5'], character_game_stats['Team 1 Roster 6'], character_game_stats['Team 1 Roster 7'], character_game_stats['Team 1 Roster 8']]    
    for character in characters:
        pitches_per_position = character['Defensive Stats']['Pitches Per Position'] if len(character['Defensive Stats']['Pitches Per Position']) == 1 else [{}]
        outs_per_position = character['Defensive Stats']['Outs Per Position'] if len(character['Defensive Stats']['Outs Per Position']) == 1 else [{}]

        character_position_summary = CharacterPositionSummary(
            pitches_at_p = 0 if 'P' not in pitches_per_position[0] else pitches_per_position[0]['P'],
            pitches_at_c = 0 if 'C' not in pitches_per_position[0] else pitches_per_position[0]['C'],
            pitches_at_1b = 0 if '1B' not in pitches_per_position[0] else pitches_per_position[0]['1B'],
            pitches_at_2b = 0 if '2B' not in pitches_per_position[0] else pitches_per_position[0]['2B'],
            pitches_at_3b = 0 if '3B' not in pitches_per_position[0] else pitches_per_position[0]['3B'],
            pitches_at_ss = 0 if 'SS' not in pitches_per_position[0] else pitches_per_position[0]['SS'],
            pitches_at_lf = 0 if 'LF' not in pitches_per_position[0] else pitches_per_position[0]['LF'],
            pitches_at_cf = 0 if 'CF' not in pitches_per_position[0] else pitches_per_position[0]['CF'],
            pitches_at_rf = 0 if 'RF' not in pitches_per_position[0] else pitches_per_position[0]['RF'],
            outs_at_p = 0 if 'P' not in outs_per_position[0] else outs_per_position[0]['P'],
            outs_at_c = 0 if 'C' not in outs_per_position[0] else outs_per_position[0]['C'],
            outs_at_1b = 0 if '1B' not in outs_per_position[0] else outs_per_position[0]['1B'],
            outs_at_2b = 0 if '2B' not in outs_per_position[0] else outs_per_position[0]['2B'],
            outs_at_3b = 0 if '3B' not in outs_per_position[0] else outs_per_position[0]['3B'],
            outs_at_ss = 0 if 'SS' not in outs_per_position[0] else outs_per_position[0]['SS'],
            outs_at_lf = 0 if 'LF' not in outs_per_position[0] else outs_per_position[0]['LF'],
            outs_at_cf = 0 if 'CF' not in outs_per_position[0] else outs_per_position[0]['CF'],
            outs_at_rf = 0 if 'RF' not in outs_per_position[0] else outs_per_position[0]['RF'],
        )

        db.session.add(character_position_summary)
        db.session.commit()

        defensive_stats = character['Defensive Stats']
        offensive_stats = character['Offensive Stats']

        character_game_summary = CharacterGameSummary(
            game_id = game.game_id,
            team_id = int(character['Team']),
            char_id = character['CharID'],
            user_id = home_player.id if character['Team'] == '0' else away_player.id,
            character_position_summary_id = character_position_summary.id,
            roster_loc = character['RosterID'],
            captain = character['Captain'],
            superstar = character['Superstar'],
            fielding_hand = character['Fielding Hand'],
            batting_hand = character['Batting Hand'],
            # Defensive Stats
            batters_faced = defensive_stats['Batters Faced'],
            runs_allowed = defensive_stats['Runs Allowed'],
            batters_walked = defensive_stats['Batters Walked'],
            batters_hit = defensive_stats['Batters Hit'],
            hits_allowed = defensive_stats['Hits Allowed'],
            homeruns_allowed = defensive_stats['HRs Allowed'],
            pitches_thrown = defensive_stats['Pitches Thrown'],
            stamina = defensive_stats['Stamina'],
            was_pitcher = defensive_stats['Was Pitcher'],
            strikeouts_pitched = defensive_stats['Strikeouts'],
            star_pitches_thrown = defensive_stats['Star Pitches Thrown'],
            big_plays = defensive_stats['Big Plays'],
            outs_pitched = defensive_stats['Outs Pitched'],
            # Offensive Stats
            at_bats = offensive_stats['At Bats'],
            hits = offensive_stats['Hits'],
            singles = offensive_stats['Singles'],
            doubles = offensive_stats['Doubles'],
            triples = offensive_stats['Triples'],
            homeruns = offensive_stats['Homeruns'],
            successful_bunts = offensive_stats['Successful Bunts'],
            sac_flys = offensive_stats['Sac Flys'],
            strikeouts = offensive_stats['Strikeouts'],
            walks_bb = offensive_stats['Walks (4 Balls)'],
            walks_hit = offensive_stats['Walks (Hit)'],
            rbi = offensive_stats['RBI'],
            bases_stolen = offensive_stats['Bases Stolen'],
            star_hits = offensive_stats['Star Hits'],
            #Star tracking (Not in JSON. Calculated in populate_db)
            offensive_star_swings = 0,
            offensive_stars_used = 0,
            offensive_stars_put_in_play = 0,
            offensive_star_successes = 0,
            offensive_star_chances = 0,
            offensive_star_chances_won = 0,
            defensive_star_pitches = 0,
            defensive_stars_used = 0,
            defensive_star_successes = 0,
            defensive_star_chances = 0,
            defensive_star_chances_won = 0
        )

        db.session.add(character_game_summary)
        db.session.commit()

        # index character_game_summarys for later use
        if character['Team'] == '0':
            teams['Home'][character['RosterID']] = character_game_summary
        else:
            teams['Away'][character['RosterID']] = character_game_summary

        # ==== GameTag ====
        if character['Superstar'] == 1:
            is_superstar_game = True 

    if game.ranked == True:
        tags.append('Ranked')
    else:
        tags.append('Unranked')

    if is_superstar_game == True:
        tags.append('Superstar')
    else:
        tags.append('Normal')
    
    for name in tags:
        tag = Tag.query.filter_by(name=name).first()
        if tag:
            game_tag = GameTag(
                game_id = game.game_id,
                tag_id = tag.id
            )
            db.session.add(game_tag)

    # Create Events, Runners, PitchSummaries, ContactSummaries, and FieldingSummaries
    # contains json data for comparing events
    previous_runners_json = {
        'Runner Batter': None,
        'Runner 1B': None,
        'Runner 2B': None,
        'Runner 3B': None
    }
    # contains model instances for use if current event data equal previous event data
    previous_runners = {
        'Runner Batter': None,
        'Runner 1B': None,
        'Runner 2B': None,
        'Runner 3B': None
    }
    events = request.json['Events']
    for index, event_data in enumerate(events):
        # ======= Create Event rows ======
        event = Event(
            game_id = game.game_id,
            pitcher_id = teams['Home'][event_data['Pitcher Roster Loc']].id if event_data['Half Inning'] == 0 else teams['Away'][event_data['Pitcher Roster Loc']].id,
            batter_id = teams['Home'][event_data['Batter Roster Loc']].id if event_data['Half Inning'] == 1 else teams['Away'][event_data['Batter Roster Loc']].id,
            catcher_id = teams['Home'][event_data['Catcher Roster Loc']].id if event_data['Half Inning'] == 0 else teams['Away'][event_data['Catcher Roster Loc']].id,
            event_num = index,
            away_score = event_data['Away Score'],
            home_score = event_data['Home Score'],
            inning = event_data['Inning'],
            half_inning = event_data['Half Inning'],
            chem_links_ob = event_data['Chemistry Links on Base'],
            star_chance = event_data['Star Chance'],
            away_stars = event_data['Away Stars'],
            home_stars = event_data['Home Stars'],
            pitcher_stamina = event_data['Pitcher Stamina'],
            outs = event_data['Outs'],
            balls = event_data['Balls'],
            strikes = event_data['Strikes'],
            result_rbi = event_data['RBI'],
            result_of_ab = event_data['Result of AB'],
        )

        # ======= Create Runner rows for batters ======
        # Loop through the four possible json event runner keys, check if their values are equal to the values from the previous event (this means they are the same character), and then use previous runner row or create a new one accordingly.
        for key in previous_runners:
            if key in event_data:
                if previous_runners_json[key] and previous_runners_json[key] == event_data[key]:
                    if key == 'Runner Batter':
                        event.runner_on_0 = previous_runners[key].id
                    elif key == 'Runner 1B':
                        event.runner_on_1 = previous_runners[key].id
                    elif key == 'Runner 2B':
                        event.runner_on_2 = previous_runners[key].id
                    elif key == 'Runner 3B':
                        event.runner_on_3 = previous_runners[key].id
                else:
                    runner = Runner(
                        runner_character_game_summary_id = teams['Away'][event_data[key]['Runner Roster Loc']].id if event_data['Half Inning'] == 0 else teams['Home'][event_data[key]['Runner Roster Loc']].id,
                        initial_base = event_data[key]['Runner Initial Base'],
                        result_base = event_data[key]['Runner Result Base'],
                        out_type = event_data[key]['Out Type'],
                        out_location = event_data[key]['Out Location'],
                        steal = event_data[key]['Steal'],                   
                    )

                    db.session.add(runner)
                    db.session.commit()

                    if key == 'Runner Batter':
                        event.runner_on_0 = runner.id
                    elif key == 'Runner 1B':
                        event.runner_on_1 = runner.id
                    elif key == 'Runner 2B':
                        event.runner_on_2 = runner.id
                    elif key == 'Runner 3B':
                        event.runner_on_3 = runner.id

                    previous_runners[key] = runner
                    previous_runners_json[key] = event_data[key]
            else:
                previous_runners['Runner Batter'] = None
                previous_runners_json['Runner Batter'] = None

            
        # ==== Pitch Summary ====
        pitch_summary = PitchSummary(
            pitch_type = event_data['Pitch']['Pitch Type'],
            charge_pitch_type = event_data['Pitch']['Charge Type'],
            star_pitch = event_data['Pitch']['Star Pitch'],
            pitch_speed = event_data['Pitch']['Pitch Speed'],
            pitch_result = event_data['Pitch']['Pitch Result'],
            type_of_swing = event_data['Pitch']['Type of Swing']
        )

        # if the batter made contact with the pitch
        if 'Contact' in event_data['Pitch']:
            #  ==== Contact Summary ====
            contact_summary = ContactSummary(
                type_of_contact = event_data['Pitch']['Contact']['Type of Contact'],
                charge_power_up = event_data['Pitch']['Contact']['Charge Power Up'],
                charge_power_down = event_data['Pitch']['Contact']['Charge Power Down'],
                star_swing_five_star = event_data['Pitch']['Contact']['Star Swing Five-Star'],
                input_direction = event_data['Pitch']['Contact']['Input Direction'],
                frame_of_swing_upon_contact = event_data['Pitch']['Contact']['Frame of Swing Upon Contact'],
                ball_angle = event_data['Pitch']['Contact']['Ball Angle'],
                ball_horiz_power = event_data['Pitch']['Contact']['Ball Horizontal Power'],
                ball_vert_power = event_data['Pitch']['Contact']['Ball Vertical Power'],
                ball_x_velocity = event_data['Pitch']['Contact']['Ball Velocity - X'],
                ball_y_velocity = event_data['Pitch']['Contact']['Ball Velocity - Y'],
                ball_z_velocity = event_data['Pitch']['Contact']['Ball Velocity - Z'],
                ball_x_pos = event_data['Pitch']['Contact']['Ball Landing Position - X'],
                ball_y_pos = event_data['Pitch']['Contact']['Ball Landing Position - Y'],
                ball_z_pos = event_data['Pitch']['Contact']['Ball Landing Position - Z'],
                ball_x_pos_upon_hit = event_data['Pitch']['Contact']['Ball Position Upon Contact - X'],
                ball_z_pos_upon_hit = event_data['Pitch']['Contact']['Ball Position Upon Contact - Z'],
                batter_x_pos_upon_hit = event_data['Pitch']['Contact']['Batter Position Upon Contact - X'],
                batter_z_pos_upon_hit = event_data['Pitch']['Contact']['Batter Position Upon Contact - Z'],
                multi_out = event_data['Pitch']['Contact']['Multi-out'],
                primary_result = event_data['Pitch']['Contact']['Contact Result - Primary'],
                secondary_result = event_data['Pitch']['Contact']['Contact Result - Secondary']
            )

            db.session.add(contact_summary)
            db.session.commit()
            pitch_summary.contact_summary_id = contact_summary.id

            # ==== Fielding Summary ====
            if 'First Fielder' in event_data['Pitch']['Contact']:
                fielder_data = event_data['Pitch']['Contact']['First Fielder']

                fielding_summary = FieldingSummary(
                    fielder_character_game_summary_id = teams['Home'][fielder_data['Fielder Roster Location']].id if event_data['Half Inning'] == 0 else teams['Away'][fielder_data['Fielder Roster Location']].id,
                    position = fielder_data['Fielder Position'],
                    action = fielder_data['Fielder Action'],
                    bobble = fielder_data['Fielder Bobble'],
                    swap = False if fielder_data['Fielder Swap'] == 0 else True,
                    fielder_x_pos = fielder_data['Fielder Position - X'],
                    fielder_y_pos = fielder_data['Fielder Position - Y'],
                    fielder_z_pos = fielder_data['Fielder Position - Z']
                )

                db.session.add(fielding_summary)
                db.session.commit()
                contact_summary.fielding_summary_id = fielding_summary.id
                db.session.add(contact_summary)
            
        db.session.add(pitch_summary)
        db.session.commit()
        event.pitch_summary_id = pitch_summary.id
        db.session.add(event)
        db.session.commit()


        # == Star Calcs Offensse ==
        # Batter summary object
        batter_summary = teams['Away'][event_data['Batter Roster Loc']] if event_data['Half Inning'] == 0 else teams['Home'][event_data['Batter Roster Loc']]

        #Bools to make this all more readable
        batter_captainable_char = (Character.query.filter_by(char_id = batter_summary.char_id, captain=1).first() != None)
        star_swing = (pitch_summary.type_of_swing == 3) # ToDo replace with decode const. 3==star swing
        made_contact = (pitch_summary.contact_summary_id != None)

        #Contact was made and was caught or landed
        star_put_in_play = (made_contact and ((pitch_summary.contact_summary.primary_result == 1) or (pitch_summary.contact_summary.primary_result == 2))) # ToDo replace with decode const. 2 == Fair, 1 == out
        star_landed = (made_contact and (pitch_summary.contact_summary.primary_result == 2)) # ToDo replace with decode const. 2 == Fair, 1 == out
        

        #Info to tell if batter won star chance
        batter_safe = event.runner_0.out_type == 0
        outs_during_play = 0
        for runner in [event.runner_0, event.runner_1, event.runner_2, event.runner_3]:
            if runner == None:
                continue
            if runner.out_type > 0:
                outs_during_play += 1
        final_pitch_of_atbat = event.result_of_ab > 0

        if (star_swing):
            batter_summary.offensive_star_swings += 1
            # Misses, non-captain contact, and captain star cost each cost 1 star.
            # Contact with a non-captain character costs 2 stars
            if (made_contact and (batter_captainable_char and batter_summary.captain == False)):
                batter_summary.offensive_stars_used += 2
            else:
                batter_summary.offensive_stars_used += 1

            if (star_put_in_play):
                batter_summary.offensive_stars_put_in_play += 1
        
            if (star_landed):
                batter_summary.offensive_star_successes += 1

        # == Star Calcs Defense ==
        pitcher_summary = teams['Away'][event_data['Pitcher Roster Loc']] if event_data['Half Inning'] == 1 else teams['Home'][event_data['Pitcher Roster Loc']]

        pitcher_captainable_char = (Character.query.filter_by(char_id = pitcher_summary.char_id, captain=1).first() != None)

        if (pitch_summary.star_pitch):
            pitcher_summary.defensive_star_pitches += 1
            if (pitch_summary.pitch_result >= 3 and pitch_summary.pitch_result >= 5):
                pitcher_summary.defensive_star_successes += 1

            if (pitcher_captainable_char and pitcher_summary.captain == False):
                pitcher_summary.defensive_stars_used += 2
            else:
                pitcher_summary.defensive_stars_used += 1
        
        #Only increment star chances when the ab is over
        if (final_pitch_of_atbat):
            if (event.star_chance):
                batter_summary.offensive_star_chances += 1
                pitcher_summary.defensive_star_chances += 1
                #Batter wins star chance if the batter is safe and the inning doesn't end
                if (batter_safe and ((event.outs + outs_during_play) < 3) ):
                    batter_summary.offensive_star_chances_won += 1
                else:
                    pitcher_summary.defensive_star_chances_won += 1

        for idx, team in teams.items():
            for character_summary in team:
                db.session.add(character_summary)
        db.session.commit()

    return 'Completed...'
