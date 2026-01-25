"""Webhooks API router for receiving external events.

T187: Create webhooks router for GitHub event handling.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from pilot_space.api.v1.schemas.integration import WebhookProcessResult
from pilot_space.config import get_settings
from pilot_space.integrations.github import (
    GitHubWebhookHandler,
    WebhookProcessingError,
    WebhookVerificationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/github",
    response_model=WebhookProcessResult,
    summary="Receive GitHub webhook",
)
async def receive_github_webhook(
    request: Request,
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    # Get raw body for signature verification
    body = await request.body()

    # Create handler and verify signature
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

    # Parse event
    try:
        webhook = handler.parse_event(
            event_type=x_github_event,
            delivery_id=x_github_delivery,
            payload=payload,
        )
    except WebhookProcessingError as e:
        logger.info(f"Unsupported webhook event: {e}")
        return WebhookProcessResult(
            processed=False,
            event_type=x_github_event,
            error=str(e),
        )

    # Check for duplicate
    if handler.is_duplicate(x_github_delivery):
        logger.info(
            "Duplicate webhook delivery",
            extra={"delivery_id": x_github_delivery},
        )
        return WebhookProcessResult(
            processed=False,
            event_type=x_github_event,
            error="Duplicate delivery",
        )

    logger.info(
        "Received GitHub webhook",
        extra={
            "event_type": webhook.event_type.value,
            "action": webhook.action,
            "delivery_id": webhook.delivery_id,
            "repository": webhook.repository,
        },
    )

    # For now, acknowledge receipt and enqueue for async processing
    # In a production setup, this would use Supabase Queue
    # TODO: Integrate with ProcessGitHubWebhookService via queue

    # Mark as processed
    handler.mark_processed(x_github_delivery)

    return WebhookProcessResult(
        processed=True,
        event_type=webhook.event_type.value,
        action=webhook.action,
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
