from . import db, bc
from flask_login import UserMixin
import secrets

class Character(db.Model):
    char_id = db.Column(db.Integer, primary_key=True)
    chemistry_table_id = db.Column(db.ForeignKey('chemistry_table.id'), nullable = False)
    name = db.Column(db.String(16))
    starting_addr = db.Column(db.String(16))
    curve_ball_speed = db.Column(db.Integer)
    fast_ball_speed = db.Column(db.Integer)
    curve = db.Column(db.Integer)
    fielding_arm = db.Column(db.Integer)
    batting_stance = db.Column(db.Integer)
    nice_contact_spot_size = db.Column(db.Integer)
    perfect_contact_spot_size = db.Column(db.Integer)
    slap_hit_power = db.Column(db.Integer)
    charge_hit_power = db.Column(db.Integer)
    bunting = db.Column(db.Integer)
    hit_trajectory_mpp = db.Column(db.Integer)
    hit_trajectory_mhl = db.Column(db.Integer)
    speed = db.Column(db.Integer)
    throwing_arm = db.Column(db.Integer)
    character_class = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    captain = db.Column(db.Integer)
    captain_star_hit_or_pitch = db.Column(db.Integer)
    non_captain_star_swing = db.Column(db.Integer)
    non_captain_star_pitch = db.Column(db.Integer)
    batting_stat_bar = db.Column(db.Integer)
    pitching_stat_bar = db.Column(db.Integer)
    running_stat_bar = db.Column(db.Integer)
    fielding_stat_bar = db.Column(db.Integer)
    
    user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_character')
    character_game_summary = db.relationship('CharacterGameSummary', backref = 'character_game_summary_from_character')

    def to_dict(self):
        return {
            'char_id': self.char_id,
            'chemistry_table_id': self.chemistry_table_id,
            'name': self.name,
            'starting_addr': self.starting_addr,
            'curve_ball_speed': self.curve_ball_speed,
            'fast_ball_speed': self.fast_ball_speed,
            'curve': self.curve,
            'fielding_arm': self.fielding_arm,
            'batting_stance': self.batting_stance,
            'nice_contact_spot_size': self.nice_contact_spot_size,
            'perfect_contact_spot_size': self.perfect_contact_spot_size,
            'slap_hit_power': self.slap_hit_power,
            'charge_hit_power': self.charge_hit_power,
            'bunting': self.bunting,
            'hit_trajectory_mpp': self.hit_trajectory_mpp,
            'hit_trajectory_mhl': self.hit_trajectory_mhl,
            'speed': self.speed,
            'throwing_arm': self.throwing_arm,
            'character_class': self.character_class,
            'weight': self.weight,
            'captain': 'True' if self.captain == '1' else 'False',
            'captain_star_hit_or_pitch': self.captain_star_hit_or_pitch,
            'non_captain_star_swing': self.non_captain_star_swing,
            'non_captain_star_pitch': self.non_captain_star_pitch,
            'batting_stat_bar': self.batting_stat_bar,
            'pitching_stat_bar': self.pitching_stat_bar,
            'running_stat_bar': self.running_stat_bar,
            'fielding_stat_bar': self.fielding_stat_bar,
        }

class ChemistryTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mario = db.Column(db.Integer)
    luigi = db.Column(db.Integer)
    dk = db.Column(db.Integer)
    diddy = db.Column(db.Integer)
    peach = db.Column(db.Integer)
    daisy = db.Column(db.Integer)
    yoshi = db.Column(db.Integer)
    baby_mario = db.Column(db.Integer)
    baby_luigi = db.Column(db.Integer)
    bowser = db.Column(db.Integer)
    wario = db.Column(db.Integer)
    waluigi = db.Column(db.Integer)
    koopa_r = db.Column(db.Integer)
    toad_r = db.Column(db.Integer)
    boo = db.Column(db.Integer)
    toadette = db.Column(db.Integer)
    shy_guy_r = db.Column(db.Integer)
    birdo = db.Column(db.Integer)
    monty = db.Column(db.Integer)
    bowser_jr = db.Column(db.Integer)
    paratroopa_r = db.Column(db.Integer)
    pianta_b = db.Column(db.Integer)
    pianta_r = db.Column(db.Integer)
    pianta_y = db.Column(db.Integer)
    noki_b = db.Column(db.Integer)
    noki_r = db.Column(db.Integer)
    noki_g = db.Column(db.Integer)
    bro_h = db.Column(db.Integer)
    toadsworth = db.Column(db.Integer)
    toad_b = db.Column(db.Integer)
    toad_y = db.Column(db.Integer)
    toad_g = db.Column(db.Integer)
    toad_p = db.Column(db.Integer)
    magikoopa_b = db.Column(db.Integer)
    magikoopa_r = db.Column(db.Integer)
    magikoopa_g = db.Column(db.Integer)
    magikoopa_y = db.Column(db.Integer)
    king_boo = db.Column(db.Integer)
    petey = db.Column(db.Integer)
    dixie = db.Column(db.Integer)
    goomba = db.Column(db.Integer)
    paragoomba = db.Column(db.Integer)
    koopa_g = db.Column(db.Integer)
    paratroopa_g = db.Column(db.Integer)
    shy_guy_b = db.Column(db.Integer)
    shy_guy_y = db.Column(db.Integer)
    shy_guy_g = db.Column(db.Integer)
    shy_guy_bk = db.Column(db.Integer)
    dry_bones_gy = db.Column(db.Integer)
    dry_bones_g = db.Column(db.Integer)
    dry_bones_r = db.Column(db.Integer)
    dry_bones_b = db.Column(db.Integer)
    bro_f = db.Column(db.Integer)
    bro_b = db.Column(db.Integer)

    character = db.relationship('Character', backref = 'character')

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer,     primary_key=True)
    username = db.Column(db.String(64),  unique = True)
    username_lowercase = db.Column(db.String(64), unique = True)
    email    = db.Column(db.String(120), unique = True)
    password = db.Column(db.String(500))
    rio_key  = db.Column(db.String(50), unique = True)
    private = db.Column(db.Boolean)

    user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_user', lazy = 'dynamic')
    character_game_summaries = db.relationship('CharacterGameSummary', backref = 'user', lazy = 'dynamic')
    away_games = db.relationship('Game', foreign_keys = 'Game.away_player_id', backref = 'games_as_away_player')
    home_games = db.relationship('Game', foreign_keys = 'Game.home_player_id', backref = 'games_as_home_player')
    password_reset = db.relationship('PasswordReset', backref = 'user')

    def __init__(self, in_username, username_lowercase, in_email, in_password):
        self.username = in_username
        self.username_lowercase = username_lowercase
        self.email    = in_email
        self.password = bc.generate_password_hash(in_password)
        self.rio_key  = secrets.token_urlsafe(32)
        self.private = True

