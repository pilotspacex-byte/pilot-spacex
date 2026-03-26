"""RFC 7807 Problem Details error handler.

Provides standardized error responses following RFC 7807 specification.
Sanitizes internal details in production to prevent information leakage.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Regex to strip UUIDs from error messages sent to clients
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# Keys that must never appear in client-facing error responses
_SENSITIVE_DETAIL_KEYS = frozenset(
    {
        "raw_response",
        "cause_type",
        "agent_name",
        "workspace_id",
        "provider",
        "missing_fields",
        "input_tokens",
        "max_tokens",
        "context_size",
        "max_context",
    }
)

# Keys safe to include in client responses
_SAFE_DETAIL_KEYS = frozenset(
    {
        "retry_after_seconds",
        "error_code",
    }
)


def _is_production() -> bool:
    """Check if running in production (cached after first call)."""
    from pilot_space.config import get_settings

    return get_settings().app_env == "production"


def _sanitize_message(message: str) -> str:
    """Strip UUIDs and internal identifiers from error messages."""
    return _UUID_RE.sub("<id>", message)


def _sanitize_details(details: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive keys from details dict for client response."""
    return {k: v for k, v in details.items() if k not in _SENSITIVE_DETAIL_KEYS}


class ProblemDetail:
    """RFC 7807 Problem Details representation."""

    def __init__(
        self,
        *,
        type_uri: str = "about:blank",
        title: str,
        status_code: int,
        detail: str | None = None,
        instance: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        self.type = type_uri
        self.title = title
        self.status = status_code
        self.detail = detail
        self.instance = instance
        self.extensions = extensions or {}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.instance:
            result["instance"] = self.instance
        result.update(self.extensions)
        return result


# Standard problem types
PROBLEM_TYPES = {
    400: ("https://httpstatuses.com/400", "Bad Request"),
    401: ("https://httpstatuses.com/401", "Unauthorized"),
    403: ("https://httpstatuses.com/403", "Forbidden"),
    404: ("https://httpstatuses.com/404", "Not Found"),
    409: ("https://httpstatuses.com/409", "Conflict"),
    422: ("https://httpstatuses.com/422", "Unprocessable Entity"),
    429: ("https://httpstatuses.com/429", "Too Many Requests"),
    500: ("https://httpstatuses.com/500", "Internal Server Error"),
    502: ("https://httpstatuses.com/502", "Bad Gateway"),
    503: ("https://httpstatuses.com/503", "Service Unavailable"),
    504: ("https://httpstatuses.com/504", "Gateway Timeout"),
}


def create_problem_response(
    status_code: int,
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a Problem Details JSON response."""
    type_uri, title = PROBLEM_TYPES.get(status_code, ("about:blank", "Error"))

    problem = ProblemDetail(
        type_uri=type_uri,
        title=title,
        status_code=status_code,
        detail=detail,
        instance=instance,
        extensions=extensions,
    )

    return JSONResponse(
        status_code=status_code,
        content=problem.to_dict(),
        media_type="application/problem+json",
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle HTTPException with Problem Details format."""
    return create_problem_response(
        status_code=exc.status_code,
        detail=str(exc.detail) if exc.detail else None,
        instance=str(request.url.path),
    )


def _sanitize_pydantic_errors(errors: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure all values in Pydantic error dicts are JSON-serializable.

    Pydantic v2 ``exc.errors()`` can include ``ctx["error"]`` entries that are
    raw Python exceptions (e.g. ``ValueError``). These are not JSON-serializable
    and cause ``JSONResponse`` to raise a 500. This helper converts any
    non-primitive ``ctx["error"]`` value to its string representation.

    Args:
        errors: Raw list returned by ``RequestValidationError.errors()``.

    Returns:
        A new list of error dicts safe for JSON serialisation.
    """
    sanitized: list[dict[str, Any]] = []
    _json_primitives = (str, int, float, bool, type(None))
    for error in errors:
        e: dict[str, Any] = dict(error)
        if "ctx" in e and isinstance(e["ctx"], dict) and "error" in e["ctx"]:
            ctx: dict[str, Any] = dict(e["ctx"])
            if not isinstance(ctx["error"], _json_primitives):
                ctx["error"] = str(ctx["error"])
            e["ctx"] = ctx
        sanitized.append(e)
    return sanitized


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle validation errors with Problem Details format."""
    if isinstance(exc, RequestValidationError):
        errors = _sanitize_pydantic_errors(exc.errors())
        # Strip 'url' key from each error dict (Pydantic v2 includes it)
        sanitized_errors = [{k: v for k, v in err.items() if k != "url"} for err in errors]
        detail = "Validation failed"
        extensions: dict[str, Any] | None = {"errors": sanitized_errors}
    else:
        detail = str(exc)
        extensions = None

    return create_problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
        instance=str(request.url.path),
        extensions=extensions,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions with Problem Details format.

    Never exposes internal details to clients.
    """
    logger.exception("Unhandled exception", exc_info=exc)

    return create_problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url.path),
    )


async def ai_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all AIError subclasses with RFC 7807 Problem Details.

    Logs full details server-side; sanitizes client response in production.
    """
    from pilot_space.ai.exceptions import AIError

    if isinstance(exc, AIError):
        # Always log full details server-side
        logger.warning(
            "ai_error",
            error_code=exc.code,
            message=exc.message,
            http_status=exc.http_status,
            details=exc.details,
        )

        # Build client-safe extensions
        extensions: dict[str, Any] = {"error_code": exc.code}
        if exc.details and not _is_production():
            extensions["details"] = exc.details
        elif exc.details:
            extensions["details"] = _sanitize_details(exc.details)

        # Sanitize message in production
        detail = exc.message
        if _is_production():
            detail = _sanitize_message(detail)

        return create_problem_response(
            status_code=exc.http_status,
            detail=detail,
            instance=str(request.url.path),
            extensions=extensions,
        )
    return await generic_exception_handler(request, exc)


async def app_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all AppError domain exceptions with RFC 7807 Problem Details.

    Logs full details server-side; sanitizes client response in production.
    """
    from pilot_space.domain.exceptions import AppError

    if isinstance(exc, AppError):
        # Log full details server-side for debugging
        logger.info(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            http_status=exc.http_status,
            details=exc.details if exc.details else None,
        )

        # Build client-safe extensions
        extensions: dict[str, Any] = {"error_code": exc.error_code}
        if exc.details and not _is_production():
            extensions["details"] = exc.details
        elif exc.details:
            extensions["details"] = _sanitize_details(exc.details)

        # Sanitize message in production (strip UUIDs)
        detail = exc.message
        if _is_production():
            detail = _sanitize_message(detail)

        return create_problem_response(
            status_code=exc.http_status,
            detail=detail,
            instance=str(request.url.path),
            extensions=extensions,
        )
    return await generic_exception_handler(request, exc)


async def transcription_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle TranscriptionError with RFC 7807 Problem Details response."""
    from pilot_space.application.services.transcription import TranscriptionError

    if isinstance(exc, TranscriptionError):
        return create_problem_response(
            status_code=exc.http_status,
            detail=exc.message,
            instance=str(request.url.path),
            extensions={"error_code": exc.error_code},
        )
    return await generic_exception_handler(request, exc)


async def feature_toggle_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle FeatureToggleError with RFC 7807 Problem Details response.

    Maps FeatureToggleError.http_status and error_code to a structured
    problem+json body so the feature toggles router stays thin.

    Args:
        request: The incoming request.
        exc: The FeatureToggleError exception.

    Returns:
        Problem Details JSON response.
    """
    from pilot_space.application.services.feature_toggle import FeatureToggleError

    if isinstance(exc, FeatureToggleError):
        return create_problem_response(
            status_code=exc.http_status,
            detail=exc.message,
            instance=str(request.url),
            extensions={"error_code": exc.error_code},
        )
    return await generic_exception_handler(request, exc)


async def workspace_member_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle WorkspaceMemberError with RFC 7807 Problem Details response."""
    from pilot_space.application.services.workspace_member import WorkspaceMemberError

    if isinstance(exc, WorkspaceMemberError):
        return create_problem_response(
            status_code=exc.http_status,
            detail=exc.message,
            instance=str(request.url.path),
            extensions={"error_code": exc.error_code},
        )
    return await generic_exception_handler(request, exc)


async def workspace_invitation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle WorkspaceInvitationError with RFC 7807 Problem Details response."""
    from pilot_space.application.services.workspace_invitation import WorkspaceInvitationError

    if isinstance(exc, WorkspaceInvitationError):
        return create_problem_response(
            status_code=exc.http_status,
            detail=exc.message,
            instance=str(request.url.path),
            extensions={"error_code": exc.error_code},
        )
    return await generic_exception_handler(request, exc)


async def mcp_server_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle McpServerError with RFC 7807 Problem Details response.

    Maps McpServerError.http_status and error_code to a structured
    problem+json body so routers don't need manual try/except → HTTPException.

    Args:
        request: The incoming request.
        exc: The McpServerError exception.

    Returns:
        Problem Details JSON response.
    """
    from pilot_space.application.services.mcp.exceptions import McpServerError

    if isinstance(exc, McpServerError):
        return create_problem_response(
            status_code=exc.http_status,
            detail=exc.message,
            instance=str(request.url),
            extensions={"error_code": exc.error_code},
        )
    return await generic_exception_handler(request, exc)


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with the app.

    Order matters: more specific exception classes must be registered before
    their base classes. FastAPI matches handlers by isinstance checks, so
    the first matching handler wins.
    """
    from pilot_space.ai.exceptions import AIError
    from pilot_space.application.services.feature_toggle import FeatureToggleError
    from pilot_space.application.services.mcp.exceptions import McpServerError
    from pilot_space.application.services.transcription import TranscriptionError
    from pilot_space.application.services.workspace_invitation import WorkspaceInvitationError
    from pilot_space.application.services.workspace_member import WorkspaceMemberError
    from pilot_space.domain.exceptions import AppError

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # Domain exceptions — specific hierarchies before generic fallback
    app.add_exception_handler(AIError, ai_error_handler)
    app.add_exception_handler(TranscriptionError, transcription_error_handler)
    app.add_exception_handler(FeatureToggleError, feature_toggle_error_handler)
    app.add_exception_handler(McpServerError, mcp_server_error_handler)
    app.add_exception_handler(WorkspaceMemberError, workspace_member_error_handler)
    app.add_exception_handler(WorkspaceInvitationError, workspace_invitation_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
