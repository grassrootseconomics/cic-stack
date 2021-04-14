"""Roles

Revision ID: 1f1b3b641d08
Revises: 9c420530eeb2
Create Date: 2021-04-02 18:40:27.787631

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f1b3b641d08'
down_revision = '9c420530eeb2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'account_role',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tag', sa.Text, nullable=False, unique=True),
        sa.Column('address_hex', sa.String(42), nullable=False),
        )


def downgrade():
    op.drop_table('account_role')
