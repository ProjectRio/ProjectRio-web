'''Computation of per-season advanced percentiles (the "Savant Sliders" set).

Split deliberately into two halves:

  * Pure functions -- percentile ranking, the higher/lower inversion, and the
    adjusted ELO formula. No database, no Flask. These hold all the logic that
    is easy to get subtly wrong, so they can be unit tested directly.
  * Database functions -- one aggregate pass per season, then a bulk upsert.

The aggregate is ONE statement on purpose. The production database caps
max_connections at 25 and managed-platform agents hold a large share of that,
so this must open one connection, do one scan, and close. Running a statement
per metric is what took the database down during design.

Metric definitions, floors and the reasoning behind them are documented in
savant_sliders_s7_validation.sql.
'''
import math


# --- the metric set --------------------------------------------------------
# Order matters only for presentation. The prefix groups a metric so a response
# can be split into batting / pitching / general without a lookup table.
cSEASON_METRICS = (
    'bat_barrel_pct',
    'bat_chase_pct',
    'bat_whiff_pct',
    'bat_ozone_contact_pct',
    'bat_k_pct',
    'bat_charge_timing_pct',
    'bat_slap_timing_pct',
    'bat_charge_down_input_pct',
    'pitch_barrels_allowed_pct',
    'pitch_whiff_pct',
    'pitch_k_pct',
    'pitch_hr_allowed_pct',
    'gen_adjusted_elo',
    'gen_games_played',
)


# --- character sets --------------------------------------------------------
# Charge Timing uses the original nine pull-power hitters. Charge Down-Input
# and the pitching home run rate use those nine plus King Boo and Wario: the
# 7-8-9 frame window that defines good charge timing does not suit those two,
# but stick input and home run prevention are measurable against any of them.
cCHARGE_TIMING_CHARS = ('bro(h)', 'bro(f)', 'bro(b)', 'bowser', 'petey',
                        'pianta(r)', 'pianta(y)', 'pianta(b)', 'dk')
cPOWER_CHARS = cCHARGE_TIMING_CHARS + ('king boo', 'wario')


# --- metric registry -------------------------------------------------------
# metric key -> (higher_is_better, min_games, min_denominator)
#
# min_games        floor on games played in the season -- the shared pool.
# min_denominator  extra floor on the metric's own denominator, for metrics
#                  restricted to a subset of characters, where playing plenty
#                  of games does not guarantee a usable sample.
cMIN_GAMES = 10

cMETRIC_RULES = {
    'bat_barrel_pct':            (True,  cMIN_GAMES, None),
    'bat_chase_pct':             (False, cMIN_GAMES, None),
    'bat_whiff_pct':             (False, cMIN_GAMES, None),
    'bat_ozone_contact_pct':     (True,  cMIN_GAMES, None),
    'bat_k_pct':                 (False, cMIN_GAMES, None),
    'bat_charge_timing_pct':     (True,  cMIN_GAMES, 25),
    'bat_slap_timing_pct':       (True,  cMIN_GAMES, None),
    'bat_charge_down_input_pct': (True,  cMIN_GAMES, 25),
    'pitch_barrels_allowed_pct': (False, cMIN_GAMES, None),
    'pitch_whiff_pct':           (True,  cMIN_GAMES, None),
    'pitch_k_pct':               (True,  cMIN_GAMES, None),
    # NOTE: the 50 floor here is a judgment call, not a confirmed decision.
    # Without it, two S7 players with 22 and 28 at-bats faced and zero home
    # runs allowed rank first and second on a 65-player board. Set to None to
    # stay purely on the games rule.
    'pitch_hr_allowed_pct':      (False, cMIN_GAMES, 50),
    'gen_adjusted_elo':          (True,  cMIN_GAMES, None),
    'gen_games_played':          (True,  cMIN_GAMES, None),
}

# Adjusted ELO constants, from the community's existing implementation.
cELO_BETA = 0.85
cELO_ALPHA = 0.1


# --- pure functions --------------------------------------------------------

