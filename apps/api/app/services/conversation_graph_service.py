"""Reconstruct the conversation graph (branches + nodes) from data a transcript
already produced, so every ingest path yields the same populated views.

The live path builds the graph incrementally as the facilitator steers; this is
the *post-processing* counterpart — a single batch pass over all segments and
their derived artifacts. Both converge on the same structure the Q&A-flow,
git-branch and subway views expect:

* a **main spine** — the scripted stages when a script is attached, otherwise
  the ordered facilitator-question → customer-answer flow of the whole call;
* **follow-up threads** — one side branch per customer answer that produced
  derived artifacts, carrying the question, the answer, and the requirement /
  finding / risk / decision nodes it yielded, linked back to their
  ``transcript_segment_id`` / ``artifact_id`` so evidence still highlights.

The same pass falls out into a **gap surface**: unanswered questions, answers
that produced nothing, and (with a script) stages no thread reached — the
"ask next time" list.

Idempotency: every branch this builder emits is id-prefixed ``auto:{sid}:`` and
the whole set is dropped and rebuilt on each run, so re-analysis never
duplicates branches or nodes and never clobbers hand-authored or live-steered
branches (which carry their own ids).
"""

from __future__ import annotations

from typing import Any

from ..domain import entities as e
from ..domain.enums import (
    ArtifactType,
    BranchStatus,
    ConversationNodeType,
    Speaker,
    ValidationState,
)
from ..repositories import SessionRepository
from ..repositories.mappers import (
    artifact_to_domain,
    segment_to_domain,
    stage_to_domain,
)
from .branch_service import BranchService
from .errors import NotFoundError

# Artifact type → the node type it surfaces as on a thread. Anything not a
# first-class requirement/risk/decision is generalized to a "finding".
_ARTIFACT_NODE_TYPE: dict[ArtifactType, ConversationNodeType] = {
    ArtifactType.REQUIREMENT: ConversationNodeType.REQUIREMENT,
    ArtifactType.RISK: ConversationNodeType.RISK,
    ArtifactType.DECISION: ConversationNodeType.DECISION,
}

# Artifacts in these validation states are no longer part of the live picture.
_HIDDEN_STATES = frozenset({ValidationState.REJECTED, ValidationState.MERGED})

_ANSWER_SPEAKERS = frozenset({Speaker.CUSTOMER, Speaker.PARTICIPANT})

_MAIN_TOPIC = "main_script"


