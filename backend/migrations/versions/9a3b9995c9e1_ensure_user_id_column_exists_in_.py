"""Ensure user_id column exists in GroupMembers table

Revision ID: 9a3b9995c9e1
Revises: 
Create Date: 2024-08-04 12:52:22.850314

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9a3b9995c9e1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
 # Check if the column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('GroupMembers')]

    if 'groupmember_id' not in columns:
        with op.batch_alter_table('GroupMembers') as batch_op:
            batch_op.add_column(sa.Column('groupmember_id', sa.Integer, nullable=False))

def downgrade():
    with op.batch_alter_table('GroupMembers') as batch_op:
        batch_op.drop_column('groupmember_id')

    # ### end Alembic commands ###
