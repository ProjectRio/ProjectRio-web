"""Add season_metric table for per-season advanced percentiles

Revision ID: c4f81a26d9e3
Revises: a7c3e9f10b24
Create Date: 2026-09-11 00:00:00.000000

Creates the table behind the Savant Sliders percentiles: one row per
(tag_set, user, metric), written twice daily by a scheduled job and read by
the /season_stats/ endpoint.

Stored long rather than wide -- one row per metric instead of one column per
metric -- so adding or removing a metric is a data change rather than another
migration, and so the rate metrics can carry a numerator/denominator while
gen_adjusted_elo and gen_games_played leave them NULL.

NOTE: written by hand, not by `flask db migrate`. Autogenerate does not know
about the vertical_trajectories and wpa_game_state_map tables, which exist in
the database but in no model, and will emit drop_table calls for both. If you
regenerate this, delete those lines before committing.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4f81a26d9e3'
down_revision = 'a7c3e9f10b24'
branch_labels = None
depends_on = None


def upgrade():
    # app/__init__.py calls db.create_all() on every boot, so on a fresh deploy
    # this table already exists by the time anyone runs `flask db upgrade`, and
    # creating it again aborts the migration with DuplicateTable. Skip the
    # create when it is already there and just let the revision advance --
    # create_all() builds the same indexes and constraint from the model.
    if sa.inspect(op.get_bind()).has_table('season_metric'):
        return

    op.create_table(
        'season_metric',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tag_set_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(length=40), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('percentile', sa.Float(), nullable=True),
        sa.Column('pool_size', sa.Integer(), nullable=True),
        sa.Column('numerator', sa.Integer(), nullable=True),
        sa.Column('denominator', sa.Integer(), nullable=True),
        sa.Column('qualified', sa.Boolean(), nullable=False),
        sa.Column('computed_at', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tag_set_id'], ['tag_set.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['rio_user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag_set_id', 'user_id', 'metric',
                            name='uq_season_metric_tagset_user_metric'),
    )
    # FK lookups
    op.create_index('ix_season_metric_tag_set_id', 'season_metric', ['tag_set_id'])
    op.create_index('ix_season_metric_user_id', 'season_metric', ['user_id'])
    # Leaderboard: one metric in one season, ordered by percentile
    op.create_index('ix_season_metric_board', 'season_metric',
                    ['tag_set_id', 'metric', 'percentile'])


def downgrade():
    # Indexes are dropped with the table.
    if sa.inspect(op.get_bind()).has_table('season_metric'):
        op.drop_table('season_metric')
