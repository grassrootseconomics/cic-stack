"""Nonce

Revision ID: 9c420530eeb2
Revises: b125cbf81e32
Create Date: 2021-04-02 18:38:56.459334

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c420530eeb2'
down_revision = 'b125cbf81e32'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nonce',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('address_hex', sa.String(42), nullable=False, unique=True),
        sa.Column('nonce', sa.Integer, nullable=False),
        )

    op.create_table(
        'nonce_task_reservation',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('address_hex', sa.String(42), nullable=False),
        sa.Column('nonce', sa.Integer, nullable=False),
        sa.Column('key', sa.String, nullable=False),
        sa.Column('date_created', sa.DateTime, nullable=False),
        )


def downgrade():
    op.drop_table('nonce_task_reservation')
    op.drop_table('nonce')
