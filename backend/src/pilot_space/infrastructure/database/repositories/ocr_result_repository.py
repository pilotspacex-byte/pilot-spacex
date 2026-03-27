"""Repository for OcrResultModel entities.

Provides attachment-scoped queries for OCR extraction results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from pilot_space.infrastructure.database.models.ocr_result import OcrResultModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class OcrResultRepository:
    """Repository for OcrResultModel entities.

    OcrResultModel uses Base (not BaseModel/SoftDeleteMixin), so this
    repository does not extend BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize OcrResultRepository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def get_latest_by_attachment_id(
        self,
        attachment_id: UUID,
    ) -> OcrResultModel | None:
        """Return the most recent OCR result for a given attachment.

        Args:
            attachment_id: UUID of the parent chat attachment.

        Returns:
            The latest OcrResultModel row or None if no OCR has run yet.
        """
        result = await self.session.execute(
            select(OcrResultModel)
            .where(OcrResultModel.attachment_id == attachment_id)
            .order_by(OcrResultModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


__all__ = ["OcrResultRepository"]
