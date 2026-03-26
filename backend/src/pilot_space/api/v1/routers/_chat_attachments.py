"""Helper: fetch and validate chat attachments, build Claude content blocks.

Extracted from ai_chat.py to keep that router under the 700-line limit.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.ai.attachment_content_service import (
    AttachmentContentService,
)
from pilot_space.domain.exceptions import AppError, ForbiddenError
from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
    ChatAttachmentRepository,
)


async def resolve_attachments(
    attachment_ids: list[UUID],
    user_id: UUID,
    session: AsyncSession,
    attachment_content_service: AttachmentContentService,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Fetch attachment records owned by *user_id* and build Claude content blocks.

    All dependencies are injected by the caller (ai_chat.py) from the DI container.

    Raises:
        ForbiddenError if any attachment is not owned by the user.
        AppError if any owned attachment has expired.

    Returns:
        Tuple of (attachment ORM records, list of Claude content-block dicts).
    """
    if not attachment_ids:
        return [], []

    repo = ChatAttachmentRepository(session)

    # Phase 1: ownership check (includes expired rows).
    all_owned = await repo.get_by_ids_for_user_include_expired(attachment_ids, user_id)
    if len(all_owned) != len(attachment_ids):
        raise ForbiddenError(
            "One or more attachments not found or not owned by user",
            error_code="ATTACHMENT_NOT_OWNED",
        )

    # Phase 2: expiry check (only non-expired rows).
    valid_records = await repo.get_by_ids_for_user(attachment_ids, user_id)
    if len(valid_records) != len(attachment_ids):
        raise AppError(
            "One or more attachments have expired",
            error_code="ATTACHMENT_EXPIRED",
        )

    blocks = await attachment_content_service.build_content_blocks(valid_records)
    return valid_records, blocks
