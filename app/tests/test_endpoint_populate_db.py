import json
import requests
from helpers import *
from connection import Connection

db = Connection()

def test_populate_db():
    wipe_db()

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
    with open('/data/game_785756763.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['Tags'] = community.tags.keys()
    

    # Submit game
    response = requests.post("http://127.0.0.1:5000/populate_db", json=data)
    print(response.status_code)
    assert response.status_code == 200
    