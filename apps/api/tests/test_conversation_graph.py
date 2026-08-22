"""Transcript → conversation-graph reconstruction (input-parity)."""

from __future__ import annotations

from app.events import get_event_bus
from app.providers.mock import MockLanguageModelProvider
from app.repositories import SqlAlchemySessionRepository
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.branch_service import BranchService
from app.services.conversation_graph_service import ConversationGraphService
from app.services.session_service import SessionService
from app.services.transcript_service import TranscriptService

# A tiny facilitator/customer exchange whose customer turns trip the mock LLM's
# deterministic rules (real-time view, "within 30 seconds", "cannot replace").
_TURNS = [
    ("facilitator", "What is pushing you to rethink this now?"),
    (
        "customer",
        "We need a real-time view of operations and updates within 30 seconds of a change.",
    ),
    ("facilitator", "Any systems we have to work around?"),
    ("customer", "We cannot replace the WMS, and staff use rugged tablets."),
    ("facilitator", "Anything about connectivity in the yard?"),
]


def _wire(db):  # type: ignore[no-untyped-def]
    repo = SqlAlchemySessionRepository(db)
    bus = get_event_bus()
    sessions = SessionService(repo, bus)
    transcript = TranscriptService(repo, bus)
    artifacts = ArtifactService(repo, bus)
    analysis = AnalysisService(repo, artifacts, MockLanguageModelProvider())
    branches = BranchService(repo, bus)
    graph = ConversationGraphService(repo, branches)
    return sessions, transcript, analysis, graph


def _session_with_transcript(db):  # type: ignore[no-untyped-def]
    sessions, transcript, analysis, graph = _wire(db)
    session = sessions.create(title="T", customer="Acme", facilitator="R")
    for speaker, text in _TURNS:
        transcript.add_segment(session.id, speaker=speaker, text=text)  # type: ignore[arg-type]
    analysis.analyze_session(session.id)
    return session.id, graph


def test_build_populates_graph_from_transcript(db) -> None:  # type: ignore[no-untyped-def]
    """The whole point: an imported transcript yields a non-empty graph."""

    session_id, graph = _session_with_transcript(db)
    result = graph.build(session_id)

    branches = result["branches"]
    assert branches, "graph should not be empty after a transcript import"

    main = next(b for b in branches if b["topic"] == "main_script")
    assert main["nodes"], "main spine should carry the Q&A flow"
    # No script attached → main is the reconstructed question/answer spine.
    kinds = {n["node_type"] for n in main["nodes"]}
    assert {"question", "answer"} & kinds

    threads = [b for b in branches if b["topic"] != "main_script"]
    assert threads, "answers that produced artifacts should spawn follow-up threads"


def test_thread_nodes_link_back_to_segment_and_artifact(db) -> None:  # type: ignore[no-untyped-def]
    session_id, graph = _session_with_transcript(db)
    result = graph.build(session_id)

    artifact_nodes = [
        n
        for b in result["branches"]
        if b["topic"] != "main_script"
        for n in b["nodes"]
        if n["node_type"] in {"requirement", "finding", "risk", "decision"}
    ]
    assert artifact_nodes, "threads should carry the derived artifacts"
    for node in artifact_nodes:
        assert node["artifact_id"], "artifact nodes must link their artifact"
        assert node["transcript_segment_id"], "…and the segment they were derived from"


def test_build_is_idempotent(db) -> None:  # type: ignore[no-untyped-def]
    session_id, graph = _session_with_transcript(db)

    first = graph.build(session_id)
    second = graph.build(session_id)

    def shape(result):  # type: ignore[no-untyped-def]
        return sorted((b["id"], tuple(n["id"] for n in b["nodes"])) for b in result["branches"])

    assert shape(first) == shape(second), "re-running must not duplicate branches/nodes"


def test_build_does_not_clobber_authored_branches(db) -> None:  # type: ignore[no-untyped-def]
    """Hand-authored / live-steered branches (their own ids) survive a rebuild."""

    sessions, transcript, analysis, graph = _wire(db)
    session = sessions.create(title="T", customer="Acme", facilitator="R")
    for speaker, text in _TURNS:
        transcript.add_segment(session.id, speaker=speaker, text=text)  # type: ignore[arg-type]
    analysis.analyze_session(session.id)

    from app.domain.enums import ConversationNodeType

    branches_svc = BranchService(SqlAlchemySessionRepository(db), get_event_bus())
    authored = branches_svc.create_branch(session.id, name="Manual", topic="manual_topic")
    branches_svc.add_node(authored.id, node_type=ConversationNodeType.FINDING, label="kept")

    graph.build(session.id)
    graph.build(session.id)

    topics = {b["topic"] for b in graph.build(session.id)["branches"]}
    assert "manual_topic" in topics, "authored branch must be preserved across rebuilds"


def test_gaps_surface_is_derived(db) -> None:  # type: ignore[no-untyped-def]
    session_id, graph = _session_with_transcript(db)
    result = graph.build(session_id)

    gaps = result["gaps"]
    assert isinstance(gaps, list)
    # The trailing facilitator turn ("connectivity in the yard?") is never
    # answered → it must surface as an unanswered-question gap.
    assert any(g["kind"] == "unanswered_question" for g in gaps)
