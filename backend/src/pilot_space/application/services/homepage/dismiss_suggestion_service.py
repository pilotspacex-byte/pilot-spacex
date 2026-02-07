"""Service for dismissing a digest suggestion.

Creates a DigestDismissal record so the suggestion is hidden
for the requesting user on future digest fetches.

References:
- specs/012-homepage-note/spec.md Digest Dismiss Endpoint
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DismissSuggestionPayload:
    """Payload for dismissing a digest suggestion.

    Attributes:
        workspace_id: Workspace scope.
        user_id: User performing the dismissal.
        suggestion_id: ID of the suggestion being dismissed.
        entity_id: ID of the related entity.
        entity_type: Type of entity (issue, note, etc.).
        category: Suggestion category being dismissed.
    """

    workspace_id: UUID
    user_id: UUID
    suggestion_id: UUID
    entity_id: UUID | None
    entity_type: str | None
    category: str


class DismissSuggestionService:
    """Service for persisting a suggestion dismissal.

    Creates a DigestDismissal row so that future digest fetches
    exclude this (entity_id, category) combination for the user.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DismissSuggestionService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(self, payload: DismissSuggestionPayload) -> None:
        """Execute dismissal.

        Args:
            payload: The dismissal payload.
        """
        from pilot_space.infrastructure.database.models.digest_dismissal import (
            DigestDismissal,
        )
        from pilot_space.infrastructure.database.repositories.digest_repository import (
            DismissalRepository,
        )

        repo = DismissalRepository(self._session)

        dismissal = DigestDismissal(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            suggestion_category=payload.category,
            entity_id=payload.entity_id,
            entity_type=payload.entity_type,
        )

        await repo.add_dismissal(dismissal)
        await self._session.flush()

        logger.info(
            "Suggestion dismissed",
            extra={
                "suggestion_id": str(payload.suggestion_id),
                "entity_id": str(payload.entity_id),
                "category": payload.category,
                "user_id": str(payload.user_id),
            },
        )


__all__ = [
    "DismissSuggestionPayload",
    "DismissSuggestionService",
]
