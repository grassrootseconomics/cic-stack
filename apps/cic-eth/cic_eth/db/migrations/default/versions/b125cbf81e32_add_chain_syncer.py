"""Add chain syncer

Revision ID: b125cbf81e32
Revises: 0ec0d6d1e785
Create Date: 2021-04-02 18:36:44.459603

"""
from alembic import op
import sqlalchemy as sa

from chainsyncer.db.migrations.default.export import (
        chainsyncer_upgrade,
        chainsyncer_downgrade,
        )


# revision identifiers, used by Alembic.
revision = 'b125cbf81e32'
down_revision = '0ec0d6d1e785'
branch_labels = None
depends_on = None

def upgrade():
    chainsyncer_upgrade(0, 0, 1)


def downgrade():
    chainsyncer_downgrade(0, 0, 1)

