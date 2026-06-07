"""Add performance indexes for /games/ and related endpoints

Revision ID: a1c7e93f5b20
Revises: b2f4c8a1d3e7
Create Date: 2026-06-01 22:30:00.000000

Adds indexes to support the optimized /games/ endpoint and the queries it
touches. No index columns existed previously (only PKs and unique constraints),
which made "last X games" style queries seq-scan + sort the entire game table.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c7e93f5b20'
down_revision = 'b2f4c8a1d3e7'
branch_labels = None
depends_on = None


def upgrade():
    # game: ORDER BY / range filter + user/stadium filters and joins
    op.create_index('ix_game_date_time_end', 'game', ['date_time_end'])
    op.create_index('ix_game_away_player_id', 'game', ['away_player_id'])
    op.create_index('ix_game_home_player_id', 'game', ['home_player_id'])
    op.create_index('ix_game_stadium_id', 'game', ['stadium_id'])

    # character_game_summary: captain lookup, roster lookup, user stats
    op.create_index('ix_character_game_summary_game_id_captain', 'character_game_summary', ['game_id', 'captain'])
    op.create_index('ix_character_game_summary_game_id_team_roster', 'character_game_summary', ['game_id', 'team_id', 'roster_loc'])
    op.create_index('ix_character_game_summary_user_id', 'character_game_summary', ['user_id'])

    # game_history: tag-set filter + ladder/games ORDER BY
    op.create_index('ix_game_history_game_id', 'game_history', ['game_id'])
    op.create_index('ix_game_history_tag_set_id', 'game_history', ['tag_set_id'])
    op.create_index('ix_game_history_date_created', 'game_history', ['date_created'])

    # event: linescore / scoring plays / events endpoint
    op.create_index('ix_event_game_id', 'event', ['game_id'])

    # tag_set_tag: reverse lookup (composite PK leads with tag_id)
    op.create_index('ix_tag_set_tag_tagset_id', 'tag_set_tag', ['tagset_id'])


def downgrade():
    op.drop_index('ix_tag_set_tag_tagset_id', table_name='tag_set_tag')
    op.drop_index('ix_event_game_id', table_name='event')
    op.drop_index('ix_game_history_date_created', table_name='game_history')
    op.drop_index('ix_game_history_tag_set_id', table_name='game_history')
    op.drop_index('ix_game_history_game_id', table_name='game_history')
    op.drop_index('ix_character_game_summary_user_id', table_name='character_game_summary')
    op.drop_index('ix_character_game_summary_game_id_team_roster', table_name='character_game_summary')
    op.drop_index('ix_character_game_summary_game_id_captain', table_name='character_game_summary')
    op.drop_index('ix_game_stadium_id', table_name='game')
    op.drop_index('ix_game_home_player_id', table_name='game')
    op.drop_index('ix_game_away_player_id', table_name='game')
    op.drop_index('ix_game_date_time_end', table_name='game')
