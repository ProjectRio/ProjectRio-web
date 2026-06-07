"""
Tests for GET /games/

Run against local server (default):
    pytest app/tests/test_endpoint_games.py

All tests skip automatically if the server is not reachable (see conftest.py).
Tests that use the `sample_game`, `any_username`, `any_captain`, or `any_tag` fixtures
are anchored to S13SuperstarsOff — a completed season with a stable game count.
"""

import pytest

S13_TAG = 'S13SuperstarsOff'

# Keys every game object must contain regardless of optional flags.
REQUIRED_GAME_KEYS = {
    'game_id', 'stadium', 'date_time_start', 'date_time_end',
    'away_user', 'away_captain', 'away_roster', 'away_score',
    'home_user', 'home_captain', 'home_roster', 'home_score',
    'innings_played', 'innings_selected',
    'winner_incoming_elo', 'loser_incoming_elo',
    'winner_result_elo', 'loser_result_elo',
    'game_mode',
}

SCORING_PLAY_KEYS = {'inning', 'half_inning', 'event_num', 'result_rbi',
                     'result_of_ab', 'batter', 'pitcher', 'away_score',
                     'home_score', 'outs', 'runners'}


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_returns_games_key(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        assert 'games' in r.json()

    def test_game_has_all_required_keys(self, server, base_url, sample_game):
        missing = REQUIRED_GAME_KEYS - set(sample_game.keys())
        assert not missing, f'Missing keys in game response: {missing}'

    def test_away_roster_is_9_element_list(self, server, base_url, sample_game):
        assert isinstance(sample_game['away_roster'], list)
        assert len(sample_game['away_roster']) == 9

    def test_home_roster_is_9_element_list(self, server, base_url, sample_game):
        assert isinstance(sample_game['home_roster'], list)
        assert len(sample_game['home_roster']) == 9

    def test_scores_are_integers(self, server, base_url, sample_game):
        assert isinstance(sample_game['away_score'], int)
        assert isinstance(sample_game['home_score'], int)

    def test_innings_played_is_positive_integer(self, server, base_url, sample_game):
        assert isinstance(sample_game['innings_played'], int)
        assert sample_game['innings_played'] > 0


# ---------------------------------------------------------------------------
# Limit parameter
# ---------------------------------------------------------------------------

class TestLimitGames:
    def test_limit_1_returns_1_game(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert len(r.json()['games']) == 1

    def test_limit_5_returns_5_games(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '5'})
        assert len(r.json()['games']) == 5

    def test_default_limit_is_50(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG})
        assert len(r.json()['games']) <= 50

    def test_limit_500_returns_up_to_500_games(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '500'})
        assert r.status_code == 200
        assert len(r.json()['games']) <= 500

    def test_false_limit_returns_all_games(self, server, base_url):
        r_default = server.get(f'{base_url}/games/', params={'tag': S13_TAG})
        r_all = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': 'False'})
        assert len(r_all.json()['games']) >= len(r_default.json()['games'])

    def test_invalid_limit_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'limit_games': 'notanumber'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

class TestOrdering:
    def test_games_ordered_newest_first(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20'})
        games = r.json()['games']
        end_times = [g['date_time_end'] for g in games if g.get('date_time_end') is not None]
        assert end_times == sorted(end_times, reverse=True)


# ---------------------------------------------------------------------------
# Username filter
# ---------------------------------------------------------------------------

class TestUsernameFilter:
    def test_username_filter_returns_only_matching_games(self, server, base_url, any_username):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'username': any_username, 'limit_games': '20'})
        assert r.status_code == 200
        games = r.json()['games']
        assert games, f'No S13 games found for username={any_username!r}'
        for game in games:
            assert game['away_user'] == any_username or game['home_user'] == any_username

    def test_unknown_username_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_exclude_username_removes_user_from_results(self, server, base_url, any_username):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'exclude_username': any_username, 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_user'] != any_username
            assert game['home_user'] != any_username

    def test_exclude_unknown_username_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'exclude_username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_vs_username_all_returned_games_contain_vs_user(self, server, base_url, any_username):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'vs_username': any_username, 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_user'] == any_username or game['home_user'] == any_username

    def test_vs_username_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'vs_username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_username_and_vs_username_both_users_appear_in_every_game(self, server, base_url, two_usernames):
        user_a, user_b = two_usernames
        r = server.get(f'{base_url}/games/', params={
            'tag': S13_TAG, 'username': user_a, 'vs_username': user_b, 'limit_games': '20',
        })
        assert r.status_code == 200
        for game in r.json()['games']:
            users = {game['away_user'], game['home_user']}
            assert user_a in users, f'username {user_a!r} missing from game'
            assert user_b in users, f'vs_username {user_b!r} missing from game'


