"""SessionRepository port and its SQLAlchemy implementation.

The port lets services depend on an abstraction; an alternate backend (document
store, in-memory) can implement the same interface for tests or edge deployments.
"""

from __future__ import annotations

import abc

from sqlalchemy import select
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

    # --- transcript -------------------------------------------------------
    @abc.abstractmethod
    def add_segment(self, row: m.TranscriptSegmentORM) -> m.TranscriptSegmentORM: ...

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
    def add_node(self, row: m.ConversationNodeORM) -> m.ConversationNodeORM: ...

    @abc.abstractmethod
    def list_nodes(self, branch_id: str) -> list[m.ConversationNodeORM]: ...

    # --- scripts ----------------------------------------------------------
    @abc.abstractmethod
    def add_script(self, row: m.ScriptDefinitionORM) -> m.ScriptDefinitionORM: ...

    @abc.abstractmethod
    def get_script(self, script_id: str) -> m.ScriptDefinitionORM | None: ...

    @abc.abstractmethod
    def list_scripts(self) -> list[m.ScriptDefinitionORM]: ...

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

    # transcript
    def add_segment(self, row: m.TranscriptSegmentORM) -> m.TranscriptSegmentORM:
        return self._add(row)

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

    def list_scripts(self) -> list[m.ScriptDefinitionORM]:
        return list(self._db.scalars(select(m.ScriptDefinitionORM)))

    def commit(self) -> None:
        self._db.commit()
