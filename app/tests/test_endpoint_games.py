import requests

'''
/games/ tests
@ Description: Returns games that fit the parameters
@ Params:
    - limit_games - Int of number of games || False to return all
    - username - list of users who appear in games to retreive
    - vs_username - list of users who MUST also appear in the game along with users
    - tag - list of tags to filter by
    - exclude_tag - List of tags to exclude from search

    - start_time - Unix time. Provides the lower (older) end of the range of games to retreive.
    - end_time - Unix time. Provides the lower (older) end of the range of games to retreive. Defaults to now (time of query).
    - exclude_username - list of users to NOT include in query results
    - captain - captain name to appear in games to retrieve
    - vs_captain - captain name who MUST appear in game along with captain
    - exclude_captian -  captain name to EXLCUDE from results
@ Output:
    - List of games and highlevel info based on flags
'''
'''
# External tests
def test_external_endpoint_games_limit_games_param_works_as_expected_1():
    response = requests.get("http://127.0.0.1:5000/games/?limit_games=1")
    data = response.json()
    assert len(data["games"]) == 1

def test_external_endpoint_games_limit_games_param_works_as_expected_5():
    response = requests.get("http://127.0.0.1:5000/games/?limit_games=5")
    data = response.json()
    assert len(data["games"]) == 5

def test_external_endpoint_games_limits_returned_games_to_50_if_no_param_passed():
    response = requests.get("http://127.0.0.1:5000/games/")
    data = response.json()
    assert len(data["games"]) == 50

def test_external_endpoint_games_data_format():
    response = requests.get("http://127.0.0.1:5000/games/?limit_games=1")
    data = response.json()
    all_keys_present = True
    keys = ["Away Captain", "Home Captain", "Away Score", "Home Score", "Away User", "Home User", "Id", "Innings Played", "Innings Selected", "Tags", "date_time_end", "date_time_start"]
    for key in keys:
        if key not in data["games"][0]:
            all_keys_present = False
    assert all_keys_present == True

def test_username_param_for_generic_away_user():
    response = requests.get("http://127.0.0.1:5000/games/?username=GenericAwayUser&limit_games=1")
    data = response.json()
    game = data["games"][0]
    assert game["Away User"] == "GenericAwayUser" 

def test_username_param_for_two_users():
    response = requests.get("http://127.0.0.1:5000/games/?username=GenericAwayUser&username=GenericHomeUser")
    data = response.json()
    games = data["games"]
    games_always_contain_at_least_one_username = True
    for game in games:
        if game['Away User'] != "GenericAwayUser" and game['Home User'] != "GenericHomeUser":
            games_always_contain_at_least_one_username = False
    assert games_always_contain_at_least_one_username == True

def test_vs_username_param():
    response = requests.get("http://127.0.0.1:5000/games/?username=GenericAwayUser&username=PeacockSlayer&vs_username=GenericHomeUser")
    data = response.json()
    games = data["games"]
    games_always_contain_the_vs_user = True
    for game in games:
        if game['Away User'] != "GenericHomeUser" and game['Home User'] != "GenericHomeUser":
            games_always_contain_the_vs_user = False
    assert games_always_contain_the_vs_user == True

def test_games_contain_specified_tag():
    response = requests.get("http://127.0.0.1:5000/games/?tag=ranked&limit_games=10")
    data = response.json()
    games = data["games"]
    games_always_contain_specified_tag = True
    for game in games:
        if "Ranked" not in game["Tags"]:
            games_always_contain_specified_tag = False
    assert games_always_contain_specified_tag == True

def test_games_excludes_specified_tags():
    response = requests.get("http://127.0.0.1:5000/games/?exclude_tag=ranked&limit_games=10")
    data = response.json()
    games = data["games"]
    games_always_excludes_specified_tags = True
    for game in games:
        if "Ranked" in game["Tags"]:
            games_always_excludes_specified_tags = False
    assert games_always_excludes_specified_tags == True

#starttime endtime

# exclude username

# captain vs_captain exclude_captain
'''


# COMMENTED OUT SOME MODEL UPDATES, MAKE SURE TO UNCOMMENT THEM
# Internal tests