# ---------------------------------------------------------------------------
# Captain filter
# ---------------------------------------------------------------------------

class TestCaptainFilter:
    def test_captain_filter_returns_only_matching_games(self, server, base_url, any_captain):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'captain': any_captain, 'limit_games': '20'})
        assert r.status_code == 200
        games = r.json()['games']
        assert games, f'No S13 games found for captain={any_captain!r}'
        for game in games:
            assert game['away_captain'] == any_captain or game['home_captain'] == any_captain

    def test_unknown_captain_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'captain': '__no_such_captain_xyzzy__'})
        assert r.status_code == 400

    def test_exclude_captain_removes_captain_from_results(self, server, base_url, any_captain):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'exclude_captain': any_captain, 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_captain'] != any_captain
            assert game['home_captain'] != any_captain

    def test_exclude_unknown_captain_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'exclude_captain': '__no_such_captain_xyzzy__'})
        assert r.status_code == 400

    def test_vs_captain_all_returned_games_contain_vs_captain(self, server, base_url, any_captain):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'vs_captain': any_captain, 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_captain'] == any_captain or game['home_captain'] == any_captain

    def test_vs_captain_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'vs_captain': '__no_such_captain_xyzzy__'})
        assert r.status_code == 400

    def test_captain_and_vs_captain_both_captains_appear_in_every_game(self, server, base_url, two_captains):
        cap_a, cap_b = two_captains
        r = server.get(f'{base_url}/games/', params={
            'tag': S13_TAG, 'captain': cap_a, 'vs_captain': cap_b, 'limit_games': '20',
        })
        assert r.status_code == 200
        for game in r.json()['games']:
            captains = {game['away_captain'], game['home_captain']}
            assert cap_a in captains, f'captain {cap_a!r} missing from game'
            assert cap_b in captains, f'vs_captain {cap_b!r} missing from game'


# ---------------------------------------------------------------------------
# Time window filter
# ---------------------------------------------------------------------------

class TestTimeFilter:
    def test_end_time_upper_bounds_results(self, server, base_url, sample_game):
        cutoff = sample_game['date_time_end']
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'end_time': str(cutoff), 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['date_time_end'] <= cutoff

    def test_start_time_lower_bounds_results(self, server, base_url, sample_game):
        cutoff = sample_game['date_time_end']
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'start_time': str(cutoff), 'limit_games': '20'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['date_time_end'] >= cutoff

    def test_end_time_before_start_time_returns_400(self, server, base_url, sample_game):
        t = sample_game['date_time_end']
        r = server.get(f'{base_url}/games/', params={'start_time': str(t + 100), 'end_time': str(t)})
        assert r.status_code == 400

    def test_time_window_with_no_results_returns_empty_list(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'start_time': '9999999999'})
        assert r.status_code == 200
        assert r.json()['games'] == []

    def test_invalid_start_time_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'start_time': 'notanumber'})
        assert r.status_code == 400

    def test_invalid_end_time_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'end_time': 'notanumber'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Linescore
# ---------------------------------------------------------------------------

class TestLinescore:
    def test_linescore_not_present_by_default(self, server, base_url, sample_game):
        assert 'linescore' not in sample_game

    def test_linescore_present_when_requested(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '5', 'include_linescore': '1'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert 'linescore' in game

    def test_linescore_is_two_arrays(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '5', 'include_linescore': '1'})
        for game in r.json()['games']:
            ls = game['linescore']
            assert isinstance(ls, list) and len(ls) == 2, f'Expected [away, home] pair, got {ls!r}'
            away, home = ls
            assert isinstance(away, list)
            assert isinstance(home, list)

    def test_linescore_length_matches_innings_played(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '10', 'include_linescore': '1'})
        for game in r.json()['games']:
            away, home = game['linescore']
            assert len(away) == game['innings_played']
            assert len(home) == game['innings_played']

    def test_linescore_sums_match_game_score(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20', 'include_linescore': '1'})
        for game in r.json()['games']:
            away, home = game['linescore']
            assert sum(away) == game['away_score'], f'Away linescore sum mismatch in game {game["game_id"]}'
            home_runs = sum(x for x in home if x != 'X')
            assert home_runs == game['home_score'], f'Home linescore sum mismatch in game {game["game_id"]}'

    def test_linescore_walk_off_inning_shown_as_X(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '100', 'include_linescore': '1'})
        found_x = False
        for game in r.json()['games']:
            _, home = game['linescore']
            if home[-1] == 'X':
                found_x = True
                assert game['home_score'] > game['away_score'], (
                    f'X in final home inning but home did not win game {game["game_id"]}'
                )
        if not found_x:
            pytest.skip('No games with walk-off X found in sample — increase limit or seed data')


# ---------------------------------------------------------------------------
# Scoring plays
# ---------------------------------------------------------------------------

