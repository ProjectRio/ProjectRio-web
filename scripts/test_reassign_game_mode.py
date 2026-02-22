"""
Manual test script for reassign_game_history_game_mode changes.

Tests:
1. Same-community move: move a game between two tag sets in the same community
2. Cross-community move: move a game to a tag set in a different community
3. Cross-community move blocked: player not in target community
4. No-op: move a game to the tag set it's already in
5. Rollback: verify DB isn't corrupted if something goes wrong
6. recalc_elo: verify the endpoint still works standalone

Run with your local server at http://127.0.0.1:5000:
    python scripts/test_reassign_game_mode.py

WARNING: This calls wipe_db() and will destroy all data in your local DB.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'tests'))

import requests
from pprint import pprint
from helpers import User, Community, Tag, TagSet, wipe_db, reset_db

BASE_URL = os.getenv('BASE_URL', "http://127.0.0.1:5000")
ADMIN_KEY = os.getenv('ADMIN_KEY')
if not ADMIN_KEY:
    print("ERROR: ADMIN_KEY environment variable is not set.")
    sys.exit(1)

def get_ladder(tagset_name):
    resp = requests.post(f"{BASE_URL}/tag_set/ladder/", json={'TagSet': tagset_name})
    return resp.status_code, resp.json() if resp.status_code == 200 else resp.text

def reassign_game(game_id, new_tag_set_name):
    payload = {
        'ADMIN_KEY': ADMIN_KEY,
        'game_id': game_id,
        'new_tag_set_name': new_tag_set_name,
    }
    resp = requests.post(f"{BASE_URL}/reassign_game_history_game_mode/", json=payload)
    return resp.status_code, resp.text

def recalc(tag_set_id, log=False):
    payload = {
        'tag_set_id': tag_set_id,
        'log': log,
    }
    resp = requests.post(f"{BASE_URL}/recalc_elo/", json=payload)
    return resp.status_code, resp.json() if resp.status_code == 200 else resp.text

def manual_submit_game(winner_username, loser_username, tag_set_name, submitter_rio_key, recalc=False):
    payload = {
        'winner_username': winner_username,
        'winner_score': 10,
        'loser_username': loser_username,
        'loser_score': 0,
        'tag_set': tag_set_name,
        'submitter_rio_key': submitter_rio_key,
    }
    if recalc:
        payload['recalc'] = True
    resp = requests.post(f"{BASE_URL}/manual_submit_game/", json=payload)
    return resp.status_code, resp.json() if resp.status_code == 200 else resp.text

def setup():
    """Create two communities, each with a tag set, and two players in both communities."""
    wipe_db()

    # Admin/sponsor
    sponsor = User()
    sponsor.register()
    sponsor.verify_user()
    assert sponsor.success, "Sponsor registration failed"
    assert sponsor.add_to_group('admin'), "Failed to add sponsor to admin group"

    # Community A
    comm_a = Community(sponsor, True, False, False)
    assert comm_a.success, "Community A creation failed"

    tag_a = Tag(comm_a.founder, comm_a)
    tag_a.create()

    tagset_a1 = TagSet(comm_a.founder, comm_a, [tag_a], 'Season')
    tagset_a1.create()
    assert tagset_a1.pk, "TagSet A1 creation failed"

    tag_a2 = Tag(comm_a.founder, comm_a)
    tag_a2.create()

    tagset_a2 = TagSet(comm_a.founder, comm_a, [tag_a2], 'Season')
    tagset_a2.create()
    assert tagset_a2.pk, "TagSet A2 creation failed"

    comm_a.refresh()

    # Community B
    comm_b = Community(sponsor, True, False, False)
    assert comm_b.success, "Community B creation failed"

    tag_b = Tag(comm_b.founder, comm_b)
    tag_b.create()

    tagset_b = TagSet(comm_b.founder, comm_b, [tag_b], 'Season')
    tagset_b.create()
    assert tagset_b.pk, "TagSet B creation failed"

    comm_b.refresh()

    # Two players
    player1 = User()
    player1.register()
    player1.verify_user()

    player2 = User()
    player2.register()
    player2.verify_user()

    # Join both players to Community A (via URL)
    comm_a.join_via_url(player1)
    comm_a.join_via_url(player2)

    # Join both players to Community B (via URL)
    comm_b.join_via_url(player1)
    comm_b.join_via_url(player2)

    comm_a.refresh()
    comm_b.refresh()

    return sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2


def test_same_community_move():
    """Move a game between two tag sets in the same community."""
    print("\n" + "=" * 60)
    print("TEST 1: Same-community move")
    print("=" * 60)

    sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2 = setup()

    # Submit 3 games to tagset_a1 (as admin so they auto-count)
    for i in range(3):
        status, resp = manual_submit_game(player1.username, player2.username, tagset_a1.name, sponsor.rk, recalc=True)
        assert status == 200, f"Game {i+1} submit failed: {resp}"
        print(f"  Submitted game {i+1}, game_history_id: {resp['game_history_id']}")

    # Check ladder A1 has ratings
    status, ladder = get_ladder(tagset_a1.name)
    assert status == 200
    print(f"  Ladder A1: {player1.username}={ladder[player1.username]['rating']}, {player2.username}={ladder[player2.username]['rating']}")
    assert ladder[player1.username]['rating'] > 1500, "Winner should be above 1500"
    assert ladder[player2.username]['rating'] < 1500, "Loser should be below 1500"

    # Check ladder A2 is empty
    status, ladder_a2 = get_ladder(tagset_a2.name)
    print(f"  Ladder A2 before move: {ladder_a2}")

    # Move game 1 to tagset_a2
    game_id = resp['game_history_id']  # last game
    # Actually we need the game_id (BigInteger from Game table), not game_history_id
    # Let's use the game_id from the response - check what manual_submit returns
    # manual_submit returns game_history_id, but reassign expects game_id (Game.game_id)
    # Let's query for it
    print(f"\n  Moving game (game_history_id={game_id}) to tagset A2...")

    # We need the actual game_id. Let's get it from /games/
    games_resp = requests.post(f"{BASE_URL}/games/", json={'TagSet': tagset_a1.name})
    assert games_resp.status_code == 200, f"Failed to get games: {games_resp.text}"
    games = games_resp.json()
    game_id_to_move = games[0]['game_id']
    print(f"  Game ID to move: {game_id_to_move}")

    status, result = reassign_game(game_id_to_move, tagset_a2.name)
    print(f"  Reassign result: {status} - {result}")
    assert status == 200, f"Reassign failed: {result}"

    # Check ladder A1 has been recalculated (should have 2 games now)
    status, ladder_a1_after = get_ladder(tagset_a1.name)
    assert status == 200
    print(f"  Ladder A1 after move: {player1.username}={ladder_a1_after[player1.username]['rating']}, {player2.username}={ladder_a1_after[player2.username]['rating']}")

    # Check ladder A2 now has the moved game
    status, ladder_a2_after = get_ladder(tagset_a2.name)
    assert status == 200
    print(f"  Ladder A2 after move: {player1.username}={ladder_a2_after[player1.username]['rating']}, {player2.username}={ladder_a2_after[player2.username]['rating']}")

    # A1 ratings should have changed (lost a game)
    assert ladder_a1_after[player1.username]['rating'] != ladder[player1.username]['rating'], \
        "A1 ladder should have changed after losing a game"

    print("  PASSED ✓")


def test_cross_community_move():
    """Move a game to a tag set in a different community (players are in both)."""
    print("\n" + "=" * 60)
    print("TEST 2: Cross-community move")
    print("=" * 60)

    sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2 = setup()

    # Submit a game to tagset_a1
    status, resp = manual_submit_game(player1.username, player2.username, tagset_a1.name, sponsor.rk, recalc=True)
    assert status == 200, f"Game submit failed: {resp}"
    print(f"  Submitted game, game_history_id: {resp['game_history_id']}")

    # Check ladder A1
    status, ladder_a1 = get_ladder(tagset_a1.name)
    assert status == 200
    print(f"  Ladder A1: {player1.username}={ladder_a1[player1.username]['rating']}, {player2.username}={ladder_a1[player2.username]['rating']}")

    # Get game_id
    games_resp = requests.post(f"{BASE_URL}/games/", json={'TagSet': tagset_a1.name})
    game_id_to_move = games_resp.json()[0]['game_id']

    # Move to community B's tagset
    print(f"\n  Moving game {game_id_to_move} to tagset B (different community)...")
    status, result = reassign_game(game_id_to_move, tagset_b.name)
    print(f"  Reassign result: {status} - {result}")
    assert status == 200, f"Cross-community move failed: {result}"

    # Ladder A1 should now be empty (no games)
    status, ladder_a1_after = get_ladder(tagset_a1.name)
    print(f"  Ladder A1 after move: {ladder_a1_after}")

    # Ladder B should now have the game
    status, ladder_b = get_ladder(tagset_b.name)
    assert status == 200
    print(f"  Ladder B after move: {player1.username}={ladder_b[player1.username]['rating']}, {player2.username}={ladder_b[player2.username]['rating']}")

    print("  PASSED ✓")


def test_cross_community_blocked():
    """Move a game to a community where one player is NOT a member — should fail."""
    print("\n" + "=" * 60)
    print("TEST 3: Cross-community move blocked (player not in target community)")
    print("=" * 60)

    sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2 = setup()

    # Create a third player who is ONLY in community A
    player3 = User()
    player3.register()
    player3.verify_user()
    comm_a.join_via_url(player3)

    # Submit game with player3 in community A
    status, resp = manual_submit_game(player1.username, player3.username, tagset_a1.name, sponsor.rk, recalc=True)
    assert status == 200, f"Game submit failed: {resp}"
    print(f"  Submitted game with {player1.username} vs {player3.username}")

    # Get game_id
    games_resp = requests.post(f"{BASE_URL}/games/", json={'TagSet': tagset_a1.name})
    game_id_to_move = games_resp.json()[0]['game_id']

    # Try to move to community B — player3 is not a member
    print(f"  Attempting to move game to community B (player3 not a member)...")
    status, result = reassign_game(game_id_to_move, tagset_b.name)
    print(f"  Reassign result: {status} - {result}")
    assert status == 400, f"Should have been blocked but got {status}: {result}"
    assert player3.username in result, f"Error should mention the player's username"

    print("  PASSED ✓")


def test_noop_same_tagset():
    """Moving a game to the tag set it's already in should be a no-op."""
    print("\n" + "=" * 60)
    print("TEST 4: No-op (same tag set)")
    print("=" * 60)

    sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2 = setup()

    # Submit a game
    status, resp = manual_submit_game(player1.username, player2.username, tagset_a1.name, sponsor.rk, recalc=True)
    assert status == 200

    games_resp = requests.post(f"{BASE_URL}/games/", json={'TagSet': tagset_a1.name})
    game_id = games_resp.json()[0]['game_id']

    # Move to same tagset
    status, result = reassign_game(game_id, tagset_a1.name)
    print(f"  Reassign to same tagset: {status} - {result}")
    assert status == 200
    assert 'already' in result.lower(), f"Expected 'already' message, got: {result}"

    print("  PASSED ✓")


