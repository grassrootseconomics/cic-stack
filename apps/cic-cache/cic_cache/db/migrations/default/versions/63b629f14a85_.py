"""Base tables

Revision ID: 63b629f14a85
Revises: 
Create Date: 2020-12-04 08:16:00.412189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63b629f14a85'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'tx',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('date_registered', sa.DateTime, nullable=False),
            sa.Column('block_number', sa.Integer, nullable=False),
            sa.Column('tx_index', sa.Integer, nullable=False),
            sa.Column('tx_hash', sa.String(66), nullable=False),
            sa.Column('sender', sa.String(42), nullable=False),
            sa.Column('recipient', sa.String(42), nullable=False),
            sa.Column('source_token', sa.String(42), nullable=False),
            sa.Column('recipient_token', sa.String(42), nullable=False),
            sa.Column('success', sa.Boolean, nullable=False),
            sa.Column('date_block', sa.DateTime, nullable=False),
            )
    op.create_table(
            'tx_sync',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tx', sa.String(66), nullable=False),
            )

    op.execute("INSERT INTO tx_sync (tx) VALUES('0x0000000000000000000000000000000000000000000000000000000000000000');")

def downgrade():
    op.drop_table('tx_sync')
    op.drop_table('tx')
