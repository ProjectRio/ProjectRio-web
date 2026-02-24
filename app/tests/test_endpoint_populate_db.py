import json
import os
import time
import requests
from pprint import pprint
from helpers import *
from connection import Connection

db = Connection()

BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')

# ============================================================
# Helper: common setup for manual submit / update status tests
# ============================================================
def setup_community_and_players():
    """Create a community with a sponsor (admin), tagset, and two verified players."""
    wipe_db()

    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success == True
    assert sponsor.add_to_group('admin') == True

    community = Community(sponsor, True, False, False)
    assert community.success == True

    tag = Tag(community.founder, community)
    tag.create()

    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()

    community.refresh()

    player_away = User()
    player_away.register()
    player_away.verify_user()

    player_home = User()
    player_home.register()
    player_home.verify_user()

    return sponsor, community, tagset, player_away, player_home


def get_ladder(tagset_name):
    """Fetch the ladder for a tagset."""
    response = requests.post(f"{BASE_URL}/tag_set/ladder/", json={'TagSet': tagset_name})
    assert response.status_code == 200
    return response.json()


def submit_manual_game(winner, loser, tagset, submitter, date=None, game_id_hex=None):
    """Submit a manual game and return the response."""
    game = {
        'winner_username': winner.username,
        'winner_score': 10,
        'loser_username': loser.username,
        'loser_score': 0,
        'tag_set': tagset.name,
        'submitter_rio_key': submitter.rk,
        'date': date or int(time.time()),
    }
    if game_id_hex:
        game['game_id_hex'] = game_id_hex
    return requests.post(f"{BASE_URL}/manual_submit_game/", json=game)


# ============================================================
# manual_submit_game: Input Validation
# ============================================================
def test_manual_submit_missing_fields():
    """Missing required fields should return 400 with field names."""
    wipe_db()
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json={})
    assert response.status_code == 400

    # Should list all missing fields
    desc = get_error_description(response)
    for field in ['submitter_rio_key', 'winner_username', 'loser_username',
                  'winner_score', 'loser_score', 'tag_set', 'date']:
        assert field in desc, f"Expected '{field}' in error description"


def test_manual_submit_partial_missing_fields():
    """Only the actually missing fields should be listed."""
    wipe_db()
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json={
        'submitter_rio_key': 'fake_key',
        'winner_username': 'someone',
        'date': int(time.time()),
    })
    assert response.status_code == 400

    desc = get_error_description(response)
    # These were provided, should NOT appear
    assert 'submitter_rio_key' not in desc
    assert 'winner_username' not in desc
    assert 'date' not in desc
    # These are missing, should appear
    assert 'loser_username' in desc
    assert 'winner_score' in desc
    assert 'loser_score' in desc
    assert 'tag_set' in desc


def test_manual_submit_not_json():
    """Non-JSON request should return 400."""
    wipe_db()
    response = requests.post(f"{BASE_URL}/manual_submit_game/", data='not json')
    assert response.status_code == 400


def test_manual_submit_both_game_ids():
    """Providing both game_id_dec and game_id_hex should return 400."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game = {
        'winner_username': player_away.username,
        'winner_score': 10,
        'loser_username': player_home.username,
        'loser_score': 0,
        'tag_set': tagset.name,
        'submitter_rio_key': player_away.rk,
        'date': int(time.time()),
        'game_id_dec': 12345,
        'game_id_hex': 'ABCDE',
    }
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game)
    assert response.status_code == 400


def test_manual_submit_invalid_rio_key():
    """Invalid submitter rio key should return 401."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=player_away)
    # Override with bad key
    game = {
        'winner_username': player_away.username,
        'winner_score': 10,
        'loser_username': player_home.username,
        'loser_score': 0,
        'tag_set': tagset.name,
        'submitter_rio_key': 'totally_invalid_key',
        'date': int(time.time()),
    }
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game)
    assert response.status_code == 401


def test_manual_submit_invalid_tagset():
    """Invalid tag_set name should return 404."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game = {
        'winner_username': player_away.username,
        'winner_score': 10,
        'loser_username': player_home.username,
        'loser_score': 0,
        'tag_set': 'nonexistent_tagset',
        'submitter_rio_key': player_away.rk,
        'date': int(time.time()),
    }
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game)
    assert response.status_code == 404


def test_manual_submit_invalid_username():
    """Invalid winner/loser username should return 404 with the role and username."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game = {
        'winner_username': 'nonexistent_player',
        'winner_score': 10,
        'loser_username': player_home.username,
        'loser_score': 0,
        'tag_set': tagset.name,
        'submitter_rio_key': player_away.rk,
        'date': int(time.time()),
    }
    response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game)
    assert response.status_code == 404