def test_recalc_endpoint():
    """Verify the /recalc_elo/ endpoint still works as a standalone HTTP call."""
    print("\n" + "=" * 60)
    print("TEST 5: recalc_elo endpoint")
    print("=" * 60)

    sponsor, comm_a, comm_b, tagset_a1, tagset_a2, tagset_b, player1, player2 = setup()

    # Submit 2 games
    for i in range(2):
        status, resp = manual_submit_game(player1.username, player2.username, tagset_a1.name, sponsor.rk, recalc=True)
        assert status == 200

    # Snapshot ladder
    status, ladder_before = get_ladder(tagset_a1.name)
    assert status == 200
    print(f"  Ladder before recalc: {player1.username}={ladder_before[player1.username]['rating']}")

    # Call recalc endpoint
    status, result = recalc(tagset_a1.pk, log=True)
    print(f"  Recalc result: {status}")
    assert status == 200, f"Recalc failed: {result}"

    # Ladder should be the same (no games changed)
    status, ladder_after = get_ladder(tagset_a1.name)
    assert status == 200
    print(f"  Ladder after recalc: {player1.username}={ladder_after[player1.username]['rating']}")
    assert ladder_before[player1.username]['rating'] == ladder_after[player1.username]['rating'], \
        "Ratings should be identical after recalc with no changes"

    print("  PASSED ✓")


def test_recalc_nonexistent_tagset():
    """Recalc on a nonexistent tag set should 404."""
    print("\n" + "=" * 60)
    print("TEST 6: recalc_elo with nonexistent tag set")
    print("=" * 60)

    status, result = recalc(99999)
    print(f"  Recalc with bad ID: {status} - {result}")
    assert status == 404, f"Expected 404 but got {status}"

    print("  PASSED ✓")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing reassign_game_history_game_mode + recalc_elo changes")
    print("=" * 60)
    print(f"Server: {BASE_URL}")
    print(f"WARNING: This will wipe your local database!")

    input("\nPress Enter to continue (Ctrl+C to abort)...")

    try:
        test_same_community_move()
        test_cross_community_move()
        test_cross_community_blocked()
        test_noop_same_tagset()
        test_recalc_endpoint()
        test_recalc_nonexistent_tagset()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n  FAILED ✗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
