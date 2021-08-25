"""Add chain syncer

Revision ID: 6604de4203e2
Revises: 63b629f14a85
Create Date: 2021-04-01 08:10:29.156243

"""
from alembic import op
import sqlalchemy as sa
from chainsyncer.db.migrations.default.export import (
        chainsyncer_upgrade,
        chainsyncer_downgrade,
        )


# revision identifiers, used by Alembic.
revision = '6604de4203e2'
down_revision = '63b629f14a85'
branch_labels = None
depends_on = None

def upgrade():
    chainsyncer_upgrade(0, 0, 1)


def downgrade():
    chainsyncer_downgrade(0, 0, 1)

