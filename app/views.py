from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
import secrets
from . import bc
from flask_mailman import EmailMessage
from .models import db, User, Character, UserCharacterStats, Game, CharacterGameSummary, PitchSummary, ContactSummary, FieldingSummary, ChemistryTable
from .schemas import UserSchema
import json
from datetime import datetime, timedelta, timezone

from .consts import *

# Schemas
user_schema = UserSchema()

# === Initalize Character Tables ===
@app.route('/create_character_tables/', methods = ['POST'])
def create_character_tables():
    f = open('./json/MSB_Stats_dec.json')
    character_list = json.load(f)["Characters"]

    for character in character_list:
        chemistry_table = ChemistryTable(
            mario = character['Mario (0x3b)'],
            luigi = character['Luigi (0x3c)'],
            dk = character['DK (0x3d)'],
            diddy = character['Diddy (0x3e)'],
            peach = character['Peach (0x3f)'],
            daisy = character['Daisy (0x40)'],
            yoshi = character['Yoshi (0x41)'],
            baby_mario = character['Baby Mario (0x42)'],
            baby_luigi = character['Baby Luigi (0x43)'],
            bowser = character['Bowser (0x44)'],
            wario = character['Wario (0x45)'],
            waluigi = character['Waluigi (0x46)'],
            koopa_r = character['Koopa(R) (0x47)'],
            toad_r = character['Toad(R) (0x48)'],
            boo = character['Boo (0x49)'],
            toadette = character['Toadette (0x4a)'],
            shy_guy_r = character['Shy Guy(R) (0x4b)'],
            birdo = character['Birdo (0x4c)'],
            monty = character['Monty (0x4d)'],
            bowser_jr = character['Bowser Jr (0x4e)'],
            paratroopa_r = character['Paratroopa(R) (0x4f)'],
            pianta_b = character['Pianta(B) (0x50)'],
            pianta_r = character['Pianta(R) (0x51)'],
            pianta_y = character['Pianta(Y) (0x52)'],
            noki_b = character['Noki(B) (0x53)'],
            noki_r = character['Noki(R) (0x54)'],
            noki_g = character['Noki(G) (0x55)'],
            bro_h = character['Bro(H) (0x56)'],
            toadsworth = character['Toadsworth (0x57)'],
            toad_b = character['Toad(B) (0x58)'],
            toad_y = character['Toad(Y) (0x59)'],
            toad_g = character['Toad(G) (0x5a)'],
            toad_p = character['Toad(P) (0x5b)'],
            magikoopa_b = character['Magikoopa(B) (0x5c)'],
            magikoopa_r = character['Magikoopa(R) (0x5d)'],
            magikoopa_g = character['Magikoopa(G) (0x5e)'],
            magikoopa_y = character['Magikoopa(Y) (0x5f)'],
            king_boo = character['King Boo (0x60)'],
            petey = character['Petey (0x61)'],
            dixie = character['Dixie (0x62)'],
            goomba = character['Goomba (0x63)'],
            paragoomba = character['Paragoomba (0x64)'],
            koopa_g = character['Koopa(G) (0x65)'],
            paratroopa_g = character['Paratroopa(G) (0x66)'],
            shy_guy_b = character['Shy Guy(B) (0x67)'],
            shy_guy_y = character['Shy Guy(Y) (0x68)'],
            shy_guy_g = character['Shy Guy(G) (0x69)'],
            shy_guy_bk = character['Shy Guy(Bk) (0x6a)'],
            dry_bones_gy = character['Dry Bones(Gy) (0x6b)'],
            dry_bones_g = character['Dry Bones(G) (0x6c)'],
            dry_bones_r = character['Dry Bones(R) (0x6d)'],
            dry_bones_b = character['Dry Bones(B) (0x6e)'],
            bro_f = character['Bro(F) (0x6f)'],
            bro_b = character['Bro(B) (0x70)'],
        )

        db.session.add(chemistry_table)
        db.session.commit()

        character = Character(
            char_id = int(character['Char Id'], 16),
            chemistry_table_id = chemistry_table.id,
            name = character['Char Name'],
            starting_addr = character['Starting Addr'],
            curve_ball_speed = character['Curve Ball Speed (0x0)'],
            fast_ball_speed = character['Fast Ball Speed (0x1)'],
            curve = character['Curve (0x3)'],
            fielding_arm = character['Fielding Arm (righty:0,lefty:1) (0x26)'],
            batting_stance = character['Batting Stance (righty:0,lefty:1) (0x27)'],
            nice_contact_spot_size = character['Nice Contact Spot Size (0x28)'],
            perfect_contact_spot_size = character['Perfect Contact Spot Size (0x29)'],
            slap_hit_power = character['Slap Hit Power (0x2a)'],
            charge_hit_power = character['Charge Hit Power (0x2b)'],
            bunting = character['Bunting (0x2c)'],
            hit_trajectory_mpp = character['Hit trajectory (mid:0,pull:1,push:2) (0x2d)'],
            hit_trajectory_mhl = character['Hit trajectory (mid:0,high:1,low:2) (0x2e)'],
            speed = character['Speed (0x2f)'],
            throwing_arm = character['Throwing Arm (0x30)'],
            character_class = character['Character Class (balance:0,power:1,speed:2,technique:3) (0x31)'],
            weight = character['Weight (0x32)'],
            captain = character['Captain (true:1,false:0) (0x33)'],
            captain_star_hit_or_pitch = character['Captain Star Hit/Pitch (0x34)'],
            non_captain_star_swing = character['Non Captain Star Swing (1:pop fly,2:grounder,3:line drive) (0x35)'],
            non_captain_star_pitch = character['Non Captain Star Pitch (0x36)'],
            batting_stat_bar = character['Batting Stat Bar (0x37)'],
            pitching_stat_bar = character['Pitching Stat Bar (0x38)'],
            running_stat_bar = character['Running Stat Bar (0x39)'],
            fielding_stat_bar = character['Fielding Stat Bar (0x3a)'],
        )

        db.session.add(character)

    db.session.commit()

    return 'Characters added...'

