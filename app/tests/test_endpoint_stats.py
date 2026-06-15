"""
Tests for GET /stats/

Run against local server (default) or override with BASE_URL env var:
    BASE_URL=http://hangar51.tailcedf4f.ts.net:5000 pytest app/tests/test_endpoint_stats.py

Response format: {'Stats': {<optional nesting> → {Batting|Pitching|Misc|Fielding: {stat_key: value}}}}

Tests are anchored to S13SuperstarsOff — a completed season with stable data.
A small limit_games=1 is used on most fixture calls to keep response times short.
"""

import pytest

S13_TAG = 'S13SuperstarsOff'

BATTING_SUMMARY_KEYS = {
    'summary_walks_bb', 'summary_walks_hbp', 'summary_strikeouts',
    'summary_singles', 'summary_doubles', 'summary_triples',
    'summary_homeruns', 'summary_rbi', 'summary_at_bats',
    'summary_hits', 'star_hits', 'summary_bases_stolen',
}
BATTING_CONTACT_KEYS = {
    'outs', 'foul_hits', 'fair_hits', 'sour_hits', 'nice_hits',
    'perfect_hits', 'singles', 'doubles', 'triples', 'homeruns',
    'sacflys', 'gidps', 'strikeouts', 'plate_appearances', 'rbi',
}
BATTING_KEYS = BATTING_SUMMARY_KEYS | BATTING_CONTACT_KEYS

PITCHING_KEYS = {
    'batters_faced', 'runs_allowed', 'hits_allowed', 'strikeouts_pitched',
    'star_pitches_thrown', 'outs_pitched', 'walks_bb', 'walks_hbp',
    'total_pitches', 'balls', 'strikes',
}

MISC_KEYS = {'away_wins', 'away_loses', 'home_wins', 'home_loses', 'game_appearances'}

FIELDING_POSITION_KEYS = {
    'pitches_per_p', 'pitches_per_c', 'pitches_per_1b', 'pitches_per_2b',
    'pitches_per_3b', 'pitches_per_ss', 'pitches_per_lf', 'pitches_per_cf',
    'pitches_per_rf',
    'outs_per_p', 'outs_per_c', 'outs_per_1b', 'outs_per_2b', 'outs_per_3b',
    'outs_per_ss', 'outs_per_lf', 'outs_per_cf', 'outs_per_rf',
    'big_plays',
}
FIELDING_ACTION_KEYS = {'jump_catches', 'diving_catches', 'wall_jumps', 'swap_successes', 'bobbles'}
FIELDING_KEYS = FIELDING_POSITION_KEYS | FIELDING_ACTION_KEYS

STAT_CATEGORIES = {'Batting', 'Pitching', 'Misc', 'Fielding'}


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sample_stats(server, base_url):
    """Stats for one S13 game, no extra grouping flags."""
    r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1'})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch /stats/ (status {r.status_code})')
    return r.json()


@pytest.fixture(scope='module')
def sample_game_id(sample_game):
    """Integer game_id from the shared S13 sample game."""
    return sample_game['game_id']


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_returns_stats_key(self, server, base_url, sample_stats):
        assert 'Stats' in sample_stats

    def test_stats_is_dict(self, server, base_url, sample_stats):
        assert isinstance(sample_stats['Stats'], dict)

    def test_default_response_has_all_four_categories(self, server, base_url, sample_stats):
        missing = STAT_CATEGORIES - set(sample_stats['Stats'].keys())
        assert not missing, f'Missing stat categories: {missing}'

    def test_each_category_is_dict(self, server, base_url, sample_stats):
        for cat, data in sample_stats['Stats'].items():
            assert isinstance(data, dict), f'Category {cat!r} is not a dict'

    def test_stat_values_are_numeric(self, server, base_url, sample_stats):
        for cat, data in sample_stats['Stats'].items():
            for key, val in data.items():
                assert isinstance(val, (int, float)), (
                    f'{cat}.{key} value {val!r} is not numeric'
                )


# ---------------------------------------------------------------------------
# Expected stat keys per category
# ---------------------------------------------------------------------------