def test_manual_submit_unverified_user():
    """Unverified users should return 422."""
    wipe_db()

    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.add_to_group('admin') == True

    community = Community(sponsor, True, False, False)
    assert community.success == True

    tag = Tag(community.founder, community)
    tag.create()
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()
    community.refresh()

    # Unverified players
    player_away = User()
    player_away.register()
    player_home = User()
    player_home.register()

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=player_away)
    assert response.status_code == 422


def test_manual_submit_unauthorized_submitter():
    """A user who is not a player or admin should get 403."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Create a third user who is in the community but not a player in this game
    bystander = User()
    bystander.register()
    bystander.verify_user()
    community.join_via_url(bystander)

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=bystander)
    assert response.status_code == 403


# ============================================================
# manual_submit_game: Player Submission (no ELO change)
# ============================================================
def test_player_submit_no_elo_change():
    """Player-submitted games should not affect ELO until accepted."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Submit as player
    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=player_away)
    assert response.status_code == 200
    game_history_id = response.json()['game_history_id']

    # Ladder should show default ratings (no change from submission alone)
    ladder = get_ladder(tagset.name)
    if player_away.username in ladder:
        away_rating = ladder[player_away.username]['rating']
        home_rating = ladder[player_home.username]['rating']
        assert away_rating == home_rating  # Both still at default


# ============================================================
# manual_submit_game: Admin Submission (immediate ELO)
# ============================================================
def test_admin_submit_immediate_elo():
    """Admin-submitted games should immediately affect ELO."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=sponsor)
    assert response.status_code == 200

    # Ladder should now reflect the game
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


# ============================================================
# manual_submit_game: Site-level Admin/Trusted User
# ============================================================
def test_site_admin_submit():
    """A site-level Admin (not in the community) can submit games."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Create a site admin who is NOT in the community
    site_admin = User()
    site_admin.register()
    site_admin.verify_user()
    assert site_admin.add_to_group('admin') == True

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=site_admin)
    assert response.status_code == 200

    # Should count as admin_accept — ELO should change
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_trusted_user_submit():
    """A site-level Trusted User (not in the community) can submit games."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Create a trusted user who is NOT in the community
    trusted = User()
    trusted.register()
    trusted.verify_user()
    assert trusted.add_to_group('TrustedUser') == True

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=trusted)
    assert response.status_code == 200

    # Should count as admin_accept — ELO should change
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


# ============================================================
# manual_submit_game: Community Admin Submit
# ============================================================
def test_community_admin_submit():
    """A community admin (sponsor) submitting should immediately affect ELO."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Sponsor is the community admin (creator) — submit as them
    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=sponsor)
    assert response.status_code == 200

    # Should count as admin_accept — ELO should change immediately
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_promoted_community_admin_submit():
    """A user promoted to community admin can submit games with immediate ELO."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Create a new user, add to community, promote to community admin
    comm_admin = User()
    comm_admin.register()
    comm_admin.verify_user()
    community.join_via_url(comm_admin)
    assert community.manage(sponsor, [comm_admin], 'admin') == True

    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=comm_admin)
    assert response.status_code == 200

    # Should count as admin_accept — ELO should change immediately
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


# ============================================================
# update_game_status: Community Admin Override
# ============================================================
def test_community_admin_override_accept():
    """A community admin can accept a game, overriding player acceptance state."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Player submits — no ELO change
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Community admin (sponsor) accepts — should trigger ELO
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': True,
    })
    assert response.status_code == 200

    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_community_admin_override_reject():
    """A community admin can reject a game that both players accepted."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Submit a baseline game as admin so players stay on the ladder
    baseline = submit_manual_game(player_away, player_home, tagset,
                                  submitter=sponsor, date=int(time.time()))
    assert baseline.status_code == 200

    # Player submits a second game, other player accepts
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away,
                                       date=int(time.time()) + 1)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Loser accepts — ELO should change
    requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': player_home.rk,
        'accept': True,
    })

    ladder = get_ladder(tagset.name)
    away_rating_accepted = ladder[player_away.username]['rating']
    home_rating_accepted = ladder[player_home.username]['rating']
    assert away_rating_accepted > home_rating_accepted

    # Community admin rejects the second game — should undo its ELO
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': False,
    })
    assert response.status_code == 200

    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] != away_rating_accepted
    assert ladder[player_home.username]['rating'] != home_rating_accepted


def test_promoted_community_admin_override():
    """A promoted community admin can accept games via update_game_status."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Promote a user to community admin
    comm_admin = User()
    comm_admin.register()
    comm_admin.verify_user()
    community.join_via_url(comm_admin)
    assert community.manage(sponsor, [comm_admin], 'admin') == True

    # Player submits
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Promoted admin accepts
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': comm_admin.user.rk if hasattr(comm_admin, 'user') else comm_admin.rk,
        'accept': True,
    })
    assert response.status_code == 200

    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


