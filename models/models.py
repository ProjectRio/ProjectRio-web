from app import db
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
import secrets


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
