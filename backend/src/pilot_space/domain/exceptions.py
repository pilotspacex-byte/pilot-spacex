"""Domain exception hierarchy for Pilot Space.

Provides structured exceptions with HTTP status codes and error codes,
enabling automatic RFC 7807 Problem Details responses via the global
exception handler — eliminating try/except → HTTPException boilerplate
in routers.

Usage:
    raise NotFoundError("Issue not found")
    raise ConflictError("Duplicate role name", error_code="duplicate_role")
    raise ForbiddenError("Not a workspace member")
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base domain exception with HTTP mapping.

    Subclass this for domain errors that should produce specific HTTP
    responses. The global ``app_error_handler`` reads ``http_status``
    and ``error_code`` to build RFC 7807 Problem Details automatically.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable code for frontend consumption.
        http_status: HTTP status code (class-level default, overridable).
        details: Optional extra context included in the response body.
    """

    error_code: str = "app_error"
    http_status: int = 400

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details or {}


class NotFoundError(AppError):
    """Resource not found (404)."""

    error_code = "not_found"
    http_status = 404


class UnauthorizedError(AppError):
    """Authentication failure — invalid credentials, expired token (401)."""

    error_code = "unauthorized"
    http_status = 401


class ForbiddenError(AppError):
    """Insufficient permissions (403)."""

    error_code = "forbidden"
    http_status = 403


class ConflictError(AppError):
    """Resource conflict — duplicate, concurrent edit, etc. (409)."""

    error_code = "conflict"
    http_status = 409


class ValidationError(AppError):
    """Domain validation failure (422)."""

    error_code = "validation_error"
    http_status = 422


class ServiceUnavailableError(AppError):
    """External service or dependency unavailable (503)."""

    error_code = "service_unavailable"
    http_status = 503


class BatchRunError(AppError):
    """Batch run operation failed (400).

    Base class for all batch run domain errors.
    """

    error_code = "batch_run_error"
    http_status = 400


class BatchRunCycleDetectedError(BatchRunError):
    """Circular dependency detected in batch run DAG (422).

    Raised when Kahn's topological sort detects a cycle in the
    issue dependency graph, preventing a valid execution order.
    """

    error_code = "batch_run_cycle_detected"
    http_status = 422


class BatchRunNotFoundError(NotFoundError):
    """Batch run not found (404)."""

    error_code = "batch_run_not_found"


__all__ = [
    "AppError",
    "BatchRunCycleDetectedError",
    "BatchRunError",
    "BatchRunNotFoundError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "ValidationError",
]
