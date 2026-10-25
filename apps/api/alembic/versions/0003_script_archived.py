"""Add archive state for managed discovery scripts.

Revision ID: 0003_script_archived
Revises: 0002_speaker_identity
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_script_archived"
down_revision: str | None = "0002_speaker_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "script_definitions",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("script_definitions", "archived")
