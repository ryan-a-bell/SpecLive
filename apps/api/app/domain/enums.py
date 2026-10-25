"""Enumerations for the discovery domain."""

from __future__ import annotations

from enum import Enum


class SessionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Speaker(str, Enum):
    FACILITATOR = "facilitator"
    CUSTOMER = "customer"
    PARTICIPANT = "participant"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SpeakerSource(str, Enum):
    MANUAL = "manual"
    DETECTED = "detected"
    CORRECTED = "corrected"
    UNKNOWN = "unknown"


class ArtifactType(str, Enum):
    OBJECTIVE = "objective"
    STAKEHOLDER_NEED = "stakeholder_need"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    RISK = "risk"
    DECISION = "decision"
    OPEN_QUESTION = "open_question"
    SUCCESS_METRIC = "success_metric"
    INTEGRATION = "integration"
    STAKEHOLDER = "stakeholder"


class ValidationState(str, Enum):
    """Artifact lifecycle. Progression is forward through the linear states;
    terminal/branch states may be reached from most states via explicit action.
    """

    DETECTED = "detected"
    INFERRED = "inferred"
    CLARIFIED = "clarified"
    CUSTOMER_CONFIRMED = "customer_confirmed"
    BASELINED = "baselined"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    MERGED = "merged"


class ArtifactStatus(str, Enum):
    """Human-facing rollup used by the UI badges/columns."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    BASELINED = "baselined"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceRelationship(str, Enum):
    DIRECT = "direct"
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    SUPERSEDING = "superseding"
    CONTEXTUAL = "contextual"


class DerivationMethod(str, Enum):
    """How a candidate artifact was produced."""

    MANUAL = "manual"
    KEYWORD_HEURISTIC = "keyword_heuristic"
    LLM = "llm"
    IMPORTED = "imported"


class BranchStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    QUEUED = "queued"
    MERGED = "merged"
    ABANDONED = "abandoned"


class ConversationNodeType(str, Enum):
    SCRIPT_STAGE = "script_stage"
    QUESTION = "question"
    ANSWER = "answer"
    FINDING = "finding"
    REQUIREMENT = "requirement"
    RISK = "risk"
    DECISION = "decision"
    MERGE = "merge"


class CoverageState(str, Enum):
    UNANSWERED = "unanswered"
    PARTIAL = "partial"
    STRONG = "strong"
    CONTRADICTORY = "contradictory"
    NEEDS_VALIDATION = "needs_validation"
    CONFIRMED = "confirmed"


class ContextScope(str, Enum):
    """Which artifacts an aggregated context bundle includes.

    ``baseline`` returns only human-confirmed items (see
    ``HUMAN_CONFIRMED_STATES``) — the requirements it is safe to architect
    *against*. ``all`` also includes candidate/inferred items, each of which
    still carries its ``validation_state`` and ``confidence`` so a consumer
    can weigh how much to trust it. This is the "depending on query type"
    knob for workspace context aggregation.
    """

    BASELINE = "baseline"
    ALL = "all"


# Which validation states count as "confirmed by a human" — never reachable
# from an automated derivation path.
HUMAN_CONFIRMED_STATES: frozenset[ValidationState] = frozenset(
    {ValidationState.CUSTOMER_CONFIRMED, ValidationState.BASELINED}
)
