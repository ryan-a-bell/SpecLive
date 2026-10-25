"""GET /api/v1/settings/analysis reports active derivation config and, above
all, never leaks the LLM API key.
"""

from __future__ import annotations

import importlib
import json

import pytest


@pytest.fixture(autouse=True)
def _restore_settings_cache():  # type: ignore[no-untyped-def]
    """These tests rebuild Settings from mutated env and clear the lru_cache;
    restore it afterward so a stale, test-specific Settings never leaks into
    other tests that rely on the defaults."""

    from app import config as config_module

    yield
    config_module.get_settings.cache_clear()


def _client_with_env(monkeypatch, **env):  # type: ignore[no-untyped-def]
    """Build a TestClient whose app reads a fresh Settings from the given env.

    Settings is lru_cached, so we set env, clear the cache, and rebuild the
    app so the meta router sees the overridden configuration.
    """

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from fastapi.testclient import TestClient

    main_module = importlib.import_module("app.main")
    app = main_module.create_app()
    return TestClient(app)


def test_analysis_settings_reports_active_config(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client_with_env(
        monkeypatch,
        ANALYSIS_CONTEXT_MODE="window",
        ANALYSIS_WINDOW_SECONDS="120",
        LLM_PROVIDER="openai_compatible",
        LLM_API_BASE="http://localhost:11434/v1",
        LLM_MODEL="llama3.1",
        LLM_API_KEY="sk-super-secret-should-never-appear",
        AUTO_ANALYZE="true",
    )
    resp = client.get("/api/v1/settings/analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["context_mode"] == "window"
    assert body["window_seconds"] == 120
    assert body["auto_analyze"] is True
    assert body["llm_provider"] == "openai_compatible"
    assert body["llm_api_base"] == "http://localhost:11434/v1"
    assert body["llm_model"] == "llama3.1"


def test_analysis_settings_never_leaks_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client_with_env(
        monkeypatch,
        LLM_PROVIDER="openai_compatible",
        LLM_API_BASE="https://api.openai.com/v1",
        LLM_MODEL="gpt-4o-mini",
        LLM_API_KEY="sk-super-secret-should-never-appear",
    )
    resp = client.get("/api/v1/settings/analysis")
    assert resp.status_code == 200
    # The secret must not appear anywhere in the serialized response, and the
    # response must have no key-like field at all.
    raw = json.dumps(resp.json())
    assert "sk-super-secret-should-never-appear" not in raw
    assert "api_key" not in resp.json()
    assert "llm_api_key" not in resp.json()


def test_analysis_settings_hides_provider_url_when_mock(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """With the mock provider, the openai_compatible base/model are irrelevant
    and should come back null rather than echoing stale defaults."""

    client = _client_with_env(
        monkeypatch,
        LLM_PROVIDER="mock",
        LLM_API_BASE="https://api.openai.com/v1",
        LLM_MODEL="gpt-4o-mini",
    )
    resp = client.get("/api/v1/settings/analysis")
    body = resp.json()
    assert body["llm_provider"] == "mock"
    assert body["llm_api_base"] is None
    assert body["llm_model"] is None
