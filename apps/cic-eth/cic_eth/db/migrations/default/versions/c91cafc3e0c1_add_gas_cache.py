"""Add gas cache

Revision ID: c91cafc3e0c1
Revises: aee12aeb47ec
Create Date: 2021-10-28 20:45:34.239865

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c91cafc3e0c1'
down_revision = 'aee12aeb47ec'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'gas_cache',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column("address", sa.String, nullable=False),
            sa.Column("tx_hash", sa.String, nullable=True),
            sa.Column("method", sa.String, nullable=True),
            sa.Column("value", sa.BIGINT(), nullable=False),
            )


def downgrade():
    op.drop_table('gas_cache')
