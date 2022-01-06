from . import ma

class UserSchema(ma.Schema):
  class Meta:
      fields = (
        'username',
        'email',
        'rio_key'
        )

class CharacterSchema(ma.Schema):
  class Meta:
    fields: (
        'char_id',
        'name',
    )
    
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
