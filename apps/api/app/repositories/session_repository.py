"""SessionRepository port and its SQLAlchemy implementation.

The port lets services depend on an abstraction; an alternate backend (document
store, in-memory) can implement the same interface for tests or edge deployments.
"""

from __future__ import annotations

import abc

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..db import models as m


class SessionRepository(abc.ABC):
    """Aggregate persistence port for a discovery session and its children."""

    # --- sessions ---------------------------------------------------------
    @abc.abstractmethod
    def add_session(self, row: m.DiscoverySessionORM) -> m.DiscoverySessionORM: ...

    @abc.abstractmethod
    def get_session(self, session_id: str) -> m.DiscoverySessionORM | None: ...

    @abc.abstractmethod
    def list_sessions(self) -> list[m.DiscoverySessionORM]: ...

    @abc.abstractmethod
    def delete_session(self, session_id: str) -> None: ...

    @abc.abstractmethod
    def pause_active_sessions(self, *, except_session_id: str | None = None) -> None: ...

    # --- workspace profiles ----------------------------------------------
    @abc.abstractmethod
    def add_workspace_profile(self, row: m.WorkspaceProfileORM) -> m.WorkspaceProfileORM: ...

    @abc.abstractmethod
    def get_workspace_profile(self, workspace_id: str) -> m.WorkspaceProfileORM | None: ...

    @abc.abstractmethod
    def list_workspace_profiles(self) -> list[m.WorkspaceProfileORM]: ...

    # --- transcript -------------------------------------------------------
    @abc.abstractmethod
    def add_segment(self, row: m.TranscriptSegmentORM) -> m.TranscriptSegmentORM: ...

    @abc.abstractmethod
    def get_segment(self, segment_id: str) -> m.TranscriptSegmentORM | None: ...

    @abc.abstractmethod
    def list_segments(self, session_id: str) -> list[m.TranscriptSegmentORM]: ...

    @abc.abstractmethod
    def next_sequence(self, session_id: str) -> int: ...

    # --- artifacts + evidence --------------------------------------------
    @abc.abstractmethod
    def add_artifact(self, row: m.DiscoveryArtifactORM) -> m.DiscoveryArtifactORM: ...

    @abc.abstractmethod
    def get_artifact(self, artifact_id: str) -> m.DiscoveryArtifactORM | None: ...

    @abc.abstractmethod
    def list_artifacts(self, session_id: str) -> list[m.DiscoveryArtifactORM]: ...

    @abc.abstractmethod
    def add_evidence(self, row: m.EvidenceLinkORM) -> m.EvidenceLinkORM: ...

    @abc.abstractmethod
    def list_evidence_for_artifact(self, artifact_id: str) -> list[m.EvidenceLinkORM]: ...

    @abc.abstractmethod
    def list_evidence(self, session_id: str) -> list[m.EvidenceLinkORM]: ...

    @abc.abstractmethod
    def add_revision(self, row: m.ArtifactRevisionORM) -> m.ArtifactRevisionORM: ...

    @abc.abstractmethod
    def list_revisions(self, artifact_id: str) -> list[m.ArtifactRevisionORM]: ...

    # --- branches + nodes -------------------------------------------------
    @abc.abstractmethod
    def add_branch(self, row: m.ConversationBranchORM) -> m.ConversationBranchORM: ...

    @abc.abstractmethod
    def get_branch(self, branch_id: str) -> m.ConversationBranchORM | None: ...

    @abc.abstractmethod
    def list_branches(self, session_id: str) -> list[m.ConversationBranchORM]: ...

    @abc.abstractmethod
    def delete_branch(self, branch_id: str) -> None: ...

    @abc.abstractmethod
    def add_node(self, row: m.ConversationNodeORM) -> m.ConversationNodeORM: ...

    @abc.abstractmethod
    def list_nodes(self, branch_id: str) -> list[m.ConversationNodeORM]: ...

    # --- scripts ----------------------------------------------------------
    @abc.abstractmethod
    def add_script(self, row: m.ScriptDefinitionORM) -> m.ScriptDefinitionORM: ...

    @abc.abstractmethod
    def get_script(self, script_id: str) -> m.ScriptDefinitionORM | None: ...

    @abc.abstractmethod
    def list_scripts(self, *, include_archived: bool = False) -> list[m.ScriptDefinitionORM]: ...

    @abc.abstractmethod
    def commit(self) -> None: ...


