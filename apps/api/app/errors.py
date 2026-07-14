"""Domain-level exceptions, mapped to HTTP status codes in the API layer."""


class DomainError(Exception):
    """Base class for expected, client-facing domain errors."""

    status_code = 400


class NotFoundError(DomainError):
    status_code = 404


class InvalidTransitionError(DomainError):
    status_code = 409


class ValidationError(DomainError):
    status_code = 422
