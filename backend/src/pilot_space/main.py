"""Pilot Space API - AI-Augmented SDLC Platform.

Entry point for the FastAPI application.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI

from pilot_space.api.middleware.cors import configure_cors
from pilot_space.api.middleware.error_handler import register_exception_handlers
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
    ai_tasks_router,
    auth_router,
    block_ownership_router,
    cycles_router,
    debug_router,
    dependency_graph_router,
    ghost_text_router,
    homepage_notes_from_chat_router,
    homepage_router,
    integrations_router,
    intents_router,
    issues_ai_context_router,
    issues_ai_context_streaming_router,
    issues_ai_router,
    issues_router,
    mcp_tools_router,
    memory_router,
    note_templates_router,
    note_versions_router,
    note_yjs_state_router,
    notes_ai_router,
    onboarding_router,
    pm_blocks_router,
    projects_router,
    role_skills_router,
    role_templates_router,
    skill_approvals_router,
    skills_router,
    webhooks_router,
    workspace_ai_settings_router,
    workspace_cycles_router,
    workspace_invitations_router,
    workspace_issues_router,
    workspace_members_router,
    workspace_note_issue_links_router,
    workspace_note_links_router,
    workspace_notes_ai_router,
    workspace_notes_router,
    workspace_tasks_router,
    workspaces_router,
)

dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown events."""
    import asyncio

    from pilot_space.config import get_settings
    from pilot_space.container import get_container
    from pilot_space.infrastructure.logging import configure_structlog, get_logger

    # Startup: Initialize DI container and connections
    container = get_container()

    # Wire container for dependency injection
    # This enables @inject decorator and Provide[Container.x] patterns
    container.wire(modules=container.wiring_config.modules)

    app.state.container = container
    settings = get_settings()

    # Configure structured logging first
    configure_structlog(settings)
    logger = get_logger(__name__)
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        app_env=settings.app_env,
        log_level=settings.log_level,
    )

    # Initialize DI container and connections
    app.state.container = get_container()

    # Connect to Redis for session management
    redis_client = app.state.container.redis_client()
    if redis_client is not None:
        await redis_client.connect()

    # Start digest worker for homepage digest generation
    digest_worker_task: asyncio.Task[None] | None = None
    digest_worker = None
    # T-069: Start memory worker for memory engine jobs (intent_dedup, embedding, DLQ)
    memory_worker_task: asyncio.Task[None] | None = None
    memory_worker = None
    queue_client = app.state.container.queue_client()
    if queue_client and redis_client:
        from pilot_space.infrastructure.queue.models import QueueName

        await queue_client.create_queue(QueueName.AI_LOW)
        await queue_client.create_queue(QueueName.AI_NORMAL)

        session_factory = app.state.container.session_factory()

        from pilot_space.ai.workers.digest_worker import DigestWorker

        digest_worker = DigestWorker(queue_client, session_factory)
        digest_worker_task = asyncio.create_task(digest_worker.start())

        from pilot_space.ai.workers.memory_worker import MemoryWorker

        _google_secret = getattr(settings, "google_api_key", None)
        _google_api_key: str | None = _google_secret.get_secret_value() if _google_secret else None
        memory_worker = MemoryWorker(
            queue=queue_client,
            session_factory=session_factory,
            google_api_key=_google_api_key,
        )
        memory_worker_task = asyncio.create_task(memory_worker.start())

    # Start question adapter cleanup task (FR-015: 5-min timeout enforcement)
    from pilot_space.ai.sdk.question_adapter import get_question_adapter

    question_adapter = get_question_adapter()
    await question_adapter.start_cleanup_task(interval_seconds=60.0)

    # Log startup completion
    logger.info(
        "application_ready",
        redis_connected=redis_client is not None,
    )

    yield

    # Shutdown: Clean up workers and connections
    logger.info("application_shutdown_start")
    await question_adapter.stop_cleanup_task()
    if digest_worker:
        await digest_worker.stop()
        logger.info("digest_worker_stopped")
    if digest_worker_task:
        digest_worker_task.cancel()
    # T-069: Graceful shutdown of memory worker
    if memory_worker:
        await memory_worker.stop()
        logger.info("memory_worker_stopped")
    if memory_worker_task:
        memory_worker_task.cancel()
    if redis_client is not None:
        await redis_client.disconnect()
        logger.info("redis_disconnected")
    logger.info("application_shutdown_complete")


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

# RFC 7807 exception handlers (must be registered before middleware)
register_exception_handlers(app)

# Request context middleware (must be first for header extraction)
app.add_middleware(RequestContextMiddleware)

configure_cors(app)


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
app.include_router(notes_ai_router, prefix=API_V1_PREFIX)
app.include_router(cycles_router, prefix=API_V1_PREFIX)
app.include_router(ai_router, prefix=API_V1_PREFIX)
app.include_router(ai_annotations_router, prefix=API_V1_PREFIX)
app.include_router(ai_approvals_router, prefix=f"{API_V1_PREFIX}/ai")
app.include_router(ai_chat_router, prefix=f"{API_V1_PREFIX}/ai")
app.include_router(ai_configuration_router, prefix=API_V1_PREFIX)
app.include_router(ai_costs_router, prefix=f"{API_V1_PREFIX}/ai")
app.include_router(ai_extraction_router, prefix=API_V1_PREFIX)
app.include_router(ghost_text_router, prefix=API_V1_PREFIX)
app.include_router(ai_tasks_router, prefix=API_V1_PREFIX)
app.include_router(mcp_tools_router, prefix=API_V1_PREFIX)
app.include_router(ai_pr_review_router, prefix=API_V1_PREFIX)
app.include_router(ai_sessions_router, prefix=API_V1_PREFIX)
app.include_router(integrations_router, prefix=API_V1_PREFIX)
app.include_router(webhooks_router, prefix=API_V1_PREFIX)
app.include_router(workspace_ai_settings_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_cycles_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_issues_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_invitations_router, prefix=API_V1_PREFIX)
app.include_router(workspace_members_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_note_issue_links_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_note_links_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_notes_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_notes_ai_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(block_ownership_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(note_templates_router, prefix=f"{API_V1_PREFIX}")
app.include_router(note_versions_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(note_yjs_state_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(workspace_tasks_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(intents_router, prefix=f"{API_V1_PREFIX}/workspaces")
app.include_router(memory_router, prefix=API_V1_PREFIX)
app.include_router(pm_blocks_router, prefix=API_V1_PREFIX)
app.include_router(dependency_graph_router, prefix=API_V1_PREFIX)
app.include_router(onboarding_router, prefix=API_V1_PREFIX)
app.include_router(homepage_router, prefix=API_V1_PREFIX)
app.include_router(homepage_notes_from_chat_router, prefix=API_V1_PREFIX)
app.include_router(role_templates_router, prefix=API_V1_PREFIX)
app.include_router(role_skills_router, prefix=API_V1_PREFIX)
app.include_router(skills_router, prefix=API_V1_PREFIX)
app.include_router(skill_approvals_router, prefix=f"{API_V1_PREFIX}/workspaces")
if debug_router:
    app.include_router(debug_router, prefix=API_V1_PREFIX)
