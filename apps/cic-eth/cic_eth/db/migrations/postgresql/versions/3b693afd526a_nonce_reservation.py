"""Nonce reservation

Revision ID: 3b693afd526a
Revises: f738d9962fdf
Create Date: 2021-03-05 07:09:50.898728

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b693afd526a'
down_revision = 'f738d9962fdf'
branch_labels = None
depends_on = None


def upgrade():
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
