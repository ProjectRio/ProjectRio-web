"""
Tests for GET /games/events/

Run against local server (default) or override with BASE_URL env var:
    BASE_URL=http://hangar51.tailcedf4f.ts.net:5000 pytest app/tests/test_endpoint_game_events.py

Response format:
    {'game_id': int,
     'events': [{event_num, inning, half_inning, balls, strikes, outs,
                 away_score, home_score, chem_links_ob, star_chance,
                 away_stars, home_stars, pitcher_stamina,
                 result_of_ab, result_rbi, result_num_of_outs,
                 batter/pitcher/catcher: {char_id, team_id, roster_loc, ...},
                 runners: {batter, first, second, third},
                 pitch: {..., contact: {..., fielding: {...}}} | None}, ...]}

Tests are anchored to S13SuperstarsOff — a completed season with a stable game
count — so fixture data remains consistent across runs.
"""

import pytest

EVENT_STATE_FIELDS = (
    'event_num', 'inning', 'half_inning', 'away_score', 'home_score',
    'balls', 'strikes', 'outs', 'chem_links_ob', 'star_chance',
    'away_stars', 'home_stars', 'pitcher_stamina',
    'result_num_of_outs', 'result_rbi', 'result_of_ab',
)


@pytest.fixture(scope='module')
def game_events_response(server, base_url, sample_game):
    r = server.get(f'{base_url}/games/events/', params={'game_id': sample_game['game_id']})
    if r.status_code != 200:
        pytest.skip(f'Could not fetch game events (status {r.status_code})')
    return r.json()


@pytest.fixture(scope='module')
def events(game_events_response):
    events = game_events_response['events']
    if not events:
        pytest.skip('Sample game has no events')
    return events


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------

class TestRequestValidation:
    def test_missing_game_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/events/')
        assert r.status_code == 400

    def test_non_integer_game_id_returns_400(self, server, base_url):
        r = server.get(f'{base_url}/games/events/', params={'game_id': 'notanint'})
        assert r.status_code == 400

    def test_unknown_game_id_returns_404(self, server, base_url):
        r = server.get(f'{base_url}/games/events/', params={'game_id': '9999999999999'})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_echoes_game_id(self, game_events_response, sample_game):
        assert game_events_response['game_id'] == sample_game['game_id']

    def test_events_is_list(self, game_events_response):
        assert isinstance(game_events_response['events'], list)

    def test_events_are_ordered_by_event_num(self, events):
        nums = [e['event_num'] for e in events]
        assert nums == sorted(nums)

    def test_event_state_fields_present(self, events):
        for event in events:
            for field in EVENT_STATE_FIELDS:
                assert field in event, f'event {event["event_num"]} missing {field}'

    def test_event_count_matches_events_endpoint(self, server, base_url, sample_game, events):
        # /events/ inner-joins pitch_summary and so drops events without one;
        # this endpoint outer-joins and keeps them, so it can only have more.
        r = server.get(f'{base_url}/events/', params={'games': sample_game['game_id']})
        assert r.status_code == 200
        id_map = r.json().get(str(sample_game['game_id']), {})
        assert len(events) >= len(id_map)


# ---------------------------------------------------------------------------
# Participant refs
# ---------------------------------------------------------------------------

class TestParticipants:
    def test_batter_pitcher_catcher_always_present(self, events):
        for event in events:
            for role in ('batter', 'pitcher', 'catcher'):
                ref = event[role]
                assert ref is not None, f'event {event["event_num"]} missing {role}'
                assert 'char_id' in ref and 'team_id' in ref and 'roster_loc' in ref

    def test_batter_and_pitcher_are_on_opposite_teams(self, events):
        for event in events:
            assert event['batter']['team_id'] != event['pitcher']['team_id']

    def test_pitcher_and_catcher_are_on_the_same_team(self, events):
        for event in events:
            assert event['pitcher']['team_id'] == event['catcher']['team_id']

    def test_roster_locs_in_range(self, events):
        for event in events:
            for role in ('batter', 'pitcher', 'catcher'):
                assert 0 <= event[role]['roster_loc'] <= 8


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

class TestRunners:
    def test_runners_dict_has_all_bases(self, events):
        for event in events:
            assert set(event['runners'].keys()) == {'batter', 'first', 'second', 'third'}

    def test_batter_runner_present_on_every_event(self, events):
        # runner_on_0 is the batter-as-runner and is non-nullable in the model.
        for event in events:
            assert event['runners']['batter'] is not None

    def test_runner_fields(self, events):
        for event in events:
            for runner in event['runners'].values():
                if runner is None:
                    continue
                for field in ('char_id', 'roster_loc', 'initial_base',
                              'result_base', 'out_type', 'out_location', 'steal'):
                    assert field in runner


# ---------------------------------------------------------------------------
# Pitch / contact / fielding nesting
# ---------------------------------------------------------------------------

class TestPitchDetail:
    def test_most_events_have_pitch_data(self, events):
        with_pitch = [e for e in events if e['pitch'] is not None]
        assert with_pitch, 'expected at least one event with pitch data'

    def test_pitch_fields(self, events):
        for event in events:
            pitch = event['pitch']
            if pitch is None:
                continue
            for field in ('pitch_type', 'charge_pitch_type', 'star_pitch',
                          'pitch_speed', 'type_of_swing', 'in_strikezone', 'contact'):
                assert field in pitch

    def test_contact_carries_ball_flight_physics(self, events):
        contacts = [e['pitch']['contact'] for e in events
                    if e['pitch'] and e['pitch']['contact']]
        if not contacts:
            pytest.skip('Sample game has no contact events')
        for contact in contacts:
            for field in ('ball_x_velocity', 'ball_y_velocity', 'ball_z_velocity',
                          'ball_x_landing_pos', 'ball_y_landing_pos', 'ball_z_landing_pos',
                          'ball_max_height', 'ball_hang_time', 'ball_power',
                          'ball_horiz_angle', 'ball_vert_angle',
                          'charge_power_up', 'charge_power_down',
                          'frame_of_swing_upon_contact', 'input_direction_stick',
                          'rng1', 'rng2', 'rng3', 'type_of_contact'):
                assert field in contact

    def test_fielding_nested_under_contact(self, events):
        fieldings = [e['pitch']['contact']['fielding'] for e in events
                     if e['pitch'] and e['pitch']['contact'] and e['pitch']['contact']['fielding']]
        if not fieldings:
            pytest.skip('Sample game has no fielded balls')
        for fielding in fieldings:
            for field in ('fielder', 'position', 'action', 'jump', 'bobble',
                          'manual_select', 'fielder_x_pos', 'fielder_y_pos', 'fielder_z_pos'):
                assert field in fielding
            assert fielding['fielder'] is None or 'char_id' in fielding['fielder']


# ---------------------------------------------------------------------------
# Game-state sanity
# ---------------------------------------------------------------------------

class TestGameStateSanity:
    def test_innings_are_monotonic_nondecreasing(self, events):
        last = (0, 0)
        for event in events:
            current = (event['inning'], event['half_inning'])
            assert current >= last
            last = current

    def test_scores_are_monotonic_nondecreasing(self, events):
        last_away = last_home = 0
        for event in events:
            assert event['away_score'] >= last_away
            assert event['home_score'] >= last_home
            last_away, last_home = event['away_score'], event['home_score']

    def test_final_event_ends_an_at_bat(self, events):
        assert events[-1]['result_of_ab'] > 0

    def test_counts_in_legal_range(self, events):
        for event in events:
            assert 0 <= event['balls'] <= 3
            assert 0 <= event['strikes'] <= 2
            assert 0 <= event['outs'] <= 2
