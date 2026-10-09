'''Rules for the competition_profile table: what each competition (tag set) is,
and what its games count toward.

A competition's category says which rules were played (Stars Off, Stars On, Big
Balla, Hazards or other); its q_ flags say whether its games are good data for
each kind of calculation. "Stars Off" covers a serious season ladder, an NPSS
bracket, and a tournament played on odd rules ("I pick your team and you pick
mine") alike -- the flags are what keep the last of those out of RE24.

  q_ranked           its games count toward ratings and ranking leaderboards
  q_league_stats     its games feed league calculations: RE24, linear weights
                     and wOBA weights, park factors, win probability
  q_player_stats     its games count in players' career stats
  q_character_stats  its games count in character performance stats
  q_pick_rates       players chose their own teams, so pick and win rates count

Every competition gets a row. A new one either continues a series an admin has
already reviewed (same name once season numbers, years and roman numerals are
taken out, same type, same significant rules), in which case it copies that
competition's decisions with status 'auto', or it waits as 'pending' with every
flag off -- counting nowhere -- until an admin decides.

This module imports nothing from the app, so it can be unit tested directly
(app/tests/test_competition_profile.py). Database access is in
competition_profile_db.py.
'''
import re

cCATEGORIES = ('stars off', 'stars on', 'big balla', 'hazards', 'other')
cTYPES = ('Season', 'League', 'Tournament', 'Exhibition')
cSTATUSES = ('pending', 'auto', 'reviewed')
cFLAGS = ('q_ranked', 'q_league_stats', 'q_player_stats', 'q_character_stats', 'q_pick_rates')

# Tag types that describe the rules a competition is played on. Rule tag names are
# compared lowercased with surrounding spaces removed (rule_names()).
cRULE_TAG_TYPES = frozenset({'Component', 'Gecko Code', 'Client Code', 'Test'})
cDISABLE_SUPERSTARS = 'disable superstars'
cDISABLE_STAR_SKILLS = 'disable star skills'
cHAZARDLESS = frozenset({'enable hazardless', "hazardless w/star pads on bowser's castle"})
cRANDOM_TEAMS = frozenset({'draft randoms', 'instant randoms'})
cDUPLICATES = frozenset({'duplicate characters gecko code', 'duplicate characters',
                         'duplicates and variants have chem', 'no captain required'})
# Every rule tag of the competitions that were reviewed as counting. A competition
# with any other rule tag is "modified" for the series match below, so a new
# edition that adds a game-changing code never inherits its predecessor's flags.
cSTANDARD_RULES = frozenset({
    # Game type
    cDISABLE_SUPERSTARS, cDISABLE_STAR_SKILLS, *cHAZARDLESS,
    # Quality-of-life and bug-fix codes
    'anti quick pitch', 'dash glitch fix', 'disable haze on every stadium',
    'enable game moderation', 'fix non-red toad hitboxes and bat reach',
    'manual fielder select 4.1', 'disable manual fielder select', 'monty mole 70 speed',
    'remove baserunner lockout', 'remove bowser castle screen shake',
    'remove dingus bunting', 'remove slice', 'show opponents batting order on swap screen',
    "star pitch doesn't subtract stamina", 'css manual team logo selection',
    'default drop spots off',
    # Game length
    'default nine innings', 'seven innings', 'five innings', "innings: users' choice",
    'unlimited extra innings', 'extra innings capped at 18',
    # Drafts, stadium picks and swaps
    'draft snake 1211', 'draft snake 1222', 'draft any', "draft: users' choice",
    'draft 1-2-1-2 (peach garden 1-2-2 draft)', 'draft 1-2-1-1, bowser banned',
    'bowser is banned', 'peach garden banned', 'pick order standard coin flip',
    'random home/away', 'random stadium', 'random stadium with option to veto yoshi park',
    'random stadium with optional re-roll', 'away bans stadium home selects',
    "stadium: users' choice", 'preassigned stadium',
    'fielder swap limit 1', 'fielder swap limit 1 plus 1', 'fielder swap limit 2',
    # Small stage tweaks
    'peach blocks all noteblocks', 'bowser castle - right thwomps down',
})

