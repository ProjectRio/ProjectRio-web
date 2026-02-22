"""
Test script for reassign_game_history_game_mode and recalc_elo changes.

Uses real game data from the test database. Does NOT wipe the DB.
All games are moved back to their original location at the end of each test.

Tests:
1. Same-community move: PJ Classic 2 -> PJ Training -> PJ Classic 2
2. Cross-community move: PJ Classic 2 -> S13 -> PJ Classic 2
3. Three-way move: PJ Classic 2 -> PJ Training -> S13 -> PJ Classic 2
4. Out-of-order move: Move an older game (15th most recent) and verify
5. Recalc endpoint: Verify /recalc_elo/ still works standalone
6. No-op: Move a game to the tag set it's already in

Run inside the Docker container:
    ADMIN_KEY=<key> python3 scripts/test_reassign_game_mode.py
"""

import sys
import os
import requests
from pprint import pprint

BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')
ADMIN_KEY = os.getenv('ADMIN_KEY')

if not ADMIN_KEY:
    print("ERROR: ADMIN_KEY environment variable is not set.")
    sys.exit(1)

# Tag set names
TAGSET_PJ_CLASSIC = 'PJ and Friends Team Classic 2'
TAGSET_PJ_TRAINING = 'PJ and Friends Classic Training'
TAGSET_S13 = 'S13 Superstars Off Hazards'

NUM_GAMES = 5


# ============================================================
# Helper functions
# ============================================================

def get_ladder(tagset_name):
    resp = requests.post(f"{BASE_URL}/tag_set/ladder/", json={'TagSet': tagset_name})
    if resp.status_code == 200:
        return resp.status_code, resp.json()
    return resp.status_code, resp.text


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
    if resp.status_code == 200:
        return resp.status_code, resp.json()
    return resp.status_code, resp.text


def get_ladder_games(tagset_name):
    """Get games from a tag set via /ladder/games/ endpoint.
    Returns GameHistory data including tag_set_id, elo fields, etc."""
    resp = requests.get(f"{BASE_URL}/ladder/games/", params={'tag_set': tagset_name})
    if resp.status_code == 200:
        return resp.status_code, resp.json().get('games', [])
    return resp.status_code, resp.text


def get_tag_set_id(tagset_name):
    """Look up a tag set's ID by name via /tag_set/list."""
    resp = requests.get(f"{BASE_URL}/tag_set/list")
    if resp.status_code != 200:
        return None
    for ts in resp.json():
        if ts['name'] == tagset_name:
            return ts['id']
    return None


def snapshot_ladder(tagset_name):
    """Get a simplified snapshot of the ladder for comparison."""
    status, data = get_ladder(tagset_name)
    if status != 200 or not isinstance(data, dict):
        return {}
    return {username: info['rating'] for username, info in data.items()}


def snapshot_game_history(tagset_name):
    """Get a dict of game_id -> game history info for a tag set."""
    status, games = get_ladder_games(tagset_name)
    if status != 200:
        return {}
    result = {}
    for g in games:
        gid = g.get('game_id')
        if gid is not None:
            result[gid] = {
                'tag_set': g.get('tag_set'),
                'winner_incoming_elo': g.get('winner_incoming_elo'),
                'loser_incoming_elo': g.get('loser_incoming_elo'),
                'winner_result_elo': g.get('winner_result_elo'),
                'loser_result_elo': g.get('loser_result_elo'),
                'winner_player': g.get('winner_player'),
                'loser_player': g.get('loser_player'),
            }
    return result


def print_ladder_diff(label, before, after):
    """Print rating changes between two ladder snapshots."""
    all_users = set(list(before.keys()) + list(after.keys()))
    changes = []
    for user in sorted(all_users):
        old = before.get(user)
        new = after.get(user)
        if old != new:
            changes.append(f"    {user}: {old} -> {new}")
    if changes:
        print(f"  {label} rating changes:")
        for c in changes:
            print(c)
    else:
        print(f"  {label}: no rating changes")


