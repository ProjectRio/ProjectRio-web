"""
Runs Scored Calculation Module

Calculates runs scored by tracing RBI events to the runners who scored.

Logic:
1. Find all events with result_rbi > 0
2. For each RBI event, examine the Runner records
3. Identify runners who scored (transitioned to home plate)
4. Credit each scoring runner's CharacterGameSummary with a run
"""

from sqlalchemy import select
from ...models import db, Event, Runner, CharacterGameSummary


def calculate_runs_scored_for_games(game_ids: list, batch_size: int = 500) -> dict:
    """
    Calculate runs scored for multiple games efficiently with bulk queries.

    Args:
        game_ids: List of game_ids to process
        batch_size: Number of games to process per batch (default 500)

    Returns:
        dict mapping CharacterGameSummary.id to number of runs scored:
        {
            cgs_id_1: 2,  # This player scored 2 runs
            cgs_id_2: 1,  # This player scored 1 run
            ...
        }
    """
    if not game_ids:
        return {}

    # Process in batches to limit memory usage
    all_results = {}
    for i in range(0, len(game_ids), batch_size):
        batch = game_ids[i:i + batch_size]
        batch_results = _calculate_runs_scored_batch(batch)
        # Aggregate runs across batches for the same CGS
        for cgs_id, runs in batch_results.items():
            all_results[cgs_id] = all_results.get(cgs_id, 0) + runs

    return all_results


def _calculate_runs_scored_batch(game_ids: list) -> dict:
    """Process a single batch of games for runs scored calculation."""

    # Fetch all RBI events (events where runs scored)
    rbi_events = db.session.execute(
        select(Event)
        .where(
            Event.game_id.in_(game_ids),
            Event.result_rbi > 0
        )
        .order_by(Event.game_id, Event.event_num)
    ).scalars().all()

    if not rbi_events:
        return {}

    # Get all runner IDs from these events
    runner_ids = set()
    for event in rbi_events:
        if event.runner_on_0:
            runner_ids.add(event.runner_on_0)
        if event.runner_on_1:
            runner_ids.add(event.runner_on_1)
        if event.runner_on_2:
            runner_ids.add(event.runner_on_2)
        if event.runner_on_3:
            runner_ids.add(event.runner_on_3)

    # Fetch all runners at once
    all_runners = db.session.execute(
        select(Runner).where(Runner.id.in_(runner_ids))
    ).scalars().all()

    # Build lookup: runner_id -> Runner object
    runners_by_id = {runner.id: runner for runner in all_runners}

    # Count runs scored per CharacterGameSummary
    runs_by_cgs = {}

    for event in rbi_events:
        num_rbi = event.result_rbi

        # Check all possible runner positions (0=batter, 1=1st, 2=2nd, 3=3rd)
        # Order from 3rd to batter to match scoring order
        possible_runners = [
            event.runner_on_3,
            event.runner_on_2,
            event.runner_on_1,
            event.runner_on_0
        ]

        scoring_runners = []
        for runner_id in possible_runners:
            if runner_id is None:
                continue

            runner = runners_by_id.get(runner_id)
            if runner is None:
                continue

            # Runner scored if they didn't get out (out_type == 0 or None means safe)
            # and they advanced (this includes home runs where batter scores)
            if runner.out_type == 0 or runner.out_type is None:
                scoring_runners.append(runner)

        # Credit runs to the scoring runners
        # Take only the first num_rbi runners (should match, but safety check)
        for i in range(min(num_rbi, len(scoring_runners))):
            runner = scoring_runners[i]
            cgs_id = runner.runner_character_game_summary_id
            runs_by_cgs[cgs_id] = runs_by_cgs.get(cgs_id, 0) + 1

    return runs_by_cgs
