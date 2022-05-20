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


# FAQ

**Q: How do I use parameters in a URL?**

Add a ? to the end of the Rio Web address and then add your parameters by specifying the parameter, followed by =, then your parameter value. If you want to add another parameter you would add an & between them.

For example, if you wanted to see Mario and Luigi's data-mined base stats using the [/characters/](#characters) endpoint, you would type out the URL, followed by ?, then the parameter _name_ followed by =, followed by Mario, followed by &, followed by name=Luigi.

https://projectrio-api-1.api.projectrio.app/?name=mario&name=luigi

**Q: How do I convert a normal date to unix datetime?**

You can use https://www.unixtimestamp.com/ or a website of your choice to convert MM/DD/YYYY HH:MM to a unix timestamp. 
	
**Q: How do I see my personal stats?**

If you are a Patron you can use your username to retrieve your personal stats from the database. Otherwise, you can view the community's stats as a whole by using GenericHomeUser and GenericAwayUser as usernames. Once we leave Beta account creation will be available to everyone. Check out the [Public Endpoints](#public-endpoints) for more information!


# Thanks for using Rio Web!