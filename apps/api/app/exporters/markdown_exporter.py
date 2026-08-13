"""Markdown discovery-package exporter."""

from __future__ import annotations

from ..providers.base import ArtifactExporter


class MarkdownExporter(ArtifactExporter):
    format_id = "markdown"
    media_type = "text/markdown"

    def export(self, package: dict) -> str:
        s = package["session"]
        lines: list[str] = []
        add = lines.append

        add(f"# Discovery Package — {s['title']}")
        add("")
        add(f"- **Customer:** {s['customer']}")
        add(f"- **Facilitator:** {s['facilitator']}")
        add(f"- **Status:** {s['status']}")
        add(f"- **Generated:** {package['generated_at']}")
        add("")

        add("## Executive summary")
        add("")
        add(package["executive_summary"])
        add("")

        self._section(add, "Customer objectives", package["objectives"])
        self._section(add, "Stakeholder needs", package["stakeholder_needs"])
        self._section(add, "Confirmed requirements", package["confirmed_requirements"])
        self._section(add, "Candidate requirements", package["candidate_requirements"])
        self._section(add, "Constraints", package["constraints"])
        self._section(add, "Assumptions", package["assumptions"])
        self._section(add, "Risks", package["risks"])
        self._section(add, "Decisions", package["decisions"])
        self._section(add, "Open questions", package["open_questions"])
        self._section(add, "Success metrics", package["success_metrics"])

        add("## Conversation branch summary")
        add("")
        if package["branch_summary"]:
            for b in package["branch_summary"]:
                add(
                    f"- **{b['name']}** ({b['topic']}) — status: {b['status']}, "
                    f"nodes: {b['node_count']}"
                )
        else:
            add("_No branches recorded._")
        add("")

        add("## Traceability appendix")
        add("")
        add("| Artifact | Type | State | Confidence | Evidence (segment → quote) |")
        add("|----------|------|-------|-----------|----------------------------|")
        for t in package["traceability"]:
            ev = (
                "; ".join(
                    f"{e['segment_id'][:8]}… “{e['quoted_text']}” ({e['relationship']})"
                    for e in t["evidence"]
                )
                or "_none_"
            )
            add(
                f"| {t['title']} | {t['type']} | {t['validation_state']} "
                f"| {t['confidence']:.0%} | {ev} |"
            )
        add("")
        return "\n".join(lines)

    @staticmethod
    def _section(add, heading: str, items: list[dict]) -> None:  # type: ignore[no-untyped-def]
        add(f"## {heading}")
        add("")
        if not items:
            add("_None recorded._")
            add("")
            return
        for it in items:
            conf = it.get("confidence")
            suffix = f" _(confidence {conf:.0%})_" if isinstance(conf, (int, float)) else ""
            add(f"- **{it['title']}** — {it['statement']}{suffix}")
        add("")
