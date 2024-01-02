#  Rio Web - A REST Api for Project Rio

[Project Rio](https://www.projectrio.online) | [Patreon](https://www.patreon.com/projectrio) | [MSB Discord Server](https://discord.gg/ZMFCuvwAyH)

Rio Web is a REST Api built to collect and return user stats from the Project Rio client. 

With Rio Web you can... 
- see how many games you've played with Shy Guy(Y)
- see how many strikeouts you've thrown with PM
- see how many games you've won against your friend with Peach as captain
- see how lucky your friend was that one time they won
- prove to your friends that bobbles matter

Please read the [FAQ](#faq) before using the Api.

## Navigation
- [Getting Started](#getting-started)
- [Public Endpoints](#public-endpoints)
	- [Characters](#characters)
	- [Games](#games)
	- [Events](#events)
	- [Plate Data](#plate-data)
	- [Landing Data](#landing-data)
	- [Star Chances](#star-chances)
	- [Pitch Analysis](#pitch-analysis)
	- [Detailed Stats](#detailed-stats)
- [FAQ](#faq)



# Public Endpoints

- [Characters](#characters)
- [Games](#games)
- [Events](#events)
- [Plate Data](#plate-data)
- [Landing Data](#landing-data)
- [Star Chances](#star-chances)
- [Pitch Analysis](#pitch-analysis)
- [Stats](#stats)


## Characters

### <u>Usage</u>

/characters/ returns an array of data-mined stat values for each character. You can narrow down the characters returned by utilizing the name parameter.

```
{
	"characters": [
		{
		"batting_stance": 0,
		"batting_stat_bar": 6,
		"bunting": 35,
		"captain": "True",
		"captain_star_hit_or_pitch": 1,
		"char_id": 0,
		"character_class": 0,
		"charge_hit_power": 64,
		"chemistry_table_id": 1,
		"curve": 53,
		"curve_ball_speed": 130,
		"fast_ball_speed": 168,
		"fielding_arm": 0,
		"fielding_stat_bar": 6,
		"hit_trajectory_mhl": 0,
		"hit_trajectory_mpp": 0,
		"name": "Mario",
		"nice_contact_spot_size": 65,
		"non_captain_star_pitch": 2,
		"non_captain_star_swing": 1,
		"perfect_contact_spot_size": 35,
		"pitching_stat_bar": 6,
		"running_stat_bar": 5,
		"slap_hit_power": 50,
		"speed": 50,
		"starting_addr": "0x8034e9a0",
		"throwing_arm": 60,
		"weight": 2
		}
	]
}
```

### <u>Parameters</u>

- **name**: provide the name of a character you want the data for to narrow down the returned results. This parameter can be passed multiple times.

### <u> Examples </u>

 **1. Get data-mined stats for Mario**:
- To get Mario's data you can use the _name_ parameter.
	- name=Mario

- Add that to the end of the API url and you’re ready to go: 
  - https://api.projectrio.app/characters/?name=Mario

 **2. Get data-mined stats for Mario and Luigi**:
- To get Mario and Luigi's data you can use the _name_ parameter twice.
	- name=Mario
	- name=Luigi
	
- Add these to the end of the API url and you’re ready to go:
  - https://api.projectrio.app/characters/?name=Mario&name=Luigi

 **3. Get data-mined stats for all 54 characters**:
- There's no need to pass any parameters to get all 54 characters back, so just use the following url to get all values.
  - https://api.projectrio.app/characters/

## Games

### <u>Usage</u>

/games/ is the backbone of our more detailed queries. It returns an array of dictionaries containing high-level stats about a game. You can narrow down the returned values by passing different parameters. The parameters you pass using this endpoint can also be passed to other endpoints to refine their sample size.

```
{
	"games": [
		{
		"away_captain": "Birdo",
		"away_score": 0,
		"away_user": "Barth",
		"date_time_end": 1704057552,
		"date_time_start": 1704057014,
		"game_id": 77905544547,
		"game_mode": 52,
		"home_captain": "DK",
		"home_score": 1,
		"home_user": "Blazethh",
		"innings_played": 5,
		"innings_selected": 5,
		"loser_incoming_elo": 1156,
		"loser_result_elo": 1150,
		"stadium": 4,
		"winner_incoming_elo": 1379,
		"winner_result_elo": 1386
		}
	]
}
```

### <u>Parameters</u>
- **limit_games** : specify the number of games to return.
- **username** : provide a username to narrow your search by, e.g. username=GenericHomeUser. Can be passed multiple times to get games from all usernames provided.
- **vs_username** : provide the username of an opponent who **MUST** appear in game against the provided _username_. Can be passed multiple times.
- **exclude_username** : provide a username of opponents who **MUST NOT** appear in results. Can be passed multiple times.
- **captain** : provide a captain name to narrow your search by, e.g. captain=DK. Can be passed multiple times to get games from all usernames provided.
- **vs_captain** : provide the name of a captain who **MUST** appear in game against the provided _captain_. Can be passed multiple times.
- **exclude_captain** : provide a name of a captain who **MUST NOT** appear in results. Can be passed multiple times.
- **tag** : provide the name of a tag to narrow your search, e.g. tag=StarsOffSeason7 will only return games with the StarsOffSeason7 tag. Can be passed multiple times to further refine your search.
- **exclude_tag** : provide the name of a tag to narrow your search, e.g. exclude_tag=StarsOffSeason7 will NOT return games with the StarsOffSeason7 tag.  Can be passed multiple times to further refine your search.
- **start_time** : specify a unix time to start getting games from. Overrides limit_games.
- **end_time** :  specify a unix time to stop getting games at. Overrides limit_games.
- **include_teams**: [0-1] bool if you want the rosters of both teams to be returned for each game. (Note: This will slow the result)

* Tags can be gecko codes or any other house rule. Game modes and communities also have a tags. Some examples of tags are: StarsOffSeason7 (Game Mode), BigBallaSeason5 (Game Mode), DuplicateCharacters (Gecko Code), RemoveSlice (Gecko Code), NationalNetplayLeague (Community).

### <u>Examples</u>

 **1. Get GenericHomeUser's most recent games**:
-  To get GenericHomeUser's most recent game we'll need to use the _username_ and _limit_games_ parameters.
	 - username=GenericHomeUser
	 - limit_games=1
 
- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/games/?limit_games=1&username=GenericHomeUser

**2. Get the 10 most recent games including GenericHomeUser and/or GenericAwayUser** 
-  To get games involving GenericHomeUser and GenericAwayUser we'll have to use a multiple the of _username_ parameter with _limit_games_ to limit the return.
	 - username=GenericHomeUser
	 - username=GenericAwayUser
	 - limit_games=10
 
- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/games/?limit_games=10&username=GenericHomeUser&username=GenericAwayUser

**3. Get GenericHomeUser and GenericAwayUser's 5 most recent StarsOffSeason7 games against each other** 
-  To get GenericHomeUser's games against GenericAwayUser we'll have to use a combination of _username_ and _vs_username_ with _limit_games_ to limit the return and _tag_ to specify we want StarsOffSeason7 games.
	 - username=GenericHomeUser
	 - vs_username=GenericAwayUser
	 - limit_games=5
	 - tag=StarsOffSeason7
 
- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/games/?limit_games=5&username=GenericHomeUser&vs_username=GenericAwayUser&tag=StarsOffSeason7


**4. Get 15 StarsOffSeason7 Normal Netplay games between 05/18 at 10:30pm EST and 05/19 at 1:00am EST between GenericHomeUser and GenericAwayUser** 
-  To specify what times you want games between, you must use unix time. You can use https://www.unixtimestamp.com/ or a different website to convert from MM/DD/YYYY HH:MM to a unix timestamp. 
- To specify we want GenericHomeUser's games against GenericAwayUser we'll have to use a combination of _username_ and _vs_username_ with _limit_games_ to limit the return.
	 - username=GenericHomeUser
	 - vs_username=GenericAwayUser
	 - limit_games=15
	 - start_time=1652927400
	 - end_time=1652936400
	 - tag=StarsOffSeason7
 
- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/games/?limit_games=15&username=GenericHomeUser&vs_username=GenericAwayUser&start_time=1652927400&end_time=1652936400&tag=StarsOffSeason7

## Events

### <u>Usage</u>

/events/ is another foundamental endpoint that can be used in conjunction with games. This endpoint is mostly meant as a helper endpoint for other endpoints to get game data but we've decided to open it to the public as well. It returns just  list of IDs to uniquely identify an event that fits the given parameters

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **games**:           [0-x],   games if not using the game endpoint params
- **limit_events**:    [0-x],	specifies the number of events to return
- **pitcher_char**:    [0-54],  pitcher char ids
- **batter_char**:     [0-54],  batter char ids
- **fielder_char**:    [0-54],  fielder char ids
- **fielder_pos**:     [0-54],  fielder pos
- **contact**:         [0-5],   contact types (0-4: in-game values, 5: no contact)
- **swing**:           [0-4],   swing types ()
- **pitch**:           [0-4],   pitch types (TODO, not implemented)
- **chem_link**:       [0-4],   chemistry on base values
- **pitcher_hand**:    [0-1],   pitchers handedness ()
- **batter_hand**:     [0-1],   batters handedness ()
- **inning**:          [0-50],  innings to collect from
- **half_inning**:     [0-1],   half inning to collect from
- **balls**:           [0-3],   balls
- **strikes**:         [0-2],   strikes
- **outs**:            [0-2],   outs
- **multi_out**:       [0-1],   bool for double plays
- **star_chance**:     [0-1],   bool for star chance
- **users_as_batter**: [0-1],   bool if you want to only get the events for the given users when they are the batter
- **users_as_pitcher** [0-1],   bool if you want to only get the events for the given users when they are the pitcher

### <u>Examples</u>

 **1. Get GenericHomeUser's events from their 5 most recent games**:
-  To get GenericHomeUser's most recent game we'll need to use the _username_ and _limit_games_ parameters. These are game parameters, but used with the event endpoint
	 - username=GenericHomeUser
	 - limit_games=5
 
- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/events/?limit_games=1&username=GenericHomeUser

**2. Get the GenericHomeUser's events from 5 most recent games where they used the charge swing with a righty batter** 
-  Give the parameters for games and then layer on the event parameters _type_of_swing_, _batter_hand_, users_as_batter_. Users as batters says only get the events where the given usernames are batting.
	 - username=GenericHomeUser
	 - limit_games=10
	 - type_of_swing=2
	 - batter_hand=1
	 - users_as_batter=1

- Add these to the end of the API url and you're ready to go:
  - https://api.projectrio.app/events/?limit_games=1&username=GenericHomeUser&type_of_swing=2&batter_hand=1&users_as_batter=1


## Plate Data
**Currently Not Functional**
```
{
    "Data": [
        {
            "batter_char_id": 0,
            "batter_username": "GenericAwayUser",
            "batting_hand": false,
            "event_id": 99936,
            "fielding_hand": false,
            "final_result": 4,
            "game_id": 1464990895,
            "pitch_ball_x_pos": 1.03709,
            "pitch_ball_z_pos": -0.240292,
            "pitch_batter_x_pos": -1.92986,
            "pitch_batter_z_pos": 0.207639,
            "pitch_result": 6,
            "pitcher_char_id": 3,
            "pitcher_username": "GenericHomeUser",
            "type_of_contact": 1,
            "type_of_swing": 1
        },
	]
}
```
### <u>Usage</u>

/plate_data/ does not have any unique parameters, you can mix and match endpoints from `/games/` and `/events/` to narrow down the events to get data for. The endpoint returns the coordinates for the ball around the plate from the pitch.

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)

## Landing Data
```
{
	"Data": [
		{
		"ball_hang_time": 149.0,
		"ball_horiz_angle": 499,
		"ball_max_height": 11.1148,
		"ball_power": 89,
		"ball_vert_angle": 1157,
		"ball_x_contact_pos": -0.134196,
		"ball_x_landing_pos": -7.45722,
		"ball_x_velocity": -0.0650114,
		"ball_y_landing_pos": 3.20591,
		"ball_y_velocity": 0.308325,
		"ball_z_contact_pos": 1.7,
		"ball_z_landing_pos": 34.0878,
		"ball_z_velocity": 0.31422,
		"batter_char_id": 15,
		"batter_username": "MattGree",
		"batting_hand": true,
		"charge_power_down": 0.0,
		"charge_power_up": 0.0,
		"chem_links_ob": 0,
		"contact_absolute": 200.0,
		"contact_quality": 0.0,
		"event_num": 2,
		"fielder_char_id": 2,
		"fielder_jump": 0,
		"fielder_position": 5,
		"fielder_x_pos": -7.80521,
		"fielder_y_pos": 0.0,
		"fielder_z_pos": 35.6002,
		"fielding_hand": false,
		"final_result": 6,
		"frame_of_swing": 7,
		"game_id": 155514857267,
		"manual_select_state": 0,
		"pitcher_char_id": 28,
		"pitcher_username": "duckydonne",
		"rng1": 13017.0,
		"rng2": 5490.0,
		"rng3": 142.0,
		"stick_input": 1,
		"type_of_contact": 4,
		"type_of_swing": 1
		}
	]
}
```

### <u>Usage</u>

`/landing_data/` does not have any unique parameters like `/plate_data/`. This endpoint returns data from events where contact with the ball is made. The data supplied in this endpoint includes all needed data to fully recreate the hit, as well as supplying data on the landing spot of the hit and the fielder who fielded it.

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)

## Star Chances
```
{
	"Data": [
		{
		"batter_win": 28556,
		"eligible_event": 282410,
		"games": 8962,
		"pitcher_win": 45013,
		"star_chances": 73569,
		"total_events": 579112
		}
	]
}
```

### <u>Usage</u>

`/star_chances/` does not have any unique parameters like `/plate_data/`. This endpoint returns data on star chances per inning/half inning and who won them

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)


## Pitch Analysis
**Currently Not Functional**
```
{
    "Data": [
        {
            "count_balls": 0,
            "count_outs": 0,
            "count_strikes": 0,
            "result_ball": 728,
            "result_hbp": 151,
            "result_strike_or_hit": 4870
        },
	]
}
```

### <u>Usage</u>

`/pitch_analysis/` does not have any unique parameters like `/plate_data/`. This endpoint counts how often a pitcher throws result_(a,b,c) given count_(x,y,x). Count is the initial state of the pitch and result are the pitches that are thrown.

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)

## Stats
```
VARIABLE DATA RETURN
```

### <u>Usage</u>

`/stats/` is one of the more complex endpoints provided by the API, it has a variable output depending on the inputs. It can return stats on a per user, a per character, and per swing (for batting stats). In the standard case (with no params) it returns agregate stats of all users and characters. `by_user` will break stats up by user, and `by_char` will break them up by character. These flags can be combined for different levels of details. This endpoint leverages `/games/` and will only analyze games that satisfy the parameters given. 

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)\
- **games**:             [0-x],        game ids to use. If not provided arguments for /games/ endpoint will be expected and used
- **username**:          [],           users to get stats for. All users if blank
- **character**:         [0-54],       character ids to get stats for. All chars if blank
- **by_user**:           [bool],       When true stats will be grouped by user. When false, all users will be separate
- **by_char**:           [bool],       When true stats will be grouped by character. When false, all characters will be separate
- **by_swing**:          [bool],       When true batting stats will be organized by swing type (slap, charge, star). When false, 
                                    all swings will be combined. Only considered for swings
- **exlude_nonfair**:    [bool],       Exlude foul and unknown hits from the return
- **exclude_batting**:   [bool],       Do not return stats from the batting section
- **exclude_pitching**:  [bool],       Do not return stats from the pitching section
- **exclude_misc**:      [bool],       Do not return stats from the misc section
- **exclude_fielding**:  [bool],       Do not return stats from the fielding section

# FAQ

**Q: How do I use parameters in a URL?**

Add a ? to the end of the Rio Web address and then add your parameters by specifying the parameter, followed by =, then your parameter value. If you want to add another parameter you would add an & between them.

For example, if you wanted to see Mario and Luigi's data-mined base stats using the [/characters/](#characters) endpoint, you would type out the URL, followed by ?, then the parameter _name_ followed by =, followed by Mario, followed by &, followed by name=Luigi.

https://api.projectrio.app/characters/?name=mario&name=luigi

**Q: How do I convert a normal date to unix datetime?**

You can use https://www.unixtimestamp.com/ or a website of your choice to convert MM/DD/YYYY HH:MM to a unix timestamp. 
	
**Q: How do I see my personal stats?**

If you have a Project Rio account you can use your username to retrieve your personal stats from the database using the `/stats/` endpoint.

# Thanks for using Rio Web!
