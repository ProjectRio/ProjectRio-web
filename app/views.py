from flask import request, jsonify, abort
from flask import current_app as app
from flask_jwt_extended import create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
import smtplib
import ssl
import secrets
from . import bc
from .models import db, User, Character, Game, CharacterGameSummary, PitchSummary, ContactSummary, FieldingSummary, ChemistryTable, Tag, GameTag
from .schemas import UserSchema
import json
from datetime import datetime, timedelta, timezone
from .consts import *

from pprint import pprint

# Schemas
user_schema = UserSchema()

# === Initalize Character Tables And Ranked/Superstar Tags ===
@app.route('/create_character_table/', methods = ['POST'])
def create_character_tables():
    f = open('./json/characters.json')
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

    return 'Characters added...\n'


@app.route('/create_tag_table/', methods =['POST'])
def create_default_tags():
    ranked = Tag(
        name = "Ranked",
        name_lowercase = "ranked",
        desc = "Tag for Ranked games"
    )

    unranked = Tag(
        name = "Unranked",
        name_lowercase = "unranked",
        desc = "Tag for Unranked games"
    )

    superstar = Tag(
        name = "Superstar",
        name_lowercase = "superstar",
        desc = "Tag for Stars On"
    )

    normal = Tag(
        name = "Normal",
        name_lowercase = "normal",
        desc = "Tag for Normal games"
    )

    db.session.add(ranked)
    db.session.add(unranked)
    db.session.add(superstar)
    db.session.add(normal)
    db.session.commit()

    return 'Tags created... \n'


# == User Routes ==
# Refresh any JWT within 7 days of expiration after requests
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

    user = User.query.filter_by(username_lowercase=username_lowercase).first()
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

        try:
            send_verify_account_email(in_username, in_email, new_user.active_url)
        except:
            return abort(502, 'Failed to send email')
        
    return jsonify({
        'username': new_user.username
    })