# ============================================================
# manual_submit_game: Auto-recalc for past games
# ============================================================
def test_auto_recalc_past_game():
    """Inserting a game with an earlier date than existing games should trigger recalc."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    now = int(time.time())

    # Submit first game as admin (recent timestamp)
    response = submit_manual_game(player_away, player_home, tagset,
                                  submitter=sponsor, date=now)
    assert response.status_code == 200

    ladder_after_first = get_ladder(tagset.name)
    away_rating_1 = ladder_after_first[player_away.username]['rating']

    # Submit second game as admin with EARLIER date (should trigger recalc)
    response = submit_manual_game(player_home, player_away, tagset,
                                  submitter=sponsor, date=now - 10000)
    assert response.status_code == 200

    # Ratings should have changed from the recalc
    ladder_after_second = get_ladder(tagset.name)
    away_rating_2 = ladder_after_second[player_away.username]['rating']
    assert away_rating_2 != away_rating_1


def test_no_recalc_latest_game():
    """Appending a game at the end of the timeline should NOT trigger recalc."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    now = int(time.time())

    # Submit two games in chronological order — no recalc needed
    response1 = submit_manual_game(player_away, player_home, tagset,
                                   submitter=sponsor, date=now)
    assert response1.status_code == 200

    response2 = submit_manual_game(player_away, player_home, tagset,
                                   submitter=sponsor, date=now + 10000)
    assert response2.status_code == 200

    # Away player won both, should have higher rating
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


# ============================================================
# update_game_status: Input Validation
# ============================================================
def test_update_status_missing_fields():
    """Missing required fields should return 400."""
    wipe_db()
    response = requests.post(f"{BASE_URL}/update_game_status/", json={})
    assert response.status_code == 400


def test_update_status_invalid_game_history_id():
    """Invalid game_history_id should return 404."""
    wipe_db()
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': 99999,
        'rio_key': 'some_key',
        'accept': True,
    })
    assert response.status_code == 404


def test_update_status_invalid_rio_key():
    """Invalid rio key should return 401."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Submit a game first
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': 'totally_invalid',
        'accept': True,
    })
    assert response.status_code == 401


# ============================================================
# update_game_status: Player Accept/Reject Flow
# ============================================================
def test_player_accept_flow():
    """Both players accepting should trigger ELO recalc."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Submit as player (no ELO change)
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Winner already accepted via submission, now loser accepts
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': player_home.rk,
        'accept': True,
    })
    assert response.status_code == 200

    # ELO should now reflect the game
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_player_reject_no_elo():
    """If loser rejects, ELO should not change."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Loser rejects
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': player_home.rk,
        'accept': False,
    })
    assert response.status_code == 200

    # Ladder should be unchanged (default ratings or no entries)
    ladder = get_ladder(tagset.name)
    if player_away.username in ladder and player_home.username in ladder:
        assert ladder[player_away.username]['rating'] == ladder[player_home.username]['rating']


# ============================================================
# update_game_status: Admin Override
# ============================================================
def test_admin_accept_overrides():
    """Admin accepting should immediately affect ELO."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Admin accepts
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': True,
    })
    assert response.status_code == 200

    # ELO should change
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_admin_reject_blocks_accepted_game():
    """Admin rejecting a game that both players accepted should undo ELO."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Submit a baseline game as admin so players stay on the ladder
    baseline = submit_manual_game(player_away, player_home, tagset,
                                  submitter=sponsor, date=int(time.time()))
    assert baseline.status_code == 200

    # Submit a second game and both players accept
    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away,
                                       date=int(time.time()) + 1)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Loser accepts
    requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': player_home.rk,
        'accept': True,
    })

    # Snapshot ratings after acceptance
    ladder = get_ladder(tagset.name)
    away_rating_accepted = ladder[player_away.username]['rating']

    # Admin rejects the second game
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': False,
    })
    assert response.status_code == 200

    # Ratings should revert (recalc without the rejected game)
    ladder = get_ladder(tagset.name)
    away_rating_after_reject = ladder[player_away.username]['rating']
    assert away_rating_after_reject != away_rating_accepted


def test_admin_no_op_same_accept():
    """Admin re-confirming the same acceptance should return 200 with no-op message."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Admin accepts
    requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': True,
    })

    # Admin re-confirms — should be a no-op 200
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': True,
    })
    assert response.status_code == 200
    assert 'already matches' in response.json().get('message', '')


