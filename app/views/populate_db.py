from flask import request, abort
from flask import current_app as app
from ..models import *
from ..consts import *
from ..glicko2 import Player
from random import random

@app.route('/populate_db/', methods=['POST'])
def populate_db2():
    # Ignore game if it's a CPU game
    if request.json['Home Player'] == "CPU" or request.json['Away Player'] == "CPU":
        return abort(400, 'Database does not accept CPU games')

    # Check if rio_keys exist in the db and get associated players
    home_player = RioUser.query.filter_by(rio_key=request.json['Home Player']).first()
    away_player = RioUser.query.filter_by(rio_key=request.json['Away Player']).first()

    if home_player is None or away_player is None:
        return abort(400, 'Invalid Rio User')
    if home_player.verified is False or away_player.verified is False:
        return abort(400, "Both users must be verified to submit games.")
    if innings_played < innings_selected and score_difference < 10:
        return abort(400, "Invalid Game: Innings Played < Innings Selected & Score Difference < 10")
    
    # Verify Tags exist
    tag_ids = list()
    json_tags = request.json['Tags']
    tag_set_tag = None
    for id in json_tags:
        tag = Tag.query.filter_by(id=id).first()
        if tag is None:
            abort(400, "Invalid Tag submitted.")
        if tag.tag_type == "Competition":
            tag_set_tag = tag
        tag_ids.append(tag.id)
    
    if not tag_set_tag:
        abort(400, "TagSet Tag not provided.")

    # Get TagSet Id
    tag_set_id = db.session.execute((
        "SELECT \n"
        "tagset_id \n"
        "FROM tag_set_tag \n"
        f"WHERE tag_set_tag.tag_id = {tag_set_tag.id}"
    )).first()

    # Get all Tags for TagSet
    tags_by_tag_set_id = db.session.execute((
        "SELECT \n"
        "tag_id \n"
        "FROM tag_set_tag \n"
        f"WHERE tag_set_tag.tagset_id = {tag_set_id}"
    )).all()

    # Verify all TagSet Tags are present in passed tags
    for tag in tags_by_tag_set_id:
        if tag.id not in tag_ids:
            abort(400, "Missing Tag from TagSet tag.")

    # Detect invalid games
    innings_selected = request.json['Innings Selected']
    innings_played = request.json['Innings Played']
    score_difference = abs(request.json['Home Score'] - request.json['Away Score'])
    is_valid = False if innings_played < innings_selected and score_difference < 10 else True

    #Reroll game id until unique one is found
    unique_id = False
    game_id = int(request.json['GameID'].replace(',', ''), 16)
    while not unique_id:
        game = Game.query.filter_by(game_id=game_id).first()
        if game == None:
            unique_id = True
        else:
            game_id = random.getrandbits(32)

    game = Game(
        game_id = game_id,
        away_player_id = away_player.id,
        home_player_id = home_player.id,
        date_time_start = int(request.json['Date - Start']),
        date_time_end = int(request.json['Date - End']),
        ranked = request.json['Ranked'],
        netplay = request.json['Netplay'],
        stadium_id = request.json['StadiumID'],
        away_score = request.json['Away Score'],
        home_score = request.json['Home Score'],
        innings_selected = request.json['Innings Selected'],
        innings_played = request.json['Innings Played'],
        quitter = 0 if request.json['Quitter Team'] == "" else request.json['Quitter Team'], #STRING OR INT
        valid = is_valid,
        average_ping = request.json['Average Ping'],
        lag_spikes = request.json['Lag Spikes'],
        version = request.json['Version'],
    )

    # Get winner and loser rio_user
    if (game.home_score > game.away_score):
        winner_player = home_player
        loser_player = away_player
        winner_score = game.home_score
        loser_score = game.away_score
    else:
        winner_player = away_player
        loser_player = home_player
        winner_score = game.away_score
        loser_score = game.home_score

    # Add game row to database
    db.session.add(game)
    db.session.commit()

    # Create GameHistory row
    game_id = submit_game_history(game.game_id, tag_set_id, winner_player.name, winner_score, loser_player.name, loser_score)['GameID']

    # Calc player elo
    calc_elo(tag_set_id, winner_player.id, loser_player.id)

    # ======= Character Game Summary =======
    teams = {
        'Home': [None] * 9,
        'Away': [None] * 9,
    }
    character_game_stats = request.json['Character Game Stats']
    characters = [character_game_stats['Team 0 Roster 0'], character_game_stats['Team 0 Roster 1'], character_game_stats['Team 0 Roster 2'], character_game_stats['Team 0 Roster 3'], character_game_stats['Team 0 Roster 4'], character_game_stats['Team 0 Roster 5'], character_game_stats['Team 0 Roster 6'], character_game_stats['Team 0 Roster 7'], character_game_stats['Team 0 Roster 8'], character_game_stats['Team 1 Roster 0'], character_game_stats['Team 1 Roster 1'], character_game_stats['Team 1 Roster 2'], character_game_stats['Team 1 Roster 3'], character_game_stats['Team 1 Roster 4'], character_game_stats['Team 1 Roster 5'], character_game_stats['Team 1 Roster 6'], character_game_stats['Team 1 Roster 7'], character_game_stats['Team 1 Roster 8']]    
    for character in characters:
        pitches_per_position = character['Defensive Stats']['Pitches Per Position'] if len(character['Defensive Stats']['Pitches Per Position']) == 1 else [{}]
        batter_outs_per_position = character['Defensive Stats']['Batter Outs Per Position'] if len(character['Defensive Stats']['Batter Outs Per Position']) == 1 else [{}]
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
            batter_outs_at_p = 0 if 'P' not in batter_outs_per_position[0] else batter_outs_per_position[0]['P'],
            batter_outs_at_c = 0 if 'C' not in batter_outs_per_position[0] else batter_outs_per_position[0]['C'],
            batter_outs_at_1b = 0 if '1B' not in batter_outs_per_position[0] else batter_outs_per_position[0]['1B'],
            batter_outs_at_2b = 0 if '2B' not in batter_outs_per_position[0] else batter_outs_per_position[0]['2B'],
            batter_outs_at_3b = 0 if '3B' not in batter_outs_per_position[0] else batter_outs_per_position[0]['3B'],
            batter_outs_at_ss = 0 if 'SS' not in batter_outs_per_position[0] else batter_outs_per_position[0]['SS'],
            batter_outs_at_lf = 0 if 'LF' not in batter_outs_per_position[0] else batter_outs_per_position[0]['LF'],
            batter_outs_at_cf = 0 if 'CF' not in batter_outs_per_position[0] else batter_outs_per_position[0]['CF'],
            batter_outs_at_rf = 0 if 'RF' not in batter_outs_per_position[0] else batter_outs_per_position[0]['RF'],
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
            earned_runs = defensive_stats['Earned Runs'],
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
            plate_appearances = 0,
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

    rio_client_version_tag = Tag.query.filter_by(name=f'client_{game.version}').first()
    if rio_client_version_tag is None:
        new_rio_client_version_tag = Tag(
            in_tag_name = f'client_{game.version}',
            in_desc = "Rio Client Version Tag",
            in_tag_type = "Global",
            in_comm_id = None
        )
        db.session.add(new_rio_client_version_tag)
        db.session.commit()
    tag_ids.append(new_rio_client_version_tag.id)

    # add rio web version tag, create tag if it doesn't exist
    rio_web_version_tag = Tag.query.filter_by(name=f'web_{cRIO_WEB_VERSION}').first()
    if rio_web_version_tag is None:
        new_rio_web_version_tag = Tag(
            in_tag_name = f'web_{cRIO_WEB_VERSION}',
            in_desc = "Rio Web Version Tag",
            in_tag_type = "Global",
            in_comm_id = None
        )
        db.session.add(new_rio_web_version_tag)
        db.session.commit()
    tag_ids.append(new_rio_web_version_tag.id)

    for id in tag_ids:
        tag = Tag.query.filter_by(id=id).first()
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
            result_num_of_outs = event_data['Num Outs During Play'],
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
                        # Increment batter plate appearances on new appearance
                        batter_character_game_summary = teams['Away'][event_data[key]['Runner Roster Loc']] if event_data['Half Inning'] == 0 else teams['Home'][event_data[key]['Runner Roster Loc']]
                        batter_character_game_summary.plate_appearances += 1
                    elif key == 'Runner 1B':
                        event.runner_on_1 = runner.id
                    elif key == 'Runner 2B':
                        event.runner_on_2 = runner.id
                    elif key == 'Runner 3B':
                        event.runner_on_3 = runner.id

                    previous_runners[key] = runner
                    previous_runners_json[key] = event_data[key]
            else:
                previous_runners[key] = None
                previous_runners_json[key] = None

            
        # ==== Pitch Summary ====
        if 'Pitch' in event_data:
            pitch_summary = PitchSummary(
                pitch_type = event_data['Pitch']['Pitch Type'],
                charge_pitch_type = event_data['Pitch']['Charge Type'],
                star_pitch = event_data['Pitch']['Star Pitch'],
                pitch_speed = event_data['Pitch']['Pitch Speed'],
                ball_position_strikezone = event_data['Pitch']['Ball Position - Strikezone'],
                bat_x_contact_pos = event_data['Pitch']['Bat Contact Pos - X'],
                bat_z_contact_pos = event_data['Pitch']['Bat Contact Pos - Z'],
                in_strikezone = event_data['Pitch']['In Strikezone'],
                type_of_swing = event_data['Pitch']['Type of Swing'],
                d_ball = event_data['Pitch']['DB'],
            )

            db.session.add(pitch_summary)
            db.session.commit()

            # if the batter made contact with the pitch
            if 'Contact' in event_data['Pitch']:
                #  ==== Contact Summary ====
                contact_summary = ContactSummary(
                    type_of_contact = event_data['Pitch']['Contact']['Type of Contact'],
                    charge_power_up = event_data['Pitch']['Contact']['Charge Power Up'],
                    charge_power_down = event_data['Pitch']['Contact']['Charge Power Down'],
                    star_swing_five_star = event_data['Pitch']['Contact']['Star Swing Five-Star'],
                    input_direction = event_data['Pitch']['Contact']['Input Direction - Push/Pull'],
                    input_direction_stick = event_data['Pitch']['Contact']['Input Direction - Stick'],
                    frame_of_swing_upon_contact = event_data['Pitch']['Contact']['Frame of Swing Upon Contact'],
                    ball_power = int(event_data['Pitch']['Contact']['Ball Power'].replace(',', '')),
                    ball_horiz_angle = int(event_data['Pitch']['Contact']['Vert Angle'].replace(',', '')),
                    ball_vert_angle = int(event_data['Pitch']['Contact']['Horiz Angle'].replace(',', '')),
                    contact_absolute = event_data['Pitch']['Contact']['Contact Absolute'],
                    contact_quality = event_data['Pitch']['Contact']['Contact Quality'],
                    rng1 = event_data['Pitch']['Contact']['RNG1'],
                    rng2 = event_data['Pitch']['Contact']['RNG2'],
                    rng3 = event_data['Pitch']['Contact']['RNG3'],
                    ball_x_velocity = event_data['Pitch']['Contact']['Ball Velocity - X'],
                    ball_y_velocity = event_data['Pitch']['Contact']['Ball Velocity - Y'],
                    ball_z_velocity = event_data['Pitch']['Contact']['Ball Velocity - Z'],
                    ball_x_contact_pos = event_data['Pitch']['Contact']['Ball Contact Pos - X'],
                    ball_z_contact_pos = event_data['Pitch']['Contact']['Ball Contact Pos - Z'],
                    ball_x_landing_pos = event_data['Pitch']['Contact']['Ball Landing Position - X'],
                    ball_y_landing_pos = event_data['Pitch']['Contact']['Ball Landing Position - Y'],
                    ball_z_landing_pos = event_data['Pitch']['Contact']['Ball Landing Position - Z'],
                    ball_max_height = event_data['Pitch']['Contact']['Ball Max Height'],
                    ball_hang_time = int(event_data['Pitch']['Contact']['Ball Hang Time'].replace(',', '')),                    
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
                        jump = fielder_data['Fielder Jump'],
                        bobble = fielder_data['Fielder Bobble'],
                        swap = False if fielder_data['Fielder Swap'] == 0 else True,
                        manual_select = fielder_data['Fielder Manual Selected'],
                        fielder_x_pos = fielder_data['Fielder Position - X'],
                        fielder_y_pos = fielder_data['Fielder Position - Y'],
                        fielder_z_pos = fielder_data['Fielder Position - Z']
                    )

                    db.session.add(fielding_summary)
                    db.session.commit()
                    contact_summary.fielding_summary_id = fielding_summary.id
                    db.session.add(contact_summary)
            
            db.session.add(pitch_summary)
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


