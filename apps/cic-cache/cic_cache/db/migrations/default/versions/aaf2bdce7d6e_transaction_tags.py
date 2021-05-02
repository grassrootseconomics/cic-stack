"""Transaction tags

Revision ID: aaf2bdce7d6e
Revises: 6604de4203e2
Create Date: 2021-05-01 09:20:20.775082

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aaf2bdce7d6e'
down_revision = '6604de4203e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
            'tag',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('domain', sa.String(), nullable=True),
            sa.Column('value', sa.String(), nullable=False),
            )
    op.create_index('idx_tag_domain_value', 'tag', ['domain', 'value'], unique=True)

    op.create_table(
            'tag_tx_link',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tag_id', sa.Integer, sa.ForeignKey('tag.id'), nullable=False),
            sa.Column('tx_id', sa.Integer, sa.ForeignKey('tx.id'), nullable=False),
                )

def downgrade():
    op.drop_table('tag_tx_link')
    op.drop_index('idx_tag_domain_value')
    op.drop_table('tag')