# Warm-ups are entered as tournaments but are exhibitions: they crown nobody.
cEXHIBITION_PREFIXES = ('practice', 'friendly')
cEXHIBITION_WORDS = ('nonbracket',)

_ROMAN = re.compile(r'^x{0,3}(ix|iv|v?i{0,3})$')


def rule_names(tags):
    '''The rule tag names among (name, tag_type) pairs, lowercased.'''
    return frozenset(name.strip().lower() for name, tag_type in tags
                     if tag_type in cRULE_TAG_TYPES and name)


def suggested_category(rules):
    '''The category a set of rule tags describes. Only ever a suggestion for a
    pending competition: tags alone matched the reviewed categories on about
    half of the competitions at review time.'''
    if cDISABLE_STAR_SKILLS in rules:
        return 'big balla'
    if cDISABLE_SUPERSTARS in rules:
        return 'stars off' if rules & cHAZARDLESS else 'hazards'
    return 'stars on'


def rule_signature(rules):
    '''What has to match for a new competition to continue a series: the category
    its tags describe, random teams, duplicate characters, and any rule outside
    the standard set.'''
    return (suggested_category(rules), bool(rules & cRANDOM_TEAMS),
            bool(rules & cDUPLICATES),
            bool(rules - cSTANDARD_RULES - cRANDOM_TEAMS - cDUPLICATES))


def profile_type(rio_type, name_lowercase):
    '''Season, League, Tournament or Exhibition. Exhibition covers warm-ups (names
    starting Practice or Friendly, or containing Non-bracket) and Rio's Test
    competitions.'''
    key = name_lowercase or ''
    if rio_type == 'Test' or key.startswith(cEXHIBITION_PREFIXES) or any(
            word in key for word in cEXHIBITION_WORDS):
        return 'Exhibition'
    return rio_type if rio_type in ('Season', 'League', 'Tournament') else 'Exhibition'


def series_name(name):
    '''A competition's name without season numbers, years or roman numerals:
    "S15 Superstars Off" -> "superstars off", "Stars On Showdown XXII" ->
    "stars on showdown", "Cryo Classic Season 5" -> "cryo classic".'''
    kept = []
    for word in re.sub(r'[^a-z0-9 ]', ' ', (name or '').lower()).split():
        word = re.sub(r'\d', '', word)
        if not word or word in ('season', 's') or _ROMAN.match(word):
            continue
        kept.append(word)
    return ' '.join(kept)


def profile_for_new(tag_set, rules, reviewed):
    '''The profile row for a competition that has none yet.

    tag_set   dict with id, name, name_lowercase and type (Rio's)
    rules     its rule tag names (rule_names())
    reviewed  the reviewed competitions, each a dict with tag_set_id, competition,
              type, category, the five flags and 'rules'

    A competition continuing a reviewed series copies the newest one's category
    and flags (status 'auto'). Anything else is 'pending' with every flag off and
    the category its rule tags suggest.
    '''
    own_type = profile_type(tag_set['type'], tag_set.get('name_lowercase'))
    own_series = series_name(tag_set['name'])
    own_signature = rule_signature(rules)
    matches = [r for r in reviewed
               if r['type'] == own_type
               and series_name(r['competition']) == own_series
               and rule_signature(r['rules']) == own_signature]
    row = {'tag_set_id': tag_set['id'], 'competition': tag_set['name'], 'type': own_type}
    if own_series and matches:
        previous = max(matches, key=lambda r: r['tag_set_id'])
        row.update({flag: bool(previous[flag]) for flag in cFLAGS})
        row.update(category=previous['category'], status='auto',
                   note='Follows {} (same series, type and rules)'.format(previous['competition']))
        return row
    row.update({flag: False for flag in cFLAGS})
    row.update(category=suggested_category(rules), status='pending',
               note='Not reviewed yet; its rule tags suggest {}'.format(suggested_category(rules)))
    return row
