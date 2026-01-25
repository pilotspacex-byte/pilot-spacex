"""API middleware for Pilot Space.

This package contains middleware components:
- auth_middleware: JWT validation and user extraction
- error_handler: RFC 7807 Problem Details error responses
- cors: CORS configuration
- rate_limiter: Rate limiting per workspace/endpoint
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

__all__ = [
    "RATE_LIMIT_CONFIGS",
    "AuthMiddleware",
    "ProblemDetail",
    "RateLimitMiddleware",
    "configure_cors",
    "create_problem_response",
    "get_current_user_from_request",
    "register_exception_handlers",
]
