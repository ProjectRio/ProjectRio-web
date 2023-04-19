"""empty message

Revision ID: 8734a6a139e8
Revises: 611bd2e0a178
Create Date: 2023-03-25 10:44:51.067662

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8734a6a139e8'
down_revision = '611bd2e0a178'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('community_user', sa.Column('community_key', sa.String(length=4), nullable=True))
    op.add_column('community_user', sa.Column('date_key_created', sa.Integer(), nullable=True))
    #NOTE: Alembic sets name to name to 'None' by default for the unique constraint. 
    #If left as 'None' the name will be generated as '<table>_<column>_key'. I've filled it in
    #to make it clear what the name is. 
    #Constraint names can be found with the following query
    '''
    SELECT conrelid::regclass AS table_from
        , conname
        , pg_get_constraintdef(oid)
    FROM   pg_constraint
    WHERE  contype IN ('u') -- u=unique, f=foreign key, p=primary key
    AND    connamespace = 'public'::regnamespace
    ORDER  BY conrelid::regclass::text, contype DESC;
    '''
    op.create_unique_constraint('community_user_community_key_key', 'community_user', ['community_key'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    #NOTE: Must replace the almbic generated 'None' with the constraint name, see above
    op.drop_constraint('community_user_community_key_key', 'community_user', type_='unique')
    op.drop_column('community_user', 'date_key_created')
    op.drop_column('community_user', 'community_key')
    # ### end Alembic commands ###