"""
Shared pytest fixtures for ProjectRio-web endpoint tests.

All tests that talk to a live server use the `server` fixture, which:
  - Reads BASE_URL from the environment (defaults to http://127.0.0.1:5000).
  - Skips the entire test if the server is not reachable.

To run against a local server (default):
    pytest app/tests/
"""

import os
import pytest
import requests as _requests

# Completed season — no new games will be added, making fixture data stable.
S13_TAG = 'S13SuperstarsOff'


@pytest.fixture(scope='session')
def base_url():
    return os.getenv('BASE_URL', 'http://127.0.0.1:5000').rstrip('/')


@pytest.fixture(scope='session')
def server(base_url):
    """A requests.Session connected to base_url. Skips if server is unreachable."""
    session = _requests.Session()
    try:
        r = session.get(f'{base_url}/games/', params={'limit_games': '1'}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f'Server not reachable at {base_url}: {e}')
    yield session


@pytest.fixture(scope='session')
def sample_games(server, base_url):
    """Up to 20 S13 games. Skips if the DB is empty."""
    r = server.get(f'{base_url}/games/', params={'tag': S13_TAG, 'limit_games': '20'})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch S13 games (status {r.status_code})')
    games = r.json().get('games', [])
    if not games:
        pytest.skip('No S13 games in DB — seed with test data first')
    return games


@pytest.fixture(scope='session')
def sample_game(sample_games):
    return sample_games[0]


@pytest.fixture(scope='session')
def any_username(sample_games):
    """A username known to exist in the S13 dataset."""
    for g in sample_games:
        if g.get('away_user'):
            return g['away_user']
    pytest.skip('No non-null away_user found in S13 sample games')


@pytest.fixture(scope='session')
def two_usernames(sample_games):
    """Two distinct usernames from S13 games, for vs_username tests."""
    seen = []
    for g in sample_games:
        for u in (g.get('away_user'), g.get('home_user')):
            if u and u not in seen:
                seen.append(u)
            if len(seen) == 2:
                return seen[0], seen[1]
    pytest.skip('Could not find two distinct usernames in S13 sample games')


@pytest.fixture(scope='session')
def any_captain(sample_games):
    """A captain name known to exist in the S13 dataset."""
    for g in sample_games:
        if g.get('away_captain'):
            return g['away_captain']
    pytest.skip('No non-null away_captain found in S13 sample games')


@pytest.fixture(scope='session')
def two_captains(sample_games):
    """Two distinct captain names from S13 games, for vs_captain tests."""
    seen = []
    for g in sample_games:
        for c in (g.get('away_captain'), g.get('home_captain')):
            if c and c not in seen:
                seen.append(c)
            if len(seen) == 2:
                return seen[0], seen[1]
    pytest.skip('Could not find two distinct captain names in S13 sample games')


@pytest.fixture(scope='session')
def any_tag(server, base_url):
    """Returns the S13 tag name (a known stable tag)."""
    return S13_TAG
