"""Add 2.2.0 ongoing game fields to ongoing_game table

Adds the new OngoingGame columns introduced for Project Rio 2.2.0's expanded
ongoing-game submissions (team logos, per-roster char/superstar/fielding-position
arrays, per-inning score arrays, star chance, live pitcher/batter stat snapshots,
runner roster locations, etc.). All columns are nullable -- OngoingGame is
ephemeral (rows are destroyed after ~2 hours) so there is no backfill concern.

Revision ID: b2f4c8a1d3e7
Revises: f354f1a77f46
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2f4c8a1d3e7'
down_revision = 'f354f1a77f46'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ongoing_game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('away_logo', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('home_logo', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('away_char_ids', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('home_char_ids', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('away_superstars', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('home_superstars', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('away_fielding_positions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('home_fielding_positions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('away_inning_scores', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('home_inning_scores', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('star_chance', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('pitcher_stats', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('batter_stats', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('innings_selected', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('loaded_from_hud', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('chemistry_links_on_base', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('batter_hand', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('current_runner_1b_roster', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('current_runner_2b_roster', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('current_runner_3b_roster', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('ongoing_game', schema=None) as batch_op:
        batch_op.drop_column('current_runner_3b_roster')
        batch_op.drop_column('current_runner_2b_roster')
        batch_op.drop_column('current_runner_1b_roster')
        batch_op.drop_column('batter_hand')
        batch_op.drop_column('chemistry_links_on_base')
        batch_op.drop_column('loaded_from_hud')
        batch_op.drop_column('innings_selected')
        batch_op.drop_column('batter_stats')
        batch_op.drop_column('pitcher_stats')
        batch_op.drop_column('star_chance')
        batch_op.drop_column('home_inning_scores')
        batch_op.drop_column('away_inning_scores')
        batch_op.drop_column('home_fielding_positions')
        batch_op.drop_column('away_fielding_positions')
        batch_op.drop_column('home_superstars')
        batch_op.drop_column('away_superstars')
        batch_op.drop_column('home_char_ids')
        batch_op.drop_column('away_char_ids')
        batch_op.drop_column('home_logo')
        batch_op.drop_column('away_logo')
