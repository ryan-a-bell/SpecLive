"""Deployment-level metadata endpoints (read-only).

Surfaces non-secret runtime configuration so the UI can show *what this
deployment is running* without exposing credentials. Config is env-var
driven and immutable at runtime (see ``app/config.py``), so these are GET
only — there is intentionally no write counterpart.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...config import Settings, get_settings
from ...storage import layout
from ..schemas import AnalysisSettingsInfo, StorageSettingsInfo

router = APIRouter(tags=["meta"])


def _analysis_settings(settings: Settings) -> AnalysisSettingsInfo:
    is_openai_compatible = settings.llm_provider == "openai_compatible"
    return AnalysisSettingsInfo(
        context_mode=settings.analysis_context_mode,
        window_seconds=settings.analysis_window_seconds,
        auto_analyze=settings.auto_analyze,
        llm_provider=settings.llm_provider,
        # Non-secret provider config, and only when it's actually in use. The
        # API key is deliberately never surfaced.
        llm_api_base=settings.llm_api_base if is_openai_compatible else None,
        llm_model=settings.llm_model if is_openai_compatible else None,
    )


@router.get("/settings/analysis", response_model=AnalysisSettingsInfo)
def analysis_settings() -> AnalysisSettingsInfo:
    """Report the active requirement-derivation configuration (no secrets)."""

    return _analysis_settings(get_settings())


def _storage_settings(settings: Settings) -> StorageSettingsInfo:
    is_local = (settings.storage_backend or "local").strip().lower() == "local"
    return StorageSettingsInfo(
        backend=settings.storage_backend,
        persist_audio=settings.storage_persist_audio,
        schema_version=layout.SCHEMA_VERSION,
        local_root=settings.storage_local_root if is_local else None,
    )


@router.get("/settings/storage", response_model=StorageSettingsInfo)
def storage_settings() -> StorageSettingsInfo:
    """Report where conversation content is persisted (no secrets)."""

    return _storage_settings(get_settings())
