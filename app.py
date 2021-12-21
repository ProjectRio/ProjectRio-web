import os.path
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

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

  def __init__(self,
    id,
    date_time,
    ranked,
    stadium_id,
    # away_player_id,
    # home_player_id,
    away_score,
    home_score,
    innings_selected,
    innings_played,
    home_captain,
    home_roster_0,
    home_roster_1,
    home_roster_2,
    home_roster_3,
    home_roster_4,
    home_roster_5,
    home_roster_6,
    home_roster_7,
    home_roster_8,
    away_captain,
    away_roster_0,
    away_roster_1,
    away_roster_2,
    away_roster_3,
    away_roster_4,
    away_roster_5,
    away_roster_6,
    away_roster_7,
    away_roster_8,
    quitter
  ):
    self.id = id
    self.date_time = date_time
    self.ranked = ranked
    self.stadium_id = stadium_id
    # self.away_player_id = away_player_id
    # self.home_player_id = home_player_id
    self.away_score = away_score
    self.home_score = home_score
    self.innings_selected = innings_selected
    self.innings_played = innings_played
    self.home_captain = home_captain
    self.home_roster_0 = home_roster_0
    self.home_roster_1 = home_roster_1
    self.home_roster_2 = home_roster_2
    self.home_roster_3 = home_roster_3
    self.home_roster_4 = home_roster_4
    self.home_roster_5 = home_roster_5
    self.home_roster_6 = home_roster_6
    self.home_roster_7 = home_roster_7
    self.home_roster_8 = home_roster_8
    self.away_captain = away_captain
    self.away_roster_0 = away_roster_0
    self.away_roster_1 = away_roster_1
    self.away_roster_2 = away_roster_2
    self.away_roster_3 = away_roster_3
    self.away_roster_4 = away_roster_4
    self.away_roster_5 = away_roster_5
    self.away_roster_6 = away_roster_6
    self.away_roster_7 = away_roster_7
    self.away_roster_8 = away_roster_8
    self.quitter = quitter



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


game_schema = GameSchema()
games_schema = GameSchema(many=True)

# ===== API Routes =====
@app.route('/')
def index():
    return 'API online...'

@app.route('/game/', methods=['POST'])
def add_game():
    id = request.json['GameID']
    date_time = request.json['Date']
    ranked = request.json['Ranked']
    stadium_id = request.json['StadiumID']
    away_score = request.json['Away Score']
    home_score = request.json['Home Score']
    innings_selected = request.json['Innings Selected']
    innings_played = request.json['Innings Played']
    home_captain = request.json['Home Team Captain']
    home_roster_0 = request.json['Home Team Roster'][0]
    home_roster_1 = request.json['Home Team Roster'][1]
    home_roster_2 = request.json['Home Team Roster'][2]
    home_roster_3 = request.json['Home Team Roster'][3]
    home_roster_4 = request.json['Home Team Roster'][4]
    home_roster_5 = request.json['Home Team Roster'][5]
    home_roster_6 = request.json['Home Team Roster'][6]
    home_roster_7 = request.json['Home Team Roster'][7]
    home_roster_8 = request.json['Home Team Roster'][8]
    away_captain = request.json['Away Team Captain']
    away_roster_0 = request.json['Away Team Roster'][0]
    away_roster_1 = request.json['Away Team Roster'][1]
    away_roster_2 = request.json['Away Team Roster'][2]
    away_roster_3 = request.json['Away Team Roster'][3]
    away_roster_4 = request.json['Away Team Roster'][4]
    away_roster_5 = request.json['Away Team Roster'][5]
    away_roster_6 = request.json['Away Team Roster'][6]
    away_roster_7 = request.json['Away Team Roster'][7]
    away_roster_8 = request.json['Away Team Roster'][8]
    quitter = request.json['Quitter Team']

    game = Game(
      id,
      date_time,
      ranked,
      stadium_id,
      # away_player_id,
      # home_player_id,
      away_score,
      home_score,
      innings_selected,
      innings_played,
      home_captain,
      home_roster_0,
      home_roster_1,
      home_roster_2,
      home_roster_3,
      home_roster_4,
      home_roster_5,
      home_roster_6,
      home_roster_7,
      home_roster_8,
      away_captain,
      away_roster_0,
      away_roster_1,
      away_roster_2,
      away_roster_3,
      away_roster_4,
      away_roster_5,
      away_roster_6,
      away_roster_7,
      away_roster_8,
      quitter,
    )

    db.session.add(game)
    db.session.commit()

    return game_schema.jsonify(game)


if __name__ == '__main__':
    app.run(debug=True)
