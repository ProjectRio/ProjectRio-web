"""
Tests for GET /star_chances/

Run against local server (default) or override with BASE_URL env var:
    BASE_URL=http://hangar51.tailcedf4f.ts.net:5000 pytest app/tests/test_endpoint_star_chances.py

Response format: {'Data': [ {..., 'games': N}, ... ]}. By default a single
aggregate row; with by_inning=true, one row per (inning, half_inning). The
`games` column is COUNT(DISTINCT event.game_id) over the resolved events.

/star_chances/ resolves games through the same get_game_ids path as
/landing_data/, so it shares the v1.6.1 limit_games regression and the same
408 error-code masking. These tests lock in both fixes.

Tests are anchored to S13SuperstarsOff — a completed season with stable data.
"""

import pytest

S13_TAG = 'S13SuperstarsOff'


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_returns_data_key(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        assert 'Data' in r.json()

    def test_rows_have_games_count(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        for row in r.json().get('Data', []):
            assert 'games' in row

    def test_by_inning_adds_inning_keys(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={
            'tag': S13_TAG, 'limit_games': '1', 'by_inning': 'true',
        })
        assert r.status_code == 200
        for row in r.json().get('Data', []):
            assert 'inning' in row
            assert 'half_inning' in row


# ---------------------------------------------------------------------------
# limit_games parameter  (regression: dropped in v1.6.1)
# ---------------------------------------------------------------------------

class TestLimitGames:
    def test_limit_games_1_counts_at_most_one_game(self, server, base_url):
        # Before the fix this ignored limit_games and aggregated the whole tag.
        r = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': '1'})
        assert r.status_code == 200
        for row in r.json().get('Data', []):
            assert row['games'] <= 1

    def test_more_games_counts_at_least_as_many(self, server, base_url):
        r1 = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': '1'})
        r3 = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': '3'})
        assert r1.status_code == 200
        assert r3.status_code == 200
        games1 = max((row['games'] for row in r1.json().get('Data', [])), default=0)
        games3 = max((row['games'] for row in r3.json().get('Data', [])), default=0)
        assert games1 <= 1
        assert games3 <= 3
        assert games3 >= games1


# ---------------------------------------------------------------------------
# Error codes  (regression: these all used to return a misleading 408)
# ---------------------------------------------------------------------------

class TestErrorCodes:
    def test_invalid_event_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'events': 'notanint'})
        assert r.status_code == 400

    def test_nonexistent_event_id_returns_404(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'events': '999999999999'})
        assert r.status_code == 404

    def test_unknown_tag_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'tag': '__no_such_tag_xyzzy__'})
        assert r.status_code == 400

    def test_invalid_limit_games_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/star_chances/', params={'tag': S13_TAG, 'limit_games': 'notanumber'})
        assert r.status_code == 400
