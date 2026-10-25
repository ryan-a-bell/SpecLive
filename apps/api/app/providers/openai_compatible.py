"""LLM-backed requirement derivation against any OpenAI-API-compliant server.

This adapter speaks the plain OpenAI chat-completions wire format
(``POST {base}/chat/completions`` with a bearer token and a ``messages``
array) and nothing vendor-specific beyond that, so pointing it at a
different backend is purely a config change (``LLM_API_BASE`` /
``LLM_API_KEY`` / ``LLM_MODEL``) — no code change, no new adapter class:

* OpenAI itself:            https://api.openai.com/v1
* A local Ollama server:    http://localhost:11434/v1   (`ollama serve`)
* A vLLM OpenAI server:     http://localhost:8000/v1    (`vllm serve ... `)
* Anthropic's OpenAI-compatible endpoint: https://api.anthropic.com/v1

Only stdlib is used (``urllib``) to keep this dependency-free, matching the
rest of the provider layer (see ``openai_realtime.py``).

Unlike ``MockLanguageModelProvider`` — which only ever sees one segment and
therefore only ever looks at customer/participant turns — this provider
overrides ``analyze_unit`` directly so it can reason over every segment in
an ``AnalysisUnit`` at once, facilitator paraphrases included. A
facilitator's "so a hard requirement is X" is often the clearest signal in
the whole transcript; a provider limited to one segment at a time can never
use it, but one with real context can.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ..domain.entities import TranscriptSegment
from ..domain.enums import ArtifactType, DerivationMethod, EvidenceRelationship, Speaker
from ..logging import get_logger
from .base import AnalysisUnit, ArtifactCandidate, EvidenceCandidate, LanguageModelProvider

logger = get_logger(__name__)

_ARTIFACT_TYPES = ", ".join(t.value for t in ArtifactType)
_RELATIONSHIPS = ", ".join(r.value for r in EvidenceRelationship)

_SYSTEM_PROMPT = f"""You are a requirements analyst reviewing a discovery-call \
transcript. Extract candidate discovery artifacts: objectives, stakeholder \
needs, requirements, constraints, assumptions, risks, decisions, open \
questions, success metrics, and integrations.

Valid "artifact_type" values: {_ARTIFACT_TYPES}
Valid evidence "relationship" values: {_RELATIONSHIPS}

