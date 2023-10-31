import json
import os
import requests
import time
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
    
    # Submit game, verified users
    player_away.verify_user()
    player_home.verify_user()
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)

    assert response.status_code == 200

    game_id = int(data['GameID'].replace(',', ''), 16)

    assert not game_exists(game_id)

    time.sleep(80)

    assert game_exists(game_id)

def test_populate_db_fail():
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
    
    # Submit game, verified users
    response = requests.post("http://127.0.0.1:5000/populate_db/", json=data)

    assert response.status_code == 200

    game_id = int(data['GameID'].replace(',', ''), 16)

    assert not game_exists(game_id)

    time.sleep(80)

    assert not game_exists(game_id)

    # Check if a file with 'defect_' prefix exists in the game directory
    defect_file_exists = any(filename.startswith('defect_') for filename in os.listdir('app/games'))

    # Assert that a defect file exists
    assert defect_file_exists, "No defect files found in the game directory"