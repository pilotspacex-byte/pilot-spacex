"""Webhooks API router for receiving external events.

T187: Create webhooks router for GitHub event handling.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from pilot_space.api.v1.dependencies import ProcessGitHubWebhookServiceDep
from pilot_space.api.v1.schemas.integration import WebhookProcessResult
from pilot_space.application.services.integration import (
    ProcessWebhookPayload,
)
from pilot_space.config import get_settings
from pilot_space.dependencies import DbSession
from pilot_space.domain.exceptions import ServiceUnavailableError
from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.github import (
    GitHubWebhookHandler,
    WebhookVerificationError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/github",
    response_model=WebhookProcessResult,
    summary="Receive GitHub webhook",
)
async def receive_github_webhook(
    request: Request,
    session: DbSession,
    service: ProcessGitHubWebhookServiceDep,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> WebhookProcessResult:
    """Receive and process GitHub webhook events.

    This endpoint receives webhook events from GitHub and processes:
    - Push events (commit linking)
    - Pull request events (PR linking, auto-transition)
    - Pull request review events

    Signature verification is performed using HMAC-SHA256.
    """
    settings = get_settings()

    if not settings.github_webhook_secret:
        raise ServiceUnavailableError("Webhook secret not configured")

    # Get raw body for signature verification
    body = await request.body()

    # Create handler and verify signature (per-request, depends on secret)
    handler = GitHubWebhookHandler(
        webhook_secret=settings.github_webhook_secret.get_secret_value(),
    )

    try:
        handler.verify_signature(body, x_hub_signature_256)
    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        ) from e

    # Parse payload
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from e

    result = await service.execute(
        ProcessWebhookPayload(
            event_type=x_github_event,
            delivery_id=x_github_delivery,
            signature=x_hub_signature_256,
            payload=payload,
        )
    )

    if result.processed:
        await session.commit()

    return WebhookProcessResult(
        processed=result.processed,
        event_type=result.event_type or x_github_event,
        action=result.action,
        links_created=result.links_created,
        issues_affected=result.issues_affected,
        auto_transitioned=result.auto_transitioned,
        error=result.error,
    )


@router.get(
    "/github/health",
    summary="GitHub webhook health check",
)
async def github_webhook_health() -> dict[str, str]:
    """Health check endpoint for GitHub webhook configuration."""
    settings = get_settings()

    configured = bool(settings.github_webhook_secret)

    return {
        "status": "configured" if configured else "not_configured",
        "endpoint": "/api/v1/webhooks/github",
    }


__all__ = ["router"]
