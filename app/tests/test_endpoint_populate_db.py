import json
import os
import requests
from pprint import pprint
from helpers import *
from connection import Connection

db = Connection()

def test_populate_db():
    wipe_db()

    print(os.getcwd())

    # Make official community
    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success == True
    assert sponsor.add_to_group('admin') == True

    # Assert community IS created, sponsor is admin
    community = Community(sponsor, True, False, False)
    assert community.success == True

    # Make Tag
    tag = Tag(community.founder, community)
    tag.create()

    # Make TagSet
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()

    # Refresh to get tags
    community.refresh()

    # Two players
    player_away = User()
    player_away.register()

    player_home = User()
    player_home.register()

    # Read dummy game
    data = dict()
    tag_list = list()

    with open('app/tests/data/20230315T212151_MaybeJon-Vs-PeacockSlayer_1867546158.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['TagSetID'] = tagset.pk

    # Submit game, nonverified users
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)
    assert response.status_code == 411
    
    # Submit game, verified users
    player_away.verify_user()
    player_home.verify_user()
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)
    assert response.status_code == 200

    # Test the ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()

    # Home Player wins this game. Check rating is higher
    away_user_rating = data[player_away.username]['rating']
    home_user_rating = data[player_home.username]['rating']
    assert away_user_rating < home_user_rating

    # ============================================================
    # Now check manual submit
    # Give the away player from the file 2 wins. Elo should be higher than home
    game1 = {'winner_username': player_away.username, 'winner_score': 10, 
             'loser_username': player_home.username, 'loser_score': 0}
    game2 = {'winner_username': player_away.username, 'winner_score': 10, 
             'loser_username': player_home.username, 'loser_score': 0}
    game1['tag_set'] = tagset.name
    game2['tag_set'] = tagset.name
    game1['submitter_rio_key'] = player_away.rk
    game2['submitter_rio_key'] = player_away.rk

    game1_response = requests.post("http://127.0.0.1:5000/manual_submit_game/", json=game1)
    assert game1_response.status_code == 200

    game2_response = requests.post("http://127.0.0.1:5000/manual_submit_game/", json=game2)
    assert game2_response.status_code == 200

    # No change until the players accept
    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

    # Confirm/Reject the games
    game1_winner_confirm = {'GameHistoryID': game1_response.json()['GameHistoryID'], 'Rio Key': player_away.rk, 'Accept': 1}
    game1_loser_reject   = {'GameHistoryID': game1_response.json()['GameHistoryID'], 'Rio Key': player_home.rk, 'Accept': 0}
    game1_loser_confirm  = {'GameHistoryID': game1_response.json()['GameHistoryID'], 'Rio Key': player_home.rk, 'Accept': 1}

    # Winner confirm game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game1_winner_confirm)
    assert response.status_code == 200

    # Loser Reject game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game1_loser_reject)
    assert response.status_code == 200

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

    # Loser confirm game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game1_loser_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] != away_user_rating
    assert data[player_home.username]['rating'] != home_user_rating


    # ============================================================
    # Game 2
    game2_winner_confirm = {'GameHistoryID': game2_response.json()['GameHistoryID'], 'Rio Key': player_away.rk, 'Accept': 1}
    game2_loser_confirm  = {'GameHistoryID': game2_response.json()['GameHistoryID'], 'Rio Key': player_home.rk, 'Accept': 1}

    # Winner confirm game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game2_winner_confirm)
    assert response.status_code == 200

    # Loser confirm game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game2_loser_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] > data[player_home.username]['rating']

    # ============================================================
    # Snapshot player ratings
    away_user_rating = data[player_away.username]['rating'] 
    home_user_rating = data[player_home.username]['rating']

    # Submit game as admin, check that it changes the ELOs
    game3 = {'winner_username': player_away.username, 'winner_score': 10, 
             'loser_username': player_home.username, 'loser_score': 0}
    game3['tag_set'] = tagset.name
    game3['submitter_rio_key'] = sponsor.rk

    game3_response = requests.post("http://127.0.0.1:5000/manual_submit_game/", json=game3)
    assert game3_response.status_code == 200

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] != away_user_rating
    assert data[player_home.username]['rating'] != home_user_rating

    # ============================================================
    # Submit game as user, confirm as admin

    # Snapshot player ratings
    away_user_rating = data[player_away.username]['rating'] 
    home_user_rating = data[player_home.username]['rating']

    # Submit game as admin, check that it changes the ELOs
    game4 = {'winner_username': player_away.username, 'winner_score': 10, 
             'loser_username': player_home.username, 'loser_score': 0}
    game4['tag_set'] = tagset.name
    game4['submitter_rio_key'] = player_away.rk

    game4_response = requests.post("http://127.0.0.1:5000/manual_submit_game/", json=game4)
    assert game4_response.status_code == 200

    # Inspect Ladder - should be no change
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

    # Game 4 - admin confirm
    game4_admin_confirm = {'GameHistoryID': game4_response.json()['GameHistoryID'], 'Rio Key': sponsor.rk, 'Accept': 1}

    # Admin confirm game
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game4_admin_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] != away_user_rating
    assert data[player_home.username]['rating'] != home_user_rating

    # ============================================================

    # Snapshot player ratings
    away_user_rating = data[player_away.username]['rating'] 
    home_user_rating = data[player_home.username]['rating']


    # Admin reconfirm game - shouldn't update elo
    response = requests.post("http://127.0.0.1:5000/update_game_status/", json=game4_admin_confirm)
    assert response.status_code == 411

    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

