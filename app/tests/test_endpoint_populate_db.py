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
    with open('app/tests/data/game_785756763.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['Tags'] = list(community.tags.keys())

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
    game1 = {'Winner Username': player_away.username, 'Winner Score': 10, 
             'Loser Username': player_home.username, 'Loser Score': 0}
    game2 = {'Winner Username': player_away.username, 'Winner Score': 10, 
             'Loser Username': player_home.username, 'Loser Score': 0}
    game1['TagSet'] = tagset.name
    game2['TagSet'] = tagset.name
    game1['Submitter Rio Key'] = player_away.rk
    game2['Submitter Rio Key'] = player_away.rk

    game1_response = requests.post("http://127.0.0.1:5000/submit_game/", json=game1)
    assert game1_response.status_code == 200

    game2_response = requests.post("http://127.0.0.1:5000/submit_game/", json=game2)
    assert game2_response.status_code == 200

    # No change until the players accept
    # Inspect Ladder
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

    # Confirm/Reject the games
    game1_winner_confirm = {'GameHistoryID': game1_response.json()['GameID'], 'Rio Key': player_away.rk, 'Accept': 1}
    game1_loser_reject   = {'GameHistoryID': game1_response.json()['GameID'], 'Rio Key': player_home.rk, 'Accept': 0}
    game1_loser_confirm  = {'GameHistoryID': game1_response.json()['GameID'], 'Rio Key': player_home.rk, 'Accept': 1}

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
    game2_winner_confirm = {'GameHistoryID': game2_response.json()['GameID'], 'Rio Key': player_away.rk, 'Accept': 1}
    game2_loser_confirm  = {'GameHistoryID': game2_response.json()['GameID'], 'Rio Key': player_home.rk, 'Accept': 1}

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
    game3 = {'Winner Username': player_away.username, 'Winner Score': 10, 
             'Loser Username': player_home.username, 'Loser Score': 0}
    game3['TagSet'] = tagset.name
    game3['Submitter Rio Key'] = sponsor.rk

    game3_response = requests.post("http://127.0.0.1:5000/submit_game/", json=game3)
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
    game4 = {'Winner Username': player_away.username, 'Winner Score': 10, 
             'Loser Username': player_home.username, 'Loser Score': 0}
    game4['TagSet'] = tagset.name
    game4['Submitter Rio Key'] = player_away.rk

    game4_response = requests.post("http://127.0.0.1:5000/submit_game/", json=game4)
    assert game4_response.status_code == 200

    # Inspect Ladder - should be no change
    response = requests.post("http://127.0.0.1:5000/tag_set/ladder/", json={'TagSet': tagset.name})
    assert response.status_code == 200
    
    data = response.json()
    assert data[player_away.username]['rating'] == away_user_rating
    assert data[player_home.username]['rating'] == home_user_rating

    # Game 4 - admin confirm
    game4_admin_confirm = {'GameHistoryID': game4_response.json()['GameID'], 'Rio Key': sponsor.rk, 'Accept': 1}

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
    with open('app/tests/data/game_785756763.json') as file:
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