def test_player_cannot_change_after_admin_decides():
    """Players should get 409 if they try to change acceptance after admin decided."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Admin accepts
    requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': sponsor.rk,
        'accept': True,
    })

    # Loser tries to reject — should fail
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': player_home.rk,
        'accept': False,
    })
    assert response.status_code == 409


# ============================================================
# update_game_status: Site-level Admin/Trusted User
# ============================================================
def test_site_admin_can_update_status():
    """A site-level Admin (not in the community) can update game status."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    # Create site admin outside community
    site_admin = User()
    site_admin.register()
    site_admin.verify_user()
    assert site_admin.add_to_group('admin') == True

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    # Site admin accepts
    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': site_admin.rk,
        'accept': True,
    })
    assert response.status_code == 200

    # ELO should change
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']


def test_non_participant_cannot_update():
    """A regular user who is not a player or admin should get 403."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    bystander = User()
    bystander.register()
    bystander.verify_user()
    community.join_via_url(bystander)

    game_response = submit_manual_game(player_away, player_home, tagset,
                                       submitter=player_away)
    assert game_response.status_code == 200
    gh_id = game_response.json()['game_history_id']

    response = requests.post(f"{BASE_URL}/update_game_status/", json={
        'game_history_id': gh_id,
        'rio_key': bystander.rk,
        'accept': True,
    })
    assert response.status_code == 403


# ============================================================
# Full integration: populate_db + manual_submit + update_status
# ============================================================
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

    with open('app/tests/data/20260219T212721_MattGree-Vs-Baltor33_1189820580.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['TagSetID'] = tagset.pk

    # Submit game, nonverified users
    response = requests.post(f"{BASE_URL}/populate_db/", json=data)
    assert response.status_code == 422

    # Submit game, verified users
    player_away.verify_user()
    player_home.verify_user()
    response = requests.post(f"{BASE_URL}/populate_db/", json=data)
    assert response.status_code == 200

    # Force game processing (normally done by APScheduler cron)
    assert force_process_games() == True

    # Test the ladder
    ladder = get_ladder(tagset.name)

    # Home Player wins this game. Check rating is higher
    away_user_rating = ladder[player_away.username]['rating']
    home_user_rating = ladder[player_home.username]['rating']
    assert away_user_rating < home_user_rating

    # ============================================================
    # Now check manual submit
    # Give the away player from the file 2 wins. Elo should be higher than home
    now = int(time.time())
    game1 = {'winner_username': player_away.username, 'winner_score': 10,
             'loser_username': player_home.username, 'loser_score': 0,
             'tag_set': tagset.name, 'submitter_rio_key': player_away.rk,
             'date': now}
    game2 = {'winner_username': player_away.username, 'winner_score': 10,
             'loser_username': player_home.username, 'loser_score': 0,
             'tag_set': tagset.name, 'submitter_rio_key': player_away.rk,
             'date': now + 1}

    game1_response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game1)
    assert game1_response.status_code == 200

    game2_response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game2)
    assert game2_response.status_code == 200

    # No change until the players accept
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] == away_user_rating
    assert ladder[player_home.username]['rating'] == home_user_rating

    # Confirm/Reject the games
    game1_winner_confirm = {'game_history_id': game1_response.json()['game_history_id'], 'rio_key': player_away.rk, 'accept': True}
    game1_loser_reject   = {'game_history_id': game1_response.json()['game_history_id'], 'rio_key': player_home.rk, 'accept': False}
    game1_loser_confirm  = {'game_history_id': game1_response.json()['game_history_id'], 'rio_key': player_home.rk, 'accept': True}

    # Winner confirm game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game1_winner_confirm)
    assert response.status_code == 200

    # Loser Reject game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game1_loser_reject)
    assert response.status_code == 200

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] == away_user_rating
    assert ladder[player_home.username]['rating'] == home_user_rating

    # Loser confirm game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game1_loser_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] != away_user_rating
    assert ladder[player_home.username]['rating'] != home_user_rating

    # ============================================================
    # Game 2
    game2_winner_confirm = {'game_history_id': game2_response.json()['game_history_id'], 'rio_key': player_away.rk, 'accept': True}
    game2_loser_confirm  = {'game_history_id': game2_response.json()['game_history_id'], 'rio_key': player_home.rk, 'accept': True}

    # Winner confirm game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game2_winner_confirm)
    assert response.status_code == 200

    # Loser confirm game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game2_loser_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] > ladder[player_home.username]['rating']

    # ============================================================
    # Snapshot player ratings
    away_user_rating = ladder[player_away.username]['rating']
    home_user_rating = ladder[player_home.username]['rating']

    # Submit game as admin, check that it changes the ELOs
    game3 = {'winner_username': player_away.username, 'winner_score': 10,
             'loser_username': player_home.username, 'loser_score': 0,
             'tag_set': tagset.name, 'submitter_rio_key': sponsor.rk,
             'date': now + 2}

    game3_response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game3)
    assert game3_response.status_code == 200

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] != away_user_rating
    assert ladder[player_home.username]['rating'] != home_user_rating

    # ============================================================
    # Submit game as user, confirm as admin

    # Snapshot player ratings
    away_user_rating = ladder[player_away.username]['rating']
    home_user_rating = ladder[player_home.username]['rating']

    game4 = {'winner_username': player_away.username, 'winner_score': 10,
             'loser_username': player_home.username, 'loser_score': 0,
             'tag_set': tagset.name, 'submitter_rio_key': player_away.rk,
             'date': now + 3}

    game4_response = requests.post(f"{BASE_URL}/manual_submit_game/", json=game4)
    assert game4_response.status_code == 200

    # Inspect Ladder - should be no change
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] == away_user_rating
    assert ladder[player_home.username]['rating'] == home_user_rating

    # Game 4 - admin confirm
    game4_admin_confirm = {'game_history_id': game4_response.json()['game_history_id'], 'rio_key': sponsor.rk, 'accept': True}

    # Admin confirm game
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game4_admin_confirm)
    assert response.status_code == 200

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] != away_user_rating
    assert ladder[player_home.username]['rating'] != home_user_rating

    # ============================================================

    # Snapshot player ratings
    away_user_rating = ladder[player_away.username]['rating']
    home_user_rating = ladder[player_home.username]['rating']

    # Admin reconfirm game - shouldn't update elo, should return 200 with message
    response = requests.post(f"{BASE_URL}/update_game_status/", json=game4_admin_confirm)
    assert response.status_code == 200
    assert 'already matches' in response.json().get('message', '')

    # Inspect Ladder
    ladder = get_ladder(tagset.name)
    assert ladder[player_away.username]['rating'] == away_user_rating
    assert ladder[player_home.username]['rating'] == home_user_rating

def test_ongoing_game():
    wipe_db()

    with open('app/tests/data/20260219T212721_MattGree-Vs-Baltor33_1189820580.json') as file:
        data = json.load(file)
        data['Away Player'] = player_away.rk
        data['Home Player'] = player_home.rk
        data['TagSetID'] = tagset.pk
        game_id = int(data['GameID'].strip(',')[-1],16)

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
        'GameID': str(game_id),
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
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game)
    assert response.status_code == 422

    player_away.verify_user()
    player_home.verify_user()

    # Start Game, verified users
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game)
    assert response.status_code == 200


    #Make sure game is there
    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 1

    #Update game
    game_update = {
        'GameID': str(game_id),
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
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game_update)
    assert response.status_code == 200

    #Make sure game is there
    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert response.json()['ongoing_games'][0]['inning'] == 1

    # Submit game, make sure ongoing game was cleared
    response = requests.post(f"{BASE_URL}/populate_db/", json=data)
    assert response.status_code == 200

    # Force game processing (normally done by APScheduler cron)
    assert force_process_games() == True

    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
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
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game)
    assert response.status_code == 422

    player_away.verify_user()
    player_home.verify_user()

    # Start Game, verified users
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game)
    assert response.status_code == 200


    #Make sure game is there
    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
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
    response = requests.post(f"{BASE_URL}/populate_db/ongoing_game/", json=game_update)
    assert response.status_code == 200


    # ============================================================
    # Now manual submit
    man_game = {'winner_username': player_away.username, 'winner_score': 10,
             'loser_username': player_home.username, 'loser_score': 0,
             'tag_set': tagset.name, 'game_id_hex': '1867546158',
             'submitter_rio_key': player_away.rk,
             'date': int(time.time())}

    #Confirm Ongoing game is still there
    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 1

    man_game_response = requests.post(f"{BASE_URL}/manual_submit_game/", json=man_game)
    assert man_game_response.status_code == 200
    response = requests.get(f"{BASE_URL}/populate_db/ongoing_game/")
    assert response.status_code == 200
    assert len(response.json()['ongoing_games']) == 0


# ============================================================
# Helper: load a game JSON file and prepare it for submission
# ============================================================
GAME_FILE = 'app/tests/data/20260219T212721_MattGree-Vs-Baltor33_1189820580.json'


def load_game_json():
    """Load the test game JSON file."""
    with open(GAME_FILE) as f:
        return json.load(f)


# ============================================================
# populate_db manual submission: Admin + Trusted User auth
# ============================================================
def test_admin_manual_populate_db():
    """Admin can submit a full game JSON with usernames in Home/Away Player fields."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    data = load_game_json()
    data['Away Player'] = player_away.username
    data['Home Player'] = player_home.username
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': sponsor.rk})
    assert response.status_code == 200


