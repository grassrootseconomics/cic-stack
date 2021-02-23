"""Add chain syncer

Revision ID: ec40ac0974c1
Revises: 6ac7a1dadc46
Create Date: 2021-02-23 06:10:19.246304

"""
from alembic import op
import sqlalchemy as sa
from chainsyncer.db.migrations.sqlalchemy import (
        chainsyncer_upgrade,
        chainsyncer_downgrade,
        )


# revision identifiers, used by Alembic.
revision = 'ec40ac0974c1'
down_revision = '6ac7a1dadc46'
branch_labels = None
depends_on = None


def upgrade():
    chainsyncer_upgrade(0, 0, 1)


def downgrade():
    chainsyncer_downgrade(0, 0, 1)