def test_ongoing_game():
    wipe_db()

    # === SETUP ===
    # Make official community
    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success == True
    assert sponsor.add_to_group('admin') == True

    # Assert community IS created, sponsor is admin
    community = Community(sponsor, True, False, False)
    assert community.success == True

    # Make Tag
    tag = Tag(community.founder, community)
    tag.create()

    # Make TagSet
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()

    # Refresh to get tags
    community.refresh()

    # Two players
    player_away = User()
    player_away.register()

    player_home = User()
    player_home.register()
    # === END SETUP ===

    #Send a game
    game = {
        'GameID': '1867546158',
        'Away Player': player_away.rk,
        'Home Player': player_home.rk,
        'TagSetID': tagset.pk,
        'Away Captain': 0,
        'Home Captain': 2,
        'Date - Start': 1121904000,
        'StadiumID': 0,
        'Inning': 0,
        'Half Inning': 0,
        'Away Score': 0,
        'Home Score': 0,
        "Away Roster 0 CharID": 0,
        "Away Roster 1 CharID": 0,
        "Away Roster 2 CharID": 0,
        "Away Roster 3 CharID": 0,
        "Away Roster 4 CharID": 0,
        "Away Roster 5 CharID": 0,
        "Away Roster 6 CharID": 0,
        "Away Roster 7 CharID": 0,
        "Away Roster 8 CharID": 0,
        "Home Roster 0 CharID": 0,
        "Home Roster 1 CharID": 0,
        "Home Roster 2 CharID": 0,
        "Home Roster 3 CharID": 0,
        "Home Roster 4 CharID": 0,
        "Home Roster 5 CharID": 0,
        "Home Roster 6 CharID": 0,
        "Home Roster 7 CharID": 0,
        "Home Roster 8 CharID": 0,
        'Away Stars': 5,
        'Home Stars': 4,
        'Outs': 0,
        'Runner 1B': False,
        'Runner 2B': False,
        'Runner 3B': False,
        'Batter': 0, 
        'Pitcher': 0
    }

    # Start Game, uverified users
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game)
    assert response.status_code == 411

    player_away.verify_user()
    player_home.verify_user()

    # Start Game, verified users
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game)
    assert response.status_code == 200


    #Make sure game is there
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 1

    #Update game
    game_update = {
        'GameID': '1867546158',
        'Inning': 1,
        'Half Inning': 0,
        'Away Score': 2,
        'Home Score': 3,
        'Away Stars': 1,
        'Home Stars': 2,
        'Outs': 1,
        'Runner 1B': True,
        'Runner 2B': False,
        'Runner 3B': True,
        'Batter': 2, 
        'Pitcher': 5
    }
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game_update)
    assert response.status_code == 200

    #Make sure game is there
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert response.json()['ongoing_games'][0]['inning'] == 1

    with open('app/tests/data/20230315T212151_MaybeJon-Vs-PeacockSlayer_1867546158.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['TagSetID'] = tagset.pk
    
    # Submit game, make sure ongoing game was cleared
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)
    assert response.status_code == 200
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 0

