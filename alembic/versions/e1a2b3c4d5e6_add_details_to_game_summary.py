"""Add details column to game_summary

Revision ID: e1a2b3c4d5e6
Revises: dd1e8a2b9f3c
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = 'dd1e8a2b9f3c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: add column only if it does not exist (e.g. DB was migrated manually or re-run)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'game_summary' AND column_name = 'details'"
    ))
    if result.scalar() is None:
        op.add_column('game_summary', sa.Column('details', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('game_summary', 'details')
