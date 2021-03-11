"""Add account lock

Revision ID: 89e1e9baa53c
Revises: 2a07b543335e
Create Date: 2021-01-27 19:57:36.793882

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89e1e9baa53c'
down_revision = '2a07b543335e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'lock',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column("address", sa.String(42), nullable=True),
            sa.Column('blockchain', sa.String),
            sa.Column("flags", sa.BIGINT(), nullable=False, default=0),
            sa.Column("date_created", sa.DateTime, nullable=False),
            sa.Column("otx_id", sa.Integer, nullable=True),
            )
    op.create_index('idx_chain_address', 'lock', ['blockchain', 'address'], unique=True)

def downgrade():
    op.drop_index('idx_chain_address')
    op.drop_table('lock')
