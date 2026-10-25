"""Add persistent client profiles for workspaces.

Revision ID: 0005_workspace_profiles
Revises: 0004_single_active_session
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_workspace_profiles"
down_revision: str | None = "0004_single_active_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_profiles",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("industry", sa.String(255), nullable=False, server_default=""),
        sa.Column("website", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_profiles_name", "workspace_profiles", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workspace_profiles_name", table_name="workspace_profiles")
    op.drop_table("workspace_profiles")
