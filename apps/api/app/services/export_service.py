"""Discovery package assembly and export.

`build_package` produces a format-neutral dict. Concrete exporters (JSON,
Markdown) turn it into a serialized artifact. The registry is the extension
point for future CSV/DOCX/ReqIF/Jira/DOORS/SysML exporters (ADR / roadmap).
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.enums import ArtifactStatus, ArtifactType
from app.errors import ValidationError
from app.models import DiscoveryArtifact
from app.schemas import ExportEnvelope
from app.services import artifact_service, branch_service, evidence_service
from app.services.session_service import get_session

_CONFIRMED = {ArtifactStatus.CUSTOMER_CONFIRMED, ArtifactStatus.BASELINED}
_ACTIVE = {
    ArtifactStatus.DETECTED,
    ArtifactStatus.INFERRED,
    ArtifactStatus.CLARIFIED,
    ArtifactStatus.CUSTOMER_CONFIRMED,
    ArtifactStatus.BASELINED,
}


def build_package(db: Session, session_id: str) -> dict:
    session = get_session(db, session_id)
    artifacts = [a for a in artifact_service.list_artifacts(db, session_id) if a.status in _ACTIVE]

    def of_type(t: ArtifactType) -> list[DiscoveryArtifact]:
        return [a for a in artifacts if a.artifact_type == t]

    confirmed_reqs = [
        a for a in of_type(ArtifactType.REQUIREMENT) if a.status in _CONFIRMED
    ]
    candidate_reqs = [
        a for a in of_type(ArtifactType.REQUIREMENT) if a.status not in _CONFIRMED
    ]

    branches = branch_service.list_branches(db, session_id)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "session": {
            "id": session.id,
            "title": session.title,
            "customer": session.customer,
            "facilitator": session.facilitator,
            "status": str(session.status),
        },
        "executive_summary": _summary(session, confirmed_reqs, candidate_reqs, artifacts),
        "objectives": [_item(a) for a in of_type(ArtifactType.OBJECTIVE)],
        "stakeholder_needs": [_item(a) for a in of_type(ArtifactType.STAKEHOLDER_NEED)],
        "confirmed_requirements": [_item(a) for a in confirmed_reqs],
        "candidate_requirements": [_item(a) for a in candidate_reqs],
        "constraints": [_item(a) for a in of_type(ArtifactType.CONSTRAINT)],
        "assumptions": [_item(a) for a in of_type(ArtifactType.ASSUMPTION)],
        "risks": [_item(a) for a in of_type(ArtifactType.RISK)],
        "decisions": [_item(a) for a in of_type(ArtifactType.DECISION)],
        "open_questions": [_item(a) for a in of_type(ArtifactType.OPEN_QUESTION)],
        "success_metrics": [_item(a) for a in of_type(ArtifactType.SUCCESS_METRIC)],
        "traceability": [_trace(db, a) for a in artifacts],
        "conversation_branches": [
            {
                "id": b.id,
                "name": b.name,
                "topic": b.topic,
                "status": str(b.status),
                "is_main": b.is_main,
                "node_count": len(b.nodes),
            }
            for b in branches
        ],
    }


def _summary(session, confirmed, candidate, artifacts) -> str:
    return (
        f"Discovery session for {session.customer} ({session.title}). "
        f"Captured {len(artifacts)} discovery artifacts, including "
        f"{len(confirmed)} customer-confirmed and {len(candidate)} candidate requirements. "
        "Candidate requirements are model-inferred and require customer validation "
        "before baselining."
    )


def _item(a: DiscoveryArtifact) -> dict:
    return {
        "id": a.id,
        "type": str(a.artifact_type),
        "title": a.title,
        "statement": a.statement,
        "status": str(a.status),
        "confidence": a.confidence,
        "validation_state": str(a.validation_state),
        "derivation_method": str(a.derivation_method),
        "rationale": a.rationale,
    }


def _trace(db: Session, a: DiscoveryArtifact) -> dict:
    links = evidence_service.list_links(db, a.id)
    return {
        "artifact_id": a.id,
        "title": a.title,
        "evidence": [
            {
                "segment_id": link.transcript_segment_id,
                "quote": link.quoted_text,
                "relationship": str(link.relationship_type),
                "confidence": link.confidence,
            }
            for link in links
        ],
    }


# --- Exporters ------------------------------------------------------------


class JsonExporter:
    format = "json"
    content_type = "application/json"

    def export(self, package: dict) -> str:
        return json.dumps(package, indent=2)


class MarkdownExporter:
    format = "markdown"
    content_type = "text/markdown"

    def export(self, package: dict) -> str:
        s = package["session"]
        out: list[str] = [
            f"# Discovery Package — {s['title']}",
            "",
            f"**Customer:** {s['customer']}  ",
            f"**Facilitator:** {s['facilitator']}  ",
            f"**Generated:** {package['generated_at']}",
            "",
            "## Executive Summary",
            "",
            package["executive_summary"],
            "",
        ]
        sections = [
            ("Customer Objectives", "objectives"),
            ("Stakeholder Needs", "stakeholder_needs"),
            ("Confirmed Requirements", "confirmed_requirements"),
            ("Candidate Requirements", "candidate_requirements"),
            ("Constraints", "constraints"),
            ("Assumptions", "assumptions"),
            ("Risks", "risks"),
            ("Decisions", "decisions"),
            ("Open Questions", "open_questions"),
            ("Success Metrics", "success_metrics"),
        ]
        for heading, key in sections:
            items = package[key]
            out.append(f"## {heading}")
            out.append("")
            if not items:
                out.append("_None captured._")
                out.append("")
                continue
            for item in items:
                out.append(
                    f"- **{item['id']}** — {item['statement']} "
                    f"_(status: {item['status']}, confidence: {item['confidence']:.0%})_"
                )
            out.append("")

        out.append("## Conversation Branch Summary")
        out.append("")
        for b in package["conversation_branches"]:
            tag = "main" if b["is_main"] else b["topic"] or "branch"
            out.append(f"- **{b['name']}** ({tag}) — {b['status']}, {b['node_count']} nodes")
        out.append("")

        out.append("## Traceability Appendix")
        out.append("")
        for trace in package["traceability"]:
            out.append(f"### {trace['artifact_id']} — {trace['title']}")
            if not trace["evidence"]:
                out.append("_No evidence linked._")
            for ev in trace["evidence"]:
                out.append(
                    f"- {ev['segment_id']} ({ev['relationship']}): "
                    f"\"{ev['quote']}\""
                )
            out.append("")
        return "\n".join(out)


_EXPORTERS = {e.format: e for e in (JsonExporter(), MarkdownExporter())}


def available_formats() -> list[str]:
    return list(_EXPORTERS)


def export_package(db: Session, session_id: str, fmt: str) -> ExportEnvelope:
    if fmt not in _EXPORTERS:
        raise ValidationError(
            f"Unsupported export format '{fmt}'. Available: {available_formats()}"
        )
    exporter = _EXPORTERS[fmt]
    package = build_package(db, session_id)
    body = exporter.export(package)
    ext = "md" if fmt == "markdown" else fmt
    return ExportEnvelope(
        format=fmt,
        filename=f"{session_id}-discovery-package.{ext}",
        content_type=exporter.content_type,
        body=body,
    )
