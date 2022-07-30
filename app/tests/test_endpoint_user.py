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

# External tests
def test_external_endpoint_register_invalid_user():
    non_alpha_numeric_username = {"username": "spaced name", "password": "123password", "email": "test@test.com"}
    response = requests.post("http://127.0.0.1:5000/register", json=non_alpha_numeric_username)
    data = response.json()
    assert response.status_code == 406

#starttime endtime

# exclude username

# captain vs_captain exclude_captain



# COMMENTED OUT SOME MODEL UPDATES, MAKE SURE TO UNCOMMENT THEM
# Internal tests