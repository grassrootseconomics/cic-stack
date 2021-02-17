"""Add cached values for tx

Revision ID: e3b5330ee71c
Revises: df19f4e69676
Create Date: 2020-10-10 00:17:07.094893

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3b5330ee71c'
down_revision = 'df19f4e69676'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
            'tx_cache',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('otx_id', sa.Integer, sa.ForeignKey('otx.id'), nullable=True),
            sa.Column('date_created', sa.DateTime, nullable=False),
            sa.Column('date_updated', sa.DateTime, nullable=False),
            sa.Column('source_token_address', sa.String(42), nullable=False),
            sa.Column('destination_token_address', sa.String(42), nullable=False),
            sa.Column('sender', sa.String(42), nullable=False),
            sa.Column('recipient', sa.String(42), nullable=False),
            sa.Column('from_value', sa.NUMERIC(), nullable=False),
            sa.Column('to_value', sa.NUMERIC(), nullable=True),
            sa.Column('block_number', sa.BIGINT(), nullable=True),
            sa.Column('tx_index', sa.Integer, nullable=True),
            )

def downgrade():
    op.drop_table('tx_cache')
    pass