class TestScoringPlays:
    def test_scoring_plays_not_present_by_default(self, server, base_url, sample_game):
        assert 'scoring_plays' not in sample_game

    def test_scoring_plays_present_when_requested(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '5', 'include_scoring_plays': '1'})
        assert r.status_code == 200
        for game in r.json()['games']:
            assert 'scoring_plays' in game

    def test_scoring_play_has_required_keys(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20', 'include_scoring_plays': '1'})
        for game in r.json()['games']:
            for play in game['scoring_plays']:
                missing = SCORING_PLAY_KEYS - set(play.keys())
                assert not missing, f'Scoring play missing keys: {missing}'

    def test_scoring_play_runners_is_4_element_list(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20', 'include_scoring_plays': '1'})
        for game in r.json()['games']:
            for play in game['scoring_plays']:
                assert isinstance(play['runners'], list) and len(play['runners']) == 4

    def test_scoring_play_rbi_is_positive(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20', 'include_scoring_plays': '1'})
        for game in r.json()['games']:
            for play in game['scoring_plays']:
                assert play['result_rbi'] > 0

    def test_linescore_and_scoring_plays_can_be_requested_together(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={
            'tag': S13_TAG, 'limit_games': '5',
            'include_linescore': '1', 'include_scoring_plays': '1',
        })
        assert r.status_code == 200
        for game in r.json()['games']:
            assert 'linescore' in game
            assert 'scoring_plays' in game


# ---------------------------------------------------------------------------
# Tag filter
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_tag_filter_returns_200(self, server, base_url, any_tag):
        r = server.get(f'{base_url}/games/', params={'tag': any_tag, 'limit_games': '20'})
        assert r.status_code == 200

    def test_tag_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_exclude_tag_returns_200(self, server, base_url, any_tag):
        r = server.get(f'{base_url}/games/', params={'exclude_tag': any_tag, 'limit_games': '20'})
        assert r.status_code == 200

    def test_exclude_tag_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'exclude_tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_tag_and_exclude_tag_results_are_disjoint(self, server, base_url, any_tag):
        r_inc = server.get(f'{base_url}/games/', params={'tag': any_tag, 'limit_games': '500'})
        r_exc = server.get(f'{base_url}/games/', params={'exclude_tag': any_tag, 'limit_games': '500'})
        assert r_inc.status_code == 200
        assert r_exc.status_code == 200
        inc_ids = {g['game_id'] for g in r_inc.json()['games']}
        exc_ids = {g['game_id'] for g in r_exc.json()['games']}
        overlap = inc_ids & exc_ids
        assert not overlap, f'{len(overlap)} game(s) appear in both tag and exclude_tag results'


# ---------------------------------------------------------------------------
# Stadium filter
# ---------------------------------------------------------------------------

class TestStadiumFilter:
    def test_stadium_filter_returns_only_matching_games(self, server, base_url, sample_game):
        stadium_id = sample_game['stadium']
        r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'stadium': str(stadium_id), 'limit_games': '20'})
        assert r.status_code == 200
        games = r.json()['games']
        assert games, f'No S13 games found for stadium_id={stadium_id}'
        for game in games:
            assert game['stadium'] == stadium_id

    def test_invalid_stadium_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/', params={'stadium': 'notanumber'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Multiple filter values (getlist support)
# ---------------------------------------------------------------------------

class TestMultipleFilterValues:
    def test_multiple_usernames_returns_games_with_either_user(self, server, base_url, two_usernames):
        user_a, user_b = two_usernames
        r = server.get(f'{base_url}/games/', params=[
            ('tag', S13_TAG), ('username', user_a), ('username', user_b), ('limit_games', '20'),
        ])
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_user'] in (user_a, user_b) or game['home_user'] in (user_a, user_b)

    def test_multiple_captains_returns_games_with_either_captain(self, server, base_url, two_captains):
        cap_a, cap_b = two_captains
        r = server.get(f'{base_url}/games/', params=[
            ('tag', S13_TAG), ('captain', cap_a), ('captain', cap_b), ('limit_games', '20'),
        ])
        assert r.status_code == 200
        for game in r.json()['games']:
            assert game['away_captain'] in (cap_a, cap_b) or game['home_captain'] in (cap_a, cap_b)

    def test_multiple_tags_same_tag_twice_is_idempotent(self, server, base_url):
        r_single = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20'})
        r_double = server.get(f'{base_url}/games/', params=[
            ('tag', S13_TAG), ('tag', S13_TAG), ('limit_games', '20'),
        ])
        assert r_double.status_code == 200
        ids_single = [g['game_id'] for g in r_single.json()['games']]
        ids_double = [g['game_id'] for g in r_double.json()['games']]
        assert ids_single == ids_double
