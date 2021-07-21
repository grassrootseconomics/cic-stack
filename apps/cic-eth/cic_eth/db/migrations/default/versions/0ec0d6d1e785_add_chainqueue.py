"""Add chainqueue

Revision ID: 0ec0d6d1e785
Revises: 
Create Date: 2021-04-02 18:30:55.398388

"""
from alembic import op
import sqlalchemy as sa

#from chainqueue.db.migrations.sqlalchemy import (
from chainqueue.db.migrations.default.export import (
        chainqueue_upgrade,
        chainqueue_downgrade,
        )

# revision identifiers, used by Alembic.
revision = '0ec0d6d1e785'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    chainqueue_upgrade(0, 0, 1)


def downgrade():
    chainqueue_downgrade(0, 0, 1)

