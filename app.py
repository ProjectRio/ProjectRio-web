import os
import struct
import secrets

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

# ===== Setup =====
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+ \
                os.path.join(basedir, 'db.sqlite3')

db = SQLAlchemy(app)
ma = Marshmallow(app)


# ===== Database Models =====
class User(db.Model):
    # PK User_id auto created by SQLAlchemy
    username = db.Column(db.String(100))
    rio_key = db.Column(db.String(32), primary_key=True)

class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key=True)
    date_time = db.Column(db.String(255))
    stadium_id = db.Column(db.Integer)
    netplay = db.Column(db.Boolean)
    ranked = db.Column(db.Integer)
    
    away_player_id = db.Column(db.ForeignKey('user.rio_key'), nullable=True) #One-to-One
    home_player_id = db.Column(db.ForeignKey('user.rio_key'), nullable=True) #One-to-One

    away_captain = db.Column(db.Integer)
    home_captain = db.Column(db.Integer)

    away_roster_0 = db.Column(db.Integer)
    away_roster_1 = db.Column(db.Integer)
    away_roster_2 = db.Column(db.Integer)
    away_roster_3 = db.Column(db.Integer)
    away_roster_4 = db.Column(db.Integer)
    away_roster_5 = db.Column(db.Integer)
    away_roster_6 = db.Column(db.Integer)
    away_roster_7 = db.Column(db.Integer)
    away_roster_8 = db.Column(db.Integer)

    home_roster_0 = db.Column(db.Integer)
    home_roster_1 = db.Column(db.Integer)
    home_roster_2 = db.Column(db.Integer)
    home_roster_3 = db.Column(db.Integer)
    home_roster_4 = db.Column(db.Integer)
    home_roster_5 = db.Column(db.Integer)
    home_roster_6 = db.Column(db.Integer)
    home_roster_7 = db.Column(db.Integer)
    home_roster_8 = db.Column(db.Integer)

    away_score = db.Column(db.Integer)
    home_score = db.Column(db.Integer)

    innings_selected = db.Column(db.Integer)
    innings_played = db.Column(db.Integer)

    quitter = db.Column(db.Integer) #0=None, 1=Away, 2=Home

class GameCharacter(db.Model):
    #GameCharacter_id auto created by SQLAlchemy
    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'), nullable=False)
    team_id = db.Column(db.Integer) #0=Away, 1=Home
    roster_loc = db.Column(db.Integer) #0-8
    char_id = db.Column(db.Integer) #TODO Convert to foreign key for character info table
    superstar = db.Column(db.Boolean)

    #Defensive stats
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
    #Rio curated stats
    innings_pitched = db.Column(db.Integer)

    #Offensive Stats
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

class PitchSummary(db.Model):
    #PitchSummary_id auto created by SQLAlchemy   
    batter_id = db.Column(db.Integer, db.ForeignKey('gamecharacter.id'))
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
    pitcher_id = db.Column(db.Integer, db.ForeignKey('gamecharacter.id'))
    pitcher_handedness = db.Column(db.Integer)
    pitch_type = db.Column(db.Integer)
    charge_pitch_type = db.Column(db.Integer)
    star_pitch = db.Column(db.Integer)
    pitch_speed = db.Column(db.Integer)    
    rbi = db.Column(db.Integer)
    num_outs = db.Column(db.Integer)
    result_inferred = db.Column(db.String(100))
    result_game = db.Column(db.Integer)

class ContactSummary(db.Model):
    pitch_id = db.Column(db.Integer, db.ForeignKey('pitchsummary.id'))
    type_of_contact = db.Column(db.Integer)
    charge_power_up = db.Column(db.Float)
    charge_power_down = db.Column(db.Float)
    star_swing = db.Column(db.Integer)
    star_swing_five_star = db.Column(db.Integer)
    input_direction = db.Column(db.Integer)
    batter_handedness = db.Column(db.Integer)
    hit_by_pitch = db.Column(db.Integer)
    ball_angle = db.Column(db.Integer)
    ball_horiz_power = db.Column(db.Integer)
    ball_vert_power = db.Column(db.Integer)
    ball_x_velocity = db.Column(db.Float)
    ball_y_velocity = db.Column(db.Float)
    ball_z_velocity = db.Column(db.Float)
    ball_x_pos = db.Column(db.Float)
    ball_y_pos = db.Column(db.Float)
    ball_z_pos = db.Column(db.Float)

class FieldingSummary(db.Model):
    contact_id = db.Column(db.Integer, db.ForeignKey('contactsummary.id'))
    char_id = db.Column(db.Integer)
    position = db.Column(db.Integer) #0-8. 0=P, 1=C, ... 8=RF

class UserCharacterStats(db.Model):
    user = db.Column(db.ForeignKey('user.rio_key'), nullable=False)
    char_id = db.Column(db.Integer) # TODO change to FK to char table
    superstar = db.Column(db.Boolean)
    games = db.Column(db.Integer)
    captained = db.Column(db.Integer)
    at_bats = db.Column(db.Integer)
    hits = db.Column(db.Integer)
    walks = db.Column(db.Integer)
    batting_avg = db.Column(db.Float) #Calculated
    obp = db.Column(db.Float) #Calculated
    slg = db.Column(db.Float) #Calculated
    ops = db.Column(db.Float) #Calculated
    rbi  = db.Column(db.Integer)
    bases_stolen = db.Column(db.Integer)
    offense_star_swings = db.Column(db.Integer)
    offense_stars_used = db.Column(db.Integer)
    offense_stars_success = db.Column(db.Integer)
    offense_star_chances = db.Column(db.Integer)
    offense_star_chances_won  = db.Column(db.Integer)#Calculated
    innings_pitched = db.Column(db.Integer)
    batters_faced = db.Column(db.Integer)
    strikeouts = db.Column(db.Integer)
    runs_allowed = db.Column(db.Integer)
    era = db.Column(db.Float) #Calculated
    defensive_star_pitches = db.Column(db.Integer)
    defensive_stars_used = db.Column(db.Integer)
    defensive_star_success = db.Column(db.Integer)
    defensive_star_chances = db.Column(db.Integer)
    defensive_star_chance_won  = db.Column(db.Integer) #Calculated

#TODO class CharacterInfo(db.Models): #Transform stat sheet into database table


# ===== Marshamllow Schemas =====
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

class GameSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Game

class GameCharacterSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GameCharacter

class PitchSummarySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PitchSummary

class ContactSummarySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ContactSummary

class FieldingSummarySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FieldingSummary

class UserCharacterStatsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserCharacterStats

#TODO add CharacterInfo model
#class CharacterInfoSchema(ma.SQLAlchemyAutoSchema):
#    class Meta:
#        model = CharacterInfo


# ===== API Routes =====