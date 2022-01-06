from . import ma

class CharacterSchema(ma.Schema):
  class Meta:
    fields: (
        'char_id',
        'name',
    )

class UserSchema(ma.Schema):
  class Meta:
      fields = (
        'username',
        'email',
        'rio_key'
        )

class UserCharacterStatsSchema(ma.Schema):
  class Meta:
    fields: (
      'id',
      'user_id',
      'char_id',
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

