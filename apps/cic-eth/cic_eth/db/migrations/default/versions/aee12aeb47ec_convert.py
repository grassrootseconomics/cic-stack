"""Convert

Revision ID: aee12aeb47ec
Revises: 5ca4b77ce205
Create Date: 2021-04-02 18:42:45.233356

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aee12aeb47ec'
down_revision = '5ca4b77ce205'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'tx_convert_transfer',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('convert_tx_hash', sa.String(66), nullable=False, unique=True),
            sa.Column('transfer_tx_hash', sa.String(66), unique=True),
            sa.Column('recipient_address', sa.String(42), nullable=False),
            )
    op.create_index('idx_tx_convert_address', 'tx_convert_transfer', ['recipient_address'])


def downgrade():
    op.drop_index('idx_tx_convert_address')
    op.drop_table('tx_convert_transfer')
