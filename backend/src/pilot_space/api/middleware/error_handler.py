"""RFC 7807 Problem Details error handler.

Provides standardized error responses following RFC 7807 specification.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ProblemDetail:
    """RFC 7807 Problem Details representation.

    Provides a standardized error response format.

    Attributes:
        type: URI reference identifying the problem type.
        title: Short, human-readable summary.
        status: HTTP status code.
        detail: Human-readable explanation specific to this occurrence.
        instance: URI reference identifying the specific occurrence.
    """

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
        """Initialize Problem Detail.

        Args:
            type_uri: URI identifying the problem type.
            title: Short summary of the problem.
            status_code: HTTP status code.
            detail: Detailed explanation of the problem.
            instance: URI of the specific occurrence.
            extensions: Additional problem-specific fields.
        """
        self.type = type_uri
        self.title = title
        self.status = status_code
        self.detail = detail
        self.instance = instance
        self.extensions = extensions or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary suitable for JSON response.
        """
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
}


def create_problem_response(
    status_code: int,
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a Problem Details JSON response.

    Args:
        status_code: HTTP status code.
        detail: Detailed error message.
        instance: URI of the specific occurrence.
        extensions: Additional problem-specific fields.

    Returns:
        JSONResponse with Problem Details format.
    """
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
    """Handle HTTPException with Problem Details format.

    Args:
        request: The incoming request.
        exc: The HTTP exception.

    Returns:
        Problem Details JSON response.
    """
    return create_problem_response(
        status_code=exc.status_code,
        detail=str(exc.detail) if exc.detail else None,
        instance=str(request.url),
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle validation errors with Problem Details format.

    Args:
        request: The incoming request.
        exc: The validation exception.

    Returns:
        Problem Details JSON response.
    """
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        detail = "Validation failed"
        extensions = {"errors": errors}
    else:
        detail = str(exc)
        extensions = None

    return create_problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
        instance=str(request.url),
        extensions=extensions,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions with Problem Details format.

    Args:
        request: The incoming request.
        exc: The exception.

    Returns:
        Problem Details JSON response.
    """
    logger.exception("Unhandled exception", exc_info=exc)

    return create_problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url),
    )


async def ai_not_configured_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle AINotConfiguredError with 503 Problem Details response.

    AIGOV-05: Workspace AI calls without a configured BYOK key return 503
    with error_code AI_BYOK_REQUIRED so the frontend can prompt for key setup.

    Args:
        request: The incoming request.
        exc: The AINotConfiguredError exception.

    Returns:
        Problem Details JSON response (503).
    """
    from pilot_space.ai.exceptions import AINotConfiguredError

    if isinstance(exc, AINotConfiguredError):
        return JSONResponse(
            status_code=503,
            content={
                "type": "about:blank",
                "title": "AI Not Configured",
                "status": 503,
                "detail": "No BYOK API key configured for this workspace. Configure a key in Settings > API Keys.",
                "error_code": "AI_BYOK_REQUIRED",
            },
            media_type="application/problem+json",
        )
    return await generic_exception_handler(request, exc)


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with the app.

    Args:
        app: FastAPI application instance.
    """
    from pilot_space.ai.exceptions import AINotConfiguredError

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AINotConfiguredError, ai_not_configured_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
