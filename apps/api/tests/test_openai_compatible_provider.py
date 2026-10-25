"""OpenAICompatibleLanguageModelProvider talks plain OpenAI chat-completions
HTTP. These tests stub urllib entirely -- no real network access -- so they
also double as a contract test for whatever backend (OpenAI, Ollama, vLLM,
Anthropic's OpenAI-compatible endpoint, ...) actually implements that wire
format.
"""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO

import pytest

from app.domain.entities import TranscriptSegment
from app.domain.enums import ArtifactType, DerivationMethod, EvidenceRelationship, Speaker
from app.providers.base import AnalysisUnit
from app.providers.openai_compatible import (
    LLMProviderError,
    OpenAICompatibleLanguageModelProvider,
)


def _segment(seg_id: str, speaker: Speaker, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        id=seg_id, session_id="S1", sequence_number=0, speaker=speaker, text=text
    )


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _chat_completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture()
def provider() -> OpenAICompatibleLanguageModelProvider:
    return OpenAICompatibleLanguageModelProvider(
        base_url="http://localhost:11434/v1", api_key="", model="test-model"
    )


def test_analyze_unit_parses_well_formed_response(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "We need it live by end of Q3.")
    unit = AnalysisUnit(segments=[seg])

    captured_request = {}

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        captured_request["body"] = json.loads(request.data)
        captured_request["url"] = request.full_url
        content = json.dumps(
            {
                "artifacts": [
                    {
                        "artifact_type": "constraint",
                        "title": "Q3 deadline",
                        "statement": "The solution shall go live by end of Q3.",
                        "confidence": 0.9,
                        "rationale": "explicit deadline",
                        "evidence": [
                            {
                                "segment_id": "seg-1",
                                "quoted_text": "live by end of Q3",
                                "relationship": "direct",
                                "confidence": 0.9,
                            }
                        ],
                    }
                ]
            }
        )
        return _FakeResponse(_chat_completion(content))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    candidates = provider.analyze_unit(unit)

    assert captured_request["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured_request["body"]["model"] == "test-model"
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.artifact_type is ArtifactType.CONSTRAINT
    assert cand.derivation_method is DerivationMethod.LLM
    assert len(cand.evidence) == 1
    ev = cand.evidence[0]
    assert ev.segment_id == "seg-1"
    assert ev.quoted_text == "live by end of Q3"
    assert seg.text[ev.quote_start : ev.quote_end] == "live by end of Q3"
    assert ev.relationship is EvidenceRelationship.DIRECT


def test_analyze_unit_drops_artifact_with_no_verifiable_evidence(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "We need it live by end of Q3.")
    unit = AnalysisUnit(segments=[seg])

    content = json.dumps(
        {
            "artifacts": [
                {
                    "artifact_type": "constraint",
                    "title": "Hallucinated",
                    "statement": "Something not actually said.",
                    "confidence": 0.9,
                    "evidence": [
                        {
                            "segment_id": "seg-1",
                            "quoted_text": "this text does not appear anywhere",
                        }
                    ],
                }
            ]
        }
    )

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        return _FakeResponse(_chat_completion(content))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert provider.analyze_unit(unit) == []


def test_analyze_unit_recovers_wrong_segment_id_by_scanning_unit(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg1 = _segment("seg-1", Speaker.FACILITATOR, "What's the deadline?")
    seg2 = _segment("seg-2", Speaker.CUSTOMER, "We need it live by end of Q3.")
    unit = AnalysisUnit(segments=[seg1, seg2])

    content = json.dumps(
        {
            "artifacts": [
                {
                    "artifact_type": "constraint",
                    "title": "Q3 deadline",
                    "statement": "The solution shall go live by end of Q3.",
                    "confidence": 0.9,
                    "evidence": [
                        # Model got the id wrong (hallucinated seg-99), but
                        # the quote is real -- should still resolve to seg2.
                        {"segment_id": "seg-99", "quoted_text": "live by end of Q3"}
                    ],
                }
            ]
        }
    )

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        return _FakeResponse(_chat_completion(content))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    candidates = provider.analyze_unit(unit)
    assert len(candidates) == 1
    assert candidates[0].evidence[0].segment_id == "seg-2"


def test_analyze_unit_tolerates_markdown_fenced_json(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "Real-time visibility is required.")
    unit = AnalysisUnit(segments=[seg])

    inner = json.dumps(
        {
            "artifacts": [
                {
                    "artifact_type": "stakeholder_need",
                    "title": "Visibility",
                    "statement": "Stakeholders need real-time visibility.",
                    "confidence": 0.7,
                    "evidence": [{"segment_id": "seg-1", "quoted_text": "Real-time visibility"}],
                }
            ]
        }
    )
    fenced = f"```json\n{inner}\n```"

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        return _FakeResponse(_chat_completion(fenced))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    candidates = provider.analyze_unit(unit)
    assert len(candidates) == 1
    assert candidates[0].title == "Visibility"


def test_analyze_unit_returns_empty_on_unparseable_content(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "Some statement.")
    unit = AnalysisUnit(segments=[seg])

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        return _FakeResponse(_chat_completion("I cannot comply with that request."))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert provider.analyze_unit(unit) == []


def test_analyze_unit_retries_without_response_format_on_400(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "Some statement.")
    unit = AnalysisUnit(segments=[seg])
    calls = []

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        body = json.loads(request.data)
        calls.append(body)
        if "response_format" in body:
            raise urllib.error.HTTPError(
                request.full_url,
                400,
                "Bad Request",
                None,
                BytesIO(b"unknown field response_format"),
            )
        return _FakeResponse(_chat_completion(json.dumps({"artifacts": []})))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert provider.analyze_unit(unit) == []
    assert len(calls) == 2
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


def test_connection_failure_raises_llm_provider_error(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    seg = _segment("seg-1", Speaker.CUSTOMER, "Some statement.")
    unit = AnalysisUnit(segments=[seg])

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(LLMProviderError):
        provider.analyze_unit(unit)


def test_analyze_segment_wraps_single_text_through_analyze_unit(monkeypatch, provider) -> None:  # type: ignore[no-untyped-def]
    content = json.dumps({"artifacts": []})

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        return _FakeResponse(_chat_completion(content))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert provider.analyze_segment("hello", speaker="customer") == []


def test_authorization_header_sent_when_api_key_configured(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    provider = OpenAICompatibleLanguageModelProvider(
        base_url="https://api.openai.com/v1", api_key="sk-test-123", model="gpt-4o-mini"
    )
    seg = _segment("seg-1", Speaker.CUSTOMER, "Some statement.")
    unit = AnalysisUnit(segments=[seg])
    captured = {}

    def fake_urlopen(request, timeout=None):  # type: ignore[no-untyped-def]
        captured["auth"] = request.get_header("Authorization")
        return _FakeResponse(_chat_completion(json.dumps({"artifacts": []})))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    provider.analyze_unit(unit)
    assert captured["auth"] == "Bearer sk-test-123"