def adjusted_elo(rating, wins, games):
    '''Community-adjusted rating. Returns None when it cannot be computed.

    `games` is the raw count of the player's rated games. The live system
    passes that count PLUS ONE into the formula. Verified against four players
    across three seasons: plus one reproduces the live value every time, and
    the raw count is short by one to two points. It also makes the formula
    total, since at zero games the raw count would divide by zero.

    The result can be negative for a low rating on very few games. That is left
    as-is rather than clamped, since it still sorts correctly as a ranking
    score.
    '''
    if rating is None or games is None or games < 0:
        return None
    player_games = games + 1
    confidence = cELO_BETA + ((1 - cELO_BETA) * (1 - math.exp(1 - (cELO_ALPHA * wins))))
    penalty = 500 * math.sqrt(math.log10(player_games + 1) / player_games)
    return confidence * (rating - penalty)


def percentile_ranks(values, higher_is_better):
    '''Map values to 0-100 percentiles where 100 is ALWAYS best.

    Matches Postgres percent_rank(): the worst value scores 0, the best scores
    100, and tied values all take the lower rank. For a lower-is-better metric
    the rank is inverted, so the lowest value still reads 100.

    A single-element pool returns 100.0 rather than percent_rank()'s 0, which
    would label a lone qualifier "worst".
    '''
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [100.0]

    # rank - 1, i.e. how many values are strictly smaller than this one
    strictly_below = {}
    for i, v in enumerate(sorted(values)):
        if v not in strictly_below:
            strictly_below[v] = i

    out = []
    for v in values:
        pr = strictly_below[v] / (n - 1)
        out.append((pr if higher_is_better else 1 - pr) * 100.0)
    return out


def qualifies(metric, games, denominator):
    '''Does this player meet the floor for this metric?'''
    _, min_games, min_den = cMETRIC_RULES[metric]
    if min_games is not None and (games or 0) < min_games:
        return False
    if min_den is not None and (denominator or 0) < min_den:
        return False
    # A rate with an empty denominator is undefined regardless of the floors.
    if denominator is not None and denominator <= 0:
        return False
    return True


def build_rows(per_user):
    '''Turn raw per-user counts into rows ready for the season_metric table.

    `per_user` maps user_id -> {
        'games':      int,            # distinct games in the season
        'elo_rating': int or None,    # result ELO on the most recent rated game
        'elo_wins':   int,
        'elo_games':  int,            # rated games, i.e. game_history rows
        'counts':     {metric: (numerator, denominator)},
    }

    Percentiles are ranked only over players who qualify for that metric, so a
    player below a floor gets a row with qualified=False, percentile=None and
    pool_size=None. Qualified rows carry the size of the pool they were ranked
    against, which differs per metric: the character-restricted metrics have
    their own extra floor, so far fewer players clear them. A percentile is not
    interpretable without it.
    Every user gets a row for every metric -- an absent row means "not yet
    computed", which is a different answer the bot needs to distinguish.
    '''
    rows = []
    for metric in cSEASON_METRICS:
        higher_is_better = cMETRIC_RULES[metric][0]

        staged = []
        for user_id, rec in per_user.items():
            if metric == 'gen_games_played':
                numerator = denominator = None
                value = rec['games']
            elif metric == 'gen_adjusted_elo':
                numerator = denominator = None
                value = adjusted_elo(rec['elo_rating'], rec['elo_wins'], rec['elo_games'])
            else:
                numerator, denominator = rec['counts'].get(metric, (0, 0))
                value = (numerator / denominator) if denominator else None

            ok = value is not None and qualifies(metric, rec['games'], denominator)
            staged.append({
                'user_id': user_id,
                'metric': metric,
                'value': value,
                'percentile': None,
                'pool_size': None,
                'numerator': numerator,
                'denominator': denominator,
                'qualified': ok,
            })

        pool = [s for s in staged if s['qualified']]
        for entry, pct in zip(pool, percentile_ranks([s['value'] for s in pool], higher_is_better)):
            entry['percentile'] = pct
            entry['pool_size'] = len(pool)

        rows.extend(staged)
    return rows