@app.route('/test_mail/')
def test_mail():
    msg = EmailMessage(
        'Test Email 1',
        'This is a test email',
        'from@example.com',
        ['to@example.com'],
        headers={'Message-ID': 'foo'},
    )
    msg.send()
    return 'Email sent...'

# == User Routes ==

# Refresh any JWT within 1 day of expiring after requests
@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()['exp']
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(days=7))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where JWT is invalid, return original response
        return response


@app.route('/register/', methods=['POST'])
def register():    
    in_username = request.json['Username']
    username_lowercase = in_username.lower()
    in_password = request.json['Password']
    in_email    = request.json['Email'].lower()

    # filter User out of database through username
    user = User.query.filter_by(username_lowercase=username_lowercase).first()

    # filter User out of database through email
    user_by_email = User.query.filter_by(email=in_email).first()

    if user or user_by_email:
        return abort(409, description='Username or Email has already been taken')
    elif in_username.isalnum() == False:
        return abort(406, description='Provided username is not alphanumeric')
    else:
        # === Create User row ===
        new_user = User(in_username, username_lowercase, in_email, in_password)
        db.session.add(new_user)
        db.session.commit()

    return jsonify({
        'riokey': new_user.rio_key,
        'username': new_user.username
    })


# Authenticate user, create new JWTs, login via username or email
@app.route('/login/', methods=['POST'])
def login():
    in_username = request.json['Username'].lower()
    in_password = request.json['Password']
    in_email    = request.json['Email'].lower()

    # filter User out of database through username
    user = User.query.filter_by(username_lowercase=in_username).first()

    # filter User out of database through email
    user_by_email = User.query.filter_by(email=in_email).first()

    if user == user_by_email:
        if bc.check_password_hash(user.password, in_password):            
            # Creating JWT and Cookies
            response = jsonify({
                'msg': 'login successful',
                'username': user.username,
            })
            access_token = create_access_token(identity=user.username)
            set_access_cookies(response, access_token)

            return response
        else:
            return abort(401, description='Incorrect password')
    else:
        return abort(408, description='Incorrect Username or Password')


# Revoke JWTs
@app.route('/logout/', methods=['POST'])
def logout():    
    response = jsonify({'msg': 'logout successful'})
    unset_jwt_cookies(response)
    return response


#GET will retreive user key, POST with empty JSON will generate new rio key and return it
@app.route('/key/', methods=['GET', 'POST'])
@jwt_required()
def update_rio_key():
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if request.method == 'GET':
        return jsonify({
            "riokey": current_user.rio_key
        })
    elif request.method == 'POST':
        current_user.rio_key = secrets.token_urlsafe(32)
        db.session.commit()
        return jsonify({
            "riokey": current_user.rio_key
        })