class TestBattingStatKeys:
    def test_batting_has_summary_keys(self, server, base_url, sample_stats):
        batting = sample_stats['Stats']['Batting']
        missing = BATTING_SUMMARY_KEYS - set(batting.keys())
        assert not missing, f'Batting missing summary keys: {missing}'

    def test_batting_has_contact_keys(self, server, base_url, sample_stats):
        batting = sample_stats['Stats']['Batting']
        missing = BATTING_CONTACT_KEYS - set(batting.keys())
        assert not missing, f'Batting missing contact keys: {missing}'

    def test_batting_at_bats_non_negative(self, server, base_url, sample_stats):
        assert sample_stats['Stats']['Batting']['summary_at_bats'] >= 0

    def test_batting_plate_appearances_non_negative(self, server, base_url, sample_stats):
        assert sample_stats['Stats']['Batting']['plate_appearances'] >= 0


class TestPitchingStatKeys:
    def test_pitching_has_all_expected_keys(self, server, base_url, sample_stats):
        pitching = sample_stats['Stats']['Pitching']
        missing = PITCHING_KEYS - set(pitching.keys())
        assert not missing, f'Pitching missing keys: {missing}'

    def test_pitching_outs_non_negative(self, server, base_url, sample_stats):
        assert sample_stats['Stats']['Pitching']['outs_pitched'] >= 0

    def test_pitching_total_pitches_positive(self, server, base_url, sample_stats):
        assert sample_stats['Stats']['Pitching']['total_pitches'] > 0


class TestMiscStatKeys:
    def test_misc_has_all_expected_keys(self, server, base_url, sample_stats):
        misc = sample_stats['Stats']['Misc']
        missing = MISC_KEYS - set(misc.keys())
        assert not missing, f'Misc missing keys: {missing}'

    def test_misc_game_appearances_positive(self, server, base_url, sample_stats):
        assert sample_stats['Stats']['Misc']['game_appearances'] > 0


class TestFieldingStatKeys:
    def test_fielding_has_position_keys(self, server, base_url, sample_stats):
        fielding = sample_stats['Stats']['Fielding']
        missing = FIELDING_POSITION_KEYS - set(fielding.keys())
        assert not missing, f'Fielding missing position keys: {missing}'

    def test_fielding_has_action_keys(self, server, base_url, sample_stats):
        fielding = sample_stats['Stats']['Fielding']
        missing = FIELDING_ACTION_KEYS - set(fielding.keys())
        assert not missing, f'Fielding missing action keys: {missing}'


# ---------------------------------------------------------------------------
# Stat exclusion flags
# ---------------------------------------------------------------------------

class TestStatExclusion:
    def test_exclude_batting_removes_batting(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'exclude_batting': '1'})
        assert r.status_code == 200
        assert 'Batting' not in r.json()['Stats']

    def test_exclude_pitching_removes_pitching(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'exclude_pitching': '1'})
        assert r.status_code == 200
        assert 'Pitching' not in r.json()['Stats']

    def test_exclude_misc_removes_misc(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'exclude_misc': '1'})
        assert r.status_code == 200
        assert 'Misc' not in r.json()['Stats']

    def test_exclude_fielding_removes_fielding(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'exclude_fielding': '1'})
        assert r.status_code == 200
        assert 'Fielding' not in r.json()['Stats']

    def test_exclude_all_but_batting_returns_only_batting(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1',
            'exclude_pitching': '1', 'exclude_misc': '1', 'exclude_fielding': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        assert 'Batting' in stats
        assert 'Pitching' not in stats
        assert 'Misc' not in stats
        assert 'Fielding' not in stats


# ---------------------------------------------------------------------------
# Grouping dimensions
# ---------------------------------------------------------------------------

class TestGroupingByUser:
    def test_by_user_nests_under_username(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'by_user': '1'})
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_key = list(stats.keys())[0]
        assert isinstance(first_key, str)
        assert STAT_CATEGORIES <= set(stats[first_key].keys())

    def test_by_user_username_filter_limits_to_one_user(self, server, base_url, any_username):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'username': any_username, 'by_user': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        assert list(stats.keys()) == [any_username]


class TestGroupingByChar:
    def test_by_char_nests_under_char_name(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1', 'by_char': '1'})
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_key = list(stats.keys())[0]
        assert isinstance(first_key, str)
        sub = stats[first_key]
        assert STAT_CATEGORIES <= set(sub.keys())

    def test_by_char_char_id_filter_returns_fewer_chars(self, server, base_url):
        r_all = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '5', 'by_char': '1'})
        r_mario = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '5', 'by_char': '1', 'char_id': '0',
        })
        assert r_mario.status_code == 200
        assert len(r_mario.json()['Stats']) <= len(r_all.json()['Stats'])


