# Handoff: Three follow-up optimizations for ProjectRio-web

Three independent follow-ups to the `/stats/` and `/events/` performance work.
Each lands on its own branch off `develop` and is mutually independent.

## Shared context & constraints (applies to all three)

- **Stack:** Flask 2.0.2, **SQLAlchemy pinned at 1.4.28**, Flask-SQLAlchemy 2.5.1,
  PostgreSQL (~50k games; `event` is the largest table).
- **Do NOT bump any package versions.** Write 2.0-ready code that runs on the
  1.4.28 pin: `db.session.execute(select(...))`, `text()`-wrapped SQL where raw is
  unavoidable, `aliased()` for self-joins, row access via **attributes** or
  `dict(row._mapping)` — **never** raw strings to `execute()`, **never** string-key
  row access like `row['col']`.
- **Don't run migrations against a DB.** If a branch needs one, generate the file
  only and set `down_revision` to develop's current Alembic head (the `revision`
  that no other file in `migrations/versions/` lists as `down_revision` — was
  `b2f4c8a1d3e7`, but re-scan, it may have moved). Keep a single Alembic head.
- **A separate unmerged branch (`optimize-games-endpoint`) owns the `/games/`
  endpoint and indexes on `game`, `character_game_summary(game_id,…)`/`(user_id)`,
  `game_history`, `event(game_id)`, `character(name_lowercase)`, `tag_set_tag`.**
  Do not modify `endpoint_games` or add those indexes. Don't depend on them either.
- The `optimize-stats-events` branch already indexed the Event FKs
  (`batter_id`/`pitcher_id`/`catcher_id`/`pitch_summary_id`),
  `cgs.char_id`/`character_position_summary_id`, and the contact/fielding/pitch
  child FKs, and converted `/events/` to `select()`. Don't redo those.
- **Verification for every branch:** `python -m py_compile` the changed files; for
  any new `select()`, compile-test against the PostgreSQL dialect on SQLAlchemy
  1.4.28 in a throwaway venv with
  `print(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))`
  and confirm the SQL/join semantics match the original. The
  `app/tests/test_endpoint_*.py` need a live server + populated Postgres and are
  largely commented out — don't assume they run.
- All query code is in `app/views/stat_retrieval.py`; models in `app/models.py`.
- Commit (don't push / don't open a PR unless asked) with trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Branch 1: `optimize-rosters-query` — fix the N+1 + 2.0-breaking roster lookup

**Target:** `get_rosters_from_game` at `app/views/stat_retrieval.py:186`.

**Why:** Two problems.
(a) **N+1:** called inside the results loop in `endpoint_games` when
`include_teams=1` (`app/views/stat_retrieval.py:682`) — one query per game, each an
18-way `LEFT JOIN` self-join of `character_game_summary`. For a 50-game page that's
50 queries x 18 joins.
(b) **2.0 hard-failure today:** string-key row access `results[0]['away_0']` …
`results[0]['home_8']` (`app/views/stat_retrieval.py:251-269`), which errors on
SQLAlchemy 2.0.

**What to do:**
1. Rewrite `get_rosters_from_game` (or add a batch sibling) to accept a **list of
   game_ids** and run **one** query returning `(game_id, team_id, roster_loc,
   char_id)` rows:
   `select(CharacterGameSummary.game_id, CharacterGameSummary.team_id,
   CharacterGameSummary.roster_loc, CharacterGameSummary.char_id)
   .where(CharacterGameSummary.game_id.in_(game_ids))`. No self-joins needed.
2. Bucket rows in Python into `{game_id: (away_dict, home_dict)}` keyed off
   `team_id` (0=away, 1=home) and `roster_loc`. Preserve the **exact output shape**:
   `away_dict`/`home_dict` are `{0..8: char_id}` with `None` for missing slots —
   keep the missing-slot behavior.
3. Update the `include_teams` branch in `endpoint_games` to call the batch version
   once (outside the loop) and look up per game. **Touch `endpoint_games` as little
   as possible** — it's the games branch's file; ideally only the `include_teams`
   block. If that risks a merge conflict, coordinate or keep it minimal.
4. Benefits from the games branch's `cgs(game_id,…)` composite but must not depend
   on it.

