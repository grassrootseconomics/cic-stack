"""Create task tracker table

Revision ID: a571d0aee6f8
Revises: 2a329190a9af
Create Date: 2021-01-04 18:28:00.462228

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a571d0aee6f8'
down_revision = '2a329190a9af'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('task_tracker',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('updated', sa.DateTime(), nullable=True),
                    sa.Column('task_uuid', sa.String(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('task_tracker')
