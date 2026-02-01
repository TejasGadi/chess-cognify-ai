"""Add outline to books table

Revision ID: dd1e8a2b9f3c
Revises: 1176feea5285
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd1e8a2b9f3c'
down_revision = '1176feea5285'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('books', sa.Column('outline', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'outline')
