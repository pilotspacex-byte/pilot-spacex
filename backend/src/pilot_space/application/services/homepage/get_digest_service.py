"""Service for fetching the latest workspace digest.

Retrieves the most recent WorkspaceDigest, filters out suggestions
dismissed by the requesting user, and returns the result.

References:
- specs/012-homepage-note/spec.md Digest Endpoints
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GetDigestPayload:
    """Payload for fetching the latest digest.

    Attributes:
        workspace_id: Workspace to query.
        user_id: Requesting user (for filtering dismissals).
    """

    workspace_id: UUID
    user_id: UUID


@dataclass
class DigestSuggestionItem:
    """A single digest suggestion after dismissal filtering.

    Attributes:
        id: Unique suggestion identifier.
        category: Suggestion category (stale_issues, unlinked_notes, etc.).
        title: Short actionable title.
        description: Detailed explanation.
        entity_id: Related entity ID (issue, note, etc.).
        entity_type: Entity type: issue, note, cycle, etc.
        action_url: Frontend route for quick action.
        relevance_score: Relevance to current user (0.0-1.0).
    """

    id: UUID
    category: str
    title: str
    description: str
    entity_id: UUID | None = None
    entity_type: str | None = None
    entity_identifier: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    action_type: str | None = None
    action_label: str | None = None
    action_url: str | None = None
    relevance_score: float = 0.5


@dataclass
class GetDigestResult:
    """Result from fetching the latest digest.

    Attributes:
        generated_at: When the digest was generated.
        generated_by: Origin — 'scheduled' or 'manual'.
        suggestions: Filtered, ranked suggestion list.
        suggestion_count: Number of suggestions after filtering.
    """

    generated_at: datetime | None = None
    generated_by: str = "scheduled"
    suggestions: list[DigestSuggestionItem] = field(default_factory=list)
    suggestion_count: int = 0


class GetDigestService:
    """Service for retrieving the latest workspace digest.

    Fetches the most recent WorkspaceDigest from DigestRepository,
    then removes any suggestions the user has dismissed via
    DismissalRepository. Remaining suggestions are sorted by
    relevance_score desc.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize GetDigestService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(self, payload: GetDigestPayload) -> GetDigestResult:
        """Execute digest retrieval.

        Args:
            payload: The digest query payload.

        Returns:
            GetDigestResult with filtered suggestions.
        """
        from pilot_space.infrastructure.database.repositories.digest_repository import (
            DigestRepository,
            DismissalRepository,
        )

        digest_repo = DigestRepository(self._session)
        dismissal_repo = DismissalRepository(self._session)

        # Fetch latest digest
        digest = await digest_repo.get_latest_digest(payload.workspace_id)
        if digest is None:
            return GetDigestResult()

        # Get dismissed (entity_id, category) pairs for this user
        dismissed = await dismissal_repo.get_dismissed_entity_ids(
            payload.workspace_id,
            payload.user_id,
        )

        # Filter and convert suggestions
        suggestions = self._filter_suggestions(digest.suggestions, dismissed)

        # Sort by relevance descending
        suggestions.sort(key=lambda s: s.relevance_score, reverse=True)

        return GetDigestResult(
            generated_at=digest.generated_at,
            generated_by=digest.generated_by,
            suggestions=suggestions,
            suggestion_count=len(suggestions),
        )

    @staticmethod
    def _filter_suggestions(
        raw_suggestions: list[dict[str, Any]],
        dismissed: set[tuple[str, str]],
    ) -> list[DigestSuggestionItem]:
        """Filter raw JSONB suggestions, removing dismissed items.

        Args:
            raw_suggestions: Raw suggestion dicts from WorkspaceDigest.suggestions.
            dismissed: Set of (entity_id_hex, category) tuples to exclude.

        Returns:
            List of DigestSuggestionItem after filtering.
        """
        result: list[DigestSuggestionItem] = []
        for s in raw_suggestions:
            entity_id_str = str(s.get("entity_id", ""))
            category = s.get("category", "")

            # Skip if user dismissed this suggestion
            if (entity_id_str, category) in dismissed:
                continue

            # Skip suggestions with missing or invalid ID
            raw_id = s.get("id")
            if not raw_id:
                continue
            try:
                suggestion_id = UUID(str(raw_id))
            except ValueError:
                continue

            raw_project_id = s.get("project_id")
            project_id = UUID(str(raw_project_id)) if raw_project_id else None

            result.append(
                DigestSuggestionItem(
                    id=suggestion_id,
                    category=category,
                    title=s.get("title", ""),
                    description=s.get("description", ""),
                    entity_id=UUID(entity_id_str) if entity_id_str else None,
                    entity_type=s.get("entity_type"),
                    entity_identifier=s.get("entity_identifier"),
                    project_id=project_id,
                    project_name=s.get("project_name"),
                    action_type=s.get("action_type"),
                    action_label=s.get("action_label"),
                    action_url=s.get("action_url"),
                    relevance_score=float(s.get("relevance_score", 0.5)),
                )
            )
        return result


__all__ = [
    "DigestSuggestionItem",
    "GetDigestPayload",
    "GetDigestResult",
    "GetDigestService",
]
