"""debug output

Revision ID: f738d9962fdf
Revises: ec40ac0974c1
Create Date: 2021-03-04 08:32:43.281214

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f738d9962fdf'
down_revision = 'ec40ac0974c1'
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
    pass


def downgrade():
    op.drop_table('debug')
    pass
