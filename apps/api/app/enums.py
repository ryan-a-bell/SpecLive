from enum import StrEnum


class SessionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SegmentStatus(StrEnum):
    RECEIVED = "received"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"


class ArtifactType(StrEnum):
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


ARTIFACT_CODE_PREFIX: dict[ArtifactType, str] = {
    ArtifactType.OBJECTIVE: "OBJ",
    ArtifactType.STAKEHOLDER_NEED: "NEED",
    ArtifactType.REQUIREMENT: "REQ",
    ArtifactType.CONSTRAINT: "CON",
    ArtifactType.ASSUMPTION: "ASM",
    ArtifactType.RISK: "RISK",
    ArtifactType.DECISION: "DEC",
    ArtifactType.OPEN_QUESTION: "Q",
    ArtifactType.SUCCESS_METRIC: "MET",
    ArtifactType.INTEGRATION: "INT",
    ArtifactType.STAKEHOLDER: "STK",
}


class ArtifactStatus(StrEnum):
    """Artifact lifecycle states.

    Progression: detected -> inferred -> clarified -> customer_confirmed -> baselined.
    Terminal side-states: rejected, superseded, merged.
    """

    DETECTED = "detected"
    INFERRED = "inferred"
    CLARIFIED = "clarified"
    CUSTOMER_CONFIRMED = "customer_confirmed"
    BASELINED = "baselined"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    MERGED = "merged"


# Transitions allowed through the generic PATCH endpoint. Entering
# CUSTOMER_CONFIRMED is deliberately absent: it requires the explicit
# /confirm action (human validation before baselining, ADR-0007).
PATCH_TRANSITIONS: dict[ArtifactStatus, set[ArtifactStatus]] = {
    ArtifactStatus.DETECTED: {ArtifactStatus.INFERRED, ArtifactStatus.REJECTED},
    ArtifactStatus.INFERRED: {
        ArtifactStatus.CLARIFIED,
        ArtifactStatus.REJECTED,
        ArtifactStatus.SUPERSEDED,
    },
    ArtifactStatus.CLARIFIED: {ArtifactStatus.REJECTED, ArtifactStatus.SUPERSEDED},
    ArtifactStatus.CUSTOMER_CONFIRMED: {
        ArtifactStatus.BASELINED,
        ArtifactStatus.SUPERSEDED,
        ArtifactStatus.REJECTED,
    },
    ArtifactStatus.BASELINED: {ArtifactStatus.SUPERSEDED},
    ArtifactStatus.REJECTED: set(),
    ArtifactStatus.SUPERSEDED: set(),
    ArtifactStatus.MERGED: set(),
}

# States from which the explicit /confirm action is allowed.
CONFIRMABLE_STATES = {
    ArtifactStatus.DETECTED,
    ArtifactStatus.INFERRED,
    ArtifactStatus.CLARIFIED,
}

# States from which /reject and /merge are allowed.
CLOSABLE_STATES = {
    ArtifactStatus.DETECTED,
    ArtifactStatus.INFERRED,
    ArtifactStatus.CLARIFIED,
    ArtifactStatus.CUSTOMER_CONFIRMED,
}


class ValidationState(StrEnum):
    UNVALIDATED = "unvalidated"
    NEEDS_VALIDATION = "needs_validation"
    VALIDATED = "validated"
    CONTRADICTED = "contradicted"


class DerivationMethod(StrEnum):
    MANUAL = "manual"
    HEURISTIC = "heuristic"
    LLM = "llm"


class EvidenceRelationship(StrEnum):
    DIRECT = "direct"
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    SUPERSEDING = "superseding"
    CONTEXTUAL = "contextual"


class BranchStatus(StrEnum):
    QUEUED = "queued"
    OPEN = "open"
    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"


class NodeType(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    FINDING = "finding"
    REQUIREMENT = "requirement"
    RISK = "risk"
    DECISION = "decision"


class CoverageState(StrEnum):
    STRONG = "strong"
    PARTIAL = "partial"
    UNANSWERED = "unanswered"
    CONTRADICTORY = "contradictory"
    NEEDS_VALIDATION = "needs_validation"
    CONFIRMED = "confirmed"