class TestGroupingByGame:
    def test_by_game_nests_under_game_id(self, server, base_url, sample_game_id):
        r = server.get(f'{base_url}/stats/', params={'games': sample_game_id, 'by_game': '1'})
        assert r.status_code == 200
        stats = r.json()['Stats']
        assert str(sample_game_id) in stats
        assert STAT_CATEGORIES <= set(stats[str(sample_game_id)].keys())

    def test_by_game_single_explicit_game_returns_1_game(self, server, base_url, sample_game_id):
        # Explicit games= pins the result to exactly one game.
        r = server.get(f'{base_url}/stats/', params={'games': sample_game_id, 'by_game': '1'})
        assert r.status_code == 200
        assert len(r.json()['Stats']) == 1

    def test_limit_games_1_resolves_a_single_game(self, server, base_url):
        # Regression: limit_games was dropped on the /stats/ game-resolution path
        # in v1.6.1. by_game nests one entry per resolved game, so limit_games=1
        # must collapse the result to a single game.
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_game': '1',
        })
        assert r.status_code == 200
        assert len(r.json()['Stats']) == 1

    def test_default_no_limit_games_caps_at_50(self, server, base_url):
        # With no limit_games, /stats/ resolves at most the newest 50 games
        # (the shared get_game_ids default) instead of the entire tag.
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'by_game': '1'})
        assert r.status_code == 200
        assert len(r.json()['Stats']) <= 50

    def test_false_limit_games_exceeds_default(self, server, base_url):
        # limit_games=False opts out of the 50 default and returns the whole tag,
        # so it resolves at least as many games as the default-capped request.
        r_default = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'by_game': '1'})
        r_all = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'by_game': '1', 'limit_games': 'False',
        })
        assert r_default.status_code == 200
        assert r_all.status_code == 200
        assert len(r_all.json()['Stats']) >= len(r_default.json()['Stats'])


class TestGroupingByRosterOrder:
    def test_by_roster_order_nests_correctly(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_roster_order': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        # Roster positions are 0-8 integers; JSON keys are strings
        for key in stats.keys():
            assert key.isdigit() or key == str(int(key))

    def test_by_roster_order_returns_9_entries_per_game(self, server, base_url, sample_game_id):
        r = server.get(f'{base_url}/stats/', params={'games': sample_game_id, 'by_roster_order': '1'})
        assert r.status_code == 200
        # 9 roster positions (0-8); both teams' chars at each position collapse into the same key
        assert len(r.json()['Stats']) == 9


# ---------------------------------------------------------------------------
# Stat-specific grouping dimensions
# ---------------------------------------------------------------------------

class TestGroupingByBattingHand:
    def test_by_batting_hand_nests_batting_under_left_right(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_batting_hand': '1', 'by_user': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        batting = stats[first_user].get('Batting', {})
        hand_keys = set(batting.keys())
        assert hand_keys <= {'Left', 'Right'}, f'Unexpected batting hand keys: {hand_keys}'
        assert hand_keys, 'No batting hand groupings found'

    def test_by_batting_hand_does_not_affect_pitching_grouping(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_batting_hand': '1', 'by_user': '1',
        })
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        pitching = stats[first_user].get('Pitching', {})
        # Pitching should still have numeric stat keys, not Left/Right
        assert 'Left' not in pitching
        assert 'Right' not in pitching


class TestGroupingByFieldingHand:
    def test_by_fielding_hand_nests_pitching_under_left_right(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_fielding_hand': '1', 'by_user': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        pitching = stats[first_user].get('Pitching', {})
        hand_keys = set(pitching.keys())
        assert hand_keys <= {'Left', 'Right'}, f'Unexpected fielding hand keys: {hand_keys}'

    def test_by_fielding_hand_does_not_affect_batting_grouping(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_fielding_hand': '1', 'by_user': '1',
        })
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        batting = stats[first_user].get('Batting', {})
        # Batting should have numeric stat keys, not Left/Right
        assert 'Left' not in batting or isinstance(batting.get('Left'), (int, float))


# ---------------------------------------------------------------------------
# Optional computed stats
# ---------------------------------------------------------------------------

class TestOptionalStats:
    def test_include_pitcher_wins_adds_field(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '5', 'include_pitcher_wins': '1', 'by_user': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        assert 'pitcher_wins' in stats[first_user]['Pitching']

    def test_include_pitcher_wins_absent_by_default(self, server, base_url, sample_stats):
        assert 'pitcher_wins' not in sample_stats['Stats']['Pitching']

    def test_include_runs_scored_adds_field(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '5', 'include_runs_scored': '1', 'by_user': '1',
        })
        assert r.status_code == 200
        stats = r.json()['Stats']
        first_user = list(stats.keys())[0]
        assert 'runs_scored' in stats[first_user]['Batting']

    def test_include_runs_scored_absent_by_default(self, server, base_url, sample_stats):
        assert 'runs_scored' not in sample_stats['Stats']['Batting']

    def test_pitcher_wins_is_non_negative(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'limit_games': '5', 'include_pitcher_wins': '1', 'by_user': '1',
        })
        stats = r.json()['Stats']
        for username, user_stats in stats.items():
            wins = user_stats['Pitching'].get('pitcher_wins', 0)
            assert wins >= 0, f'{username} has negative pitcher_wins'


