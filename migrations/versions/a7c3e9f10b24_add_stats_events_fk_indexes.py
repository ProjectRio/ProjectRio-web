"""Add indexes for /stats/ and /events/ query paths

Adds indexes on the foreign keys that the /stats/ and /events/ aggregation
queries join/filter on but that PostgreSQL does not index automatically:

  Game composite indexes (head-to-head bidirectional player queries):
    - game(away_player_id, home_player_id)
    - game(home_player_id, away_player_id)

  Event FKs (largest table, reverse-direction joins from CharacterGameSummary):
    - event.batter_id          (query_detailed_batting_stats join)
    - event.pitcher_id         (query_detailed_pitching_stats join)
    - event.catcher_id         (completeness; used by /stats/fix/ + future filters)
    - event.pitch_summary_id   (event -> pitch_summary joins in /events/, /landing_data/)

  CharacterGameSummary filter/join FKs:
    - character_game_summary.char_id                         (filtered in every stats query)
    - character_game_summary.character_position_summary_id   (fielding position join)

  Child-table FKs (deep event joins / fielding stats):
    - fielding_summary.fielder_character_game_summary_id
    - contact_summary.fielding_summary_id
    - pitch_summary.contact_summary_id

Single-column index names follow the Flask-SQLAlchemy ``index=True`` convention
(``ix_<table>_<column>``). Composite index names use ``ix_<table>_<col1>_<col2>``
and are defined explicitly in both the model ``__table_args__`` and this migration.

NOTE: event is the largest table (~50k games -> millions of events). The four
event-FK indexes are the most expensive by storage. Run
``EXPLAIN (ANALYZE, BUFFERS)`` on a representative /stats/ query and review the
event row count before/after applying in production; catcher_id in particular is
not on any hot read path and can be dropped if storage is a concern.

Revision ID: a7c3e9f10b24
Revises: b2f4c8a1d3e7
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c3e9f10b24'
down_revision = 'a1c7e93f5b20'
branch_labels = None
depends_on = None


def upgrade():
    # Game head-to-head composite indexes (both directions for bidirectional player queries)
    op.create_index('ix_game_away_player_home_player', 'game', ['away_player_id', 'home_player_id'], unique=False)
    op.create_index('ix_game_home_player_away_player', 'game', ['home_player_id', 'away_player_id'], unique=False)

    # Event foreign keys (largest table)
    op.create_index(op.f('ix_event_batter_id'), 'event', ['batter_id'], unique=False)
    op.create_index(op.f('ix_event_pitcher_id'), 'event', ['pitcher_id'], unique=False)
    op.create_index(op.f('ix_event_catcher_id'), 'event', ['catcher_id'], unique=False)
    op.create_index(op.f('ix_event_pitch_summary_id'), 'event', ['pitch_summary_id'], unique=False)

    # CharacterGameSummary filter/join foreign keys
    op.create_index(op.f('ix_character_game_summary_char_id'), 'character_game_summary', ['char_id'], unique=False)
    op.create_index(op.f('ix_character_game_summary_character_position_summary_id'), 'character_game_summary', ['character_position_summary_id'], unique=False)

    # Child-table foreign keys
    op.create_index(op.f('ix_fielding_summary_fielder_character_game_summary_id'), 'fielding_summary', ['fielder_character_game_summary_id'], unique=False)
    op.create_index(op.f('ix_contact_summary_fielding_summary_id'), 'contact_summary', ['fielding_summary_id'], unique=False)
    op.create_index(op.f('ix_pitch_summary_contact_summary_id'), 'pitch_summary', ['contact_summary_id'], unique=False)


def downgrade():
    op.drop_index('ix_game_home_player_away_player', table_name='game')
    op.drop_index('ix_game_away_player_home_player', table_name='game')

    op.drop_index(op.f('ix_pitch_summary_contact_summary_id'), table_name='pitch_summary')
    op.drop_index(op.f('ix_contact_summary_fielding_summary_id'), table_name='contact_summary')
    op.drop_index(op.f('ix_fielding_summary_fielder_character_game_summary_id'), table_name='fielding_summary')

    op.drop_index(op.f('ix_character_game_summary_character_position_summary_id'), table_name='character_game_summary')
    op.drop_index(op.f('ix_character_game_summary_char_id'), table_name='character_game_summary')

    op.drop_index(op.f('ix_event_pitch_summary_id'), table_name='event')
    op.drop_index(op.f('ix_event_catcher_id'), table_name='event')
    op.drop_index(op.f('ix_event_pitcher_id'), table_name='event')
    op.drop_index(op.f('ix_event_batter_id'), table_name='event')
