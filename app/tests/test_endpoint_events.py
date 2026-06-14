"""
Tests for GET /events/

Run against local server (default) or override with BASE_URL env var:
    BASE_URL=http://hangar51.tailcedf4f.ts.net:5000 pytest app/tests/test_endpoint_events.py

Response format: {game_id_str: {event_num_str: event_id_int}}

Tests are anchored to S13SuperstarsOff — a completed season with a stable game
count — so fixture data remains consistent across runs.
"""

import pytest

S13_TAG = 'S13SuperstarsOff'

# char_id 0 = Mario; appears in every S13 game as a team captain slot.
MARIO_CHAR_ID = 0


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sample_event_game_id(sample_game):
    """Integer game_id pulled from the shared S13 sample game fixture."""
    return sample_game['game_id']


@pytest.fixture(scope='module')
def sample_events(server, base_url, sample_event_game_id):
    """All events for a single known S13 game.  Skips if the game has no events."""
    r = server.get(f'{base_url}/events/', params={'games': sample_event_game_id})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch events (status {r.status_code})')
    data = r.json()
    if not data:
        pytest.skip(f'No events found for game {sample_event_game_id}')
    return data


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_returns_dict(self, server, base_url, sample_events):
        assert isinstance(sample_events, dict)

    def test_outer_keys_are_game_id_strings(self, server, base_url, sample_events):
        for key in sample_events:
            assert isinstance(key, str)
            int(key)  # must be parseable as int

    def test_inner_values_are_dicts(self, server, base_url, sample_events):
        for game_id, event_map in sample_events.items():
            assert isinstance(event_map, dict), f'Expected dict for game {game_id}'

    def test_inner_keys_are_event_num_strings(self, server, base_url, sample_events):
        for game_id, event_map in sample_events.items():
            for key in event_map:
                assert isinstance(key, str)
                int(key)  # must be parseable as int

    def test_inner_values_are_event_id_ints(self, server, base_url, sample_events):
        for game_id, event_map in sample_events.items():
            for event_num, event_id in event_map.items():
                assert isinstance(event_id, int), (
                    f'event_id for game {game_id} event {event_num} is not int'
                )

    def test_events_are_positive_integers(self, server, base_url, sample_events):
        for game_id, event_map in sample_events.items():
            for event_num, event_id in event_map.items():
                assert event_id > 0


# ---------------------------------------------------------------------------
# limit_events parameter
# ---------------------------------------------------------------------------

class TestLimitEvents:
    def _count_events(self, data):
        return sum(len(events) for events in data.values())

    def test_limit_1_returns_at_most_1_event(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '1'})
        assert r.status_code == 200
        assert self._count_events(r.json()) <= 1

    def test_limit_10_returns_at_most_10_events(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '10'})
        assert r.status_code == 200
        assert self._count_events(r.json()) <= 10

    def test_default_limit_is_1000(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG})
        assert r.status_code == 200
        assert self._count_events(r.json()) <= 1000

    def test_larger_limit_returns_more_events(self, server, base_url):
        r_small = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '5'})
        r_large = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '50'})
        assert r_small.status_code == 200
        assert r_large.status_code == 200
        assert self._count_events(r_large.json()) >= self._count_events(r_small.json())

    def test_invalid_limit_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': 'notanint'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Filtering by explicit game IDs
# ---------------------------------------------------------------------------

class TestGameFilter:
    def test_single_game_id_returns_only_that_game(self, server, base_url, sample_event_game_id):
        r = server.get(f'{base_url}/events/', params={'games': sample_event_game_id})
        assert r.status_code == 200
        data = r.json()
        assert str(sample_event_game_id) in data
        assert len(data) == 1

    def test_nonexistent_game_id_returns_404(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'games': '9999999999999'})
        assert r.status_code == 404

    def test_invalid_game_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'games': 'notanint'})
        assert r.status_code == 400

    def test_multiple_game_ids_returns_all_of_them(self, server, base_url, sample_games):
        if len(sample_games) < 2:
            pytest.skip('Need at least 2 S13 games')
        ids = [g['game_id'] for g in sample_games[:2]]
        r = server.get(f'{base_url}/events/', params=[('games', ids[0]), ('games', ids[1])])
        assert r.status_code == 200
        data = r.json()
        for gid in ids:
            assert str(gid) in data, f'game {gid} missing from events response'