# === Upload Game Data ===
@app.route('/upload_game_data/', methods = ['POST'])
def populate_db():
    #get players from db User table
    home_player = User.query.filter_by(username=request.json['Home Player']).first()
    away_player = User.query.filter_by(username=request.json['Away Player']).first()

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
            batter_user_char_stats = home_player.user_character_stats.filter_by(char_id=character["Character"], captain=character['Captain'], superstar=character['Superstar']).first()
            if (batter_user_char_stats == None):
                print("Created UserCharStat for batter. Roster Loc:", character['RosterID'])
                batter_user_char_stats = UserCharacterStats(home_player.id, character["Character"], character['Captain'], character['Superstar'])
            batting_character_game_summary = teams['Home'][character['RosterID']]
        else: 
            batter_user_char_stats = away_player.user_character_stats.filter_by(char_id=character["Character"], captain=character['Captain'], superstar=character['Superstar']).first()
            if (batter_user_char_stats == None):
                print("Created UserCharStat for batter. Roster Loc:", character['RosterID'])
                batter_user_char_stats = UserCharacterStats(away_player.id, character["Character"], character['Captain'], character['Superstar'])
            batting_character_game_summary = teams['Away'][character['RosterID']]
        
        batter_user_char_stats.num_of_games += 1
        batter_user_char_stats.at_bats += batting_character_game_summary.at_bats
        batter_user_char_stats.hits += batting_character_game_summary.hits
        batter_user_char_stats.singles += batting_character_game_summary.singles
        batter_user_char_stats.doubles += batting_character_game_summary.doubles
        batter_user_char_stats.triples += batting_character_game_summary.triples
        batter_user_char_stats.homeruns += batting_character_game_summary.homeruns
        batter_user_char_stats.walks_bb += batting_character_game_summary.walks_bb
        batter_user_char_stats.walks_hit += batting_character_game_summary.walks_hit
        batter_user_char_stats.strikeouts += batting_character_game_summary.strikeouts
        batter_user_char_stats.bases_stolen += batting_character_game_summary.bases_stolen
        batter_user_char_stats.strikeouts_pitched += batting_character_game_summary.strikeouts_pitched
        batter_user_char_stats.inning_appearances += batting_character_game_summary.inning_appearances
        batter_user_char_stats.outs_pitched += batting_character_game_summary.outs_pitched
        batter_user_char_stats.batters_faced += batting_character_game_summary.batters_faced
        batter_user_char_stats.runs_allowed += batting_character_game_summary.runs_allowed
 
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
                pitcher_user_char_stats = away_player.user_character_stats.filter_by(char_id=pitch["PitcherID"], captain=pitcher_character_game_summary.captain, superstar=pitcher_character_game_summary.superstar).first()
                if (pitcher_user_char_stats == None):
                    print("Created UserCharStat for pitcher. Roster Loc:", pitch['Pitcher Roster Location'])
                    pitcher_user_char_stats = UserCharacterStats(away_player.id, pitch["PitcherID"], pitcher_character_game_summary.captain, pitcher_character_game_summary.superstar)
            else: 
                pitcher_character_game_summary = teams['Home'][pitch['Pitcher Roster Location']]
                pitcher_user_char_stats = home_player.user_character_stats.filter_by(char_id=pitch["PitcherID"], captain=pitcher_character_game_summary.captain, superstar=pitcher_character_game_summary.superstar).first()
                if (pitcher_user_char_stats == None):
                    print("Created UserCharStat for pitcher. Roster Loc:", pitch['Pitcher Roster Location'])
                    pitcher_user_char_stats = UserCharacterStats(home_player.id, pitch["PitcherID"], pitcher_character_game_summary.captain, pitcher_character_game_summary.superstar)
            
            # == Offensive Star Use ==
            star_swing = pitch['Type of Swing'] == 'Star'
            star_cost = 1
            is_captainable_char = Character.query.filter_by(char_id = batter_user_char_stats.char_id, captain=1).first()
            #Star hits/pitches cost two star for captain eligible characters that are not captains when contact is made
            if ((is_captainable_char is not None) and not batter_user_char_stats.captain and pitch['Contact Summary']):
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

            batter_user_char_stats.double_plays += int(pitch['Number Outs During Play'] >= 2)


            # == Defensive Star Use ==
            star_pitch = pitch['Star Pitch']
            star_cost = 1
            is_captainable_char = Character.query.filter_by(char_id = pitcher_user_char_stats.char_id, captain=1).first()
            #Star hits/pitches cost two star for captain eligible characters that are not captains
            if (is_captainable_char and not pitcher_user_char_stats.captain):
                star_cost = 2
            pitcher_character_game_summary.defensive_star_pitches += star_pitch
            pitcher_character_game_summary.defensive_stars_used += star_pitch * star_cost
            pitcher_character_game_summary.defensive_star_successes += int(star_pitch and strike_or_strikeout_or_foul)

            #Play is over, see if AB was a star chance
            if int(pitch['Final Result - Game']) not in cPLAY_RESULT_INVLD:
                batting_character_game_summary.offensive_star_chances += pitch['Star Chance']
                batter_user_char_stats.offensive_star_chances += batting_character_game_summary.offensive_star_chances

                pitcher_character_game_summary.defensive_star_chances += pitch['Star Chance']

            batter_user_char_stats.offensive_star_swings       += batting_character_game_summary.offensive_star_swings
            batter_user_char_stats.offensive_stars_used        += batting_character_game_summary.offensive_stars_used
            batter_user_char_stats.offensive_star_successes    += batting_character_game_summary.offensive_star_successes
            batter_user_char_stats.offensive_star_chances_won  += batting_character_game_summary.offensive_star_chances_won
            batter_user_char_stats.offensive_star_chances      += batting_character_game_summary.offensive_star_chances
            batter_user_char_stats.offensive_stars_put_in_play += batting_character_game_summary.offensive_stars_put_in_play
            
            pitcher_user_char_stats.defensive_star_pitches     += pitcher_character_game_summary.defensive_star_pitches
            pitcher_user_char_stats.defensive_stars_used       += pitcher_character_game_summary.defensive_stars_used
            pitcher_user_char_stats.defensive_star_successes   += pitcher_character_game_summary.defensive_star_successes
            pitcher_user_char_stats.defensive_star_chances_won += pitcher_character_game_summary.defensive_star_chances_won
            pitcher_user_char_stats.defensive_star_chances     += pitcher_character_game_summary.defensive_star_chances

            db.session.add(pitcher_user_char_stats)
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
                    ball_x_pos_upon_hit = pitch['Contact Summary'][0]['Ball Position Upon Contact - x'],
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
        db.session.add(batter_user_char_stats)
        db.session.commit()

    return 'Successfully added...'



