"""Artifact lifecycle transition rules.

The lifecycle is the guardrail behind the product's central promise: a
model-inferred requirement is never treated as customer-confirmed without an
explicit human action. Automated derivation may only ever *propose* an artifact
in `detected` or `inferred`; reaching `customer_confirmed`/`baselined` requires
a human-initiated transition (optionally justified by confirmation evidence).
"""

from __future__ import annotations

from .enums import HUMAN_CONFIRMED_STATES, ArtifactStatus, ValidationState

# Allowed transitions between validation states.
_ALLOWED: dict[ValidationState, frozenset[ValidationState]] = {
    ValidationState.DETECTED: frozenset(
        {
            ValidationState.INFERRED,
            ValidationState.CLARIFIED,
            ValidationState.CUSTOMER_CONFIRMED,
            ValidationState.REJECTED,
            ValidationState.SUPERSEDED,
            ValidationState.MERGED,
        }
    ),
    ValidationState.INFERRED: frozenset(
        {
            ValidationState.CLARIFIED,
            ValidationState.CUSTOMER_CONFIRMED,
            ValidationState.REJECTED,
            ValidationState.SUPERSEDED,
            ValidationState.MERGED,
        }
    ),
    ValidationState.CLARIFIED: frozenset(
        {
            ValidationState.CUSTOMER_CONFIRMED,
            ValidationState.REJECTED,
            ValidationState.SUPERSEDED,
            ValidationState.MERGED,
        }
    ),
    ValidationState.CUSTOMER_CONFIRMED: frozenset(
        {
            ValidationState.BASELINED,
            ValidationState.SUPERSEDED,
            ValidationState.REJECTED,
        }
    ),
    ValidationState.BASELINED: frozenset({ValidationState.SUPERSEDED}),
    # Terminal states.
    ValidationState.REJECTED: frozenset(),
    ValidationState.SUPERSEDED: frozenset(),
    ValidationState.MERGED: frozenset(),
}

# Transitions an automated (non-human) actor may perform.
_AUTOMATED_ALLOWED: frozenset[ValidationState] = frozenset(
    {ValidationState.DETECTED, ValidationState.INFERRED}
)


class InvalidTransition(ValueError):
    """Raised when a lifecycle transition is not permitted."""


def can_transition(current: ValidationState, target: ValidationState) -> bool:
    return target in _ALLOWED.get(current, frozenset())


def assert_transition(
    current: ValidationState, target: ValidationState, *, actor_is_human: bool
) -> None:
    """Validate a transition, enforcing the human-confirmation guardrail."""

    if current == target:
        return
    if not can_transition(current, target):
        raise InvalidTransition(
            f"Cannot transition artifact from {current.value} to {target.value}"
        )
    if target in HUMAN_CONFIRMED_STATES and not actor_is_human:
        raise InvalidTransition(
            f"Transition to {target.value} requires an explicit human action; "
            "automated derivation may not confirm or baseline an artifact."
        )
    if not actor_is_human and target not in _AUTOMATED_ALLOWED:
        raise InvalidTransition(
            f"Automated actors may only set state to {sorted(s.value for s in _AUTOMATED_ALLOWED)}"
        )


def status_for(state: ValidationState) -> ArtifactStatus:
    """Roll a fine-grained validation state up to the UI-facing status."""

    return {
        ValidationState.DETECTED: ArtifactStatus.CANDIDATE,
        ValidationState.INFERRED: ArtifactStatus.CANDIDATE,
        ValidationState.CLARIFIED: ArtifactStatus.CANDIDATE,
        ValidationState.CUSTOMER_CONFIRMED: ArtifactStatus.CONFIRMED,
        ValidationState.BASELINED: ArtifactStatus.BASELINED,
        ValidationState.REJECTED: ArtifactStatus.REJECTED,
        ValidationState.SUPERSEDED: ArtifactStatus.SUPERSEDED,
        ValidationState.MERGED: ArtifactStatus.SUPERSEDED,
    }[state]