@app.route('/submit_game/', methods=['POST'])
def submit_game_history(in_game_id=None, in_tag_set_id=None,
                        in_winner_username=None, in_winner_score=None, 
                        in_loser_username=None, in_loser_score=None):
    game_id = in_game_id
    winner_username = in_winner_username if (in_winner_username != None) else request.json['Winner Username']
    winner_score = in_winner_score if (in_winner_score != None) else request.json['Winner Score']
    loser_username = in_loser_username if (in_loser_username != None) else request.json['Loser Username']
    loser_score = in_loser_score if (in_loser_score != None) else request.json['Loser Score']
    tag_set_id = None
    if in_tag_set_id != None:
        tag_set_id = in_tag_set_id
    else:
        # Lookup tagset id
        tag_set = TagSet.query.filter_by(name_lowercase=request.json['Ladder']).first()
        if tag_set == None:
            return abort(409, description='No TagSet found with provided name')
        tag_set_id = tag_set.id

    #Get users and community users
    winner_user = RioUser.query.filter_by(username_lowercase=winner_username.lower())
    loser_user = RioUser.query.filter_by(username_lowercase=loser_username.lower())

    if winner_user == None or loser_user == None:
        return abort(409, description='No RioUser found for at least one of the provided usernames')

    winner_comm_user = CommunityUser.query.filter_by(user_id=winner_user)
    loser_comm_user = CommunityUser.query.filter_by(user_id=loser_user)


    if winner_comm_user == None or loser_comm_user == None:
        return abort(409, description='No CommunityUser found for at least one of the RioUsers')

    #Get TagSet. If season, update/track ELO. Else just add the GameHistory row
    winner_elo = None
    loser_elo = None
    tag_set = TagSet.query.filter_by(id=tag_set_id).first()
    if (tag_set.type == 'Season'):
        #Get ELOs
        winner_ladder = Ladder.query.filter_by(community_user_id=winner_comm_user.id).first()
        loser_ladder = Ladder.query.filter_by(community_user_id=loser_comm_user.id).first()

        #Create elos for new players
        if winner_ladder == None:
            new_glicko_player = Player()
            winner_ladder = Ladder(tag_set_id, winner_comm_user.id, new_glicko_player.rating , new_glicko_player.rd, new_glicko_player.vol)
            db.session.add(winner_ladder)
            db.session.commit()
        if loser_ladder == None:
            new_glicko_player = Player()
            loser_ladder = Ladder(tag_set_id, loser_comm_user.id, new_glicko_player.rating , new_glicko_player.rd, new_glicko_player.vol)
            db.session.add(loser_ladder)
            db.session.commit()

        winner_elo = winner_ladder.rating
        loser_elo = loser_ladder.rating
    
    #Acceptance
    winner_accept = False
    loser_accept = False
    admin_accept = False

    #Get submitters key, if it matches set accept for them
    if (in_game_id == None):
        submitter_key_provided = request.is_json and 'Submitter Rio Key' in request.json
        if submitter_key_provided:
            submitter_rio_key = request.json['Submitter Rio Key']
            comm_list = CommunityUser.query.join(RioUser, RioUser.rio_key==submitter_rio_key)

            if len(comm_list) == 0:        
                return abort(409, description=f"Submitter not part of provided community")
            submitter = comm_list[0]
            if (submitter.id != winner_comm_user.id and submitter.id != loser_comm_user.id and not submitter.admin):
                return abort(409, description=f"Submitter is not a player or admin")
            winner_accept = submitter.id == winner_comm_user.id
            loser_accept = submitter.id == loser_comm_user.id
            admin_accept = submitter.admin and (not winner_accept and not loser_accept)
    else:
        winner_accept = True
        loser_accept = True

    #Finally ready to write the row
    new_game_history = GameHistory(game_id, tag_set_id, winner_comm_user.id, loser_comm_user.id, 
                                   winner_score, loser_score, 
                                   winner_elo, loser_elo, 
                                   winner_accept, loser_accept, admin_accept)
    db.session.add(new_game_history)
    db.session.commit()

    if (in_game_id == None):
        return {'GameID': new_game_history.id}
    else:
        return {'GameID': new_game_history.game_id}


