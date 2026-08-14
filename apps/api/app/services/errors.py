"""Service-layer exceptions (transport-agnostic)."""

from __future__ import annotations


class NotFoundError(Exception):
    """A referenced entity does not exist."""


class ValidationError(Exception):
    """A request violates a domain invariant."""
