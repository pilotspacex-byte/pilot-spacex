"""GhostText API endpoint with rate limiting.

Provides fast-path text completions for real-time writing assistance.

Reference: T082-T083 (GhostText Endpoint + Rate Limiting)
Design Decisions: DD-011 (Haiku for latency)
"""

from __future__ import annotations

import time
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pilot_space.dependencies import CurrentUserId, DbSession, GhostTextServiceDep, RedisDep
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai/ghost-text", tags=["ghost-text"])

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 10  # requests
RATE_LIMIT_WINDOW = 1  # seconds
RATE_LIMIT_KEY_PREFIX = "ghost_text_rate_limit"


class GhostTextRequest(BaseModel):
    """GhostText completion request.

    Attributes:
        context: Context text (previous paragraphs, max 500 chars).
        prefix: Prefix to complete (current line, max 200 chars).
        workspace_id: Workspace UUID for context and caching.
        block_type: TipTap block type for prompt routing (paragraph, codeBlock,
            heading, bulletList). Defaults to paragraph behavior when omitted.
        note_title: Title of the note being edited (optional context).
        linked_issues: Linked issue identifiers for context (optional).
    """

    context: str = Field(..., max_length=500, description="Context text")
    prefix: str = Field(..., max_length=200, description="Prefix to complete")
    workspace_id: UUID = Field(..., description="Workspace ID")
    block_type: Literal["paragraph", "codeBlock", "heading", "bulletList"] | None = Field(
        None, description="TipTap block type for prompt routing"
    )
    note_title: str | None = Field(None, max_length=200, description="Note title for context")
    linked_issues: list[str] | None = Field(
        None, max_length=20, description="Linked issue identifiers"
    )


class GhostTextResponse(BaseModel):
    """GhostText completion response.

    Attributes:
        suggestion: Completion suggestion text.
        confidence: Confidence score (0.0-1.0).
        cached: Whether result was cached.
    """

    suggestion: str = Field(..., description="Completion suggestion")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    cached: bool = Field(False, description="Whether cached")


async def check_rate_limit(
    user_id: UUID,
    redis: RedisDep,
) -> None:
    """Check rate limit for user.

    Args:
        user_id: User UUID.
        redis: Redis client.

    Raises:
        HTTPException: 429 if rate limit exceeded.
    """
    key = f"{RATE_LIMIT_KEY_PREFIX}:{user_id}"
    current_time = time.time()

    # Get request timestamps from Redis
    timestamps_str = await redis.get(key)

    if timestamps_str:
        # Parse timestamps
        timestamps = [float(ts) for ts in timestamps_str.split(",")]

        # Filter out expired timestamps
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]

        # Check limit
        if len(valid_timestamps) >= RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} second(s)",
            )

        # Add current timestamp
        valid_timestamps.append(current_time)
    else:
        valid_timestamps = [current_time]

    # Store updated timestamps
    timestamps_str_new = ",".join(str(ts) for ts in valid_timestamps)
    await redis.set(key, timestamps_str_new, ttl=RATE_LIMIT_WINDOW + 1)


@router.post("")
async def generate_ghost_text(
    request: GhostTextRequest,
    user_id: CurrentUserId,
    redis: RedisDep,
    session: DbSession,
    service: GhostTextServiceDep,
) -> GhostTextResponse:
    """Generate ghost text completion.

    Rate limited to 10 requests per second per user.

    Args:
        request: GhostText request with context and prefix.
        user_id: Current user ID (from auth).
        redis: Redis client.
        session: Database session for workspace membership check.
        service: GhostTextService with BYOK, executor, and cost tracking.

    Returns:
        Completion suggestion with confidence score.

    Raises:
        HTTPException: 402 if no API key configured, 403 if not a workspace member,
            429 if rate limited, 500 if generation fails.
    """
    await check_rate_limit(user_id, redis)

    from sqlalchemy import exists, select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )

    stmt = select(
        exists().where(
            WorkspaceMember.workspace_id == request.workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    if not result.scalar():
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    try:
        result = await service.generate_completion(
            context=request.context,
            prefix=request.prefix,
            workspace_id=request.workspace_id,
            user_id=user_id,
            block_type=request.block_type,
            note_title=request.note_title,
            linked_issues=request.linked_issues,
        )

        return GhostTextResponse(
            suggestion=result["suggestion"],
            confidence=result["confidence"],
            cached=result["cached"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ghost text generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate completion. Please try again.",
        ) from e


@router.delete("/cache/{workspace_id}")
async def clear_workspace_cache(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    service: GhostTextServiceDep,
) -> dict[str, Any]:
    """Clear ghost text cache for workspace.

    Args:
        workspace_id: Workspace UUID.
        user_id: Current user ID (from auth).
        session: Database session.
        service: GhostTextService for cache operations.

    Returns:
        Cache clear result with count.

    Raises:
        HTTPException: 403 if user is not a workspace member.
    """
    from sqlalchemy import exists, select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )

    # Verify workspace membership
    stmt = select(
        exists().where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    is_member = result.scalar()

    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    keys_cleared = await service.clear_workspace_cache(workspace_id)

    return {
        "message": "Cache cleared successfully",
        "keys_cleared": keys_cleared,
    }


__all__ = ["router"]