# === FRONT END REQUESTS ===
@app.route('/get_user_info/<username>', methods = ['GET'])
@jwt_required(optional=True)
def get_user_info(username):
    current_user = get_jwt_identity()
    in_username_lowercase = username.lower()
    user = User.query.filter_by(username_lowercase=in_username_lowercase).first()

    if not user:
        return abort(408, description='User does not exist')
    elif user.username == current_user:
        return {
            "username": user.username,
            "private": user.private,
            "loggedIn": True
        }
    else:
        return {
            "username": user.username,
            "private": user.private,
            "loggedIn": False
        }

@app.route('/characters/', methods = ['GET'])
def get_characters():
    characters = []
    for character in Character.query.all():
        characters.append(character.to_dict())

    return {
        'characters': characters
        }

@app.route('/get_user_character_stats/<user>', methods = ['GET'])
@jwt_required(optional=True)
def get_user_character_stats(user):
    current_user = get_jwt_identity()

    in_username_lowercase = user.lower()
    user_to_query = User.query.filter_by(username_lowercase=in_username_lowercase).first()

    if not user_to_query:
        return abort(408, description='User does not exist')

    if user_to_query.private and user_to_query.username != current_user:
        return {
            'private': True,
            'username': user_to_query.username
        }

    if not user_to_query.private or user_to_query.username == current_user:
        characters = []
        user_characters = user_to_query.user_character_stats.all()    
        for character in user_characters:
            characters.append(character.to_dict())
        
        return {
            'User Characters': characters,
            'username': user_to_query.username
            }

@app.route('/get_games/<username>/', methods = ['GET'])
def get_games(username):
    in_username_lowercase = username.lower()
    user_id = User.query.filter_by(username_lowercase=in_username_lowercase).first().id
    games = Game.query.filter(db.or_(Game.away_player_id == user_id, Game.home_player_id == user_id))
    
    games_list = []
    for game in games:
        games_list.append(game.to_dict())

    return {
        'games': games_list,
    }

