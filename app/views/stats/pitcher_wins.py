"""
Pitcher Wins Calculation Module

Implements official baseball scoring rules for determining the winning pitcher.

Rules:
1. Find the last lead change event
2. Determine the pitcher of record at the time of the last lead change
3. If the starting pitcher was the pitcher of record:
   - They must have pitched at least 5 innings (15 outs) in a 9-inning game
   - OR it's a shortened game (less than 9 innings played)
   - Otherwise, award the win to the relief pitcher with the most innings
4. If a relief pitcher was the pitcher of record, they get the win
"""

from sqlalchemy import select
from ...models import db, Event, Game, CharacterGameSummary


def calculate_pitcher_wins_for_games(game_ids: list, batch_size: int = 500) -> dict:
    """
    Calculate pitcher wins for multiple games efficiently with bulk queries.

    Args:
        game_ids: List of game_ids to process
        batch_size: Number of games to process per batch (default 500)

    Returns:
        dict mapping game_id to winning pitcher's CharacterGameSummary.id:
        {
            game_id_1: cgs_id_1,  # Game 1's winning pitcher
            game_id_2: cgs_id_2,  # Game 2's winning pitcher
            ...
        }
    """
    if not game_ids:
        return {}

    # Process in batches to limit memory usage
    all_results = {}
    for i in range(0, len(game_ids), batch_size):
        batch = game_ids[i:i + batch_size]
        batch_results = _calculate_pitcher_wins_batch(batch)
        all_results.update(batch_results)

    return all_results


def _calculate_pitcher_wins_batch(game_ids: list) -> dict:
    """Process a single batch of games for pitcher wins calculation."""
    # Fetch all games at once
    games = db.session.execute(
        select(Game).where(Game.game_id.in_(game_ids))
    ).scalars().all()

    games_by_id = {g.game_id: g for g in games}

    # Fetch all events for all games at once
    all_events = db.session.execute(
        select(Event)
        .where(Event.game_id.in_(game_ids))
        .order_by(Event.game_id, Event.event_num)
    ).scalars().all()

    # Group events by game_id
    events_by_game = {}
    for event in all_events:
        if event.game_id not in events_by_game:
            events_by_game[event.game_id] = []
        events_by_game[event.game_id].append(event)

    # Fetch all CharacterGameSummary records
    all_cgs = db.session.execute(
        select(CharacterGameSummary)
        .where(CharacterGameSummary.game_id.in_(game_ids))
    ).scalars().all()

    # Build lookup: game_id -> {cgs.id: cgs}
    cgs_by_game = {}
    for cgs in all_cgs:
        if cgs.game_id not in cgs_by_game:
            cgs_by_game[cgs.game_id] = {}
        cgs_by_game[cgs.game_id][cgs.id] = cgs

    # Process each game to find winning pitcher
    winning_pitcher_by_game = {}

    for game_id in game_ids:
        game = games_by_id.get(game_id)
        if not game or game.away_score == game.home_score:
            continue

        events = events_by_game.get(game_id, [])

        # Determine winning team for validation
        winning_team_id = 0 if game.away_score > game.home_score else 1

        if not events:
            # No events - can't determine pitcher win
            continue

        # Find lead changes
        lead_change_events = []
        prev_score_diff = 0

        for event in events:
            score_diff = event.home_score - event.away_score

            if prev_score_diff == 0 and score_diff != 0:
                lead_change_events.append(event)
            elif prev_score_diff < 0 and score_diff > 0:
                lead_change_events.append(event)
            elif prev_score_diff > 0 and score_diff < 0:
                lead_change_events.append(event)

            prev_score_diff = score_diff

        if not lead_change_events:
            # No lead changes found - can't determine pitcher win
            continue

        last_lead_change = lead_change_events[-1]

        lead_change_inning = last_lead_change.inning
        lead_change_half_inning = last_lead_change.half_inning

        # If the lead change happened in the top of the first, then we need to look at the bottom of the first for the pitcher of record
        # Otherwise, we look at the previous half inning for the pitcher of record
        if (lead_change_half_inning == 0) and (lead_change_inning == 1):
            pitcher_inning = 1
            pitcher_half_inning = 1
        else:
            pitcher_half_inning  = abs(lead_change_half_inning - 1)
            if pitcher_half_inning == 1:
                pitcher_inning = lead_change_inning - 1
            else:
                pitcher_inning = lead_change_inning

        # Find pitcher of record (last event in that inning/half)
        pitcher_of_record_event = None
        for event in reversed(events):
            if event.inning == pitcher_inning and event.half_inning == pitcher_half_inning:
                pitcher_of_record_event = event
                break

        if not pitcher_of_record_event:
            # Can't find pitcher of record - skip this game
            continue

        pitcher_of_record_cgs = cgs_by_game[game_id].get(pitcher_of_record_event.pitcher_id)
        if not pitcher_of_record_cgs:
            # Pitcher of record CGS not found - skip this game
            continue

        # Find starting pitcher
        starting_pitcher_event = None
        for event in events:
            if event.inning == 1 and event.half_inning == pitcher_half_inning:
                starting_pitcher_event = event
                break

        if not starting_pitcher_event:
            # Can't find starting pitcher event - skip this game
            continue

        starting_pitcher_cgs = cgs_by_game[game_id].get(starting_pitcher_event.pitcher_id)
        if not starting_pitcher_cgs:
            # Starting pitcher CGS not found - skip this game
            continue

        full_nine_played = game.innings_played == 9

        # Determine winning pitcher
        if pitcher_of_record_cgs.roster_loc == starting_pitcher_cgs.roster_loc:
            # Starting pitcher was pitcher of record
            if starting_pitcher_cgs.outs_pitched >= 15 or not full_nine_played:
                winning_pitcher_by_game[game_id] = starting_pitcher_cgs.id
            else:
                # Find relief pitcher with most outs
                team_id = starting_pitcher_cgs.team_id
                relief_pitcher = None
                max_outs = 0

                for cgs in cgs_by_game[game_id].values():
                    if (cgs.team_id == team_id and
                        cgs.roster_loc != starting_pitcher_cgs.roster_loc and
                        cgs.outs_pitched > max_outs):
                        max_outs = cgs.outs_pitched
                        relief_pitcher = cgs

                if relief_pitcher:
                    winning_pitcher_by_game[game_id] = relief_pitcher.id
                else:
                    winning_pitcher_by_game[game_id] = starting_pitcher_cgs.id
        else:
            # Relief pitcher was pitcher of record
            winning_pitcher_by_game[game_id] = pitcher_of_record_cgs.id

        # Validate: ensure winning pitcher is on the winning team
        assigned_cgs = cgs_by_game[game_id].get(winning_pitcher_by_game[game_id])
        if assigned_cgs and assigned_cgs.team_id != winning_team_id:
            # Wrong team! Don't assign a win for this game
            del winning_pitcher_by_game[game_id]

    return winning_pitcher_by_game
