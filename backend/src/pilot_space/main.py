"""Pilot Space API - AI-Augmented SDLC Platform.

Entry point for the FastAPI application.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pilot_space.api.middleware.request_context import RequestContextMiddleware
from pilot_space.api.v1.routers import (
    ai_annotations_router,
    ai_approvals_router,
    ai_chat_router,
    ai_configuration_router,
    ai_costs_router,
    ai_extraction_router,
    ai_pr_review_router,
    ai_router,
    ai_sessions_router,
    auth_router,
    cycles_router,
    debug_router,
    homepage_notes_from_chat_router,
    homepage_router,
    integrations_router,
    issues_ai_context_router,
    issues_ai_context_streaming_router,
    issues_ai_router,
    issues_router,
    notes_ai_router,
    notes_router,
    onboarding_router,
    projects_router,
    role_skills_router,
    role_templates_router,
    webhooks_router,
    workspace_ai_settings_router,
    workspace_cycles_router,
    workspace_invitations_router,
    workspace_issues_router,
    workspace_members_router,
    workspace_notes_ai_router,
    workspace_notes_router,
    workspaces_router,
)

dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown events."""
    import asyncio

    from pilot_space.config import get_settings
    from pilot_space.container import get_container

    # Startup: Initialize DI container and connections
    app.state.container = get_container()
    settings = get_settings()

    # Connect to Redis for session management
    redis_client = app.state.container.redis_client()
    if redis_client is not None:
        await redis_client.connect()

    # Start conversation worker if queue mode enabled
    worker_task: asyncio.Task[None] | None = None
    worker = None
    digest_worker_task: asyncio.Task[None] | None = None
    digest_worker = None
    if settings.ai_queue_mode:
        queue_client = app.state.container.queue_client()
        if queue_client and redis_client:
            from pilot_space.infrastructure.queue.models import QueueName

            await queue_client.create_queue(QueueName.AI_CHAT)
            await queue_client.create_queue(QueueName.AI_LOW)

            from pilot_space.ai.workers.conversation_worker import ConversationWorker

            agent = app.state.container.pilotspace_agent()
            session_handler = None
            session_manager = app.state.container.session_manager()
            if session_manager is not None:
                from pilot_space.ai.sdk.session_handler import SessionHandler

                session_handler = SessionHandler(session_manager=session_manager)

            worker = ConversationWorker(queue_client, redis_client, agent, session_handler)
            worker_task = asyncio.create_task(worker.start())

            # Start digest worker for AI_LOW queue
            from pilot_space.ai.workers.digest_worker import DigestWorker

            session_factory = app.state.container.session_factory()
            digest_worker = DigestWorker(queue_client, session_factory)
            digest_worker_task = asyncio.create_task(digest_worker.start())

    yield

    # Shutdown: Clean up workers and connections
    if digest_worker:
        await digest_worker.stop()
    if digest_worker_task:
        digest_worker_task.cancel()
    if worker:
        await worker.stop()
    if worker_task:
        worker_task.cancel()
    if redis_client is not None:
        await redis_client.disconnect()


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
app.include_router(issues_ai_context_streaming_router, prefix=API_V1_PREFIX)
app.include_router(notes_router, prefix=API_V1_PREFIX)
if notes_ai_router is not None:
    app.include_router(notes_ai_router, prefix=API_V1_PREFIX)
app.include_router(cycles_router, prefix=API_V1_PREFIX)
if ai_router is not None:
    app.include_router(ai_router, prefix=API_V1_PREFIX)
if ai_annotations_router is not None:
    app.include_router(ai_annotations_router, prefix=API_V1_PREFIX)
app.include_router(ai_approvals_router, prefix=API_V1_PREFIX)
app.include_router(ai_chat_router, prefix=f"{API_V1_PREFIX}/ai")
app.include_router(ai_configuration_router, prefix=API_V1_PREFIX)
app.include_router(ai_costs_router, prefix=API_V1_PREFIX)
app.include_router(ai_extraction_router, prefix=API_V1_PREFIX)
if ai_pr_review_router is not None:
    app.include_router(ai_pr_review_router, prefix=API_V1_PREFIX)
app.include_router(ai_sessions_router, prefix=API_V1_PREFIX)
app.include_router(integrations_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)
app.include_router(workspace_ai_settings_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_cycles_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_issues_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_invitations_router, prefix=API_V1_PREFIX)
app.include_router(workspace_members_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_notes_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_notes_ai_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(onboarding_router, prefix=API_V1_PREFIX)
app.include_router(homepage_router, prefix=API_V1_PREFIX)
app.include_router(homepage_notes_from_chat_router, prefix=API_V1_PREFIX)
app.include_router(role_templates_router, prefix=API_V1_PREFIX)
app.include_router(role_skills_router, prefix=API_V1_PREFIX)
if debug_router:
    app.include_router(debug_router, prefix=API_V1_PREFIX)
