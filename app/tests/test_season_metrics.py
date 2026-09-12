"""Unit tests for the season metric computation.

Unlike the other tests in this directory these need no running server and no
database -- app/season_metrics.py imports only `math`. Run them with:

    pytest app/tests/test_season_metrics.py

The expected values below are not invented. The adjusted ELO cases are four
real players whose live adjusted rating is known, and the percentile
checkpoints are taken from real Postgres percent_rank() output over the 80
qualified batters in the S7 barrel rate pool.
"""
import importlib.util
import pathlib

import pytest

# Loaded straight from the file rather than as `app.season_metrics`. Importing
# it through the package would execute app/__init__.py, which pulls in Flask,
# SQLAlchemy, JWT and APScheduler -- none of which this module needs, since it
# imports only `math`. Loading by path keeps the test honest about what the
# module actually depends on.
#
# It does NOT make the suite runnable without those packages: conftest.py in
# this directory is resolved as part of the `app` package, so pytest imports
# app/__init__.py before any test here runs. Install requirements.txt as usual.
_PATH = pathlib.Path(__file__).resolve().parents[1] / 'season_metrics.py'
_spec = importlib.util.spec_from_file_location('season_metrics', _PATH)
season_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(season_metrics)

adjusted_elo = season_metrics.adjusted_elo
build_rows = season_metrics.build_rows
percentile_ranks = season_metrics.percentile_ranks
qualifies = season_metrics.qualifies
cMETRIC_RULES = season_metrics.cMETRIC_RULES
cSEASON_METRICS = season_metrics.cSEASON_METRICS


# --- adjusted ELO ----------------------------------------------------------

# (rating, wins, games, live adjusted value)
KNOWN_PLAYERS = [
    (2076, 50, 55, 1982),   # Toasty,         mid-S9 snapshot
    (1415,  7, 19, 1026),   # Clutch1908,     S9 Superstars Off game 19
    (1795, 26, 32, 1636),   # Muddy,          S15 Superstars Off
    (1848, 15, 18, 1561),   # BalambTransfer, S15 Superstars Off
]


@pytest.mark.parametrize('rating,wins,games,expected', KNOWN_PLAYERS)
def test_adjusted_elo_matches_live_values(rating, wins, games, expected):
    """Within half a point of what the live system reports for each player."""
    assert adjusted_elo(rating, wins, games) == pytest.approx(expected, abs=0.5)


def test_adjusted_elo_survives_zero_games():
    """games=0 must not raise. The +1 on player_games is what makes it total."""
    assert adjusted_elo(1500, 0, 0) is not None


def test_adjusted_elo_returns_none_without_a_rating():
    assert adjusted_elo(None, 5, 10) is None


def test_adjusted_elo_may_go_negative():
    """A low rating on one game is penalised past zero. Left unclamped so it
    still sorts correctly as a ranking score."""
    assert adjusted_elo(200, 0, 1) < 0


def test_adjusted_elo_penalty_never_vanishes():
    """Even at a high game count the adjusted value stays below the raw one."""
    assert adjusted_elo(1557, 48, 83) < 1557


# --- percentile ranking ----------------------------------------------------

def test_percentile_matches_postgres_percent_rank():
    """Checkpoints from the real S7 barrel rate pool of 80 players."""
    ranks = percentile_ranks(list(range(80)), higher_is_better=True)
    assert ranks[0] == pytest.approx(0.00, abs=0.005)
    assert ranks[1] == pytest.approx(1.27, abs=0.005)
    assert ranks[2] == pytest.approx(2.53, abs=0.005)
    assert ranks[75] == pytest.approx(94.94, abs=0.005)
    assert ranks[79] == pytest.approx(100.00, abs=0.005)


def test_lower_is_better_is_inverted():
    """The smallest value must read 100, not 0."""
    assert percentile_ranks([1, 2, 3], higher_is_better=False) == [100.0, 50.0, 0.0]


def test_ties_take_the_lower_rank():
    """Matches percent_rank(): tied values share the rank of the first of them."""
    assert percentile_ranks([5, 5, 9], higher_is_better=True) == [0.0, 0.0, 100.0]


def test_single_qualifier_scores_100():
    """percent_rank() would return 0 here, which would label a lone qualifier
    'worst'. We deviate deliberately."""
    assert percentile_ranks([0.5], higher_is_better=True) == [100.0]


def test_empty_pool():
    assert percentile_ranks([], higher_is_better=True) == []


def test_order_of_input_is_preserved():
    """Callers zip the result back onto their own row order."""
    assert percentile_ranks([9, 1, 5], higher_is_better=True) == [100.0, 0.0, 50.0]


# --- qualification ---------------------------------------------------------

def test_games_floor_excludes_below_threshold():
    assert not qualifies('bat_barrel_pct', games=9, denominator=500)
    assert qualifies('bat_barrel_pct', games=10, denominator=500)


def test_denominator_floor_applies_on_top_of_games():
    """Charge timing needs 25 swings as well as 10 games."""
    assert not qualifies('bat_charge_timing_pct', games=40, denominator=24)
    assert qualifies('bat_charge_timing_pct', games=40, denominator=25)


def test_empty_denominator_never_qualifies():
    """A rate over zero events is undefined however many games were played."""
    assert not qualifies('bat_chase_pct', games=100, denominator=0)


