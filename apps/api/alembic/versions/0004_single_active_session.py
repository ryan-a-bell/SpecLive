"""Allow only one active discovery session.

Revision ID: 0004_single_active_session
Revises: 0003_script_archived
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_single_active_session"
down_revision: str | None = "0003_script_archived"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    active_ids = list(
        bind.execute(
            sa.text(
                "SELECT id FROM discovery_sessions "
                "WHERE status = 'active' ORDER BY created_at DESC, id DESC"
            )
        ).scalars()
    )
    if len(active_ids) > 1:
        bind.execute(
            sa.text(
                "UPDATE discovery_sessions SET status = 'paused' "
                "WHERE status = 'active' AND id != :keep_id"
            ),
            {"keep_id": active_ids[0]},
        )

    op.create_index(
        "uq_discovery_sessions_one_active",
        "discovery_sessions",
        ["status"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_discovery_sessions_one_active", table_name="discovery_sessions")
