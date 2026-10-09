"""Add competition_profile and the RE24 tables

Revision ID: af0cf49eb907
Revises: a7c3e9f10b24
Create Date: 2026-10-09 00:00:00.000000

  competition_profile  one row per tag set: its category (stars off, stars on,
                       big balla, hazards, other), type, the q_ flags saying what
                       its games count toward, and a review status
  re24_game            ledger of the games the RE24 job has read
  re24_game_state      per game: pitches and runs from each base-out state
  re24                 the RE24 table per game type, rebuilt nightly

All four are filled by the nightly job in app/re24_db.py; competition_profile
starts from app/data/competition_profile_seed.csv on the first run.

Every foreign key cascades on delete, so /delete_game/ and /tag_set/delete keep
working: a deleted game takes its RE24 rows with it, and a deleted tag set its
profile.

NOTE: written by hand, not by `flask db migrate`. Autogenerate does not know
about the vertical_trajectories and wpa_game_state_map tables, which exist in
the database but in no model, and will emit drop_table calls for both. If you
regenerate this, delete those lines before committing.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af0cf49eb907'
down_revision = 'a7c3e9f10b24'
branch_labels = None
depends_on = None


def upgrade():
    # app/__init__.py calls db.create_all() on every boot, so on a fresh deploy
    # these tables can exist before anyone runs `flask db upgrade`. Create only
    # the missing ones; create_all() builds the same columns and constraints.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if 'competition_profile' not in existing:
        op.create_table(
            'competition_profile',
            sa.Column('tag_set_id', sa.Integer(), nullable=False),
            sa.Column('competition', sa.String(length=100), nullable=False),
            sa.Column('category', sa.String(length=16), nullable=False),
            sa.Column('type', sa.String(length=16), nullable=False),
            sa.Column('q_ranked', sa.Boolean(), nullable=False),
            sa.Column('q_league_stats', sa.Boolean(), nullable=False),
            sa.Column('q_player_stats', sa.Boolean(), nullable=False),
            sa.Column('q_character_stats', sa.Boolean(), nullable=False),
            sa.Column('q_pick_rates', sa.Boolean(), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('note', sa.String(length=500), nullable=True),
            sa.Column('updated_at', sa.Integer(), nullable=False),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.CheckConstraint("category IN ('stars off', 'stars on', 'big balla', 'hazards', 'other')",
                               name='ck_competition_profile_category'),
            sa.CheckConstraint("type IN ('Season', 'League', 'Tournament', 'Exhibition')",
                               name='ck_competition_profile_type'),
            sa.CheckConstraint("status IN ('pending', 'auto', 'reviewed')",
                               name='ck_competition_profile_status'),
            sa.ForeignKeyConstraint(['tag_set_id'], ['tag_set.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['updated_by'], ['rio_user.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('tag_set_id'),
        )

    if 're24_game' not in existing:
        op.create_table(
            're24_game',
            sa.Column('game_id', sa.BigInteger(), nullable=False),
            sa.Column('complete', sa.Boolean(), nullable=False),
            sa.Column('pitches', sa.Integer(), nullable=False),
            sa.Column('processed_at', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['game_id'], ['game.game_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('game_id'),
        )
        # The nightly recheck of recently read games
        op.create_index('ix_re24_game_processed_at', 're24_game', ['processed_at'])

    if 're24_game_state' not in existing:
        op.create_table(
            're24_game_state',
            sa.Column('game_id', sa.BigInteger(), nullable=False),
            sa.Column('outs', sa.Integer(), nullable=False),
            sa.Column('runners', sa.Integer(), nullable=False),
            sa.Column('pitches', sa.Integer(), nullable=False),
            sa.Column('runs', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['game_id'], ['re24_game.game_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('game_id', 'outs', 'runners'),
        )

    if 're24' not in existing:
        op.create_table(
            're24',
            sa.Column('gametype', sa.String(length=16), nullable=False),
            sa.Column('outs', sa.Integer(), nullable=False),
            sa.Column('runners', sa.Integer(), nullable=False),
            sa.Column('xruns', sa.Numeric(precision=6, scale=4), nullable=False),
            sa.Column('pitches', sa.Integer(), nullable=False),
            sa.Column('computed_at', sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint('gametype', 'outs', 'runners'),
        )


def downgrade():
    # Children first; indexes go with their tables.
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ('re24', 're24_game_state', 're24_game', 'competition_profile'):
        if table in existing:
            op.drop_table(table)
