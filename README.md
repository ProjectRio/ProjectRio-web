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
- [FAQ](#faq)



# Public Endpoints

- [Characters](#characters)
- [Games](#games)


## Characters

### <u>Usage</u>

/characters/ returns an array of data-mined bast stat values for each character. You can narrow down the characters returned by utilizing the name parameter.

```
{
	"characters": [
		{
			"char_id":0,
			"name":"Mario",
			"batting_stance":0,
			"batting_stat_bar":6,
			"bunting":35,
			"captain":"True",
			"captain_star_hit_or_pitch":1,
			"character_class":0,
			"charge_hit_power":64,
			"chemistry_table_id":1,
			"curve":53,
			"curve_ball_speed":130,
			"fast_ball_speed":168,
			"fielding_arm":0,
			"fielding_stat_bar":6,
			"hit_trajectory_mhl":0,
			"hit_trajectory_mpp":0,
			"nice_contact_spot_size":65,
			"non_captain_star_pitch":2,
			"non_captain_star_swing":1,
			"perfect_contact_spot_size":35,
			"pitching_stat_bar":6,
			"running_stat_bar":5,
			"slap_hit_power":50,
			"speed":50,
			"starting_addr":"0x8034e9a0",
			"throwing_arm":60,
			"weight":2
		},
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
  - https://projectrio-api-1.api.projectrio.app/characters/?name=Mario

 **2. Get data-mined stats for Mario and Luigi**:
- To get Mario and Luigi's data you can use the _name_ parameter twice.
	- name=Mario
	- name=Luigi
	
- Add these to the end of the API url and you’re ready to go:
  - https://projectrio-api-1.api.projectrio.app/characters/?name=Mario&name=Luigi

 **3. Get data-mined stats for all 54 characters**:
- There's no need to pass any parameters to get all 54 characters back, so just use the following url to get all values.
  - https://projectrio-api-1.api.projectrio.app/characters/

## Games

### <u>Usage</u>

/games/ is the backbone of our more detailed queries. It returns an array of dictionaries containing high-level stats about a game. You can narrow down the returned values by passing different parameters. The parameters you pass using this endpoint can also be passed to other endpoints to refine their sample size.

```
{
	"games":[
		{
			"Away Captain":"Bowser",
			"Away Score":14,
			"Away User":"GenericAwayUser",
			"Home Captain":"Yoshi",
			"Home Score":0,
			"Home User":"GenericHomeUser",
			"Id":2503858538,
			"Innings Played":7,
			"Innings Selected":9,
			"Tags":["Unranked","Normal","Netplay"],
			"date_time_end":1652965941,
			"date_time_start":1652964753
		}
	]
}
```

### <u>Parameters</u>
- **recent** : specify the number of games to return.
- **username** : provide a username to narrow your search by, e.g. username=GenericHomeUser. Can be passed multiple times to get games from all usernames provided.
- **vs_username** : provide the username of an opponent who **MUST** appear in game against the provided _username_. Can be passed multiple times.
- **exclude_username** : provide a username of opponents who **MUST NOT** appear in results. Can be passed multiple times.
- **captain** : provide a captain name to narrow your search by, e.g. captain=DK. Can be passed multiple times to get games from all usernames provided.
- **vs_captain** : provide the name of a captain who **MUST** appear in game against the provided _captain_. Can be passed multiple times.
- **exclude_captain** : provide a name of a captain who **MUST NOT** appear in results. Can be passed multiple times.
- **tag** : provide the name of a tag to narrow your search, e.g. tag=Ranked will only return games with the ranked tag. Can be passed multiple times to further refine your search.
- **exclude_tag** : provide the name of a tag to narrow your search, e.g. exclude_tag=Ranked will NOT return games with the ranked tag.  Can be passed multiple times to further refine your search.
- **start_time** : specify a unix time to start getting games from. Overrides recent.
- **end_time** :  specify a unix time to stop getting games at. Overrides recent.

_*list of tags currently available: Ranked, Unranked, Normal, Superstar, Local, Netplay_

### <u>Examples</u>

 **1. Get GenericHomeUser's 5 most recent games**:
-  To get GenericHomeUser's most recent game we'll need to use the _username_ and _recent_ parameters.
	 - username=GenericHomeUser
	 - recent=1
 
- Add these to the end of the API url and you're ready to go:
  - https://projectrio-api-1.api.projectrio.app/games/?recent=1&username=GenericHomeUser

**2. Get the 5 most recent games including GenericHomeUser and/or GenericAwayUser** 
-  To get GenericHomeUser's games against GenericAwayUser we'll have to use a combination of _username_ and _vs_username_ with _recent_ to limit the return.
	 - username=GenericHomeUser
	 - username=GenericAwayUser
	 - recent=10
 
- Add these to the end of the API url and you're ready to go:
  - https://projectrio-api-1.api.projectrio.app/games/?recent=10&username=GenericHomeUser&username=GenericAwayUser

**3. Get GenericHomeUser and GenericAwayUser's 5 most recent Ranked games against each other** 
-  To get GenericHomeUser's games against GenericAwayUser we'll have to use a combination of _username_ and _vs_username_ with _recent_ to limit the return and _tag_ to specify we want Ranked games.
	 - username=GenericHomeUser
	 - vs_username=GenericAwayUser
	 - recent=5
	 - tag=Ranked
 
- Add these to the end of the API url and you're ready to go:
  - https://projectrio-api-1.api.projectrio.app/games/?recent=5&username=GenericHomeUser&vs_username=GenericAwayUser&tag=Ranked


**4. Get 15 Ranked Normal Netplay games between 05/18 at 10:30pm EST and 05/19 at 1:00am EST between GenericHomeUser and GenericAwayUser** 
-  To specify what times you want games between, you must use unix time. You can use https://www.unixtimestamp.com/ or a different website to convert from MM/DD/YYYY HH:MM to a unix timestamp. 
- To specify we want GenericHomeUser's games against GenericAwayUser we'll have to use a combination of _username_ and _vs_username_ with _recent_ to limit the return.
	 - username=GenericHomeUser
	 - vs_username=GenericAwayUser
	 - recent=15
	 - start_time=1652927400
	 - end_time=1652936400
	 - tag=Ranked
	 - tag=Normal
	 - tag=Netplay
 
- Add these to the end of the API url and you're ready to go:
  - https://projectrio-api-1.api.projectrio.app/games/?recent=15&username=GenericHomeUser&vs_username=GenericAwayUser&start_time=1652927400&end_time=1652936400&tag=Ranked&tag=Normal&tag=Netplay

## Events

### <u>Usage</u>

/events/ is another foundamental endpoint that can be used in conjunction with games. This endpoint is mostly meant as a helper endpoint for other endpoints to get game data but we've decided to open it to the public as well. It returns just  list of IDs to uniquely identify an event that fits the given parameters

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **games**:           [0-x],   games if not using the game endpoint params
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
-  To get GenericHomeUser's most recent game we'll need to use the _username_ and _recent_ parameters. These are game parameters, but used with the event endpoint
	 - username=GenericHomeUser
	 - recent=5
 
- Add these to the end of the API url and you're ready to go:
  - https://projectrio-api-1.api.projectrio.app/events/?recent=1&username=GenericHomeUser

**2. Get the GenericHomeUser's events from 5 most recent games where they used the charge swing with a righty batter** 
-  Give the parameters for games and then layer on the event parameters _type_of_swing_, _batter_hand_, users_as_batter_. Users as batters says only get the events where the given usernames are batting.
	 - username=GenericHomeUser
	 - recent=10
	 - type_of_swing=2
	 - batter_hand=1
	 - users_as_batter=1

## Plate Data

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
            "batter_char_id": 0,
            "batter_username": "GenericAwayUser",
            "batting_hand": false,
            "event_id": 99936,
            "fielder_char_id": 3,
            "fielder_jump": 1,
            "fielder_position": 3,
            "fielding_hand": false,
            "final_result": 4,
            "game_id": 1464990895,
            "manual_select_state": 0,
            "pitcher_username": "GenericHomeUser",
            "stick_input": 0,
            "type_of_contact": 1,
            "type_of_swing": 1,
            "x_pos": 3.59528,
            "x_velo": 0.0426119,
            "y_pos": 0.0,
            "y_velo": 0.0522467,
            "z_pos": 37.1124,
            "z_velo": 0.616323
        },
	]
}
```

### <u>Usage</u>

`/landing_data/` does not have any unique parameters like `/plate_data/`. This endpoint returns data on the landing spot of the hit and the fielder who fielded

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)

## Star Chances
```
{
    "Data": [
		{
            "batter_win": 382,
            "elligible_event": 0,
            "games": 215,
            "half_inning": 0,
            "inning": 1,
            "pitcher_win": 667,
            "star_chances": 85
        },
	]
}
```

### <u>Usage</u>

`/star_chances/` does not have any unique parameters like `/plate_data/`. This endpoint returns data on star chances per inning/half inning and who won them

### <u>Parameters</u>
- **Game params**:     Params for /games/ (tags/users/date/etc)
- **Event params**:    Params for /events/ (swing_type/inning/)


## Pitch Analysis
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

## Detailed Stats
```
VARIABLE DATA RETURN
```

### <u>Usage</u>

`/detailed_stats/` is one of the more complex endpoints provided by the API, it has a variable output depending on the inputs. It can return stats on a per user, a per character, and per swing (for batting stats). In the standard case (with no params) it returns agregate stats of all users and characters. `by_user` will break stats up by user, and `by_char` will break them up by character. These flags can be combined for different levels of details. This endpoint leverages `/games/` and will only analyze games that satisfy the parameters given. 

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

https://projectrio-api-1.api.projectrio.app/characters/?name=mario&name=luigi

**Q: How do I convert a normal date to unix datetime?**

You can use https://www.unixtimestamp.com/ or a website of your choice to convert MM/DD/YYYY HH:MM to a unix timestamp. 
	
**Q: How do I see my personal stats?**

If you are a Patron you can use your username to retrieve your personal stats from the database. Otherwise, you can view the community's stats as a whole by using GenericHomeUser and GenericAwayUser as usernames. Once we leave Beta account creation will be available to everyone. Check out the [Public Endpoints](#public-endpoints) for more information!


# Thanks for using Rio Web!