"""Pilot Space API - AI-Augmented SDLC Platform.

Entry point for the FastAPI application.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pilot_space.api.middleware.request_context import RequestContextMiddleware
from pilot_space.api.v1.routers import (
    ai_configuration_router,
    ai_router,
    auth_router,
    cycles_router,
    integrations_router,
    issues_ai_context_router,
    issues_ai_router,
    issues_router,
    notes_router,
    projects_router,
    webhooks_router,
    workspace_issues_router,
    workspace_notes_router,
    workspaces_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Initialize connections (database, redis, etc.)
    # These will be implemented in Phase 2 (Foundation)
    yield
    # Shutdown: Clean up connections


app = FastAPI(
    title="Pilot Space API",
    description=(
        "AI-Augmented SDLC Platform with Note-First Workflow. "
        "Provides project management enhanced with AI capabilities including "
        "ghost text suggestions, PR review, and context generation."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Request context middleware (must be first for header extraction)
app.add_middleware(RequestContextMiddleware)

# CORS middleware configuration
# In production, replace with actual frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring.

    Returns:
        dict with status "healthy"
    """
    return {"status": "healthy"}


@app.get("/ready", tags=["Health"])
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint for Kubernetes probes.

    Verifies that the application is ready to receive traffic.
    In Phase 2, this will check database and cache connectivity.

    Returns:
        dict with status "ready"
    """
    return {"status": "ready"}


# Mount all routers under /api/v1
API_V1_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(workspaces_router, prefix=API_V1_PREFIX)
app.include_router(projects_router, prefix=API_V1_PREFIX)
app.include_router(issues_router, prefix=API_V1_PREFIX)
app.include_router(issues_ai_router, prefix=API_V1_PREFIX)
app.include_router(issues_ai_context_router, prefix=API_V1_PREFIX)
app.include_router(notes_router, prefix=API_V1_PREFIX)
app.include_router(cycles_router, prefix=API_V1_PREFIX)
app.include_router(ai_router, prefix=API_V1_PREFIX)
app.include_router(ai_configuration_router, prefix=API_V1_PREFIX)
app.include_router(integrations_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)
app.include_router(workspace_issues_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_notes_router, prefix=f"{API_V1_PREFIX}/workspaces")
