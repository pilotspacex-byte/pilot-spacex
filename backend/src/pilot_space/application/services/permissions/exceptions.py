"""Domain exceptions for the granular tool permission service."""

from __future__ import annotations

from pilot_space.domain.exceptions import ForbiddenError, ValidationError


class PermissionDeniedError(ForbiddenError):
    """Tool invocation blocked by workspace policy (mode=deny).

    Raised by runtime permission checks — NOT by admin CRUD endpoints.
    Maps to HTTP 403 via the global ``app_error_handler``.
    """

    error_code = "permission_denied_by_policy"


class InvalidPolicyError(ValidationError):
    """Admin attempted an illegal permission change.

    Raised when an admin tries to downgrade a ``CRITICAL_REQUIRE_APPROVAL``
    tool to ``AUTO`` (DD-003 invariant) or sets an unknown tool name.
    Maps to HTTP 422 via the global ``app_error_handler``.
    """

    error_code = "invalid_permission_policy"


__all__ = ["InvalidPolicyError", "PermissionDeniedError"]
