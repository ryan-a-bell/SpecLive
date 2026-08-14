"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "script_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "script_stages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("script_id", sa.String(36), sa.ForeignKey("script_definitions.id"), index=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("primary_prompt", sa.Text(), nullable=False),
        sa.Column("alternative_prompts", sa.JSON(), nullable=False),
        sa.Column("completion_criteria", sa.JSON(), nullable=False),
    )
    op.create_table(
        "discovery_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(255), nullable=False),
        sa.Column("facilitator", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("script_id", sa.String(36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("discovery_sessions.id"), index=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(32), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=True),
        sa.Column("end_time", sa.Float(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "discovery_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("discovery_sessions.id"), index=True),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="candidate"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("validation_state", sa.String(32), nullable=False, server_default="detected"),
        sa.Column("derivation_method", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("parent_id", sa.String(36), nullable=True, index=True),
        sa.Column("branch_id", sa.String(36), nullable=True, index=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("superseded_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "evidence_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "artifact_id", sa.String(36), sa.ForeignKey("discovery_artifacts.id"), index=True
        ),
        sa.Column(
            "transcript_segment_id",
            sa.String(36),
            sa.ForeignKey("transcript_segments.id"),
            index=True,
        ),
        sa.Column("quote_start", sa.Integer(), nullable=False),
        sa.Column("quote_end", sa.Integer(), nullable=False),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False, server_default="supporting"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "artifact_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "artifact_id", sa.String(36), sa.ForeignKey("discovery_artifacts.id"), index=True
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=False),
        sa.Column("new_value", sa.JSON(), nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "conversation_branches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("discovery_sessions.id"), index=True),
        sa.Column("parent_branch_id", sa.String(36), nullable=True),
        sa.Column("source_stage_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_from_segment_id", sa.String(36), nullable=True),
        sa.Column("merge_target_stage_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "conversation_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "branch_id", sa.String(36), sa.ForeignKey("conversation_branches.id"), index=True
        ),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("transcript_segment_id", sa.String(36), nullable=True),
        sa.Column("artifact_id", sa.String(36), nullable=True),
        sa.Column("parent_node_id", sa.String(36), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for table in [
        "conversation_nodes",
        "conversation_branches",
        "artifact_revisions",
        "evidence_links",
        "discovery_artifacts",
        "transcript_segments",
        "discovery_sessions",
        "script_stages",
        "script_definitions",
    ]:
        op.drop_table(table)