def test_ongoing_game_with_man_submit():
    wipe_db()

    # === SETUP ===
    # Make official community
    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success == True
    assert sponsor.add_to_group('admin') == True

    # Assert community IS created, sponsor is admin
    community = Community(sponsor, True, False, False)
    assert community.success == True

    # Make Tag
    tag = Tag(community.founder, community)
    tag.create()

    # Make TagSet
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()

    # Refresh to get tags
    community.refresh()

    # Two players
    player_away = User()
    player_away.register()

    player_home = User()
    player_home.register()

    #Get the tag id of the tagset tag
    tag_list = list()
    for tag in tagset.tags.values():
        if tag.name == tagset.name:
            tag_list.append(tag.pk)
    # === END SETUP ===

    #Send a game
    game = {
        'GameID': '1867546158',
        'Away Player': player_away.rk,
        'Home Player': player_home.rk,
        'TagSetID': tagset.pk,
        'Away Captain': 0,
        'Home Captain': 2,
        'Date - Start': 1121904000,
        'StadiumID': 0,
        'Inning': 0,
        'Half Inning': 0,
        'Away Score': 0,
        'Home Score': 0,
        "Away Roster 0 CharID": 0,
        "Away Roster 1 CharID": 0,
        "Away Roster 2 CharID": 0,
        "Away Roster 3 CharID": 0,
        "Away Roster 4 CharID": 0,
        "Away Roster 5 CharID": 0,
        "Away Roster 6 CharID": 0,
        "Away Roster 7 CharID": 0,
        "Away Roster 8 CharID": 0,
        "Home Roster 0 CharID": 0,
        "Home Roster 1 CharID": 0,
        "Home Roster 2 CharID": 0,
        "Home Roster 3 CharID": 0,
        "Home Roster 4 CharID": 0,
        "Home Roster 5 CharID": 0,
        "Home Roster 6 CharID": 0,
        "Home Roster 7 CharID": 0,
        "Home Roster 8 CharID": 0,
        'Away Stars': 5,
        'Home Stars': 4,
        'Outs': 0,
        'Runner 1B': False,
        'Runner 2B': False,
        'Runner 3B': False,
        'Batter': 0, 
        'Pitcher': 0
    }

    # Start Game, uverified users
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game)
    assert response.status_code == 411

    player_away.verify_user()
    player_home.verify_user()

    # Start Game, verified users
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game)
    assert response.status_code == 200


    #Make sure game is there
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 1

    #Update game
    game_update = {
        'GameID': '1867546158',
        'Inning': 1,
        'Half Inning': 0,
        'Away Score': 2,
        'Home Score': 3,
        'Away Stars': 1,
        'Home Stars': 2,
        'Outs': 1,
        'Runner 1B': True,
        'Runner 2B': False,
        'Runner 3B': True,
        'Batter': 2, 
        'Pitcher': 5
    }
    response = requests.post("http://127.0.0.1:5000/populate_db/ongoing_game/", json=game_update)
    assert response.status_code == 200

    
    # ============================================================
    # Now manual submit
    # Give the away player from the file 2 wins. Elo should be higher than home
    man_game = {'winner_username': player_away.username, 'winner_score': 10, 
             'loser_username': player_home.username, 'loser_score': 0}
    man_game['tag_set'] = tagset.name
    man_game['game_id_hex'] = '1867546158'
    man_game['submitter_rio_key'] = player_away.rk

    #Confirm Ongoing game is still there
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 1

    man_game_response = requests.post("http://127.0.0.1:5000/manual_submit_game/", json=man_game)
    assert man_game_response.status_code == 200
    response = requests.get("http://127.0.0.1:5000/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 0


'''
def test_populate_db():
    wipe_db()

    print(os.getcwd())

    # Make official community
    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success == True
    assert sponsor.add_to_group('admin') == True

    # Assert community IS created, sponsor is admin
    community = Community(sponsor, True, False, False)
    assert community.success == True

    # Make Tag
    tag = Tag(community.founder, community)
    tag.create()

    # Make TagSet
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()

    # Refresh to get tags
    community.refresh()

    # Two players
    player_away = User()
    player_away.register()

    player_home = User()
    player_home.register()

    # Read dummy game
    data = dict()
    with open('app/tests/data/game_1867546158.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['Tags'] = list(community.tags.keys())

    # Submit game, verified users
    player_away.verify_user()
    player_home.verify_user()
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)
    assert response.status_code == 200
'''