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
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Fetch attachment records owned by *user_id* and build Claude content blocks.

    Raises:
        HTTPException 403 if any attachment is missing or not owned by the user.

    Returns:
        Tuple of (attachment ORM records, list of Claude content-block dicts).
    """
    if not attachment_ids:
        return [], []

    repo = ChatAttachmentRepository(session)
    records = await repo.get_by_ids_for_user(attachment_ids, user_id)

    if len(records) != len(attachment_ids):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ATTACHMENT_NOT_OWNED",
                "message": "One or more attachments not found or not owned by user",
            },
        )

    blocks = await AttachmentContentService(SupabaseStorageClient()).build_content_blocks(records)
    return records, blocks
