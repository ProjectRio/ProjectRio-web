from . import db, bc
from flask_login import UserMixin
import secrets

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer,     primary_key=True)
    username = db.Column(db.String(64),  unique = True)
    email    = db.Column(db.String(120), unique = True)
    password = db.Column(db.String(500))
    rio_key  = db.Column(db.String(50), unique = True)

    # user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_user')
    away_games = db.relationship('Game', foreign_keys = 'Game.away_player_id', backref = 'games_as_away_player')
    home_games = db.relationship('Game', foreign_keys = 'Game.home_player_id', backref = 'games_as_home_player')

    def __init__(self, in_username, in_email, in_password):
        self.username = in_username
        self.email    = in_email
        self.password = bc.generate_password_hash(in_password)
        self.rio_key  = secrets.token_urlsafe(32)


class Character(db.Model):
    char_id = db.Column(db.String(4), primary_key=True)
    name = db.Column(db.String(16))

    # user_character_stats = db.relationship('UserCharacterStats', backref = 'user_character_stats_from_character')
    # character_game_summary = db.relationship('CharacterGameSummary', backref = 'character_game_summary_from_character')


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

    # character_game_summary = db.relationship('CharacterGameSummary', backref='game')