class ConversationGraphService:
    def __init__(self, repo: SessionRepository, branches: BranchService) -> None:
        self._repo = repo
        self._branches = branches

    # -- public API --------------------------------------------------------
    def build(self, session_id: str) -> dict[str, Any]:
        """(Re)build the conversation graph for a session and return it, with a
        ``gaps`` surface appended. Safe to re-run — idempotent by construction."""

        session = self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")

        segments = [segment_to_domain(r) for r in self._repo.list_segments(session_id)]
        artifacts = [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]
        stages: list[e.ScriptStage] = []
        if session.script_id:
            script = self._repo.get_script(session.script_id)
            if script is not None:
                stages = [stage_to_domain(s) for s in script.stages]

        # segment_id → artifacts derived from it (each artifact attached once, to
        # the first *answer* segment among its evidence, else its first segment).
        arts_by_segment = self._artifacts_by_segment(session_id, segments, artifacts)

        # Drop any previously auto-built graph before rebuilding (idempotency).
        self._clear_generated(session_id)

        ids = _IdFactory(session_id)
        self._build_main(session_id, ids, stages, segments)
        used_stage_ids = self._build_threads(session_id, ids, stages, segments, arts_by_segment)

        graph = self._branches.graph(session_id)
        graph["gaps"] = self._gaps(segments, arts_by_segment, stages, used_stage_ids)
        return graph

    # -- main spine --------------------------------------------------------
    def _build_main(
        self,
        session_id: str,
        ids: _IdFactory,
        stages: list[e.ScriptStage],
        segments: list[e.TranscriptSegment],
    ) -> None:
        main = self._branches.create_branch(
            session_id,
            name="Main discovery script",
            topic=_MAIN_TOPIC,
            status=BranchStatus.ACTIVE,
            branch_id=ids.main_branch(),
        )
        if stages:
            # Scripted spine: one stage node per stage (mirrors the seed shape).
            for i, stage in enumerate(stages):
                self._branches.add_node(
                    main.id,
                    node_type=ConversationNodeType.SCRIPT_STAGE,
                    label=stage.title,
                    sequence=i,
                    node_id=ids.node(),
                )
            return
        # No script: reconstruct the Q&A spine from the raw turns so the flow
        # view has a conversation to render.
        seq = 0
        pending_q: e.TranscriptSegment | None = None
        for seg in segments:
            if seg.speaker is Speaker.FACILITATOR:
                pending_q = seg
            elif seg.speaker in _ANSWER_SPEAKERS:
                if pending_q is not None:
                    self._branches.add_node(
                        main.id,
                        node_type=ConversationNodeType.QUESTION,
                        label=_summarize(pending_q.text),
                        transcript_segment_id=pending_q.id,
                        sequence=seq,
                        node_id=ids.node(),
                    )
                    seq += 1
                    pending_q = None
                self._branches.add_node(
                    main.id,
                    node_type=ConversationNodeType.ANSWER,
                    label=_summarize(seg.text),
                    transcript_segment_id=seg.id,
                    sequence=seq,
                    node_id=ids.node(),
                )
                seq += 1

    # -- follow-up threads -------------------------------------------------
    def _build_threads(
        self,
        session_id: str,
        ids: _IdFactory,
        stages: list[e.ScriptStage],
        segments: list[e.TranscriptSegment],
        arts_by_segment: dict[str, list[e.DiscoveryArtifact]],
    ) -> set[str]:
        """One branch per customer answer that produced artifacts. Returns the
        set of script-stage ids a thread was attached to (for gap detection)."""

        by_id = {seg.id: seg for seg in segments}
        preceding_q = self._preceding_questions(segments)
        answer_positions = self._answer_positions(segments)
        used_stage_ids: set[str] = set()
        thread_no = 0

        for seg in segments:
            arts = arts_by_segment.get(seg.id)
            if not arts or seg.speaker not in _ANSWER_SPEAKERS:
                continue
            thread_no += 1

            source_stage_id: str | None = None
            merge_target_stage_id: str | None = None
            if stages:
                idx = self._stage_for_answer(seg, answer_positions, len(stages))
                source_stage_id = stages[idx].id
                used_stage_ids.add(source_stage_id)
                if idx + 1 < len(stages):
                    merge_target_stage_id = stages[idx + 1].id

            branch = self._branches.create_branch(
                session_id,
                name=_thread_name(arts),
                topic=_thread_topic(arts, thread_no),
                source_stage_id=source_stage_id,
                created_from_segment_id=seg.id,
                merge_target_stage_id=merge_target_stage_id,
                status=BranchStatus.MERGED if merge_target_stage_id else BranchStatus.OPEN,
                branch_id=ids.thread_branch(thread_no),
            )

            seq = 0
            q_seg = preceding_q.get(seg.id)
            if q_seg is not None:
                self._branches.add_node(
                    branch.id,
                    node_type=ConversationNodeType.QUESTION,
                    label=_summarize(by_id[q_seg].text),
                    transcript_segment_id=q_seg,
                    sequence=seq,
                    node_id=ids.node(),
                )
                seq += 1
            self._branches.add_node(
                branch.id,
                node_type=ConversationNodeType.ANSWER,
                label=_summarize(seg.text),
                transcript_segment_id=seg.id,
                sequence=seq,
                node_id=ids.node(),
            )
            seq += 1
            for art in arts:
                self._branches.add_node(
                    branch.id,
                    node_type=_ARTIFACT_NODE_TYPE.get(
                        art.artifact_type, ConversationNodeType.FINDING
                    ),
                    label=art.title,
                    transcript_segment_id=seg.id,
                    artifact_id=art.id,
                    sequence=seq,
                    node_id=ids.node(),
                )
                seq += 1

        return used_stage_ids

    # -- helpers -----------------------------------------------------------
    def _artifacts_by_segment(
        self,
        session_id: str,
        segments: list[e.TranscriptSegment],
        artifacts: list[e.DiscoveryArtifact],
    ) -> dict[str, list[e.DiscoveryArtifact]]:
        speaker_of = {seg.id: seg.speaker for seg in segments}
        order = {seg.id: i for i, seg in enumerate(segments)}
        art_by_id = {a.id: a for a in artifacts if a.validation_state not in _HIDDEN_STATES}

        # Gather every evidence segment per artifact, in transcript order.
        ev_segments: dict[str, list[str]] = {}
        for link in self._repo.list_evidence(session_id):
            if link.artifact_id not in art_by_id:
                continue
            ev_segments.setdefault(link.artifact_id, []).append(link.transcript_segment_id)

        out: dict[str, list[e.DiscoveryArtifact]] = {}
        for art_id, seg_ids in ev_segments.items():
            seg_ids = sorted(set(seg_ids), key=lambda sid: order.get(sid, 1 << 30))
            # Prefer the first answer segment (handles cross-turn: a requirement
            # inferred from a question + a later answer hangs off the answer).
            anchor = next(
                (sid for sid in seg_ids if speaker_of.get(sid) in _ANSWER_SPEAKERS),
                seg_ids[0] if seg_ids else None,
            )
            if anchor is not None:
                out.setdefault(anchor, []).append(art_by_id[art_id])
        # Keep each anchor's artifacts in creation order for stable output.
        for anchor in out:
            out[anchor].sort(key=lambda a: a.created_at)
        return out

    @staticmethod
    def _preceding_questions(
        segments: list[e.TranscriptSegment],
    ) -> dict[str, str]:
        """Map each answer segment id → the facilitator segment id just before
        it (the question that prompted it), if any."""

        out: dict[str, str] = {}
        last_q: str | None = None
        for seg in segments:
            if seg.speaker is Speaker.FACILITATOR:
                last_q = seg.id
            elif seg.speaker in _ANSWER_SPEAKERS and last_q is not None:
                out[seg.id] = last_q
        return out

    @staticmethod
    def _answer_positions(segments: list[e.TranscriptSegment]) -> dict[str, int]:
        """Map each answer segment id → its 0-based position among all answers."""

        out: dict[str, int] = {}
        n = 0
        for seg in segments:
            if seg.speaker in _ANSWER_SPEAKERS:
                out[seg.id] = n
                n += 1
        return out

    @staticmethod
    def _stage_for_answer(
        seg: e.TranscriptSegment, answer_positions: dict[str, int], n_stages: int
    ) -> int:
        """Spread threads across the scripted stages by the answer's position in
        the conversation, so follow-ups land under plausible stages in order."""

        total = max(1, len(answer_positions))
        pos = answer_positions.get(seg.id, 0)
        return min(n_stages - 1, (pos * n_stages) // total)

    @staticmethod
    def _gaps(
        segments: list[e.TranscriptSegment],
        arts_by_segment: dict[str, list[e.DiscoveryArtifact]],
        stages: list[e.ScriptStage],
        used_stage_ids: set[str],
    ) -> list[dict[str, str]]:
        gaps: list[dict[str, str]] = []

        # Questions the facilitator asked that nobody answered.
        pending_q: e.TranscriptSegment | None = None
        for seg in segments:
            if seg.speaker is Speaker.FACILITATOR:
                if pending_q is not None:
                    gaps.append(
                        {
                            "kind": "unanswered_question",
                            "label": _summarize(pending_q.text),
                            "detail": "Asked but no answer was captured before the next question.",
                        }
                    )
                pending_q = seg
            elif seg.speaker in _ANSWER_SPEAKERS:
                pending_q = None
        if pending_q is not None:
            gaps.append(
                {
                    "kind": "unanswered_question",
                    "label": _summarize(pending_q.text),
                    "detail": "Asked but no answer was captured before the call ended.",
                }
            )

        # Answers that yielded no derived artifact.
        for seg in segments:
            if seg.speaker in _ANSWER_SPEAKERS and not arts_by_segment.get(seg.id):
                gaps.append(
                    {
                        "kind": "answer_without_artifact",
                        "label": _summarize(seg.text),
                        "detail": "Answer produced no requirement/finding — clarify next time.",
                    }
                )

        # Scripted stages no follow-up thread reached.
        for stage in stages:
            if stage.id not in used_stage_ids:
                gaps.append(
                    {
                        "kind": "uncovered_stage",
                        "label": stage.title,
                        "detail": "No answer-derived artifact mapped to this stage yet.",
                    }
                )

        return gaps[:20]

    def _clear_generated(self, session_id: str) -> None:
        prefix = _IdFactory(session_id).prefix
        for branch in self._repo.list_branches(session_id):
            if branch.id.startswith(prefix):
                self._repo.delete_branch(branch.id)
        self._repo.commit()


class _IdFactory:
    """Deterministic, session-scoped ids so a rebuild produces the same graph
    and the generated set is recognizable (and removable) by prefix."""

    def __init__(self, session_id: str) -> None:
        self.prefix = f"auto:{session_id}:"
        self._n = 0

    def main_branch(self) -> str:
        return f"{self.prefix}branch:main"

    def thread_branch(self, n: int) -> str:
        return f"{self.prefix}branch:thread:{n}"

    def node(self) -> str:
        self._n += 1
        return f"{self.prefix}node:{self._n}"


def _summarize(text: str, max_len: int = 80) -> str:
    """A short label for a turn: its first sentence, trimmed."""

    text = " ".join(text.split())
    for stop in (". ", "? ", "! "):
        idx = text.find(stop)
        if 0 < idx < max_len:
            return text[: idx + 1].strip()
    return text if len(text) <= max_len else f"{text[: max_len - 1].rstrip()}…"


def _thread_name(arts: list[e.DiscoveryArtifact]) -> str:
    return arts[0].title if arts else "Follow-up"


def _thread_topic(arts: list[e.DiscoveryArtifact], thread_no: int) -> str:
    """A stable, human-ish topic slug for the branch (never ``main_script``)."""

    kind = arts[0].artifact_type.value if arts else "thread"
    return f"{kind}_{thread_no}"
