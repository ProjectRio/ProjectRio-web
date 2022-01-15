from . import db, bc
from flask_login import UserMixin
import secrets

class Character(db.Model):
    char_id = db.Column(db.Integer, primary_key=True)
    chemistry_table_id = db.Column(db.ForeignKey('chemistry_table.id'), nullable = False)
    name = db.Column(db.String(16))
    starting_addr = db.Column(db.String(16))
    curve_ball_speed = db.Column(db.String(3))
    fast_ball_speed = db.Column(db.String(3))
    curve = db.Column(db.String(2))
    fielding_arm = db.Column(db.String(1))
    batting_stance = db.Column(db.String(1))
    nice_contact_spot_size = db.Column(db.String(3))
    perfect_contact_spot_size = db.Column(db.String(3))
    slap_hit_power = db.Column(db.String(2))
    charge_hit_power = db.Column(db.String(3))
    bunting = db.Column(db.String(2))
    hit_trajectory_mpp = db.Column(db.String(2))
    hit_trajectory_mhl = db.Column(db.String(2))
    speed = db.Column(db.String(3))
    throwing_arm = db.Column(db.String(3))
    character_class = db.Column(db.String(3))
    weight = db.Column(db.String(3))
    captain = db.Column(db.String(1))
    captain_star_hit_or_pitch = db.Column(db.String(1))
    non_captain_star_swing = db.Column(db.String(1))
    non_captain_star_pitch = db.Column(db.String(1))
    batting_stat_bar = db.Column(db.String(1))
    pitching_stat_bar = db.Column(db.String(1))
    running_stat_bar = db.Column(db.String(1))
    fielding_stat_bar = db.Column(db.String(1))
    
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
    mario = db.Column(db.String(3))
    luigi = db.Column(db.String(3))
    dk = db.Column(db.String(3))
    diddy = db.Column(db.String(3))
    peach = db.Column(db.String(3))
    daisy = db.Column(db.String(3))
    yoshi = db.Column(db.String(3))
    baby_mario = db.Column(db.String(3))
    baby_luigi = db.Column(db.String(3))
    bowser = db.Column(db.String(3))
    wario = db.Column(db.String(3))
    waluigi = db.Column(db.String(3))
    koopa_r = db.Column(db.String(3))
    toad_r = db.Column(db.String(3))
    boo = db.Column(db.String(3))
    toadette = db.Column(db.String(3))
    shy_guy_r = db.Column(db.String(3))
    birdo = db.Column(db.String(3))
    monty = db.Column(db.String(3))
    bowser_jr = db.Column(db.String(3))
    paratroopa_r = db.Column(db.String(3))
    pianta_b = db.Column(db.String(3))
    pianta_r = db.Column(db.String(3))
    pianta_y = db.Column(db.String(3))
    noki_b = db.Column(db.String(3))
    noki_r = db.Column(db.String(3))
    noki_g = db.Column(db.String(3))
    bro_h = db.Column(db.String(3))
    toadsworth = db.Column(db.String(3))
    toad_b = db.Column(db.String(3))
    toad_y = db.Column(db.String(3))
    toad_g = db.Column(db.String(3))
    toad_p = db.Column(db.String(3))
    magikoopa_b = db.Column(db.String(3))
    magikoopa_r = db.Column(db.String(3))
    magikoopa_g = db.Column(db.String(3))
    magikoopa_y = db.Column(db.String(3))
    king_boo = db.Column(db.String(3))
    petey = db.Column(db.String(3))
    dixie = db.Column(db.String(3))
    goomba = db.Column(db.String(3))
    paragoomba = db.Column(db.String(3))
    koopa_g = db.Column(db.String(3))
    paratroopa_g = db.Column(db.String(3))
    shy_guy_b = db.Column(db.String(3))
    shy_guy_y = db.Column(db.String(3))
    shy_guy_g = db.Column(db.String(3))
    shy_guy_bk = db.Column(db.String(3))
    dry_bones_gy = db.Column(db.String(3))
    dry_bones_g = db.Column(db.String(3))
    dry_bones_r = db.Column(db.String(3))
    dry_bones_b = db.Column(db.String(3))
    bro_f = db.Column(db.String(3))
    bro_b = db.Column(db.String(3))

    character = db.relationship('Character', backref = 'character')

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer,     primary_key=True)
    username = db.Column(db.String(64),  unique = True)
    email    = db.Column(db.String(120), unique = True)
    password = db.Column(db.String(500))
    rio_key  = db.Column(db.String(50), unique = True)
    private = db.Column(db.Boolean)

    user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_user', lazy = 'dynamic')
    away_games = db.relationship('Game', foreign_keys = 'Game.away_player_id', backref = 'games_as_away_player')
    home_games = db.relationship('Game', foreign_keys = 'Game.home_player_id', backref = 'games_as_home_player')

    def __init__(self, in_username, in_email, in_password):
        self.username = in_username
        self.email    = in_email
        self.password = bc.generate_password_hash(in_password)
        self.rio_key  = secrets.token_urlsafe(32)
        self.private = True

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

class CharacterGameSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'), nullable=False)
    char_id = db.Column(db.Integer, db.ForeignKey('character.char_id'), nullable=False)
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
