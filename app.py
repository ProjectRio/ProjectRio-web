import os.path
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
DB_URI = 'sqlite:///{}'.format(DB_PATH)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db = SQLAlchemy(app)
ma = Marshmallow(app)

# ===== Models =====
class Game(db.Model):
  id = db.Column(db.String(255), primary_key = True)
  date_time = db.Column(db.String(255))
  ranked = db.Column(db.Integer)
  stadium_id = db.Column(db.String(255))
  # away_player_id = db.Column(db.ForeignKey('user.rio_key'), nullable=True) #One-to-One
  # home_player_id = db.Column(db.ForeignKey('user.rio_key'), nullable=True) #One-to-One
  away_score = db.Column(db.Integer)
  home_score = db.Column(db.Integer)
  innings_selected = db.Column(db.Integer)
  innings_played = db.Column(db.Integer)
  home_captain = db.Column(db.String(255))
  home_roster_0 = db.Column(db.String(255))
  home_roster_1 = db.Column(db.String(255))
  home_roster_2 = db.Column(db.String(255))
  home_roster_3 = db.Column(db.String(255))
  home_roster_4 = db.Column(db.String(255))
  home_roster_5 = db.Column(db.String(255))
  home_roster_6 = db.Column(db.String(255))
  home_roster_7 = db.Column(db.String(255))
  home_roster_8 = db.Column(db.String(255))
  away_captain = db.Column(db.String(255))
  away_roster_0 = db.Column(db.String(255))
  away_roster_1 = db.Column(db.String(255))
  away_roster_2 = db.Column(db.String(255))
  away_roster_3 = db.Column(db.String(255))
  away_roster_4 = db.Column(db.String(255))
  away_roster_5 = db.Column(db.String(255))
  away_roster_6 = db.Column(db.String(255))
  away_roster_7 = db.Column(db.String(255))
  away_roster_8 = db.Column(db.String(255))
  quitter = db.Column(db.Integer) #0=None, 1=Away, 2=Home

  game_character = db.relationship('GameCharacter', backref='game')


class GameCharacter(db.Model):
  GameCharacter_id = db.Column(db.Integer, primary_key=True)
  game_id = db.Column(db.String(255), db.ForeignKey('game.id'), nullable=False)
  team_id = db.Column(db.Integer)
  roster_loc = db.Column(db.Integer) #0-8
  superstar = db.Column(db.Boolean)

  # #Defensive stats
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


# ===== Schema =====
class GameSchema(ma.Schema):
  class Meta:
    fields = (
      'id',
      'date_time',
      'ranked',
      'stadium_id',
      # 'away_player_id',
      # 'home_player_id',
      'away_score',
      'home_score',
      'innings_selected',
      'innings_played',
      'home_captain',
      'home_roster_0',
      'home_roster_1',
      'home_roster_2',
      'home_roster_3',
      'home_roster_4',
      'home_roster_5',
      'home_roster_6',
      'home_roster_7',
      'home_roster_8',
      'away_captain',
      'away_roster_0',
      'away_roster_1',
      'away_roster_2',
      'away_roster_3',
      'away_roster_4',
      'away_roster_5',
      'away_roster_6',
      'away_roster_7',
      'away_roster_8',
      'quitter',
    )

class GameCharacterSchema(ma.Schema):
  class Meta:
    fields = (
      'game_char_id',
      'game_id',
      'team_id',
      'roster_loc',
      'superstar',

      #Defensive stats
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
      #Rio curated stats
      'innings_pitched',

      #Offensive Stats
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


game_schema = GameSchema()
games_schema = GameSchema(many=True)

game_character_schema = GameCharacterSchema()

# ===== API Routes =====
@app.route('/')
def index():
    return 'API online...'

@app.route('/game/', methods=['POST'])
def populate_db():

  game = Game(
    id = request.json['GameID'],
    date_time = request.json['Date'],
    ranked = request.json['Ranked'],
    stadium_id = request.json['StadiumID'],
    away_score = request.json['Away Score'],
    home_score = request.json['Home Score'],
    innings_selected = request.json['Innings Selected'],
    innings_played = request.json['Innings Played'],
    home_captain = request.json['Home Team Captain'],
    home_roster_0 = request.json['Home Team Roster'][0],
    home_roster_1 = request.json['Home Team Roster'][1],
    home_roster_2 = request.json['Home Team Roster'][2],
    home_roster_3 = request.json['Home Team Roster'][3],
    home_roster_4 = request.json['Home Team Roster'][4],
    home_roster_5 = request.json['Home Team Roster'][5],
    home_roster_6 = request.json['Home Team Roster'][6],
    home_roster_7 = request.json['Home Team Roster'][7],
    home_roster_8 = request.json['Home Team Roster'][8],
    away_captain = request.json['Away Team Captain'],
    away_roster_0 = request.json['Away Team Roster'][0],
    away_roster_1 = request.json['Away Team Roster'][1],
    away_roster_2 = request.json['Away Team Roster'][2],
    away_roster_3 = request.json['Away Team Roster'][3],
    away_roster_4 = request.json['Away Team Roster'][4],
    away_roster_5 = request.json['Away Team Roster'][5],
    away_roster_6 = request.json['Away Team Roster'][6],
    away_roster_7 = request.json['Away Team Roster'][7],
    away_roster_8 = request.json['Away Team Roster'][8],
    quitter = request.json['Quitter Team'],
  )
  db.session.add(game)


  # Game Characters
  player_stats = request.json['Player Stats']
  for character in player_stats:
    defensive_stats = character['Defensive Stats']
    offensive_stats = character['Offensive Stats']

    game_character = GameCharacter(
      game = game,
      team_id = 0 if character['Team'] == 'Home' else 1,
      roster_loc = character['RosterID'],
      superstar = True if character['Is Starred'] == 1 else False,

      #Defensive stats
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
      #Rio curated stats
      innings_pitched = defensive_stats['Innings Pitched'],

      #Offensive Stats
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

    db.session.add(game_character)


  db.session.commit()
  return game_schema.jsonify(game)


if __name__ == '__main__':
    app.run(debug=True)
