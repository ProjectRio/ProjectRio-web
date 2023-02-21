#This test should only be used to create rio users, a community, and a tagset for client testing
import json
import os
import requests
from pprint import pprint
from helpers import *
from connection import Connection

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
    user1 = {'Username':'TestUser1'}
    player_away = User(user1)
    player_away.register()
    player_away.verify_user()

    user2 = {'Username':'TestUser2'}
    player_home = User(user2)
    player_home.register()
    player_home.verify_user()

    pprint(player_away.to_dict())
    pprint(player_home.to_dict())

    #Print TagSet Info
    response = requests.post("http://127.0.0.1:5000/tag_set/list", json={'Client': 'true', 'Active': 't'})
    assert response.status_code == 200

    data = response.json()
    pprint(data)

    assert True == False
