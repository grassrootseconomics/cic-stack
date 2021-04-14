"""Lock

Revision ID: 75d4767b3031
Revises: 1f1b3b641d08
Create Date: 2021-04-02 18:41:20.864265

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75d4767b3031'
down_revision = '1f1b3b641d08'
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
            sa.Column("otx_id", sa.Integer, sa.ForeignKey('otx.id'), nullable=True),
            )
    op.create_index('idx_chain_address', 'lock', ['blockchain', 'address'], unique=True)


def downgrade():
    op.drop_index('idx_chain_address')
    op.drop_table('lock')
