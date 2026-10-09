"""Unit tests for the RE24 computation in app/re24.py.

These need no running server and no database -- app/re24.py imports nothing.
Run them with:

    pytest app/tests/test_re24.py

The games below are made up and small enough to check by hand. The job itself was
checked on a copy of the full database against an independent implementation:
every game type's pitches and runs matched in all 96 states; see the pull request.
"""
import importlib.util
import pathlib

import pytest

# Loaded by path rather than as `app.re24`, so the test does not depend on
# anything app/re24.py doesn't import itself. conftest.py still imports the app
# package, so install requirements.txt as usual.
_PATH = pathlib.Path(__file__).resolve().parents[1] / 're24.py'
_spec = importlib.util.spec_from_file_location('re24', _PATH)
re24 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(re24)


def pitch(inning, half, outs, runners, away, home):
    '''A pitch tuple from a runners code (1st = 1, 2nd = 2, 3rd = 4).'''
    return (inning, half, outs, bool(runners & 1), bool(runners & 2), bool(runners & 4), away, home)


# --- runners code -------------------------------------------------------------

@pytest.mark.parametrize('on_1st, on_2nd, on_3rd, code', [
    (False, False, False, 0), (True, False, False, 1), (False, True, False, 2),
    (True, True, False, 3), (False, False, True, 4), (True, False, True, 5),
    (False, True, True, 6), (True, True, True, 7),
])
def test_runners_code(on_1st, on_2nd, on_3rd, code):
    assert re24.runners_code(on_1st, on_2nd, on_3rd) == code


def test_runners_code_takes_runner_ids():
    # The job passes "runner_on_N IS NOT NULL"; ids or None work the same way.
    assert re24.runners_code(1234, None, 99) == 5


# --- complete pitch logs ------------------------------------------------------

def test_complete_log():
    log = [pitch(1, 0, 0, 0, 0, 0)] * 9 + [pitch(9, 1, 2, 0, 3, 2)]
    assert re24.log_is_complete(log, innings_played=9, box_pitches=10)


def test_empty_log_is_not_complete():
    assert not re24.log_is_complete([], innings_played=9, box_pitches=150)


def test_game_without_a_box_score_or_an_inning_is_not_complete():
    log = [pitch(1, 0, 0, 0, 0, 0)] * 10
    assert not re24.log_is_complete(log, innings_played=1, box_pitches=None)
    assert not re24.log_is_complete(log, innings_played=0, box_pitches=10)


def test_log_that_stops_before_the_last_inning_is_not_complete():
    # e.g. a 9-inning game logged only through the 1st
    log = [pitch(1, 0, 0, 0, 0, 0)] * 12
    assert not re24.log_is_complete(log, innings_played=9, box_pitches=12)


def test_log_missing_too_many_pitches_is_not_complete():
    log = [pitch(9, 0, 0, 0, 0, 0)] * 89
    assert not re24.log_is_complete(log, innings_played=9, box_pitches=100)
    assert re24.log_is_complete(log + [pitch(9, 1, 0, 0, 0, 0)], innings_played=9, box_pitches=100)


# --- per-game observations ----------------------------------------------------

def test_runs_to_the_end_of_the_half_inning():
    # Top 1st: a solo homer on the 2nd pitch, then a 2-run homer on the last
    # pitch of the half. The bottom of the 1st opens with the away team up 3-0,
    # which is where the top half's runs are counted to.
    game = [
        pitch(1, 0, 0, 0, 0, 0),   # 0 outs, empty          -> 3 runs to come
        pitch(1, 0, 0, 0, 0, 0),   # solo homer             -> 3
        pitch(1, 0, 0, 0, 1, 0),   # 0 outs, empty, 1-0     -> 2
        pitch(1, 0, 1, 0, 1, 0),   # 1 out                  -> 2
        pitch(1, 0, 2, 1, 1, 0),   # 2 outs, runner on 1st, 2-run homer -> 2
        pitch(1, 1, 0, 0, 3, 0),   # bottom 1st opens 3-0
        pitch(1, 1, 1, 0, 3, 0),
    ]
    states = re24.game_states(game, final_away=3, final_home=1)
    assert states[(0, 0)] == (4, 3 + 3 + 2 + 1)  # 3 top pitches + bottom's first; home scores 1 after
    assert states[(1, 0)] == (2, 2 + 1)
    assert states[(2, 1)] == (1, 2)


def test_last_half_inning_counts_to_the_final_score():
    game = [
        pitch(1, 0, 0, 0, 0, 0),
        pitch(1, 1, 0, 0, 0, 0),
        pitch(1, 1, 0, 2, 0, 0),   # runner on 2nd; a hit scores him and ends the game
    ]
    states = re24.game_states(game, final_away=0, final_home=1)
    assert states[(0, 0)] == (2, 0 + 1)
    assert states[(0, 2)] == (1, 1)


def test_innings_after_the_8th_are_left_out():
    game = [pitch(8, 1, 0, 0, 2, 2), pitch(9, 0, 0, 0, 2, 2), pitch(9, 1, 0, 7, 2, 2)]
    states = re24.game_states(game, final_away=2, final_home=3)
    assert states == {(0, 0): (1, 0)}


def test_bad_out_counts_are_skipped():
    game = [pitch(1, 0, 3, 0, 0, 0), pitch(1, 0, None, 0, 0, 0), pitch(1, 0, 0, 0, 0, 0)]
    assert re24.game_states(game, final_away=0, final_home=0) == {(0, 0): (1, 0)}


def test_empty_game():
    assert re24.game_states([], final_away=0, final_home=0) == {}


# --- the table ----------------------------------------------------------------

def test_re24_rows():
    sums = {
        ('hazards', 0, 0): (3, 2),
        ('stars off', 2, 7): (6, 5),
        ('stars off', 0, 0): (200, 187),
        ('big balla', 1, 0): (0, 0),     # no pitches: no row
    }
    rows = re24.re24_rows(sums)
    assert [(r['gametype'], r['outs'], r['runners']) for r in rows] == [
        ('stars off', 0, 0), ('stars off', 2, 7), ('hazards', 0, 0)]
    assert rows[0] == {'gametype': 'stars off', 'outs': 0, 'runners': 0, 'xruns': 0.935, 'pitches': 200}
    assert rows[1]['xruns'] == 0.8333     # four decimals
    assert rows[2]['xruns'] == 0.6667
