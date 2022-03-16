from flask import request, jsonify, abort
from flask import current_app as app
from ..models import db, User, Character, Game, CharacterGameSummary, PitchSummary, ContactSummary, FieldingSummary, ChemistryTable, Tag, GameTag
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

    # Boolean to check if a game has a superstar player
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
    )

    db.session.add(game)
    db.session.commit()

    return 'completed...'