"""Add diarization-ready speaker identity fields.

Revision ID: 0002_speaker_identity
Revises: 0001_initial
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_speaker_identity"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transcript_segments", sa.Column("speaker_id", sa.String(128), nullable=True))
    op.add_column("transcript_segments", sa.Column("speaker_name", sa.String(255), nullable=True))
    op.add_column(
        "transcript_segments",
        sa.Column("speaker_source", sa.String(32), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "transcript_segments", sa.Column("speaker_confidence", sa.Float(), nullable=True)
    )
    op.create_index(
        "ix_transcript_segments_speaker_id", "transcript_segments", ["speaker_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_segments_speaker_id", table_name="transcript_segments")
    op.drop_column("transcript_segments", "speaker_confidence")
    op.drop_column("transcript_segments", "speaker_source")
    op.drop_column("transcript_segments", "speaker_name")
    op.drop_column("transcript_segments", "speaker_id")