# ---------------------------------------------------------------------------
# by_swing grouping (Batting only)
# ---------------------------------------------------------------------------

class TestGroupingBySwing:
    def test_by_swing_adds_swing_type_level_under_batting(self, server, base_url, sample_game_id):
        r = server.get(f'{base_url}/stats/', params={
            'games': sample_game_id, 'by_swing': '1',
        })
        assert r.status_code == 200
        batting = r.json()['Stats'].get('Batting', {})
        # Should have swing-type sub-keys instead of raw stat keys
        assert batting, 'Batting is empty'
        first_key = list(batting.keys())[0]
        # Swing type names are strings like 'Slap', 'Charge', 'Star', etc.
        assert isinstance(first_key, str)


# ---------------------------------------------------------------------------
# Username filter on stats
# ---------------------------------------------------------------------------

class TestUsernameFilter:
    def test_username_filter_returns_200(self, server, base_url, any_username):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'username': any_username,
        })
        assert r.status_code == 200

    def test_unknown_username_returns_400(self, server, base_url):
        # get_game_ids() processes username via resolve_names() which aborts 400
        # before the stats-level username lookup (which would be 404) can run
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'username': '__no_such_user_xyzzy__',
        })
        assert r.status_code == 400

    def test_multiple_usernames_returns_combined_stats(self, server, base_url, two_usernames):
        user_a, user_b = two_usernames
        r = server.get(f'{base_url}/stats/', params=[
            ('tag', S13_TAG), ('username', user_a), ('username', user_b), ('by_user', '1'),
        ])
        assert r.status_code == 200
        stats = r.json()['Stats']
        assert user_a in stats
        assert user_b in stats


# ---------------------------------------------------------------------------
# Character ID filter
# ---------------------------------------------------------------------------

class TestCharIdFilter:
    def test_valid_char_id_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'char_id': '0',  # Mario
        })
        assert r.status_code == 200

    def test_invalid_char_id_string_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'char_id': 'mario',
        })
        assert r.status_code == 400

    def test_char_id_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={
            'tag': S13_TAG, 'char_id': '999',
        })
        assert r.status_code == 400

    def test_multiple_char_ids_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params=[
            ('tag', S13_TAG), ('char_id', '0'), ('char_id', '1'), ('by_char', '1'),
        ])
        assert r.status_code == 200
        stats = r.json()['Stats']
        assert len(stats) <= 2


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_invalid_game_id_string_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'games': 'notanint'})
        assert r.status_code == 400

    def test_nonexistent_game_id_returns_404(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'games': '9999999999999'})
        assert r.status_code == 404

    def test_exclude_tag_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'exclude_tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_unknown_tag_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tag-based game filtering passes through to stats
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_valid_tag_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '5'})
        assert r.status_code == 200

    def test_stats_scale_with_more_games(self, server, base_url):
        r1 = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '1'})
        r5 = server.get(f'{base_url}/stats/', params={'tag': S13_TAG, 'limit_games': '5'})
        assert r1.status_code == 200
        assert r5.status_code == 200
        # More games → more at-bats
        ab1 = r1.json()['Stats']['Batting']['summary_at_bats']
        ab5 = r5.json()['Stats']['Batting']['summary_at_bats']
        assert ab5 >= ab1
