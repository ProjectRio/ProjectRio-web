"""Unit tests for the competition_profile rules in app/competition_profile.py.

These need no running server and no database -- app/competition_profile.py
imports only `re`. Run them with:

    pytest app/tests/test_competition_profile.py

The names are real competition names. On the 198 competitions reviewed in 2026,
the series rule (profile_for_new) agreed with the review on every competition
it applied to (89 of 89).
"""
import importlib.util
import pathlib

import pytest

_PATH = pathlib.Path(__file__).resolve().parents[1] / 'competition_profile.py'
_spec = importlib.util.spec_from_file_location('competition_profile', _PATH)
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

STARS_OFF = frozenset({'disable superstars', 'enable hazardless', 'remove slice', 'draft snake 1222'})
ALL_ON = {flag: True for flag in cp.cFLAGS}


def reviewed(tag_set_id, name, kind, category, rules, **flags):
    row = {'tag_set_id': tag_set_id, 'competition': name, 'type': kind, 'category': category,
           'rules': frozenset(rules), 'status': 'reviewed'}
    row.update(ALL_ON)
    row.update(flags)
    return row


def tag_set(tag_set_id, name, kind):
    return {'id': tag_set_id, 'name': name, 'type': kind,
            'name_lowercase': ''.join(c for c in name if c.isalnum()).lower()}


# --- names ----------------------------------------------------------------------

@pytest.mark.parametrize('name, series', [
    ('S15 Superstars Off', 'superstars off'),
    ('S9 Superstars Off', 'superstars off'),
    ('Stars Off Hazardous, Season 7', 'stars off hazardous'),
    ('Stars On Showdown XXII', 'stars on showdown'),
    ('Stars On Showdown XXI', 'stars on showdown'),
    ('Cryo Classic Season 5', 'cryo classic'),
    ('Practice: SLICE 2026 Big Balla', 'practice slice big balla'),
    ('Netplay Superstars 25', 'netplay superstars'),
    ('Mid-Tier Mania 6', 'mid tier mania'),     # "mid" is not a roman numeral
    ('BBM13', 'bbm'),
])
def test_series_name(name, series):
    assert cp.series_name(name) == series


# --- type ---------------------------------------------------------------------

@pytest.mark.parametrize('rio_type, name, expected', [
    ('Season', 'S15 Superstars Off', 'Season'),
    ('League', 'MBA Champions League 2025', 'League'),
    ('Tournament', 'Netplay Superstars 25', 'Tournament'),
    ('Tournament', 'Practice: SLICE 2026 Big Balla', 'Exhibition'),
    ('Tournament', 'Friendly: SLICE 2023, Stars Off', 'Exhibition'),
    ('Tournament', 'Bobble: Non-bracket', 'Exhibition'),
    ('Test', 'BigBallTest', 'Exhibition'),
])
def test_profile_type(rio_type, name, expected):
    assert cp.profile_type(rio_type, tag_set(0, name, rio_type)['name_lowercase']) == expected


# --- rule tags ----------------------------------------------------------------

def test_rule_names_keeps_rule_tags_only():
    tags = [('Disable Superstars', 'Component'), (' Remove Slice ', 'Gecko Code'),
            ('S15 Superstars Off', 'Competition'), ('Netplay', 'Community')]
    assert cp.rule_names(tags) == {'disable superstars', 'remove slice'}


@pytest.mark.parametrize('rules, category', [
    ({'disable star skills', 'disable superstars'}, 'big balla'),
    ({'disable superstars', 'enable hazardless'}, 'stars off'),
    ({'disable superstars', "hazardless w/star pads on bowser's castle"}, 'stars off'),
    ({'disable superstars'}, 'hazards'),
    (set(), 'stars on'),
])
def test_suggested_category(rules, category):
    assert cp.suggested_category(frozenset(rules)) == category


def test_rule_signature_flags_significant_rules():
    assert cp.rule_signature(STARS_OFF) == ('stars off', False, False, False)
    assert cp.rule_signature(STARS_OFF | {'draft randoms'}) == ('stars off', True, False, False)
    assert cp.rule_signature(STARS_OFF | {'duplicate characters'}) == ('stars off', False, True, False)
    assert cp.rule_signature(STARS_OFF | {'some new mod'}) == ('stars off', False, False, True)


# --- new competitions ---------------------------------------------------------

SEASONS = [
    reviewed(208, 'S14 Superstars Off', 'Season', 'stars off', STARS_OFF),
    reviewed(223, 'S15 Superstars Off', 'Season', 'stars off', STARS_OFF),
    reviewed(50, 'Big Balla Randoms, Season 7', 'Season', 'big balla',
             {'disable star skills', 'disable superstars', 'draft randoms'}, q_pick_rates=False),
    reviewed(150, 'NNL Season 9', 'League', 'other', STARS_OFF | {'duplicate characters'},
             q_ranked=False),
]


def test_next_season_follows_the_newest_reviewed_one():
    row = cp.profile_for_new(tag_set(300, 'S16 Superstars Off', 'Season'), STARS_OFF, SEASONS)
    assert row['status'] == 'auto'
    assert row['category'] == 'stars off' and row['type'] == 'Season'
    assert all(row[flag] for flag in cp.cFLAGS)
    assert row['note'] == 'Follows S15 Superstars Off (same series, type and rules)'


def test_copied_flags_include_the_ones_turned_off():
    rules = frozenset({'disable star skills', 'disable superstars', 'draft randoms'})
    row = cp.profile_for_new(tag_set(301, 'Big Balla Randoms, Season 9', 'Season'), rules, SEASONS)
    assert row['status'] == 'auto' and row['q_pick_rates'] is False and row['q_league_stats'] is True


def test_a_new_rule_breaks_the_series():
    row = cp.profile_for_new(tag_set(302, 'S16 Superstars Off', 'Season'),
                             STARS_OFF | {'duplicate characters'}, SEASONS)
    assert row['status'] == 'pending'
    assert not any(row[flag] for flag in cp.cFLAGS)
    assert row['category'] == 'stars off'


def test_a_different_type_breaks_the_series():
    row = cp.profile_for_new(tag_set(303, 'S16 Superstars Off', 'Tournament'), STARS_OFF, SEASONS)
    assert row['status'] == 'pending'


def test_unknown_competition_waits_with_every_flag_off():
    row = cp.profile_for_new(tag_set(304, 'I Pick Your Team Invitational', 'Tournament'),
                             frozenset({'disable superstars'}), SEASONS)
    assert row['status'] == 'pending' and row['category'] == 'hazards'
    assert not any(row[flag] for flag in cp.cFLAGS)
    assert row['note'] == 'Not reviewed yet; its rule tags suggest hazards'


def test_series_rule_needs_a_name_to_match():
    row = cp.profile_for_new(tag_set(305, '2026', 'Season'), STARS_OFF,
                             [reviewed(1, '2025', 'Season', 'stars off', STARS_OFF)])
    assert row['status'] == 'pending'
