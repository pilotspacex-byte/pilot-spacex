"""API middleware for Pilot Space.

This package contains middleware components:
- auth_middleware: JWT validation and user extraction
- error_handler: RFC 7807 Problem Details error responses
- cors: CORS configuration
- rate_limiter: Rate limiting per workspace/endpoint
- request_context: Workspace and correlation ID extraction
"""

from pilot_space.api.middleware.auth_middleware import (
    AuthMiddleware,
    get_current_user_from_request,
)
from pilot_space.api.middleware.cors import configure_cors
from pilot_space.api.middleware.error_handler import (
    ProblemDetail,
    create_problem_response,
    register_exception_handlers,
)
from pilot_space.api.middleware.rate_limiter import (
    RATE_LIMIT_CONFIGS,
    RateLimitMiddleware,
)
from pilot_space.api.middleware.request_context import (
    CorrelationId,
    RequestContextMiddleware,
    WorkspaceId,
    get_correlation_id,
    get_workspace_id,
)

__all__ = [
    "RATE_LIMIT_CONFIGS",
    "AuthMiddleware",
    "CorrelationId",
    "ProblemDetail",
    "RateLimitMiddleware",
    "RequestContextMiddleware",
    "WorkspaceId",
    "configure_cors",
    "create_problem_response",
    "get_correlation_id",
    "get_current_user_from_request",
    "get_workspace_id",
    "register_exception_handlers",
]