def send_verify_account_email(receiver_username, receiver_email, active_url):
    port = 465
    smtp_server = 'smtp.gmail.com'
    sender_email = 'projectrio.webtest@gmail.com'
    password = 'PRWT1234!'

    message = (
        'Subject: Verify your Project Rio Account\n'
        'Dear {0},\n'
        '\n'
        'Please click the following link to verify your email address and get your Rio Key.\n'
        '{1}'
        '\n'
        'Happy Hitting!\n'
        'Project Rio Web Team'
    ).format(
        receiver_username,
        active_url
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

    return


@app.route('/verify_email/', methods=['POST'])
def verify_email():
    try:
        active_url = request.json['active_url']
        user = User.query.filter_by(active_url=active_url).first()
        user.verified = True
        user.active_url = None

        db.session.add(user)
        db.session.commit()
        return {
            'Rio Key': user.rio_key,
        }, 200
    except:
        return abort(422, 'Invalid Key')


@app.route('/retire_account/', methods=[''])
@jwt_required()
def retire_account():
    # Check for valid JWT
    # Get User using valid JWT
    # Remove email
    # Remove discord
    # Set Private to true
    # Set Retired to true

    return {
        'msg': 'Account Retired...'
    }


@app.route('/request_email_change/', methods=['GET'])
@jwt_required()
def request_email_change():
    # Check for valid JWT
    # Get User using valid JWT
    # Create secret code for link when changing email
    # Add secret link to table for short period of time
    # Send out email for email validation w link

    return {
       'msg': 'Link emailed...'
    }


@app.route('/change_email/<secretcode>/', methods=['POST'])
@jwt_required()
def change_email(secretcode):
    # Check for valid JWT
    # Get User using valid JWT
    # Check for valid secretlink related to logged in user
    # Use user input to switch email to a new email

    return {
        'msg': 'Email changed...'
    }


@app.route('/request_password_change/', methods=['POST'])
def request_password_change():
    if '@' in request.json['username or email']:
        email_lowercase = request.json['username or email'].lower()
        user = User.query.filter_by(email=email_lowercase).first()
    else:
        username_lower = request.json['username or email'].lower()
        user = User.query.filter_by(username_lowercase=username_lower).first()

    if not user:
        abort(408, 'Corresponding user does not exist')

    if user.verified == False:
        abort(401, 'Email unverified')

    active_url = secrets.token_urlsafe(32)
    user.active_url = active_url
    db.session.add(user)
    db.session.commit()

    try:
        send_password_reset_email(user)
    except:
        abort(502, 'Failed to send email')

    return {
        'msg': 'Link emailed...'
    }

def send_password_reset_email(user):
    port = 465   
    smtp_server = 'smtp.gmail.com'
    sender_email = 'projectrio.webtest@gmail.com'
    receiver_email = user.email
    receiver_username = user.username
    active_url = user.active_url
     # Will be saved securely on server on roll out    
    password = 'PRWT1234!'

    message = (
        'Subject: Project Rio Password Reset\n'

        'Dear {0},\n'
        '\n'
        'We received a password reset request. If you did not make this request, please ignore this email.\n'
        'Otherwise, follow this link to reset your account\n'
        '{1}\n'
        '\n'
        'Happy hitting!\n'
        'Project Rio Web Team'
    ).format(
            receiver_username, 
            active_url
        )
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

    return


# === RIO Client Endpoints ===

# Evaluate users provided to Client
# /validateuserfromclient/?username=demouser1&rio_key=fI8WbLJ3Ti2gkcEuMh1DvcMGl4LQvYFRJvlpgwcCnpw
@app.route('/validate_user_from_client/', methods=['GET'])
def validate_user_from_client():
    in_username = request.args.get('username')
    in_username_lower = in_username.lower()
    in_rio_key = request.args.get('rio_key')

    user = User.query.filter_by(username_lowercase = in_username_lower, rio_key = in_rio_key).first()

    if user is None:
        abort(404, 'Invalid UserID or RioKey')

    return {'msg': 'success'}


@app.route('/get_available_tags/<username>/', methods=['GET'])
def get_available_tags(username):
    in_username_lower = username.lower()

    query = (
        'SELECT '
        'tag.name AS tag_name '
        'FROM tag '
        'WHERE tag.community_id IS NULL'
    )

    result = db.session.execute(query).all()

    print(result)

    return 'Success...'




@app.route('/change_password/', methods=['POST'])
def change_password():
    active_url = request.json['active_url']
    password = request.json['password']

    user = User.query.filter_by(active_url=active_url).first()

    if not user:
        return abort(422, 'Invalid Key')

    if user.verified == False:
        return abort(401, 'Email unverified')

    user.password = bc.generate_password_hash(password)
    user.active_url = None
    db.session.add(user)
    db.session.commit()

    return {
        'msg': 'Password changed...'
    }, 200

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


# === FRONT END REQUESTS ===
@app.route('/characters/', methods = ['GET'])
def get_characters():
    characters = []
    for character in Character.query.all():
        characters.append(character.to_dict())

    return {
        'characters': characters
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


@app.route('/<username>/stats/', methods = ['GET'])
@jwt_required(optional=True)
def user_stats(username):
    # # Check if user is logged in
    # logged_in_user = get_jwt_identity()
    
    # # Get User row
    in_username_lowercase = username.lower()
    user_to_query = User.query.filter_by(username_lowercase=in_username_lowercase).first()

    if not user_to_query:
        return abort(408, description='User does not exist')

    # if user_to_query.private and user_to_query.username != logged_in_user:
    #     return {
    #         'private': True,
    #         'username': user_to_query.username
    #     }

    # if not user_to_query.private or user_to_query.username == logged_in_user: 
    user_query = create_query(user_to_query.id, cUser)
    char_query = create_query(user_to_query.id, cCharacters)
    captain_query = create_query(user_to_query.id, cCaptains)

    user_totals = get_user_totals(user_to_query.id, user_query)
    char_totals = get_per_char_totals(user_to_query.id, char_query)
    captain_totals = get_captain_totals(user_to_query.id, captain_query)


    return {
        "username": user_to_query.username,
        "user_totals": user_totals,
        "top_characters": char_totals,
        "top_captains": captain_totals,
    }

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
    elif query_subject is cUser:
        group_by_statement = 'GROUP BY character_game_summary.user_id'
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

def get_user_totals(user_id, query):
    result = db.session.execute(query).all()

    user_totals = []
    for row in result:
        user_totals = {
            "games": row.games/9,
            "wins": row.wins/9,
            "losses": row.losses/9,
            "homeruns": row.homeruns,
            "batting_average": row.hits/row.at_bats,
            "obp": (row.hits + row.walks_bb + row.walks_hit)/(row.at_bats + row.walks_bb + row.walks_hit),
            "rbi": row.rbi,
            "slg": (row.singles + (row.doubles * 2) + (row.triples * 3) + (row.homeruns * 4))/row.at_bats,
            "era": calculate_era(row.runs_allowed, row.outs_pitched)
        }
    
    return user_totals

def get_captain_totals(user_id, query):
    result = db.session.execute(query).all()

    # Get top 3 captains
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

def get_per_char_totals(user_id, query):
    result = db.session.execute(query).all()

    # Get top 6 batter by rbi
    batters = sorted(result, key=lambda batter: batter.rbi, reverse=True)
    top_batters = [batter.name for batter in batters if batter.at_bats > 20][0:6]

    # Get top 6 pitchers by era
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

# http://127.0.0.1:5000/games/?recent=5&username=demOuser4&username=demouser1&username=demouser5&vs=True
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