class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key = True)
    away_player_id = db.Column(db.ForeignKey('user.id'), nullable=False) #One-to-One
    home_player_id = db.Column(db.ForeignKey('user.id'), nullable=False) #One-to-One
    date_time = db.Column(db.Integer)
    ranked = db.Column(db.Integer)
    stadium_id = db.Column(db.Integer)
    away_score = db.Column(db.Integer)
    home_score = db.Column(db.Integer)
    innings_selected = db.Column(db.Integer)
    innings_played = db.Column(db.Integer)
    quitter = db.Column(db.Integer) #0=None, 1=Away, 2=Home

    character_game_summary = db.relationship('CharacterGameSummary', backref='game')

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'away_player_id': self.away_player_id,
            'home_player_id': self.home_player_id,
            'away_score': self.away_score,
            'home_score': self.home_score,
            'innings_played': self.innings_played            
        }

class CharacterGameSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'), nullable=False)
    char_id = db.Column(db.Integer, db.ForeignKey('character.char_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer)
    roster_loc = db.Column(db.Integer) #0-8
    captain = db.Column(db.Boolean)
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
    strikeouts_pitched = db.Column(db.Integer)
    star_pitches_thrown = db.Column(db.Integer)
    big_plays = db.Column(db.Integer)
    outs_pitched = db.Column(db.Integer)
    inning_appearances = db.Column(db.Integer)
    at_bats = db.Column(db.Integer)
    hits = db.Column(db.Integer)
    singles = db.Column(db.Integer)
    doubles = db.Column(db.Integer)
    triples = db.Column(db.Integer)
    homeruns = db.Column(db.Integer)
    strikeouts = db.Column(db.Integer)
    walks_bb = db.Column(db.Integer)
    walks_hit = db.Column(db.Integer)
    rbi = db.Column(db.Integer)
    bases_stolen = db.Column(db.Integer)
    star_hits = db.Column(db.Integer)
    offensive_star_swings = db.Column(db.Integer)
    offensive_stars_used = db.Column(db.Integer)
    offensive_stars_put_in_play = db.Column(db.Integer)
    offensive_star_successes = db.Column(db.Integer)
    offensive_star_chances = db.Column(db.Integer)
    offensive_star_chances_won = db.Column(db.Integer)
    defensive_star_pitches = db.Column(db.Integer)
    defensive_stars_used = db.Column(db.Integer)
    defensive_star_successes = db.Column(db.Integer)
    defensive_star_chances = db.Column(db.Integer)
    defensive_star_chances_won = db.Column(db.Integer)

    batter_summary = db.relationship('PitchSummary', foreign_keys = 'PitchSummary.batter_id', backref = 'character_game_summary_batter')
    pitcher_summary = db.relationship('PitchSummary', foreign_keys = 'PitchSummary.pitcher_id', backref = 'character_game_summary_pitcher')
    fielding_summary = db.relationship('FieldingSummary', backref = 'fielding_summary')

    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'char_id': self.char_id,
            "user_id": self.user_id,
            "team_id": self.team_id
        }

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
    type_of_swing = db.Column(db.Integer)
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
    ball_angle = db.Column(db.Integer)
    ball_horiz_power = db.Column(db.Integer)
    ball_vert_power = db.Column(db.Integer)
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
    fielder_character_game_summary_id = db.Column(db.Integer, db.ForeignKey('character_game_summary.id'), nullable=False)
    position = db.Column(db.Integer)

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reset_token = db.Column(db.String(32), nullable=False)



# Depreciated

class UserStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    num_of_games = db.Column(db.Integer)
    homeruns = db.Column(db.Integer)
    innings_played = db.Column(db.Integer)

    def __init__(self, user_id):
        self.user_id = user_id
        self.num_of_games = 0
        self.homeruns = 0
        self.innings_played = 0

    def to_dict(self):
        return {
            'num_of_games': self.num_of_games,
            'homeruns': self.homeruns,
            'innings_played': self.innings_played
        }

class UserCharacterStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    char_id = db.Column(db.Integer, db.ForeignKey('character.char_id'), nullable=False)
    captain = db.Column(db.Integer)
    superstar = db.Column(db.Integer)
    num_of_games = db.Column(db.Integer)
    at_bats = db.Column(db.Integer)
    hits = db.Column(db.Integer)
    singles = db.Column(db.Integer)
    doubles = db.Column(db.Integer)
    triples = db.Column(db.Integer)
    homeruns = db.Column(db.Integer)
    walks_bb = db.Column(db.Integer)
    walks_hit = db.Column(db.Integer)
    strikeouts = db.Column(db.Integer)
    bases_stolen = db.Column(db.Integer)
    double_plays = db.Column(db.Integer)
    offensive_star_swings = db.Column(db.Integer)
    offensive_stars_used = db.Column(db.Integer)
    offensive_stars_put_in_play = db.Column(db.Integer)
    offensive_star_successes = db.Column(db.Integer)
    offensive_star_chances = db.Column(db.Integer)
    offensive_star_chances_won = db.Column(db.Integer)
    strikeouts_pitched = db.Column(db.Integer)
    outs_pitched = db.Column(db.Integer)
    inning_appearances = db.Column(db.Integer)
    batters_faced = db.Column(db.Integer)
    runs_allowed = db.Column(db.Integer)
    defensive_star_pitches = db.Column(db.Integer)
    defensive_stars_used = db.Column(db.Integer)
    defensive_star_successes = db.Column(db.Integer)
    defensive_star_chances = db.Column(db.Integer)
    defensive_star_chances_won = db.Column(db.Integer)

    def __init__(self, user_id, char_id, captain, superstar):
        self.user_id = user_id
        self.char_id = char_id
        self.captain = captain
        self.superstar = superstar
        self.num_of_games = 0
        self.at_bats = 0
        self.hits = 0
        self.singles = 0
        self.doubles = 0
        self.triples = 0
        self.homeruns = 0
        self.walks_bb = 0
        self.walks_hit = 0
        self.strikeouts = 0
        self.bases_stolen = 0
        self.double_plays = 0
        self.offensive_star_swings = 0
        self.offensive_stars_used = 0
        self.offensive_stars_put_in_play = 0
        self.offensive_star_successes = 0
        self.offensive_star_chances = 0
        self.offensive_star_chances_won = 0
        self.strikeouts_pitched = 0
        self.outs_pitched = 0
        self.inning_appearances = 0
        self.batters_faced = 0
        self.runs_allowed = 0
        self.defensive_star_pitches = 0
        self.defensive_stars_used = 0
        self.defensive_star_successes = 0
        self.defensive_star_chances = 0
        self.defensive_star_chances_won = 0

    def to_dict(self): 
        return {
            'id': self.id,
            'user_id': self.user_id,
            'char_id': self.char_id,
            'captain': self.captain,
            'superstar': self.superstar,
            'num_of_games': self.num_of_games,
            'at_bats': self.at_bats,
            'hits': self.hits,
            'singles': self.singles,
            'doubles': self.doubles,
            'triples': self.triples,
            'homeruns': self.homeruns,
            'walks_bb': self.walks_bb,
            'walks_hit': self.walks_hit,
            'strikeouts': self.strikeouts,
            'bases_stolen': self.bases_stolen,
            'double_plays': self.double_plays,
            'offensive_star_swings': self.offensive_star_swings,
            'offensive_stars_used': self.offensive_stars_used,
            'offensive_stars_put_in_play': self.offensive_stars_put_in_play,
            'offensive_star_successes': self.offensive_star_successes,
            'offensive_star_chances': self.offensive_star_chances,
            'offensive_star_chances_won': self.offensive_star_chances_won,
            'strikeouts_pitched': self.strikeouts,
            "outs_pitched": self.outs_pitched,
            'inning_appearances': self.inning_appearances,
            'batters_faced': self.batters_faced,
            'runs_allowed': self.runs_allowed,
            'defensive_star_pitches': self.defensive_star_pitches,
            'defensive_stars_used': self.defensive_stars_used,
            'defensive_star_successes': self.defensive_star_successes,
            'defensive_star_chances': self.defensive_star_chances,
            'defensive_stars_chance_won': self.defensive_star_chances_won

            #TODO Add calculated stats
        }
        
