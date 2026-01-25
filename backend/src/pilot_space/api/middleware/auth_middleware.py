"""Authentication middleware for JWT validation.

Validates Supabase JWT tokens on protected routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from pilot_space.infrastructure.auth import (
    SupabaseAuth,
    SupabaseAuthError,
    TokenExpiredError,
    TokenPayload,
)

if TYPE_CHECKING:
    from starlette.responses import Response


# Public routes that don't require authentication
PUBLIC_ROUTES: set[str] = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/callback",
    "/api/v1/auth/refresh",
}


def is_public_route(path: str) -> bool:
    """Check if path is a public route.

    Args:
        path: Request path.

    Returns:
        True if route is public.
    """
    return path in PUBLIC_ROUTES or path.startswith("/static")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication.

    Validates Bearer tokens on non-public routes and attaches
    user context to request state.
    """

    def __init__(
        self,
        app: Any,
        auth: SupabaseAuth | None = None,
    ) -> None:
        """Initialize auth middleware.

        Args:
            app: FastAPI application.
            auth: Optional SupabaseAuth instance.
        """
        super().__init__(app)
        self._auth = auth or SupabaseAuth()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request through authentication.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response from next handler.

        Raises:
            HTTPException: If authentication fails.
        """
        # Skip auth for public routes
        if is_public_route(request.url.path):
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Use: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]

        # Validate token
        try:
            payload = self._auth.validate_token(token)
            # Store user context in request state
            request.state.user = payload
            request.state.user_id = payload.user_id
            request.state.token = token
        except TokenExpiredError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except SupabaseAuthError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        return await call_next(request)


def get_current_user_from_request(request: Request) -> TokenPayload:
    """Extract current user from request state.

    Args:
        request: The current request.

    Returns:
        User token payload.

    Raises:
        HTTPException: If user not authenticated.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user  # type: ignore[no-any-return]
