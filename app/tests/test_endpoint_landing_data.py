"""
Tests for GET /landing_data/

Run against local server (default) or override with BASE_URL env var:
    BASE_URL=http://hangar51.tailcedf4f.ts.net:5000 pytest app/tests/test_endpoint_landing_data.py

Response format: {'Data': [ {event row dict}, ... ]} where each row carries a
`game_id`. The endpoint resolves the /games/ filters (tags/users/limit_games/…)
to a set of games, expands those to events, then returns per-event detail.

Regression anchor: in v1.6.1 `limit_games` was silently dropped on the
internal game-resolution path, so a tag-scoped request resolved every game in
the tag and ran an unbounded join until it hit statement_timeout (surfaced as a
misleading 408 "Invalid GameID"). TestLimitGames locks in that limit_games is
honored again; TestErrorCodes locks in the corrected 400/404 codes.

Tests are anchored to S13SuperstarsOff — a completed season with stable data.
"""

import pytest

S13_TAG = 'S13SuperstarsOff'


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sample_landing_data(server, base_url):
    """landing_data for a single S13 game (limit_games=1). Skips if empty."""
    r = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': '1'})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch /landing_data/ (status {r.status_code})')
    data = r.json().get('Data', [])
    if not data:
        pytest.skip('No landing_data rows for the S13 sample game')
    return data


@pytest.fixture(scope='module')
def sample_event_id(server, base_url, sample_game):
    """A real event id, pulled from /events/ for the shared S13 sample game."""
    r = server.get(f'{base_url}/events/', params={'games': sample_game['game_id']})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch events (status {r.status_code})')
    events = r.json()
    for event_map in events.values():
        for event_id in event_map.values():
            return event_id
    pytest.skip('No events found for the S13 sample game')


def _distinct_game_ids(data):
    return {row['game_id'] for row in data}


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_returns_data_key(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        assert 'Data' in r.json()

    def test_data_is_a_list(self, server, base_url, sample_landing_data):
        assert isinstance(sample_landing_data, list)

    def test_rows_are_dicts_with_game_id(self, server, base_url, sample_landing_data):
        for row in sample_landing_data:
            assert isinstance(row, dict)
            assert 'game_id' in row

    def test_rows_carry_expected_fields(self, server, base_url, sample_landing_data):
        expected = {'game_id', 'event_num', 'batter_char_id', 'pitcher_char_id'}
        for row in sample_landing_data:
            assert expected <= set(row.keys()), f'Missing {expected - set(row.keys())}'

    def test_empty_filters_with_no_matching_events_returns_empty(self, server, base_url, sample_game):
        # inning=49 is valid (cMAX_INNING=50) but virtually never occurs → empty result
        r = server.get(f'{base_url}/landing_data/', params={
            'games': sample_game['game_id'], 'inning': '49',
        })
        assert r.status_code == 200
        assert r.json() == {}


# ---------------------------------------------------------------------------
# limit_games parameter  (regression: dropped in v1.6.1)
# ---------------------------------------------------------------------------

class TestLimitGames:
    def test_limit_games_1_resolves_at_most_one_game(self, server, base_url):
        # The core regression: before the fix this ignored limit_games, resolved
        # the entire tag, and timed out (non-200) instead of returning one game.
        r = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        assert len(_distinct_game_ids(r.json()['Data'])) <= 1

    def test_more_games_yields_at_least_as_many_games(self, server, base_url):
        r1 = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': '1'})
        r3 = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': '3'})
        assert r1.status_code == 200
        assert r3.status_code == 200
        g1 = _distinct_game_ids(r1.json()['Data'])
        g3 = _distinct_game_ids(r3.json()['Data'])
        assert len(g1) <= 1
        assert len(g3) <= 3
        assert len(g3) >= len(g1)


# ---------------------------------------------------------------------------
# Explicit events filter
# ---------------------------------------------------------------------------

class TestEventsFilter:
    def test_single_event_id_returns_only_that_event(self, server, base_url, sample_event_id):
        r = server.get(f'{base_url}/landing_data/', params={'events': sample_event_id})
        assert r.status_code == 200
        data = r.json().get('Data', [])
        # An event maps to at most one landing_data row (LEFT JOIN on fielder),
        # but some events (e.g. strikeouts) have no contact row and drop out.
        assert len(data) <= 1


# ---------------------------------------------------------------------------
# Error codes  (regression: these all used to return a misleading 408)
# ---------------------------------------------------------------------------

class TestErrorCodes:
    def test_invalid_event_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'events': 'notanint'})
        assert r.status_code == 400

    def test_nonexistent_event_id_returns_404(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'events': '999999999999'})
        assert r.status_code == 404

    def test_unknown_tag_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_unknown_username_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'username': '__no_such_user_xyzzy__'})
        assert r.status_code == 400

    def test_invalid_limit_games_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/landing_data/', params={'tag': S13_TAG, 'limit_games': 'notanumber'})
        assert r.status_code == 400
