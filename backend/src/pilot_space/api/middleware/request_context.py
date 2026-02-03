"""Request context middleware for workspace and correlation ID extraction.

Extracts common request context (workspace_id, correlation_id) from headers
and stores them in request.state for use by dependencies.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import Response

# Demo workspace configuration
DEMO_WORKSPACE_UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEMO_WORKSPACE_SLUGS = {"pilot-space-demo", "demo", "test"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and store request context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Extract workspace_id and correlation_id from headers.

        Args:
            request: Incoming request.
            call_next: Next middleware in chain.

        Returns:
            Response with correlation ID header.
        """
        # Extract workspace ID from headers
        workspace_id_str = request.headers.get("X-Workspace-ID") or request.headers.get(
            "X-Workspace-Id"
        )

        if workspace_id_str:
            # Check for demo workspace slugs
            if workspace_id_str.lower() in DEMO_WORKSPACE_SLUGS:
                request.state.workspace_id = DEMO_WORKSPACE_UUID
            else:
                try:
                    request.state.workspace_id = uuid.UUID(workspace_id_str)
                except ValueError:
                    request.state.workspace_id = None
        else:
            request.state.workspace_id = None

        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response = await call_next(request)

        # Add correlation ID to response headers for tracing
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_workspace_id(request: Request) -> uuid.UUID:
    """Dependency to get workspace ID from request state.

    Args:
        request: FastAPI request.

    Returns:
        Workspace UUID from request state.

    Raises:
        HTTPException: If workspace ID is not set or invalid.
    """
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID header required",
        )
    return workspace_id


def get_correlation_id(request: Request) -> str:
    """Dependency to get correlation ID from request state.

    Args:
        request: FastAPI request.

    Returns:
        Correlation ID string from request state.
    """
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


# Type aliases for dependency injection
WorkspaceId = Annotated[uuid.UUID, Depends(get_workspace_id)]
CorrelationId = Annotated[str, Depends(get_correlation_id)]


__all__ = [
    "DEMO_WORKSPACE_SLUGS",
    "DEMO_WORKSPACE_UUID",
    "CorrelationId",
    "RequestContextMiddleware",
    "WorkspaceId",
    "get_correlation_id",
    "get_workspace_id",
]