def test_every_metric_has_a_rule():
    assert set(cSEASON_METRICS) == set(cMETRIC_RULES)


# --- row building ----------------------------------------------------------

def _user(games, counts=None, rating=1500, wins=5, elo_games=None):
    return {
        'games': games,
        'elo_rating': rating,
        'elo_wins': wins,
        'elo_games': games if elo_games is None else elo_games,
        'counts': counts or {},
    }


def test_every_user_gets_a_row_for_every_metric():
    """An absent row means 'not computed'. Not qualifying is a row, not a gap."""
    rows = build_rows({1: _user(20), 2: _user(3)})
    assert len(rows) == 2 * len(cSEASON_METRICS)


def test_unqualified_rows_carry_no_percentile():
    rows = build_rows({1: _user(3, {'bat_chase_pct': (60, 200)})})
    chase = [r for r in rows if r['metric'] == 'bat_chase_pct'][0]
    assert chase['qualified'] is False
    assert chase['percentile'] is None
    assert chase['value'] == pytest.approx(0.3)


def test_ranking_ignores_unqualified_players():
    """A player below the games floor must not shift anyone else's percentile."""
    qualified_only = build_rows({
        1: _user(20, {'bat_barrel_pct': (80, 100)}),
        2: _user(20, {'bat_barrel_pct': (60, 100)}),
    })
    with_a_straggler = build_rows({
        1: _user(20, {'bat_barrel_pct': (80, 100)}),
        2: _user(20, {'bat_barrel_pct': (60, 100)}),
        3: _user(2, {'bat_barrel_pct': (99, 100)}),
    })

    def pct(rows, user_id):
        return [r for r in rows
                if r['metric'] == 'bat_barrel_pct' and r['user_id'] == user_id][0]['percentile']

    assert pct(qualified_only, 1) == pct(with_a_straggler, 1) == 100.0
    assert pct(qualified_only, 2) == pct(with_a_straggler, 2) == 0.0
    assert pct(with_a_straggler, 3) is None


def test_qualified_rows_carry_the_pool_they_were_ranked_over():
    """percentile is meaningless without its denominator, so it is stored."""
    rows = build_rows({
        1: _user(20, {'bat_barrel_pct': (80, 100)}),
        2: _user(20, {'bat_barrel_pct': (60, 100)}),
        3: _user(20, {'bat_barrel_pct': (40, 100)}),
    })
    barrel = [r for r in rows if r['metric'] == 'bat_barrel_pct']
    assert [r['pool_size'] for r in barrel] == [3, 3, 3]


def test_unqualified_rows_carry_no_pool_size():
    """Same rule as percentile: NULL means 'did not make the pool'."""
    rows = build_rows({1: _user(3, {'bat_chase_pct': (60, 200)})})
    chase = [r for r in rows if r['metric'] == 'bat_chase_pct'][0]
    assert chase['pool_size'] is None


def test_pool_size_differs_between_metrics():
    """Charge timing needs 25 swings on top of the games floor, so its pool is
    smaller than barrel rate's in the same season. Reporting one number for the
    whole season would be wrong."""
    rows = build_rows({
        1: _user(20, {'bat_barrel_pct': (80, 100), 'bat_charge_timing_pct': (20, 40)}),
        2: _user(20, {'bat_barrel_pct': (60, 100), 'bat_charge_timing_pct': (4, 8)}),
    })

    def pool(metric):
        return [r for r in rows if r['metric'] == metric and r['qualified']][0]['pool_size']

    assert pool('bat_barrel_pct') == 2
    assert pool('bat_charge_timing_pct') == 1


def test_stragglers_do_not_inflate_the_pool():
    """A player below the floor must not be counted in anyone's denominator."""
    rows = build_rows({
        1: _user(20, {'bat_barrel_pct': (80, 100)}),
        2: _user(20, {'bat_barrel_pct': (60, 100)}),
        3: _user(2, {'bat_barrel_pct': (99, 100)}),
    })
    barrel = [r for r in rows if r['metric'] == 'bat_barrel_pct']
    assert sorted(r['pool_size'] for r in barrel if r['qualified']) == [2, 2]
    assert [r['pool_size'] for r in barrel if not r['qualified']] == [None]


def test_general_metrics_have_no_numerator_or_denominator():
    rows = build_rows({1: _user(20)})
    for name in ('gen_games_played', 'gen_adjusted_elo'):
        row = [r for r in rows if r['metric'] == name][0]
        assert row['numerator'] is None
        assert row['denominator'] is None


def test_games_played_reports_the_game_count():
    rows = build_rows({1: _user(37)})
    row = [r for r in rows if r['metric'] == 'gen_games_played'][0]
    assert row['value'] == 37
    assert row['qualified'] is True


def test_elo_uses_rated_games_not_the_season_game_count():
    """The two counts differ: a player can appear in games with no rated row.
    The ELO formula must use the rated count."""
    same = build_rows({1: _user(30, rating=1795, wins=26, elo_games=30)})
    rated = build_rows({1: _user(30, rating=1795, wins=26, elo_games=32)})

    def elo(rows):
        return [r for r in rows if r['metric'] == 'gen_adjusted_elo'][0]['value']

    assert elo(same) != elo(rated)
    assert elo(rated) == pytest.approx(1636, abs=0.5)
