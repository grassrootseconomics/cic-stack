"""Create ussd session table

Revision ID: 2a329190a9af
Revises: b5ab9371c0b8
Create Date: 2020-10-06 00:06:54.354168

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2a329190a9af'
down_revision = 'f289e8510444'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ussd_session',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('updated', sa.DateTime(), nullable=True),
                    sa.Column('external_session_id', sa.String(), nullable=False),
                    sa.Column('service_code', sa.String(), nullable=False),
                    sa.Column('msisdn', sa.String(), nullable=False),
                    sa.Column('user_input', sa.String(), nullable=True),
                    sa.Column('state', sa.String(), nullable=False),
                    sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
                    sa.Column('version', sa.Integer(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_ussd_session_external_session_id'), 'ussd_session', ['external_session_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_ussd_session_external_session_id'), table_name='ussd_session')
    op.drop_table('ussd_session')