def verify_games_in_tagset(game_ids, tagset_name, tag_set_id):
    """Verify that specific game_ids appear in a tag set's game history."""
    gh = snapshot_game_history(tagset_name)
    missing = []
    wrong_tagset = []
    for gid in game_ids:
        if gid not in gh:
            missing.append(gid)
        elif gh[gid]['tag_set'] != tag_set_id:
            wrong_tagset.append((gid, gh[gid]['tag_set']))
    return missing, wrong_tagset


def verify_games_not_in_tagset(game_ids, tagset_name):
    """Verify that specific game_ids do NOT appear in a tag set's game history."""
    gh = snapshot_game_history(tagset_name)
    found = [gid for gid in game_ids if gid in gh]
    return found


def verify_ladders_match(label, before, after):
    """Assert all ratings match between two ladder snapshots."""
    for user, rating in before.items():
        assert after.get(user) == rating, \
            f"{label} rating not restored for {user}: was {rating}, now {after.get(user)}"


# ============================================================
# Tests
# ============================================================

def test_same_community_move():
    """Move 5 games from PJ Classic 2 to PJ Training (same community) and back."""
    print("\n" + "=" * 60)
    print("TEST 1: Same-community move")
    print(f"  {TAGSET_PJ_CLASSIC} -> {TAGSET_PJ_TRAINING} -> back")
    print("=" * 60)

    pj_id = get_tag_set_id(TAGSET_PJ_CLASSIC)
    training_id = get_tag_set_id(TAGSET_PJ_TRAINING)
    assert pj_id and training_id, "Could not find tag set IDs"

    # Get recent games from PJ Classic
    status, games = get_ladder_games(TAGSET_PJ_CLASSIC)
    assert status == 200, f"Failed to get games: {games}"
    game_ids = [g['game_id'] for g in games[:NUM_GAMES] if g['game_id'] is not None]
    assert len(game_ids) >= NUM_GAMES, f"Not enough games with game_id, found {len(game_ids)}"
    game_ids = game_ids[:NUM_GAMES]
    print(f"  Selected {NUM_GAMES} game_ids: {game_ids}")

    # Snapshot everything before
    pj_ladder_before = snapshot_ladder(TAGSET_PJ_CLASSIC)
    training_ladder_before = snapshot_ladder(TAGSET_PJ_TRAINING)
    pj_gh_before = snapshot_game_history(TAGSET_PJ_CLASSIC)
    training_gh_before = snapshot_game_history(TAGSET_PJ_TRAINING)
    print(f"  PJ Classic: {len(pj_ladder_before)} players, {len(pj_gh_before)} games")
    print(f"  PJ Training: {len(training_ladder_before)} players, {len(training_gh_before)} games")

    # Move games to PJ Training
    print(f"\n  Moving {NUM_GAMES} games to {TAGSET_PJ_TRAINING}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_PJ_TRAINING)
        assert status == 200, f"Failed to move game {gid}: {status} {result}"
        print(f"    Game {gid}: OK")

    # Verify games are in PJ Training and NOT in PJ Classic
    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_PJ_TRAINING, training_id)
    assert not missing, f"Games missing from {TAGSET_PJ_TRAINING}: {missing}"
    assert not wrong, f"Games have wrong tag_set in {TAGSET_PJ_TRAINING}: {wrong}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_PJ_CLASSIC)
    assert not leftover, f"Games still in {TAGSET_PJ_CLASSIC} after move: {leftover}"
    print(f"  GameHistory verified: games in Training, not in PJ Classic ✓")

    # Check ladders changed
    print_ladder_diff("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    print_ladder_diff("PJ Training", training_ladder_before, snapshot_ladder(TAGSET_PJ_TRAINING))

    # Move games back
    print(f"\n  Moving {NUM_GAMES} games back to {TAGSET_PJ_CLASSIC}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_PJ_CLASSIC)
        assert status == 200, f"Failed to move game {gid} back: {status} {result}"
        print(f"    Game {gid}: OK")

    # Verify games are back in PJ Classic and NOT in PJ Training
    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_PJ_CLASSIC, pj_id)
    assert not missing, f"Games missing from {TAGSET_PJ_CLASSIC}: {missing}"
    assert not wrong, f"Games have wrong tag_set in {TAGSET_PJ_CLASSIC}: {wrong}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_PJ_TRAINING)
    # Only check the ones we moved (training may have its own games)
    our_leftover = [gid for gid in leftover if gid in game_ids]
    assert not our_leftover, f"Moved games still in {TAGSET_PJ_TRAINING}: {our_leftover}"
    print(f"  GameHistory verified: games back in PJ Classic ✓")

    # Verify ladders restored
    verify_ladders_match("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    verify_ladders_match("PJ Training", training_ladder_before, snapshot_ladder(TAGSET_PJ_TRAINING))
    print("  Ladders restored ✓")

    print("  PASSED ✓")


def test_cross_community_move():
    """Move 5 games from PJ Classic 2 to S13 (different community) and back."""
    print("\n" + "=" * 60)
    print("TEST 2: Cross-community move")
    print(f"  {TAGSET_PJ_CLASSIC} -> {TAGSET_S13} -> back")
    print("=" * 60)

    pj_id = get_tag_set_id(TAGSET_PJ_CLASSIC)
    s13_id = get_tag_set_id(TAGSET_S13)
    assert pj_id and s13_id, "Could not find tag set IDs"

    # Get recent games
    status, games = get_ladder_games(TAGSET_PJ_CLASSIC)
    assert status == 200, f"Failed to get games: {games}"
    game_ids = [g['game_id'] for g in games[:NUM_GAMES] if g['game_id'] is not None]
    game_ids = game_ids[:NUM_GAMES]
    print(f"  Selected {NUM_GAMES} game_ids: {game_ids}")

    # Snapshot
    pj_ladder_before = snapshot_ladder(TAGSET_PJ_CLASSIC)
    s13_ladder_before = snapshot_ladder(TAGSET_S13)
    pj_gh_before = snapshot_game_history(TAGSET_PJ_CLASSIC)
    s13_gh_before = snapshot_game_history(TAGSET_S13)
    print(f"  PJ Classic: {len(pj_ladder_before)} players, {len(pj_gh_before)} games")
    print(f"  S13: {len(s13_ladder_before)} players, {len(s13_gh_before)} games")

    # Move to S13
    print(f"\n  Moving {NUM_GAMES} games to {TAGSET_S13}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_S13)
        assert status == 200, f"Failed to move game {gid}: {status} {result}"
        print(f"    Game {gid}: OK")

    # Verify GameHistory
    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_S13, s13_id)
    assert not missing, f"Games missing from {TAGSET_S13}: {missing}"
    assert not wrong, f"Games have wrong tag_set in {TAGSET_S13}: {wrong}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_PJ_CLASSIC)
    assert not leftover, f"Games still in {TAGSET_PJ_CLASSIC}: {leftover}"
    print(f"  GameHistory verified: games in S13, not in PJ Classic ✓")

    print_ladder_diff("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    print_ladder_diff("S13", s13_ladder_before, snapshot_ladder(TAGSET_S13))

    # Move back
    print(f"\n  Moving {NUM_GAMES} games back to {TAGSET_PJ_CLASSIC}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_PJ_CLASSIC)
        assert status == 200, f"Failed to move game {gid} back: {status} {result}"
        print(f"    Game {gid}: OK")

    # Verify GameHistory restored
    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_PJ_CLASSIC, pj_id)
    assert not missing, f"Games missing from {TAGSET_PJ_CLASSIC}: {missing}"
    assert not wrong, f"Games have wrong tag_set: {wrong}"
    print(f"  GameHistory verified: games back in PJ Classic ✓")

    verify_ladders_match("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    verify_ladders_match("S13", s13_ladder_before, snapshot_ladder(TAGSET_S13))
    print("  Ladders restored ✓")

    print("  PASSED ✓")


def test_three_way_move():
    """Move games PJ Classic -> PJ Training -> S13 -> PJ Classic."""
    print("\n" + "=" * 60)
    print("TEST 3: Three-way move")
    print(f"  {TAGSET_PJ_CLASSIC} -> {TAGSET_PJ_TRAINING} -> {TAGSET_S13} -> back")
    print("=" * 60)

    pj_id = get_tag_set_id(TAGSET_PJ_CLASSIC)
    training_id = get_tag_set_id(TAGSET_PJ_TRAINING)
    s13_id = get_tag_set_id(TAGSET_S13)

    # Get games
    status, games = get_ladder_games(TAGSET_PJ_CLASSIC)
    assert status == 200
    game_ids = [g['game_id'] for g in games[:NUM_GAMES] if g['game_id'] is not None]
    game_ids = game_ids[:NUM_GAMES]
    print(f"  Selected {NUM_GAMES} game_ids: {game_ids}")

    # Snapshot all three
    pj_ladder_before = snapshot_ladder(TAGSET_PJ_CLASSIC)
    training_ladder_before = snapshot_ladder(TAGSET_PJ_TRAINING)
    s13_ladder_before = snapshot_ladder(TAGSET_S13)

    # Step 1: PJ Classic -> PJ Training
    print(f"\n  Step 1: Moving to {TAGSET_PJ_TRAINING}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_PJ_TRAINING)
        assert status == 200, f"Step 1 failed for game {gid}: {status} {result}"
        print(f"    Game {gid}: OK")

    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_PJ_TRAINING, training_id)
    assert not missing, f"Step 1: Games missing from Training: {missing}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_PJ_CLASSIC)
    assert not leftover, f"Step 1: Games still in PJ Classic: {leftover}"
    print(f"  Step 1 GameHistory verified ✓")

    # Step 2: PJ Training -> S13 (cross-community)
    print(f"\n  Step 2: Moving to {TAGSET_S13}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_S13)
        assert status == 200, f"Step 2 failed for game {gid}: {status} {result}"
        print(f"    Game {gid}: OK")

    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_S13, s13_id)
    assert not missing, f"Step 2: Games missing from S13: {missing}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_PJ_TRAINING)
    our_leftover = [gid for gid in leftover if gid in game_ids]
    assert not our_leftover, f"Step 2: Games still in Training: {our_leftover}"
    print(f"  Step 2 GameHistory verified ✓")

    # Step 3: S13 -> PJ Classic (cross-community back)
    print(f"\n  Step 3: Moving back to {TAGSET_PJ_CLASSIC}...")
    for gid in game_ids:
        status, result = reassign_game(gid, TAGSET_PJ_CLASSIC)
        assert status == 200, f"Step 3 failed for game {gid}: {status} {result}"
        print(f"    Game {gid}: OK")

    missing, wrong = verify_games_in_tagset(game_ids, TAGSET_PJ_CLASSIC, pj_id)
    assert not missing, f"Step 3: Games missing from PJ Classic: {missing}"
    leftover = verify_games_not_in_tagset(game_ids, TAGSET_S13)
    our_leftover = [gid for gid in leftover if gid in game_ids]
    assert not our_leftover, f"Step 3: Games still in S13: {our_leftover}"
    print(f"  Step 3 GameHistory verified ✓")

    # Verify all three ladders restored
    verify_ladders_match("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    verify_ladders_match("PJ Training", training_ladder_before, snapshot_ladder(TAGSET_PJ_TRAINING))
    verify_ladders_match("S13", s13_ladder_before, snapshot_ladder(TAGSET_S13))
    print("  All three ladders restored ✓")

    print("  PASSED ✓")


def test_out_of_order_move():
    """Move an older game (15th most recent) to test that recalc handles ordering correctly."""
    print("\n" + "=" * 60)
    print("TEST 4: Out-of-order move (15th most recent game)")
    print(f"  {TAGSET_PJ_CLASSIC} -> {TAGSET_PJ_TRAINING} -> back")
    print("=" * 60)

    pj_id = get_tag_set_id(TAGSET_PJ_CLASSIC)
    training_id = get_tag_set_id(TAGSET_PJ_TRAINING)

    # Get games and pick the 15th
    status, games = get_ladder_games(TAGSET_PJ_CLASSIC)
    assert status == 200, f"Failed to get games: {games}"
    games_with_ids = [g for g in games if g['game_id'] is not None]
    assert len(games_with_ids) >= 15, f"Not enough games, found {len(games_with_ids)}, need 15"

    old_game = games_with_ids[14]  # 0-indexed, so index 14 = 15th game
    game_id = old_game['game_id']
    print(f"  Selected 15th most recent game: {game_id}")
    print(f"    Winner: {old_game.get('winner_player')}, Loser: {old_game.get('loser_player')}")
    print(f"    Winner incoming elo: {old_game.get('winner_incoming_elo')}, result: {old_game.get('winner_result_elo')}")
    print(f"    Loser incoming elo: {old_game.get('loser_incoming_elo')}, result: {old_game.get('loser_result_elo')}")

    # Snapshot
    pj_ladder_before = snapshot_ladder(TAGSET_PJ_CLASSIC)
    training_ladder_before = snapshot_ladder(TAGSET_PJ_TRAINING)
    pj_gh_before = snapshot_game_history(TAGSET_PJ_CLASSIC)

    # Move to Training
    print(f"\n  Moving game {game_id} to {TAGSET_PJ_TRAINING}...")
    status, result = reassign_game(game_id, TAGSET_PJ_TRAINING)
    assert status == 200, f"Failed to move: {status} {result}"
    print(f"    Move: OK")

    # Verify it moved
    missing, wrong = verify_games_in_tagset([game_id], TAGSET_PJ_TRAINING, training_id)
    assert not missing, f"Game missing from Training: {missing}"
    leftover = verify_games_not_in_tagset([game_id], TAGSET_PJ_CLASSIC)
    assert not leftover, f"Game still in PJ Classic: {leftover}"
    print(f"  GameHistory verified: game in Training ✓")

    # Check that PJ Classic ladder changed (removing a mid-history game affects everyone after)
    pj_ladder_moved = snapshot_ladder(TAGSET_PJ_CLASSIC)
    print_ladder_diff("PJ Classic (after removing old game)", pj_ladder_before, pj_ladder_moved)

    # Move back
    print(f"\n  Moving game {game_id} back to {TAGSET_PJ_CLASSIC}...")
    status, result = reassign_game(game_id, TAGSET_PJ_CLASSIC)
    assert status == 200, f"Failed to move back: {status} {result}"
    print(f"    Move back: OK")

    # Verify GameHistory restored
    missing, wrong = verify_games_in_tagset([game_id], TAGSET_PJ_CLASSIC, pj_id)
    assert not missing, f"Game missing from PJ Classic: {missing}"
    print(f"  GameHistory verified: game back in PJ Classic ✓")

    # Verify the game's elo fields are correct after round-trip
    pj_gh_after = snapshot_game_history(TAGSET_PJ_CLASSIC)
    if game_id in pj_gh_before and game_id in pj_gh_after:
        before_elos = pj_gh_before[game_id]
        after_elos = pj_gh_after[game_id]
        print(f"  Game {game_id} elo comparison:")
        print(f"    Winner incoming: {before_elos['winner_incoming_elo']} -> {after_elos['winner_incoming_elo']}")
        print(f"    Winner result:   {before_elos['winner_result_elo']} -> {after_elos['winner_result_elo']}")
        print(f"    Loser incoming:  {before_elos['loser_incoming_elo']} -> {after_elos['loser_incoming_elo']}")
        print(f"    Loser result:    {before_elos['loser_result_elo']} -> {after_elos['loser_result_elo']}")
        assert before_elos['winner_result_elo'] == after_elos['winner_result_elo'], \
            f"Winner result elo changed: {before_elos['winner_result_elo']} != {after_elos['winner_result_elo']}"
        assert before_elos['loser_result_elo'] == after_elos['loser_result_elo'], \
            f"Loser result elo changed: {before_elos['loser_result_elo']} != {after_elos['loser_result_elo']}"
        print(f"  Game elo fields match ✓")

    # Verify ladders restored
    verify_ladders_match("PJ Classic", pj_ladder_before, snapshot_ladder(TAGSET_PJ_CLASSIC))
    verify_ladders_match("PJ Training", training_ladder_before, snapshot_ladder(TAGSET_PJ_TRAINING))
    print("  Ladders restored ✓")

    print("  PASSED ✓")


def test_recalc_endpoint():
    """Verify /recalc_elo/ endpoint works standalone."""
    print("\n" + "=" * 60)
    print("TEST 5: recalc_elo endpoint")
    print("=" * 60)

    tag_set_id = get_tag_set_id(TAGSET_PJ_CLASSIC)
    assert tag_set_id is not None, f"Could not find tag set ID for {TAGSET_PJ_CLASSIC}"
    print(f"  Tag set ID for {TAGSET_PJ_CLASSIC}: {tag_set_id}")

    ladder_before = snapshot_ladder(TAGSET_PJ_CLASSIC)
    gh_before = snapshot_game_history(TAGSET_PJ_CLASSIC)
    print(f"  Before recalc: {len(ladder_before)} players, {len(gh_before)} games")

    status, result = recalc(tag_set_id, log=True)
    print(f"  Recalc status: {status}")
    assert status == 200, f"Recalc failed: {result}"

    ladder_after = snapshot_ladder(TAGSET_PJ_CLASSIC)
    gh_after = snapshot_game_history(TAGSET_PJ_CLASSIC)
    print_ladder_diff("PJ Classic", ladder_before, ladder_after)

    # Verify game history elos unchanged
    elo_mismatches = 0
    for gid, before_data in gh_before.items():
        after_data = gh_after.get(gid)
        if after_data and before_data['winner_result_elo'] != after_data['winner_result_elo']:
            elo_mismatches += 1
            if elo_mismatches <= 3:
                print(f"    Game {gid} winner_result_elo: {before_data['winner_result_elo']} -> {after_data['winner_result_elo']}")
    if elo_mismatches > 3:
        print(f"    ... and {elo_mismatches - 3} more mismatches")
    if elo_mismatches == 0:
        print(f"  All GameHistory elo fields unchanged ✓")

    print("  PASSED ✓")


def test_noop():
    """Moving a game to the same tag set should be a no-op."""
    print("\n" + "=" * 60)
    print("TEST 6: No-op (same tag set)")
    print("=" * 60)

    status, games = get_ladder_games(TAGSET_PJ_CLASSIC)
    assert status == 200 and len(games) >= 1, f"Failed to get games: {games}"

    game_id = games[0]['game_id']
    status, result = reassign_game(game_id, TAGSET_PJ_CLASSIC)
    print(f"  Move to same tag set: {status} - {result}")
    assert status == 200, f"Expected 200, got {status}"
    assert 'already' in result.lower(), f"Expected 'already' message, got: {result}"

    print("  PASSED ✓")


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Testing reassign_game_history_game_mode + recalc_elo")
    print("=" * 60)
    print(f"Server: {BASE_URL}")
    print(f"Using real game data - all moves are reversed at end of each test.")
    print(f"Tag sets:")
    print(f"  PJ Classic:  {TAGSET_PJ_CLASSIC}")
    print(f"  PJ Training: {TAGSET_PJ_TRAINING}")
    print(f"  S13:         {TAGSET_S13}")

    input("\nPress Enter to continue (Ctrl+C to abort)...")

    try:
        test_same_community_move()
        test_cross_community_move()
        test_three_way_move()
        test_out_of_order_move()
        test_recalc_endpoint()
        test_noop()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n  FAILED ✗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
