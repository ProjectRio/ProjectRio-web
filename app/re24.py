'''RE24: the average number of runs scored from each base-out state to the end of
the half-inning, per game type.

Method: the "wRC+ Advanced_Stats table" query in
github.com/nperkins27/Rio-Sabermetrics, with two changes (the first and last
points below):

  - Only games whose pitch log is complete (log_is_complete). About one game in
    eight has a log that stops early, which would undercount runs.
  - Innings 1-8 only, so walk-offs and extra innings don't cut half-innings short.
  - Every pitch is one observation of the base-out state before it.
  - Runs = the batting team's score when the next half-inning starts (the final
    score after the last one) minus its score before the pitch, so runs scored on
    the last play of a half-inning count.

The work is split so the event table is read once per game, ever: game_states()
reduces one game to a few rows of (outs, runners) -> pitches and runs, which the
nightly job stores per game in re24_game_state; re24_rows() turns the sums of
those rows into the RE24 table. Which competitions count is decided only at that
last step (competition_profile), so re-sorting a competition needs no rescan.

This module imports nothing from the app, so it can be unit tested directly
(app/tests/test_re24.py). Database access is in re24_db.py.
'''

# The four game types RE24 covers: competition_profile categories other than 'other'.
cGAME_TYPES = ('stars off', 'stars on', 'big balla', 'hazards')
cLAST_INNING = 8
# A pitch log counts as complete when it reaches the last inning played and holds
# at least this share of the pitches the box score says were thrown.
cMIN_LOG_SHARE = 0.9
cXRUNS_DECIMALS = 4


def runners_code(on_1st, on_2nd, on_3rd):
    '''0-7: runner on 1st = 1, on 2nd = 2, on 3rd = 4, added together
    (3 = 1st and 2nd, 5 = 1st and 3rd, 6 = 2nd and 3rd, 7 = bases loaded).'''
    return (1 if on_1st else 0) + (2 if on_2nd else 0) + (4 if on_3rd else 0)


def log_is_complete(pitches, innings_played, box_pitches):
    '''True unless the game's pitch log stops early.

    pitches         the game's pitches (see game_states); only inning is used here
    innings_played  game.innings_played
    box_pitches     sum of character_game_summary.pitches_thrown for the game

    A game with no box score or no inning played can't be checked, so it isn't
    complete either.
    '''
    if not pitches or not box_pitches or not innings_played:
        return False
    last_inning = max(p[0] for p in pitches)
    return last_inning >= (innings_played or 0) and len(pitches) >= cMIN_LOG_SHARE * (box_pitches or 0)


def game_states(pitches, final_away, final_home):
    '''One game's RE24 observations: {(outs, runners): (pitches, runs)}.

    pitches  the game's pitches in order (event_num), each a tuple
             (inning, half_inning, outs, on_1st, on_2nd, on_3rd, away_score, home_score)
             with half_inning 0 = top, 1 = bottom, the on_ values truthy when a
             runner is there, and the scores as they stood before the pitch
    final_away, final_home  the game's final score

    Pitches recorded with an out count outside 0-2 are skipped.
    '''
    halves = []
    for p in pitches:
        key = (p[0], p[1])
        if not halves or halves[-1][0] != key:
            halves.append((key, []))
        halves[-1][1].append(p)

    totals = {}
    for i, ((inning, half), half_pitches) in enumerate(halves):
        if inning > cLAST_INNING:
            continue
        score = 6 if half == 0 else 7          # away bats in the top, home in the bottom
        if i + 1 < len(halves):
            end = halves[i + 1][1][0][score]
        else:
            end = final_away if half == 0 else final_home
        for p in half_pitches:
            outs = p[2]
            if outs not in (0, 1, 2):
                continue
            state = (outs, runners_code(p[3], p[4], p[5]))
            seen, runs = totals.get(state, (0, 0))
            totals[state] = (seen + 1, runs + end - p[score])
    return totals


def re24_rows(sums):
    '''The RE24 table from summed observations.

    sums  {(gametype, outs, runners): (pitches, runs)}
    Returns one dict per state, xruns = runs / pitches to cXRUNS_DECIMALS places,
    ordered by game type, outs and runners.
    '''
    order = {game_type: i for i, game_type in enumerate(cGAME_TYPES)}
    rows = []
    for (game_type, outs, runners), (pitches, runs) in sums.items():
        if not pitches:
            continue
        rows.append({'gametype': game_type, 'outs': outs, 'runners': runners,
                     'xruns': round(runs / pitches, cXRUNS_DECIMALS), 'pitches': pitches})
    rows.sort(key=lambda r: (order.get(r['gametype'], len(order)), r['outs'], r['runners']))
    return rows