@app.route('/validate_JWT/', methods = ['GET'])
@jwt_required(optional=True)
def validate_JWT():
    try:
        current_user_username = get_jwt_identity()
        return jsonify(logged_in_as=current_user_username)
    except:
        return 'No JWT...'

@app.route('/set_privacy/', methods = ['GET', 'POST'])
@jwt_required()
def set_privacy():
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if request.method == 'GET':
        return jsonify({
            'private': current_user.private
        })
    if request.method == 'POST':
        current_user.private = not current_user.private
        db.session.commit()
        return jsonify({
            'private': current_user.private
        })
    characters = []
    #user_characters = User.query.filter_by(username=user).first().user_character_stats.all()
    #
    #for character in user_characters:
    #    characters.append(character.to_dict())
    
    #user_games = Game.query.filter((Game.away_player_id==user.id) | (Game.home_player_id==user.id) )
    #user_characters = CharacterGameSummary.query.filter_by(user_id==user.id)
    #print(user_characters)

    return {
        # 'User Characters': characters
        }

@app.route('/character_game_summaries/<user>/', methods = ['GET'])
def get_character_game_summaries(user):
    user = User.query.filter_by(username=user).first()
    game_summaries_list = []


    game_summaries = user.character_game_summaries
    for game_summary in game_summaries:
        game_summaries_list.append(game_summary.to_dict())

    return {
            'Game Summaries': game_summaries_list,
        }


@app.route('/sum_stats/<username>/<char_id>/', methods = ['GET'])
def sum_stats(username, char_id):
    user = User.query.filter_by(username=username).first()

    result = CharacterGameSummary.query.with_entities(
            db.func.sum(CharacterGameSummary.pitches_thrown).label('sum_pitches_thrown'),
            db.func.sum(CharacterGameSummary.hits_allowed).label('sum_hits_allowed'),
            db.func.sum(CharacterGameSummary.batters_walked).label('sum_batters_walked'),
            db.func.sum(CharacterGameSummary.runs_allowed).label('sum_runs_allowed'),
            db.func.sum(CharacterGameSummary.inning_appearances).label('sum_inning_appearances'),
        ).filter_by(
            user_id=user.id,
            char_id=char_id,
        ).first()

    return {
        'Char Id': char_id,
        'Sum Pitches': result.sum_pitches_thrown,
        'Sum Hits Allowed': result.sum_hits_allowed,
        'Sum Batters Walked': result.sum_batters_walked,
        'Sum Runs Allowed': result.sum_runs_allowed,
        'Average Hits allowed per Inning Appearance': result.sum_hits_allowed/result.sum_inning_appearances,
        'Average Batters Walked per Inning Appearance': result.sum_batters_walked/result.sum_inning_appearances,
        'Average # Runs allowed per Inning Appearance': result.sum_runs_allowed/result.sum_inning_appearances,
    }

@app.route('/session_execute_test/<username>/', methods = ['GET'])
def session_execute_test(username):

    # user_id  sum_pitches_thrown
    # ______   ___________________
    #   1              n
    #   2              n

    user_stats = (
        'SELECT user_id, sum(pitches_thrown) AS sum_pitches_thrown '
        'FROM character_game_summary '
        'GROUP BY user_id'
    )
    user_stats_query_result = db.session.execute(user_stats)

    user_stats_list = []
    for row in user_stats_query_result:
        user_stats_list.append({
            'User ID': row.user_id,
            'Pitches Thrown': row.sum_pitches_thrown,
        })



    
    # user_id       char_id       sum_pitches_thrown
    # ______       __________     ___________________
    #   1            0 - 53              n
    #   2            0 - 53              n

    user_char_stats = (
        'SELECT user_id, char_id, sum(pitches_thrown) AS sum_pitches_thrown '
        'FROM character_game_summary '
        'GROUP BY user_id, char_id'
    )
    user_char_stats_query_result = db.session.execute(user_char_stats)

    user_char_stats_list = []
    for row in user_char_stats_query_result:
        user_char_stats_list.append({
            'User ID': row.user_id,
            'Char ID': row.char_id,
            'Pitches Thrown': row.sum_pitches_thrown
        })
        


    return {
        "User Stats": user_stats_list,
        "User Char Stats": user_char_stats_list
    }