# ---------------------------------------------------------------------------
# Tag filter (uses game-level filtering)
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_valid_tag_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '10'})
        assert r.status_code == 200

    def test_unknown_tag_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_tag_filter_returns_events(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'limit_events': '10'})
        assert r.json()


# ---------------------------------------------------------------------------
# Username filter
# ---------------------------------------------------------------------------

class TestUsernameFilter:
    def test_valid_username_returns_200(self, server, base_url, any_username):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'username': any_username, 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_unknown_username_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_vs_username_unknown_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'vs_username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_users_as_batter_flag_returns_200(self, server, base_url, any_username):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'username': any_username,
            'users_as_batter': '1', 'limit_events': '20',
        })
        assert r.status_code == 200

    def test_users_as_pitcher_flag_returns_200(self, server, base_url, any_username):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'username': any_username,
            'users_as_pitcher': '1', 'limit_events': '20',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Character filters
# ---------------------------------------------------------------------------

class TestCharacterFilter:
    def test_valid_batter_char_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'batter_char': MARIO_CHAR_ID, 'limit_events': '20',
        })
        assert r.status_code == 200

    def test_valid_pitcher_char_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'pitcher_char': MARIO_CHAR_ID, 'limit_events': '20',
        })
        assert r.status_code == 200

    def test_batter_char_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'batter_char': '999'})
        assert r.status_code == 400

    def test_pitcher_char_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'pitcher_char': '999'})
        assert r.status_code == 400

    def test_invalid_batter_char_string_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'batter_char': 'mario'})
        assert r.status_code == 400

    def test_multiple_batter_chars_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params=[
            ('tag', S13_TAG), ('batter_char', '0'), ('batter_char', '1'), ('limit_events', '20'),
        ])
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Situation filters (inning, outs, balls, strikes, half_inning)
# ---------------------------------------------------------------------------

class TestSituationFilter:
    def test_inning_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'inning': '1', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_outs_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'outs': '0', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_balls_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'balls': '3', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_strikes_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'strikes': '2', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_half_inning_0_top_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'half_inning': '0', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_half_inning_1_bottom_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'half_inning': '1', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_outs_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'outs': '99'})
        assert r.status_code == 400

    def test_balls_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'balls': '99'})
        assert r.status_code == 400

    def test_strikes_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'strikes': '99'})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Contact and swing type filters
# ---------------------------------------------------------------------------

class TestContactFilter:
    def test_contact_0_ground_ball_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'contact': '0', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_contact_5_no_contact_sentinel_returns_200(self, server, base_url):
        # contact=5 is the sentinel for "no contact" (miss/foul), stored as NULL
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'contact': '5', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_contact_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'contact': '99'})
        assert r.status_code == 400

    def test_swing_type_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'swing': '0', 'limit_events': '50',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Scoring context filters
# ---------------------------------------------------------------------------

class TestScoringContextFilter:
    def test_star_chance_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'star_chance': '1', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_final_result_filter_returns_200(self, server, base_url):
        # final_result=0 = non-out result (common)
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'final_result': '0', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_final_result_out_of_range_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={'tag': S13_TAG, 'final_result': '99'})
        assert r.status_code == 400

    def test_chem_link_filter_returns_200(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'chem_link': '0', 'limit_events': '50',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------

class TestCombinedFilters:
    def test_tag_plus_batter_char_plus_inning(self, server, base_url):
        r = server.get(f'{base_url}/events/', params={
            'tag': S13_TAG, 'batter_char': str(MARIO_CHAR_ID),
            'inning': '1', 'limit_events': '50',
        })
        assert r.status_code == 200

    def test_games_plus_outs_plus_strikes(self, server, base_url, sample_event_game_id):
        r = server.get(f'{base_url}/events/', params={
            'games': sample_event_game_id, 'outs': '0', 'strikes': '0',
        })
        assert r.status_code == 200

    def test_valid_filters_with_no_matching_events_returns_empty(self, server, base_url, sample_event_game_id):
        # inning=49 is valid (cMAX_INNING=50) but virtually never occurs → empty result
        r = server.get(f'{base_url}/events/', params={
            'games': sample_event_game_id,
            'inning': '49',
            'limit_events': '10',
        })
        assert r.status_code == 200
        assert r.json() == {}
