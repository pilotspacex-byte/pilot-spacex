"""Helper: fetch and validate chat attachments, build Claude content blocks.

Extracted from ai_chat.py to keep that router under the 700-line limit.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.ai.attachment_content_service import (
    AttachmentContentService,
)
from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
    ChatAttachmentRepository,
)
from pilot_space.infrastructure.storage.client import SupabaseStorageClient


async def resolve_attachments(
    attachment_ids: list[UUID],
    user_id: UUID,
    session: AsyncSession,
    storage_client: SupabaseStorageClient,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Fetch attachment records owned by *user_id* and build Claude content blocks.

    Distinguishes between two failure modes:
    - 403 ATTACHMENT_NOT_OWNED: one or more IDs do not exist or belong to another user.
    - 400 ATTACHMENT_EXPIRED: all IDs are owned but one or more have passed their TTL.

    Args:
        attachment_ids: List of attachment UUIDs to resolve.
        user_id: Authenticated user ID.
        session: Async DB session.
        storage_client: Injected storage client from the DI container.

    Raises:
        HTTPException 403 if any attachment is not owned by the user.
        HTTPException 400 if any owned attachment has expired.

    Returns:
        Tuple of (attachment ORM records, list of Claude content-block dicts).
    """
    if not attachment_ids:
        return [], []

    repo = ChatAttachmentRepository(session)

    # Phase 1: ownership check (includes expired rows).
    all_owned = await repo.get_by_ids_for_user_include_expired(attachment_ids, user_id)
    if len(all_owned) != len(attachment_ids):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ATTACHMENT_NOT_OWNED",
                "message": "One or more attachments not found or not owned by user",
            },
        )

    # Phase 2: expiry check (only non-expired rows).
    valid_records = await repo.get_by_ids_for_user(attachment_ids, user_id)
    if len(valid_records) != len(attachment_ids):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ATTACHMENT_EXPIRED",
                "message": "One or more attachments have expired",
            },
        )

    blocks = await AttachmentContentService(storage_client).build_content_blocks(valid_records)
    return valid_records, blocks
