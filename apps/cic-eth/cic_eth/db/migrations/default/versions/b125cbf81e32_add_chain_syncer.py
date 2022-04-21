"""Add chain syncer

Revision ID: b125cbf81e32
Revises: 0ec0d6d1e785
Create Date: 2021-04-02 18:36:44.459603

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b125cbf81e32'
down_revision = '0ec0d6d1e785'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
            'chain_sync',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('blockchain', sa.String, nullable=False),
            sa.Column('block_start', sa.Integer, nullable=False, default=0),
            sa.Column('tx_start', sa.Integer, nullable=False, default=0),
            sa.Column('block_cursor', sa.Integer, nullable=False, default=0),
            sa.Column('tx_cursor', sa.Integer, nullable=False, default=0),
            sa.Column('block_target', sa.Integer, nullable=True),
            sa.Column('date_created', sa.DateTime, nullable=False),
            sa.Column('date_updated', sa.DateTime),
            )

    op.create_table(
            'chain_sync_filter',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('chain_sync_id', sa.Integer, sa.ForeignKey('chain_sync.id'), nullable=True),
            sa.Column('flags', sa.LargeBinary, nullable=True),
            sa.Column('flags_lock', sa.Integer, nullable=False, default=0),
            sa.Column('flags_start', sa.LargeBinary, nullable=True),
            sa.Column('count', sa.Integer, nullable=False, default=0),
            sa.Column('digest', sa.String(64), nullable=False),
            )

    op.create_table(
            'chain_sync_tx',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('blockchain', sa.String, nullable=False),
            sa.Column('chain_sync_id', sa.Integer, sa.ForeignKey('chain_sync.id'), nullable=False),
            sa.Column('flags', sa.LargeBinary, nullable=True),
            sa.Column('block', sa.Integer, nullable=False),
            sa.Column('tx', sa.Integer, nullable=False),
            )




def downgrade():
    op.drop_table('chain_sync_tx')
    op.drop_table('chain_sync_filter')
    op.drop_table('chain_sync')
