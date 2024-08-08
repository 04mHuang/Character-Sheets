"""Initial migration with updated Person model

Revision ID: c95c87a6e8cb
Revises: 
Create Date: 2024-08-07 23:16:36.122741

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c95c87a6e8cb'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Rename 'interests' column to 'likes' with the existing type specified
    op.alter_column('People', 'interests', new_column_name='likes', type_=sa.Text())
    
    # Add new columns
    op.add_column('People', sa.Column('relationship', sa.String(length=100), nullable=True))
    op.add_column('People', sa.Column('anniversaries', sa.Date(), nullable=True))
    op.add_column('People', sa.Column('dislikes', sa.Text(), nullable=True))

def downgrade():
    # Revert changes: rename 'likes' back to 'interests' with the existing type specified
    op.alter_column('People', 'likes', new_column_name='interests', type_=sa.Text())
    
    # Remove the new columns
    op.drop_column('People', 'relationship')
    op.drop_column('People', 'anniversaries')
    op.drop_column('People', 'dislikes')