@app.route('/update_game_status/', methods=['POST'])
def update_game_status():
    game_id = request.json.get('GameID')
    confirmer_rio_key = request.json.get('Rio Key')
    confirmer_accept = request.json.get('Accept') == 1

    game_history = GameHistory.query.filter_by(game_id=game_id).first()

    if game_history == None:
        return abort(409, description="")

    #Get comm users
    winner_comm_user = CommunityUser.query.filter_by(id=game_history.winner_comm_user_id)
    loser_comm_user = CommunityUser.query.filter_by(id=game_history.loser_comm_user_id)

    comm_id = winner_comm_user.community_id

    if (confirmer_rio_key == winner_comm_user.rio_user.rio_key):
        game_history.winner_accept = confirmer_accept
    if (confirmer_rio_key == loser_comm_user.rio_user.rio_key):
        game_history.loser_accept = confirmer_accept

    # Check for admin verification
    admin = db.session.query(
            CommunityUser
        ).join(
            RioUser
        ).filter(
            (RioUser.rio_key == confirmer_rio_key)
            & (Community.id == comm_id)
        ).first()
    
    if admin != None:
        game_history.admin_accept = confirmer_accept

    # Commit changes to GameHistory
    db.session.commit()

    # Update ELO if tag_set is a season
    tag_set = TagSet.query.filter_by(id=game_history.tag_set_id)

    if (tag_set == None):
        return abort(409, description='Somehow tagset is invalid')

    if (tag_set.type == 'Season' and
       ((game_history.winner_accept and game_history.loser_accept) or game_history.admin_accept)):
        calc_elo(game_history.tag_set_id, winner_comm_user.rio_user.id, loser_comm_user.rio_user.id)
    
    return 'Success', 200