def test_trusted_user_manual_populate_db():
    """TrustedUser can submit a full game JSON with usernames."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    trusted = User()
    trusted.register()
    trusted.verify_user()
    assert trusted.add_to_group('TrustedUser') == True

    data = load_game_json()
    data['Away Player'] = player_away.username
    data['Home Player'] = player_home.username
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': trusted.rk})
    assert response.status_code == 200


def test_manual_populate_db_unauthorized():
    """A regular user providing submitter_rio_key but not Admin/TrustedUser gets 403."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    bystander = User()
    bystander.register()
    bystander.verify_user()

    data = load_game_json()
    data['Away Player'] = player_away.username
    data['Home Player'] = player_home.username
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': bystander.rk})
    assert response.status_code == 403


def test_manual_populate_db_invalid_username():
    """Admin submitting with a nonexistent username gets 400."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    data = load_game_json()
    data['Away Player'] = 'nonexistent_player_xyz'
    data['Home Player'] = player_home.username
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': sponsor.rk})
    assert response.status_code == 400


def test_manual_populate_db_unverified_user():
    """Admin submitting with an unverified player username gets 422."""
    wipe_db()

    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.add_to_group('admin') == True

    community = Community(sponsor, True, False, False)
    assert community.success == True

    tag = Tag(community.founder, community)
    tag.create()
    tagset = TagSet(community.founder, community, [tag], 'Season')
    tagset.create()
    community.refresh()

    # Unverified players
    player_away = User()
    player_away.register()
    player_home = User()
    player_home.register()

    data = load_game_json()
    data['Away Player'] = player_away.username
    data['Home Player'] = player_home.username
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': sponsor.rk})
    assert response.status_code == 422


def test_client_flow_unchanged():
    """Client submitting with rio_keys (no submitter_rio_key) works as before."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    data = load_game_json()
    data['Away Player'] = player_away.rk
    data['Home Player'] = player_home.rk
    data['TagSetID'] = tagset.pk

    response = requests.post(f"{BASE_URL}/populate_db/", json=data)
    assert response.status_code == 200


def test_manual_populate_db_invalid_tagset():
    """Admin submitting a game JSON with a nonexistent TagSetID gets 200 from
    save_game (it writes to disk), but process_game will mark it as defective.
    This test verifies save_game accepts the file — the TagSetID validation
    happens in process_game."""
    sponsor, community, tagset, player_away, player_home = setup_community_and_players()

    data = load_game_json()
    data['Away Player'] = player_away.username
    data['Home Player'] = player_home.username
    data['TagSetID'] = 5000  # nonexistent

    response = requests.post(f"{BASE_URL}/populate_db/", json=data,
                             params={'submitter_rio_key': sponsor.rk})
    # save_game writes to disk without checking TagSetID
    assert response.status_code == 200
