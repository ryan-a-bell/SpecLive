"""Structured logging setup using structlog.

Credential-shaped keys are redacted before rendering so provider secrets never
reach the logs (see SECURITY.md).
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from structlog.types import EventDict

_REDACT_KEYS = {"api_key", "authorization", "password", "secret", "token"}


def _redact_secrets(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    for key in list(event_dict.keys()):
        if key.lower() in _REDACT_KEYS:
            event_dict[key] = "***redacted***"
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure standard library + structlog once at startup."""

    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_secrets,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