Rules:
- Use ALL speakers, not just the customer. A facilitator's paraphrase or \
recap ("so a hard requirement is X") is often the clearest statement of a \
requirement in the whole transcript — use it.
- Every artifact needs at least one evidence item. Each evidence item must \
quote a short, EXACT, verbatim substring of one segment's text (copy it \
character-for-character, do not paraphrase or reformat it) and name the \
"segment_id" it came from, copied exactly from the transcript below.
- Do not invent facts that are not in the transcript. Prefer fewer, \
well-evidenced artifacts over many speculative ones.
- confidence is a float from 0 to 1 reflecting how explicit/certain the \
statement was.
- Respond with a single JSON object of the exact shape \
{{"artifacts": [{{"artifact_type": "...", "title": "...", "statement": "...", \
"confidence": 0.0, "rationale": "...", "evidence": [{{"segment_id": "...", \
"quoted_text": "...", "relationship": "...", "confidence": 0.0, \
"rationale": "..."}}]}}]}}. No prose, no markdown fences, JSON only."""

_RECOMMEND_SYSTEM_PROMPT = (
    "You are a requirements analyst. Given a discovery session's context and a "
    "list of known coverage gaps, propose the single most valuable next "
    'questions to ask. Respond with a JSON object {"questions": ["...", ...]}. '
    "JSON only, no prose."
)


class LLMProviderError(RuntimeError):
    """The configured OpenAI-compatible endpoint could not be reached or
    returned something other than a valid chat-completion response. Distinct
    from a malformed *content* payload (bad JSON from the model itself),
    which is handled per-call without raising — see ``_parse_artifacts``.
    """


@dataclass
class _ChatConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0
    extra_headers: dict[str, str] = field(default_factory=dict)


class OpenAICompatibleLanguageModelProvider(LanguageModelProvider):
    """Derives artifacts by calling an OpenAI-API-compliant chat-completions
    endpoint. Works against OpenAI, Ollama, vLLM, Anthropic's
    OpenAI-compatible endpoint, or any other server implementing the same
    contract — see the module docstring.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._cfg = _ChatConfig(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            timeout=timeout,
            extra_headers=extra_headers or {},
        )

    # --- LanguageModelProvider ------------------------------------------
    def analyze_segment(self, text: str, *, speaker: str) -> list[ArtifactCandidate]:
        """Single-segment convenience path (required by the ABC). Wraps the
        text in a synthetic one-segment unit and delegates to
        ``analyze_unit`` so single-segment and multi-segment calls share one
        code path.
        """

        try:
            speaker_role = Speaker(speaker)
        except ValueError:
            speaker_role = Speaker.UNKNOWN
        segment = TranscriptSegment(
            session_id="adhoc",
            sequence_number=0,
            speaker=speaker_role,
            text=text,
        )
        return self.analyze_unit(AnalysisUnit(segments=[segment]))

    def analyze_unit(self, unit: AnalysisUnit) -> list[ArtifactCandidate]:
        if not unit.segments:
            return []
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _render_transcript(unit)},
        ]
        content = self._chat(messages)  # raises LLMProviderError on transport/auth failure
        return self._parse_artifacts(content, unit)

    def recommend_questions(self, context: str, *, gaps: list[str]) -> list[str]:
        messages = [
            {"role": "system", "content": _RECOMMEND_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\nKnown gaps:\n"
                    + "\n".join(f"- {g}" for g in gaps)
                ),
            },
        ]
        try:
            content = self._chat(messages)
        except LLMProviderError:
            logger.warning("llm.recommend_questions_failed", exc_info=True)
            return []
        try:
            payload = _extract_json_object(content)
            questions = payload.get("questions", [])
            return [str(q) for q in questions if str(q).strip()]
        except (json.JSONDecodeError, AttributeError, TypeError):
            logger.warning("llm.recommend_questions_unparseable", content=content[:200])
            return []

    # --- HTTP -------------------------------------------------------------
    def _chat(self, messages: list[dict[str, str]]) -> str:
        try:
            payload = self._post_chat(messages, want_json_mode=True)
        except LLMProviderError as exc:
            # Some OpenAI-compatible servers (older vLLM/Ollama builds) reject
            # an unrecognized response_format field outright instead of
            # ignoring it. Retry once without it before giving up.
            if "HTTP 400" in str(exc) or "HTTP 422" in str(exc):
                payload = self._post_chat(messages, want_json_mode=False)
            else:
                raise

        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                f"unexpected chat-completions response shape from {self._cfg.base_url}: "
                f"{json.dumps(payload)[:500]}"
            ) from exc

    def _post_chat(self, messages: list[dict[str, str]], *, want_json_mode: bool) -> dict:
        body_dict: dict[str, object] = {
            "model": self._cfg.model,
            "messages": messages,
            "temperature": 0.0,
        }
        if want_json_mode:
            body_dict["response_format"] = {"type": "json_object"}
        body = json.dumps(body_dict).encode("utf-8")
        headers = {"Content-Type": "application/json", **self._cfg.extra_headers}
        if self._cfg.api_key:
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"
        request = urllib.request.Request(
            f"{self._cfg.base_url}/chat/completions",
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._cfg.timeout) as resp:
                return dict(json.loads(resp.read()))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise LLMProviderError(
                f"{self._cfg.base_url} returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(f"could not reach {self._cfg.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMProviderError(
                f"{self._cfg.base_url} timed out after {self._cfg.timeout}s"
            ) from exc

    # --- response parsing ---------------------------------------------
    def _parse_artifacts(self, content: str, unit: AnalysisUnit) -> list[ArtifactCandidate]:
        try:
            payload = _extract_json_object(content)
        except json.JSONDecodeError:
            logger.warning("llm.analysis_unparseable", content=content[:500])
            return []

        raw_artifacts = payload.get("artifacts", [])
        if not isinstance(raw_artifacts, list):
            logger.warning("llm.analysis_bad_shape", content=content[:500])
            return []

        segments_by_id = {s.id: s for s in unit.segments}
        produced: list[ArtifactCandidate] = []
        for raw in raw_artifacts:
            candidate = self._parse_one_artifact(raw, segments_by_id)
            if candidate is not None:
                produced.append(candidate)
        return produced

    def _parse_one_artifact(
        self, raw: object, segments_by_id: dict[str, TranscriptSegment]
    ) -> ArtifactCandidate | None:
        if not isinstance(raw, dict):
            return None
        try:
            artifact_type = ArtifactType(str(raw["artifact_type"]).strip().lower())
        except (KeyError, ValueError):
            logger.warning("llm.unknown_artifact_type", raw_type=raw.get("artifact_type"))
            return None
        title = str(raw.get("title", "")).strip()
        statement = str(raw.get("statement", "")).strip()
        if not title or not statement:
            return None

        evidence: list[EvidenceCandidate] = []
        for raw_ev in raw.get("evidence", []) or []:
            ev = self._parse_one_evidence(raw_ev, segments_by_id)
            if ev is not None:
                evidence.append(ev)
        if not evidence:
            # Evidence-first traceability (ADR-0006): don't persist an
            # ungrounded claim just because the model asserted one.
            logger.warning("llm.artifact_dropped_no_evidence", title=title)
            return None

        confidence = _clamp01(raw.get("confidence", 0.5))
        rationale = str(raw.get("rationale") or "Derived by LLM analysis.").strip()
        return ArtifactCandidate(
            artifact_type=artifact_type,
            title=title,
            statement=statement,
            confidence=confidence,
            rationale=rationale,
            evidence=evidence,
            derivation_method=DerivationMethod.LLM,
        )

    def _parse_one_evidence(
        self, raw: object, segments_by_id: dict[str, TranscriptSegment]
    ) -> EvidenceCandidate | None:
        if not isinstance(raw, dict):
            return None
        quoted_text = str(raw.get("quoted_text", "")).strip()
        if not quoted_text:
            return None

        segment_id = str(raw.get("segment_id", "")).strip()
        segment = segments_by_id.get(segment_id)
        if segment is None:
            # The model may have gotten the id wrong; fall back to searching
            # every segment in the unit for the quote before giving up.
            segment = next(
                (s for s in segments_by_id.values() if quoted_text in s.text), None
            )
        if segment is None:
            logger.warning("llm.evidence_dropped_unverifiable", quoted_text=quoted_text[:120])
            return None

        start = segment.text.find(quoted_text)
        if start == -1:
            start = segment.text.lower().find(quoted_text.lower())
        if start == -1:
            logger.warning("llm.evidence_dropped_not_verbatim", quoted_text=quoted_text[:120])
            return None

        try:
            relationship = EvidenceRelationship(str(raw.get("relationship", "supporting")).lower())
        except ValueError:
            relationship = EvidenceRelationship.SUPPORTING

        return EvidenceCandidate(
            quote_start=start,
            quote_end=start + len(quoted_text),
            quoted_text=segment.text[start : start + len(quoted_text)],
            relationship=relationship,
            confidence=_clamp01(raw.get("confidence", 0.5)),
            rationale=str(raw.get("rationale") or "").strip() or None,
            segment_id=segment.id,
        )


def _render_transcript(unit: AnalysisUnit) -> str:
    lines = ["Transcript segments (cite the bracketed id exactly as \"segment_id\"):", ""]
    for segment in unit.segments:
        speaker = segment.speaker_name or segment.speaker
        lines.append(f"[{segment.id}] {speaker} ({segment.speaker}): {segment.text}")
    return "\n".join(lines)


def _extract_json_object(content: str) -> dict:
    """Parse a chat-completion's text content as a JSON object, tolerating
    markdown code fences and incidental prose some servers/models add
    despite being asked for JSON-only output.
    """

    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _clamp01(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.5


__all__ = ["OpenAICompatibleLanguageModelProvider", "LLMProviderError"]
