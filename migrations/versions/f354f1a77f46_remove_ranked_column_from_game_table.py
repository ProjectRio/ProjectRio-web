"""Remove ranked column from game table

Revision ID: f354f1a77f46
Revises: de7d5b19d918
Create Date: 2026-05-31 11:39:30.826577

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f354f1a77f46'
down_revision = 'de7d5b19d918'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.drop_column('ranked')


def downgrade():
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ranked', sa.BOOLEAN(), autoincrement=False, nullable=True))
