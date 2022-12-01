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
    response = requests.post("http://127.0.0.1:5000/populate_db", json=data)
    assert response.status_code == 411
    
    # Submit game, verified users
    player_away.verify_user()
    player_home.verify_user()
    response = requests.post("http://127.0.0.1:5000/populate_db", json=data)
    assert response.status_code == 200