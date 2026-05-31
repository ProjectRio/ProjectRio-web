"""Remove ranked column from game table

Revision ID: a1b2c3d4e5f6
Revises: de7d5b19d918
Create Date: 2026-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'de7d5b19d918'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('game', 'ranked')


def downgrade():
    op.add_column('game', sa.Column('ranked', sa.Boolean(), nullable=True))