class SqlAlchemySessionRepository(SessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def _add(self, row):  # type: ignore[no-untyped-def]
        self._db.add(row)
        self._db.flush()
        return row

    # sessions
    def add_session(self, row: m.DiscoverySessionORM) -> m.DiscoverySessionORM:
        return self._add(row)

    def get_session(self, session_id: str) -> m.DiscoverySessionORM | None:
        return self._db.get(m.DiscoverySessionORM, session_id)

    def list_sessions(self) -> list[m.DiscoverySessionORM]:
        return list(
            self._db.scalars(
                select(m.DiscoverySessionORM).order_by(m.DiscoverySessionORM.created_at.desc())
            )
        )

    def delete_session(self, session_id: str) -> None:
        row = self.get_session(session_id)
        if row is not None:
            self._db.delete(row)  # relationships cascade to the full conversation aggregate
            self._db.flush()

    def pause_active_sessions(self, *, except_session_id: str | None = None) -> None:
        statement = update(m.DiscoverySessionORM).where(m.DiscoverySessionORM.status == "active")
        if except_session_id is not None:
            statement = statement.where(m.DiscoverySessionORM.id != except_session_id)
        self._db.execute(statement.values(status="paused"))
        # An active-session uniqueness constraint protects concurrent writers.
        # Flush the pauses before a new active row is inserted.
        self._db.flush()

    # workspace profiles
    def add_workspace_profile(self, row: m.WorkspaceProfileORM) -> m.WorkspaceProfileORM:
        return self._add(row)

    def get_workspace_profile(self, workspace_id: str) -> m.WorkspaceProfileORM | None:
        return self._db.get(m.WorkspaceProfileORM, workspace_id)

    def list_workspace_profiles(self) -> list[m.WorkspaceProfileORM]:
        return list(
            self._db.scalars(select(m.WorkspaceProfileORM).order_by(m.WorkspaceProfileORM.name))
        )

    # transcript
    def add_segment(self, row: m.TranscriptSegmentORM) -> m.TranscriptSegmentORM:
        return self._add(row)

    def get_segment(self, segment_id: str) -> m.TranscriptSegmentORM | None:
        return self._db.get(m.TranscriptSegmentORM, segment_id)

    def list_segments(self, session_id: str) -> list[m.TranscriptSegmentORM]:
        return list(
            self._db.scalars(
                select(m.TranscriptSegmentORM)
                .where(m.TranscriptSegmentORM.session_id == session_id)
                .order_by(m.TranscriptSegmentORM.sequence_number)
            )
        )

    def next_sequence(self, session_id: str) -> int:
        rows = self.list_segments(session_id)
        return (max((r.sequence_number for r in rows), default=0)) + 1

    # artifacts + evidence
    def add_artifact(self, row: m.DiscoveryArtifactORM) -> m.DiscoveryArtifactORM:
        return self._add(row)

    def get_artifact(self, artifact_id: str) -> m.DiscoveryArtifactORM | None:
        return self._db.get(m.DiscoveryArtifactORM, artifact_id)

    def list_artifacts(self, session_id: str) -> list[m.DiscoveryArtifactORM]:
        return list(
            self._db.scalars(
                select(m.DiscoveryArtifactORM)
                .where(m.DiscoveryArtifactORM.session_id == session_id)
                .order_by(m.DiscoveryArtifactORM.created_at)
            )
        )

    def add_evidence(self, row: m.EvidenceLinkORM) -> m.EvidenceLinkORM:
        return self._add(row)

    def list_evidence_for_artifact(self, artifact_id: str) -> list[m.EvidenceLinkORM]:
        return list(
            self._db.scalars(
                select(m.EvidenceLinkORM).where(m.EvidenceLinkORM.artifact_id == artifact_id)
            )
        )

    def list_evidence(self, session_id: str) -> list[m.EvidenceLinkORM]:
        return list(
            self._db.scalars(
                select(m.EvidenceLinkORM)
                .join(m.DiscoveryArtifactORM)
                .where(m.DiscoveryArtifactORM.session_id == session_id)
            )
        )

    def add_revision(self, row: m.ArtifactRevisionORM) -> m.ArtifactRevisionORM:
        return self._add(row)

    def list_revisions(self, artifact_id: str) -> list[m.ArtifactRevisionORM]:
        return list(
            self._db.scalars(
                select(m.ArtifactRevisionORM)
                .where(m.ArtifactRevisionORM.artifact_id == artifact_id)
                .order_by(m.ArtifactRevisionORM.revision_number)
            )
        )

    # branches + nodes
    def add_branch(self, row: m.ConversationBranchORM) -> m.ConversationBranchORM:
        return self._add(row)

    def get_branch(self, branch_id: str) -> m.ConversationBranchORM | None:
        return self._db.get(m.ConversationBranchORM, branch_id)

    def list_branches(self, session_id: str) -> list[m.ConversationBranchORM]:
        return list(
            self._db.scalars(
                select(m.ConversationBranchORM)
                .where(m.ConversationBranchORM.session_id == session_id)
                .order_by(m.ConversationBranchORM.created_at)
            )
        )

    def delete_branch(self, branch_id: str) -> None:
        row = self._db.get(m.ConversationBranchORM, branch_id)
        if row is not None:
            self._db.delete(row)  # cascade removes the branch's nodes
            self._db.flush()

    def add_node(self, row: m.ConversationNodeORM) -> m.ConversationNodeORM:
        return self._add(row)

    def list_nodes(self, branch_id: str) -> list[m.ConversationNodeORM]:
        return list(
            self._db.scalars(
                select(m.ConversationNodeORM)
                .where(m.ConversationNodeORM.branch_id == branch_id)
                .order_by(m.ConversationNodeORM.sequence)
            )
        )

    # scripts
    def add_script(self, row: m.ScriptDefinitionORM) -> m.ScriptDefinitionORM:
        return self._add(row)

    def get_script(self, script_id: str) -> m.ScriptDefinitionORM | None:
        return self._db.get(m.ScriptDefinitionORM, script_id)

    def list_scripts(self, *, include_archived: bool = False) -> list[m.ScriptDefinitionORM]:
        statement = select(m.ScriptDefinitionORM).order_by(m.ScriptDefinitionORM.name)
        if not include_archived:
            statement = statement.where(m.ScriptDefinitionORM.archived.is_(False))
        return list(self._db.scalars(statement))

    def commit(self) -> None:
        self._db.commit()