**No migration needed.** Verify by compile-testing the new `select()` and confirming
the bucketed dict matches the old shape for a hand-traced example.

---

## Branch 2: `modernize-event-derived-endpoints` — kill remaining raw f-string SQL

**Targets (all in `app/views/stat_retrieval.py`):**
- `endpoint_landing_data` / `/landing_data/` — raw query at `:1110`, builds SQL off
  `endpoint_event(True)['Events']`.
- `endpoint_star_chances` / `/star_chances/` — raw query at `:1175`, same pattern,
  with optional `by_inning` grouping + `COUNT(CASE …)` aggregates.
- `endpoint_ladder_games` / `/ladder/games/` — raw query at `:1916`, plus
  `_asdict()` consumption.

**Why:** These still pass f-strings to `db.session.execute()` (2.0 hard-error +
injection surface). `/events/` was already converted, so they now consume a clean
id list.

**What to do:**
1. Convert each to a parameterized `select()`. Use `aliased()` for the repeated
   `character_game_summary`/`rio_user`/`character` roles (batter/pitcher/fielder,
   away/home, winner/loser). Mirror the existing inner-vs-`LEFT JOIN` choices
   exactly (e.g. landing_data inner-joins `contact_summary` but left-joins
   `fielding_summary` and `fielder`).
2. Reproduce the `COUNT(CASE WHEN … )` / `SUM(CASE …)` aggregates in
   `star_chances` with `func.count(case((cond, 1)))` / `func.sum(case(...))`, and
   its conditional `GROUP BY event.inning, event.half_inning` when `by_inning` is
   set.
3. **Keep JSON payloads byte-for-byte identical** — the web frontend depends on the
   keys. Current code returns rows via `entry._asdict()`; preserve every label
   exactly. Replace `_asdict()` with `dict(row._mapping)` or attribute access.
4. **Leave `endpoint_games` and `get_rosters_from_game` alone** (games branch /
   Branch 1 respectively).

**No new indexes needed** — these filter on `event.id IN (...)` (PK) and fan out
through the contact/fielding child FKs already indexed by the prior branch. Verify
each rewritten statement by compile-test against the postgres dialect.

---

## Branch 3: `optimize-pitcher-wins-runs-scored` — push in-memory aggregation into SQL (investigate first)

**Targets:** the `include_pitcher_wins` / `include_runs_scored` paths in
`query_detailed_pitching_stats` / `query_detailed_batting_stats`
(`app/views/stat_retrieval.py:1436` onward) and their helpers in
`app/views/stats/pitcher_wins.py` and `app/views/stats/runs_scored.py`.

**Why:** The docstrings state these *"require loading events into memory"* — i.e.
they pull from the largest table and aggregate in Python. If RioBot or the frontend
sets these flags on broad (all-games) queries, this is a latent hotspot.

**What to do:**
1. **Profile first.** Read `calculate_pitcher_wins_for_games` /
   `calculate_runs_scored_for_games`, identify the per-event/per-runner Python
   loops, and run `EXPLAIN (ANALYZE, BUFFERS)` on a representative
   `/stats/?...&include_pitcher_wins=1` query (against a dev copy — read-only, no
   writes) to quantify the cost.
2. Where the logic is expressible in SQL, replace the in-memory pass with a
   `select()` aggregation (window functions / `GROUP BY` / `DISTINCT ON`), feeding
   into the existing `update_detailed_stats_dict` flow the same way the current
   `pitcher_wins_query` / `runs_scored_query` do. Keep the
   `_add_default_to_stat_category(..., 0)` zero-fill so absent players still
   report `0`.
3. **Output must stay byte-for-byte identical** — same nested dict keys/values for
   the same inputs. This is the riskiest of the three; if the win/run rules can't be
   cleanly pushed to SQL, document why and stop rather than changing results.
4. If EXPLAIN shows a missing index would help, generate a migration (single head,
   chained off develop's head) — but `event(game_id)` is already owned by the games
   branch, so check before adding anything on `event`.

**This branch is investigation-led**; it's fine for the deliverable to be
"profiled, here's the finding, here's the safe subset I pushed to SQL."
