"""Session, transcript, projection, analysis, script and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from ...domain import entities as e
from ..deps import Services, get_services
from ..schemas import (
    SessionCreate,
    SessionPatch,
    TranscriptSegmentCreate,
    TranscriptSpeakerCorrection,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=e.DiscoverySession, status_code=201)
def create_session(
    body: SessionCreate, svc: Services = Depends(get_services)
) -> e.DiscoverySession:
    return svc.sessions.create(
        title=body.title,
        customer=body.customer,
        facilitator=body.facilitator,
        script_id=body.script_id,
        metadata=body.metadata,
    )


@router.get("", response_model=list[e.DiscoverySession])
def list_sessions(svc: Services = Depends(get_services)) -> list[e.DiscoverySession]:
    return svc.sessions.list()


@router.get("/{session_id}", response_model=e.DiscoverySession)
def get_session(session_id: str, svc: Services = Depends(get_services)) -> e.DiscoverySession:
    return svc.sessions.get(session_id)


@router.patch("/{session_id}", response_model=e.DiscoverySession)
def patch_session(
    session_id: str, body: SessionPatch, svc: Services = Depends(get_services)
) -> e.DiscoverySession:
    return svc.sessions.patch(session_id, **body.model_dump(exclude_unset=True))


# --- transcript -----------------------------------------------------------
@router.post("/{session_id}/transcript", response_model=e.TranscriptSegment, status_code=201)
def add_transcript_segment(
    session_id: str, body: TranscriptSegmentCreate, svc: Services = Depends(get_services)
) -> e.TranscriptSegment:
    return svc.transcript.add_segment(
        session_id,
        speaker=body.speaker,
        text=body.text,
        start_time=body.start_time,
        end_time=body.end_time,
        is_final=body.is_final,
        sequence_number=body.sequence_number,
        speaker_id=body.speaker_id,
        speaker_name=body.speaker_name,
        speaker_source=body.speaker_source,
        speaker_confidence=body.speaker_confidence,
    )


@router.patch(
    "/{session_id}/transcript/{segment_id}/speaker",
    response_model=list[e.TranscriptSegment],
)
def correct_transcript_speaker(
    session_id: str,
    segment_id: str,
    body: TranscriptSpeakerCorrection,
    svc: Services = Depends(get_services),
) -> list[e.TranscriptSegment]:
    return svc.transcript.correct_speaker(
        session_id,
        segment_id,
        speaker=body.speaker,
        speaker_name=body.speaker_name,
        apply_to_voice=body.apply_to_voice,
    )


@router.get("/{session_id}/transcript", response_model=list[e.TranscriptSegment])
def list_transcript(
    session_id: str, svc: Services = Depends(get_services)
) -> list[e.TranscriptSegment]:
    return svc.transcript.list_segments(session_id)


@router.get("/{session_id}/evidence", response_model=list[e.EvidenceLink])
def list_session_evidence(
    session_id: str, svc: Services = Depends(get_services)
) -> list[e.EvidenceLink]:
    """All evidence links in the session — used to highlight transcript spans."""

    return svc.artifacts.list_evidence_for_session(session_id)


# --- projections ----------------------------------------------------------
@router.get("/{session_id}/discovery-tree")
def discovery_tree(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.tree.build(session_id)


@router.get("/{session_id}/conversation-graph")
def conversation_graph(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.branches.graph(session_id)


@router.get("/{session_id}/coverage")
def coverage(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.coverage.build(session_id)


@router.get("/{session_id}/recommendations")
def recommendations(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.recommendations.recommend(session_id)


# --- analysis -------------------------------------------------------------
@router.post("/{session_id}/analyze", response_model=list[e.DiscoveryArtifact])
def analyze_session(
    session_id: str, svc: Services = Depends(get_services)
) -> list[e.DiscoveryArtifact]:
    return svc.analysis.analyze_session(session_id)


# --- script ---------------------------------------------------------------
@router.get("/{session_id}/script")
def script_state(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.scripts.state(session_id)


@router.post("/{session_id}/script/advance")
def advance_script(session_id: str, svc: Services = Depends(get_services)) -> dict:
    return svc.scripts.advance(session_id)


# --- export ---------------------------------------------------------------
@router.get("/{session_id}/export")
def export_session(
    session_id: str, format: str = "json", svc: Services = Depends(get_services)
) -> Response:
    content, media_type = svc.export.export(session_id, format)
    return Response(content=content, media_type=media_type)
