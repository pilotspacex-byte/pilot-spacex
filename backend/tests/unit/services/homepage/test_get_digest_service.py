"""Unit tests for GetDigestService (H054).

Tests:
- No digest returns empty result
- Returns latest digest
- Filters dismissed suggestions
- Relevance ranking (sorted by relevance_score desc)
- Suggestion count matches filtered results

Note: Uses mocked repositories to avoid database complexity in unit tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from pilot_space.application.services.homepage.get_digest_service import (
    GetDigestPayload,
    GetDigestService,
)


@pytest.mark.asyncio
class TestGetDigestService:
    """Test suite for GetDigestService."""

    async def test_no_digest_returns_empty(self) -> None:
        """Empty workspace returns empty suggestions."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_session = AsyncMock()

        mock_digest_repo = AsyncMock()
        mock_digest_repo.get_latest_digest.return_value = None
        mock_dismissal_repo = AsyncMock()
        mock_dismissal_repo.get_dismissed_entity_ids.return_value = set()

        service = GetDigestService(
            mock_session,
            digest_repository=mock_digest_repo,
            dismissal_repository=mock_dismissal_repo,
        )
        payload = GetDigestPayload(workspace_id=workspace_id, user_id=user_id)

        result = await service.execute(payload)

        assert result.generated_at is None
        assert result.generated_by == "scheduled"
        assert len(result.suggestions) == 0
        assert result.suggestion_count == 0

    async def test_returns_latest_digest(self) -> None:
        """Returns the latest digest when multiple exist."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC)

        # Mock digest object
        mock_digest = AsyncMock()
        mock_digest.generated_at = now
        mock_digest.generated_by = "manual"
        mock_digest.suggestions = [
            {
                "id": str(uuid.uuid4()),
                "category": "unlinked_notes",
                "title": "New suggestion",
                "description": "This is new",
                "relevance_score": 0.8,
            }
        ]

        mock_digest_repo = AsyncMock()
        mock_digest_repo.get_latest_digest.return_value = mock_digest
        mock_dismissal_repo = AsyncMock()
        mock_dismissal_repo.get_dismissed_entity_ids.return_value = set()

        service = GetDigestService(
            mock_session,
            digest_repository=mock_digest_repo,
            dismissal_repository=mock_dismissal_repo,
        )
        payload = GetDigestPayload(workspace_id=workspace_id, user_id=user_id)

        result = await service.execute(payload)

        assert result.generated_at == now
        assert result.generated_by == "manual"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].title == "New suggestion"

    async def test_filters_dismissed_suggestions(self) -> None:
        """Dismissed suggestions are filtered out."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_session = AsyncMock()

        entity_id_1 = uuid.uuid4()
        entity_id_2 = uuid.uuid4()
        entity_id_3 = uuid.uuid4()

        mock_digest = AsyncMock()
        mock_digest.generated_at = datetime.now(tz=UTC)
        mock_digest.generated_by = "scheduled"
        mock_digest.suggestions = [
            {
                "id": str(uuid.uuid4()),
                "category": "stale_issues",
                "title": "Suggestion 1",
                "description": "First one",
                "entity_id": str(entity_id_1),
                "entity_type": "issue",
                "relevance_score": 0.9,
            },
            {
                "id": str(uuid.uuid4()),
                "category": "unlinked_notes",
                "title": "Suggestion 2",
                "description": "Second one",
                "entity_id": str(entity_id_2),
                "entity_type": "note",
                "relevance_score": 0.7,
            },
            {
                "id": str(uuid.uuid4()),
                "category": "review_needed",
                "title": "Suggestion 3",
                "description": "Third one",
                "entity_id": str(entity_id_3),
                "entity_type": "issue",
                "relevance_score": 0.6,
            },
        ]

        # Dismiss the second suggestion
        dismissed_set = {(str(entity_id_2), "unlinked_notes")}

        mock_digest_repo = AsyncMock()
        mock_digest_repo.get_latest_digest.return_value = mock_digest
        mock_dismissal_repo = AsyncMock()
        mock_dismissal_repo.get_dismissed_entity_ids.return_value = dismissed_set

        service = GetDigestService(
            mock_session,
            digest_repository=mock_digest_repo,
            dismissal_repository=mock_dismissal_repo,
        )
        payload = GetDigestPayload(workspace_id=workspace_id, user_id=user_id)

        result = await service.execute(payload)

        assert result.suggestion_count == 2
        assert len(result.suggestions) == 2

        titles = [s.title for s in result.suggestions]
        assert "Suggestion 1" in titles
        assert "Suggestion 2" not in titles
        assert "Suggestion 3" in titles

    async def test_relevance_ranking(self) -> None:
        """Suggestions are sorted by relevance_score desc."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_session = AsyncMock()

        mock_digest = AsyncMock()
        mock_digest.generated_at = datetime.now(tz=UTC)
        mock_digest.generated_by = "scheduled"
        mock_digest.suggestions = [
            {
                "id": str(uuid.uuid4()),
                "category": "stale_issues",
                "title": "Low priority",
                "description": "Low relevance",
                "relevance_score": 0.3,
            },
            {
                "id": str(uuid.uuid4()),
                "category": "unlinked_notes",
                "title": "High priority",
                "description": "High relevance",
                "relevance_score": 0.9,
            },
            {
                "id": str(uuid.uuid4()),
                "category": "review_needed",
                "title": "Medium priority",
                "description": "Medium relevance",
                "relevance_score": 0.6,
            },
        ]

        mock_digest_repo = AsyncMock()
        mock_digest_repo.get_latest_digest.return_value = mock_digest
        mock_dismissal_repo = AsyncMock()
        mock_dismissal_repo.get_dismissed_entity_ids.return_value = set()

        service = GetDigestService(
            mock_session,
            digest_repository=mock_digest_repo,
            dismissal_repository=mock_dismissal_repo,
        )
        payload = GetDigestPayload(workspace_id=workspace_id, user_id=user_id)

        result = await service.execute(payload)

        # Should be sorted by relevance_score desc
        assert result.suggestions[0].title == "High priority"
        assert result.suggestions[0].relevance_score == 0.9

        assert result.suggestions[1].title == "Medium priority"
        assert result.suggestions[1].relevance_score == 0.6

        assert result.suggestions[2].title == "Low priority"
        assert result.suggestions[2].relevance_score == 0.3

    async def test_suggestion_count(self) -> None:
        """Suggestion count matches filtered results."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_session = AsyncMock()

        mock_digest = AsyncMock()
        mock_digest.generated_at = datetime.now(tz=UTC)
        mock_digest.generated_by = "scheduled"
        mock_digest.suggestions = [
            {
                "id": str(uuid.uuid4()),
                "category": "stale_issues",
                "title": "Suggestion 1",
                "description": "First",
                "relevance_score": 0.8,
            },
            {
                "id": str(uuid.uuid4()),
                "category": "unlinked_notes",
                "title": "Suggestion 2",
                "description": "Second",
                "relevance_score": 0.7,
            },
        ]

        mock_digest_repo = AsyncMock()
        mock_digest_repo.get_latest_digest.return_value = mock_digest
        mock_dismissal_repo = AsyncMock()
        mock_dismissal_repo.get_dismissed_entity_ids.return_value = set()

        service = GetDigestService(
            mock_session,
            digest_repository=mock_digest_repo,
            dismissal_repository=mock_dismissal_repo,
        )
        payload = GetDigestPayload(workspace_id=workspace_id, user_id=user_id)

        result = await service.execute(payload)

        assert result.suggestion_count == 2
        assert len(result.suggestions) == 2
