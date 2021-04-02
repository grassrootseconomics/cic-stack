"""DEbug

Revision ID: 5ca4b77ce205
Revises: 75d4767b3031
Create Date: 2021-04-02 18:42:12.257244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ca4b77ce205'
down_revision = '75d4767b3031'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'debug',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tag', sa.String, nullable=False),
            sa.Column('description', sa.String, nullable=False),
            sa.Column('date_created', sa.DateTime, nullable=False),
            )


def downgrade():
    op.drop_table('debug')