def calc_elo(tag_set_id, winner_user_id, loser_user_id):
    winner_ladder = db.session.query(
            Ladder
        ).join(
            CommunityUser
        ).filter(
            (Ladder.tag_set_id == tag_set_id) &
            (CommunityUser.user_id == winner_user_id)
        ).first()
    loser_ladder = db.session.query(
            Ladder
        ).join(
            CommunityUser
        ).filter(
            (Ladder.tag_set_id == tag_set_id) &
            (CommunityUser.user_id == loser_user_id)
        ).first()

    if winner_ladder == None:
        return abort(409, description="No winner ladder entry")
    if loser_ladder == None:
        return abort(409, description="No loser ladder entry")

    winner_player = Player(winner_ladder.rating, winner_ladder.rd, winner_ladder.vol)
    loser_player = Player(loser_ladder.rating, loser_ladder.rd, loser_ladder.vol)

    winner_player.update_player([loser_ladder.rating], [loser_ladder.rd], [1])
    loser_player.update_player([winner_ladder.rating], [winner_ladder.rd], [0])

    #Todo function in Ladder
    winner_ladder.rating = winner_player.rating
    winner_ladder.rd = winner_ladder.rd
    winner_ladder.vol = winner_ladder.vol

    loser_ladder.rating = loser_player.rating
    loser_ladder.rd = loser_player.rd
    loser_ladder.vol = loser_player.vol

    db.session.commit()

    return