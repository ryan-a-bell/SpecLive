"""Artifact lifecycle transition rules — the human-confirmation guardrail."""

from __future__ import annotations

import pytest

from app.domain.enums import ArtifactStatus, ValidationState
from app.domain.lifecycle import (
    InvalidTransition,
    assert_transition,
    can_transition,
    status_for,
)


def test_forward_progression_is_allowed() -> None:
    assert can_transition(ValidationState.DETECTED, ValidationState.INFERRED)
    assert can_transition(ValidationState.INFERRED, ValidationState.CLARIFIED)
    assert can_transition(ValidationState.CLARIFIED, ValidationState.CUSTOMER_CONFIRMED)
    assert can_transition(ValidationState.CUSTOMER_CONFIRMED, ValidationState.BASELINED)


def test_cannot_skip_backwards() -> None:
    assert not can_transition(ValidationState.BASELINED, ValidationState.DETECTED)
    assert not can_transition(ValidationState.REJECTED, ValidationState.INFERRED)


def test_automated_actor_cannot_confirm() -> None:
    with pytest.raises(InvalidTransition):
        assert_transition(
            ValidationState.INFERRED,
            ValidationState.CUSTOMER_CONFIRMED,
            actor_is_human=False,
        )


def test_automated_actor_cannot_baseline() -> None:
    with pytest.raises(InvalidTransition):
        assert_transition(
            ValidationState.CUSTOMER_CONFIRMED,
            ValidationState.BASELINED,
            actor_is_human=False,
        )


def test_human_confirmation_is_allowed() -> None:
    # Does not raise.
    assert_transition(
        ValidationState.CLARIFIED,
        ValidationState.CUSTOMER_CONFIRMED,
        actor_is_human=True,
    )


def test_automated_actor_limited_to_detected_inferred() -> None:
    assert_transition(ValidationState.DETECTED, ValidationState.INFERRED, actor_is_human=False)
    with pytest.raises(InvalidTransition):
        assert_transition(ValidationState.INFERRED, ValidationState.CLARIFIED, actor_is_human=False)


def test_status_rollup() -> None:
    assert status_for(ValidationState.INFERRED) is ArtifactStatus.CANDIDATE
    assert status_for(ValidationState.CUSTOMER_CONFIRMED) is ArtifactStatus.CONFIRMED
    assert status_for(ValidationState.BASELINED) is ArtifactStatus.BASELINED
    assert status_for(ValidationState.REJECTED) is ArtifactStatus.REJECTED
