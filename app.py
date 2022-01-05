import os.path
from decouple import config
import json

import secrets #For key generation
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from flask_login      import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_bcrypt     import Bcrypt


# ===== Setup =====
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
DB_URI = 'sqlite:///{}'.format(DB_PATH)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
 # Set up the App SECRET_KEY
app.config['SECRET_KEY'] = config('SECRET_KEY', default='S#perS3crEt_007')

db = SQLAlchemy(app)
ma = Marshmallow(app)

bc = Bcrypt(app)
lm = LoginManager()
lm.init_app(app)

# ===== Models =====
class User(db.Model, UserMixin):
    id       = db.Column(db.Integer,     primary_key=True)
    username = db.Column(db.String(64),  unique = True)
    email    = db.Column(db.String(120), unique = True)
    password = db.Column(db.String(500))
    rio_key  = db.Column(db.String(50), unique = True)

    user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_user')
    away_games = db.relationship('Game', foreign_keys = 'Game.away_player_id', backref = 'games_as_away_player')
    home_games = db.relationship('Game', foreign_keys = 'Game.home_player_id', backref = 'games_as_home_player')

    def __init__(self, in_username, in_email, in_password):
        self.username = in_username
        self.email    = in_email
        self.password = bc.generate_password_hash(in_password)
        self.rio_key  = secrets.token_urlsafe(32)

class Game(db.Model):
    game_id = db.Column(db.String(255), primary_key = True)
    away_player_id = db.Column(db.ForeignKey('user.id'), nullable=True) #One-to-One
    home_player_id = db.Column(db.ForeignKey('user.id'), nullable=True) #One-to-One
    date_time = db.Column(db.String(255))
    ranked = db.Column(db.Integer)
    stadium_id = db.Column(db.String(255))
    away_score = db.Column(db.Integer)
    home_score = db.Column(db.Integer)
    innings_selected = db.Column(db.Integer)
    innings_played = db.Column(db.Integer)
    quitter = db.Column(db.Integer) #0=None, 1=Away, 2=Home

    character_game_summary = db.relationship('CharacterGameSummary', backref='game')

class CharacterGameSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(255), db.ForeignKey('game.game_id'), nullable=False)
    char_id = db.Column(db.String(4), db.ForeignKey('character.char_id'), nullable=False)
    team_id = db.Column(db.Integer)
    roster_loc = db.Column(db.Integer) #0-8
    superstar = db.Column(db.Boolean)
    batters_faced = db.Column(db.Integer)
    runs_allowed = db.Column(db.Integer)
    batters_walked = db.Column(db.Integer)
    batters_hit = db.Column(db.Integer)
    hits_allowed = db.Column(db.Integer)
    homeruns_allowed = db.Column(db.Integer)
    pitches_thrown = db.Column(db.Integer)
    stamina = db.Column(db.Integer)
    was_pitcher = db.Column(db.Integer)
    batter_outs = db.Column(db.Integer)
    strike_outs_pitched = db.Column(db.Integer)
    star_pitches_thrown = db.Column(db.Integer)
    big_plays = db.Column(db.Integer)
    innings_pitched = db.Column(db.Integer)
    at_bats = db.Column(db.Integer)
    hits = db.Column(db.Integer)
    singles = db.Column(db.Integer)
    doubles = db.Column(db.Integer)
    triples = db.Column(db.Integer)
    homeruns = db.Column(db.Integer)
    strike_outs = db.Column(db.Integer)
    walks_bb = db.Column(db.Integer)
    walks_hit = db.Column(db.Integer)
    rbi = db.Column(db.Integer)
    bases_stolen = db.Column(db.Integer)
    star_hits = db.Column(db.Integer)

    batter_summary = db.relationship('PitchSummary', foreign_keys = 'PitchSummary.batter_id', backref = 'character_game_summary_batter')
    pitcher_summary = db.relationship('PitchSummary', foreign_keys = 'PitchSummary.pitcher_id', backref = 'character_game_summary_pitcher')
    fielding_summary = db.relationship('FieldingSummary', backref = 'fielding_summary')

class PitchSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batter_id = db.Column(db.Integer, db.ForeignKey('character_game_summary.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('character_game_summary.id'), nullable=False)
    inning = db.Column(db.Integer)
    half_inning = db.Column(db.Integer)
    batter_score = db.Column(db.Integer)
    pitcher_score = db.Column(db.Integer)
    balls = db.Column(db.Integer)
    strikes = db.Column(db.Integer)
    outs = db.Column(db.Integer)
    runner_on_1 = db.Column(db.Integer)
    runner_on_2 = db.Column(db.Integer)
    runner_on_3 = db.Column(db.Integer)
    chem_links_ob = db.Column(db.Integer)
    star_chance = db.Column(db.Integer)
    batter_stars = db.Column(db.Integer)
    pitcher_stars = db.Column(db.Integer)
    pitcher_handedness = db.Column(db.Integer)
    pitch_type = db.Column(db.Integer)
    charge_pitch_type = db.Column(db.Integer)
    star_pitch = db.Column(db.Integer)
    pitch_speed = db.Column(db.Integer)
    type_of_swing = db.Column(db.String(64))
    rbi = db.Column(db.Integer)
    num_outs = db.Column(db.Integer)
    result_inferred = db.Column(db.Integer)
    result_game = db.Column(db.Integer)

    contact_summary = db.relationship('ContactSummary', backref = 'contact_summary')

class ContactSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pitchsummary_id = db.Column(db.Integer, db.ForeignKey('pitch_summary.id'), nullable=False)
    type_of_contact = db.Column(db.Integer)
    charge_power_up = db.Column(db.Float)
    charge_power_down = db.Column(db.Float)
    star_swing_five_star = db.Column(db.Integer)
    input_direction = db.Column(db.Integer)
    batter_handedness = db.Column(db.Integer)
    ball_angle = db.Column(db.String(64))
    ball_horiz_power = db.Column(db.String(64))
    ball_vert_power = db.Column(db.String(64))
    ball_x_velocity = db.Column(db.Float)
    ball_y_velocity = db.Column(db.Float)
    ball_z_velocity = db.Column(db.Float)
    ball_x_pos = db.Column(db.Float)
    ball_y_pos = db.Column(db.Float)
    ball_z_pos = db.Column(db.Float)
    ball_x_pos_upon_hit = db.Column(db.Float)
    ball_y_pos_upon_hit = db.Column(db.Float)

    fielding_summary = db.relationship('FieldingSummary', backref = 'fielding_summary_table')

class FieldingSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_summary_id = db.Column(db.Integer, db.ForeignKey('contact_summary.id'), nullable=False)
    character_game_summary_id = db.Column(db.Integer, db.ForeignKey('character_game_summary.id'), nullable=False)
    position = db.Column(db.Integer)

class Character(db.Model):
    char_id = db.Column(db.String(4), primary_key=True)
    name = db.Column(db.String(16))

    user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_character')
    character_game_summary = db.relationship('CharacterGameSummary', backref = 'character_game_summary_from_character')

class UserCharacterStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    char_id = db.Column(db.String(4), db.ForeignKey('character.char_id'), nullable=False)

# ===== Schema =====

class UserSchema(ma.Schema):
  class Meta:
      fields = ('username', 'email', 'rio_key')

class GameSchema(ma.Schema):
  class Meta:
    fields = (
      'game_id',
      'date_time',
      'ranked',
      'stadium_id',
      'away_player_id',
      'home_player_id',
      'away_score',
      'home_score',
      'innings_selected',
      'innings_played',
      'quitter',
    )

class CharacterGameSummarySchema(ma.Schema):
  class Meta:
    fields = (
      'id',
      'game_id',
      'char_id',
      'team_id',
      'roster_loc',
      'superstar',
      'batters_faced',
      'runs_allowed',
      'batters_walked',
      'batters_hit',
      'hits_allowed',
      'homeruns_allowed',
      'pitches_thrown',
      'stamina',
      'was_pitcher',
      'batter_outs',
      'strike_outs_pitched',
      'star_pitches_thrown',
      'big_plays',
      'innings_pitched',
      'at_bats',
      'hits',
      'singles',
      'doubles',
      'triples',
      'homeruns',
      'strike_outs',
      'walks_bb',
      'walks_hit',
      'rbi',
      'bases_stolen',
      'star_hits',
    )

class PitchSummarySchema(ma.Schema):
  class Meta:
    fields = (
      'id',
      'batter_id',
      'batter_id',
      'pitcher_id',
      'inning',
      'half_inning',
      'batter_score',
      'pitcher_score',
      'balls',
      'strikes',
      'outs',
      'runner_on_1',
      'runner_on_2',
      'runner_on_3',
      'chem_links_ob',
      'star_chance',
      'batter_stars',
      'pitcher_stars',
      'pitcher_handedness',
      'pitch_type',
      'charge_pitch_type',
      'star_pitch',
      'pitch_speed',
      'type_of_swing',
      'rbi',
      'num_outs',
      'result_inferred',
      'result_game',
    )

class ContactSummarySchema(ma.Schema):
  class Meta:
    fields = (
      'id',
      'pitchsummary_id',
      'type_of_contact',
      'charge_power_up',
      'charge_power_down',
      'star_swing_five_star',
      'input_direction',
      'batter_handedness',
      'ball_angle',
      'ball_horiz_power',
      'ball_vert_power',
      'ball_x_velocity',
      'ball_y_velocity',
      'ball_z_velocity',
      'ball_x_pos',
      'ball_y_pos',
      'ball_z_pos',
      'ball_x_pos_upon_hit',
      'ball_y_pos_upon_hit',
    )

class FieldingSummarySchema(ma.Schema):
  class Meta:
    fields = (
      'id',
      'contact_summary_id',
      'character_game_summary_id',
      'position',
    )

class CharacterSchema(ma.Schema):
  class Meta:
    fields: (
        'char_id',
        'name',
    )

class UserCharacterStatsSchema(ma.Schema):
  class Meta:
    fields: (
      'id',
      'user_id',
      'char_id',
    )

user_schema = UserSchema()
game_schema = GameSchema()
user_character_stats_schema = UserCharacterStatsSchema(many=True)

# ===== API Routes =====
@app.route('/')
def index():
    return 'API online...'

# ===== Init DB Routes ===== 
@app.route('/create_characters/', methods = ['POST'])
def create_characters():
    f = open('./json/MSB_Stats_dec.json')
    character_list = json.load(f)["Characters"]

    for character in character_list:
        character = Character(
            char_id = character['Char Id'],
            name = character['Char Name']
        )

        db.session.add(character)

    db.session.commit()

    return 'Character tables created...'

# == User Routes ==

# provide login manager with load_user callback
@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Logout user
@app.route('/logout/')
def logout():
    logout_user()
    
    resp = jsonify(success=True)
    return resp

@app.route('/register/', methods=['POST'])
def register():    
    in_username = request.json['Username']
    in_password = request.json['Password']
    in_email    = request.json['Email']

    # filter User out of database through username
    user = User.query.filter_by(username=in_username).first()

    # filter User out of database through email
    user_by_email = User.query.filter_by(email=in_email).first()

    if user or user_by_email:
        return abort(409, description='Username has already been taken')
    elif in_username.isalnum() == False:
        return abort(406, description='Provided username is not alphanumeric')
    else:
        new_user = User(in_username, in_email, in_password)
        db.session.add(new_user)
        db.session.commit()

        # === Create UserCharacterStats tables ===
        characters = Character.query.all()
        for character in characters:
            user_character_stats = UserCharacterStats(
                user_id = new_user.id,
                char_id = character.char_id,
            )

            db.session.add(user_character_stats)
            db.session.commit()

    return user_schema.dump(new_user)

# Authenticate user, login via username or email
@app.route('/login/', methods=['POST'])
def login():
    in_username = request.json['Username']
    in_password = request.json['Password']
    in_email    = request.json['Email']

    # filter User out of database through username
    user = User.query.filter_by(username=in_username).first()

    # filter User out of database through email
    user_by_email = User.query.filter_by(email=in_email).first()

    if user or user_by_email:
        user_to_login = user if user else user_by_email
        if bc.check_password_hash(user_to_login.password, in_password):
            login_user(user_to_login)
            return user_schema.dump(user_to_login)
        else:
            return abort(401, description='Incorrect password')
    else:
        return abort(406, description='User does not exist')

#GET will retreive user key, POST with empty JSON will generate new rio key and return it
@app.route('/key/', methods=['GET', 'POST'])
@login_required
def update_rio_key():
    if current_user.is_authenticated:
        # Return Key
        if request.method == 'GET':
            return user_schema.dump(current_user)
        # Generate new key and return it
        elif request.method == 'POST':
            current_user.rio_key  = secrets.token_urlsafe(32)            
            db.session.commit()
            return user_schema.dump(current_user)
    

# == Game Routes ==
@app.route('/game/', methods=['POST'])
def populate_db():
    # === Game ===
    # Get players from User table
    home_player = User.query.filter_by(username=request.json['Home Player']).first()
    away_player = User.query.filter_by(username=request.json['Away Player']).first()

    game = Game(
        game_id = request.json['GameID'],
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
            game = game,
            team_id = 0 if character['Team'] == 'Home' else 1,
            char_id = Character.query.filter_by(name=character["Character"]).first().char_id,
            roster_loc = character['RosterID'],
            superstar = True if character['Is Starred'] == 1 else False,
            batters_faced = defensive_stats['Batters Faced'],
            runs_allowed = defensive_stats['Runs Allowed'],
            batters_walked = defensive_stats['Batters Walked'],
            batters_hit = defensive_stats['Batters Hit'],
            hits_allowed = defensive_stats['Hits Allowed'],
            homeruns_allowed = defensive_stats['HRs Allowed'],
            pitches_thrown = defensive_stats['Pitches Thrown'],
            stamina = defensive_stats['Stamina'],
            was_pitcher = defensive_stats['Was Pitcher'],
            batter_outs = defensive_stats['Batter Outs'],
            strike_outs_pitched = defensive_stats['Strikeouts'],
            star_pitches_thrown = defensive_stats['Star Pitches Thrown'],
            big_plays = defensive_stats['Big Plays'],
            innings_pitched = defensive_stats['Innings Pitched'],
            at_bats = offensive_stats['At Bats'],
            hits = offensive_stats['Hits'],
            singles = offensive_stats['Singles'],
            doubles = offensive_stats['Doubles'],
            triples = offensive_stats['Triples'],
            homeruns = offensive_stats['Homeruns'],
            strike_outs = offensive_stats['Strikeouts'],
            walks_bb = offensive_stats['Walks (4 Balls)'],
            walks_hit = offensive_stats['Walks (Hit)'],
            rbi = offensive_stats['RBI'],
            bases_stolen = offensive_stats['Bases Stolen'],
            star_hits = offensive_stats['Star Hits'],
        )

        db.session.add(character_game_summary)
        db.session.commit()

        teams[character['Team']][character['RosterID']] = character_game_summary

    # === Pitch Summary ===
    for character in player_stats:
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
                runner_on_1 = True if pitch['Runners on Base'][2] == 1 else False,
                runner_on_2 = True if pitch['Runners on Base'][1] == 1 else False,
                runner_on_3 = True if pitch['Runners on Base'][0] == 1 else False,
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
                    ball_x_pos_upon_hit = pitch['Contact Summary'][0]['Ball Position Upon Contact- x'],
                    ball_y_pos_upon_hit = pitch['Contact Summary'][0]['Ball Position Upon Contact- Y'],
                )

                db.session.add(contact_summary)
                db.session.commit()

                # === Fielding Summary ===
                if pitch['Contact Summary'][0]['Fielding Summary']:
                    fielder_roster_location = pitch['Contact Summary'][0]['Fielding Summary'][0]['Fielder Roster Location']
                    fielder_team = 'Home' if character['Team'] == 'Away' else 'Away'

                    fielding_summary = FieldingSummary(
                        contact_summary_id = contact_summary.id,
                        character_game_summary_id = teams[fielder_team][fielder_roster_location].id,
                        position = pitch['Contact Summary'][0]['Fielding Summary'][0]['Fielder Position'],
                    )

                db.session.add(fielding_summary)
                db.session.commit()

    db.session.commit()
    return game_schema.jsonify(game)

if __name__ == '__main__':
    app.run(debug=True)
