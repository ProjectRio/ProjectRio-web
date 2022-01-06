from flask import request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from flask import current_app as app
import secrets
from . import lm, bc
from .models import db, User, Character, Game
from .schemas import UserSchema, GameSchema
import json

# Schemas
user_schema = UserSchema()
game_schema = GameSchema()

# === Initalize Character Tables ===
@app.route('/create_character_tables/', methods = ['POST'])
def create_character_tables():
    f = open('./json/MSB_Stats_dec.json')
    character_list = json.load(f)["Characters"]

    for character in character_list:
        character = Character(
            char_id = character['Char Id'],
            name = character['Char Name']
        )

        db.session.add(character)

    db.session.commit()

    return 'Characters added...'



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
        # characters = Character.query.all()
        # for character in characters:
        #     user_character_stats = UserCharacterStats(
        #         user_id = new_user.id,
        #         char_id = character.char_id,
        #     )

        #     db.session.add(user_character_stats)
        #     db.session.commit()

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



# === Upload Game Data ===
@app.route('/upload_game_data/', methods = ['POST'])
def populate_db():
  #get players from db User table
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
  db.session.commit()

  return 'Successfully added...'
