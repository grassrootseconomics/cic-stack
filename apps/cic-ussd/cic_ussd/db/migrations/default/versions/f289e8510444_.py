"""Create account table

Revision ID: f289e8510444
Revises: 
Create Date: 2020-07-14 21:37:13.014200

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f289e8510444'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('account',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('blockchain_address', sa.String(), nullable=False),
                    sa.Column('phone_number', sa.String(), nullable=False),
                    sa.Column('preferred_language', sa.String(), nullable=True),
                    sa.Column('password_hash', sa.String(), nullable=True),
                    sa.Column('failed_pin_attempts', sa.Integer(), nullable=False),
                    sa.Column('guardians', sa.String(), nullable=True),
                    sa.Column('guardian_quora', sa.Integer(), nullable=False),
                    sa.Column('status', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=False),
                    sa.Column('updated', sa.DateTime(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_account_phone_number'), 'account', ['phone_number'], unique=True)
    op.create_index(op.f('ix_account_blockchain_address'), 'account', ['blockchain_address'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_account_blockchain_address'), table_name='account')
    op.drop_index(op.f('ix_account_phone_number'), table_name='account')
    op.drop_table('account')
