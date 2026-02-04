"""Unit tests for ActivityService - activity_metadata attribute fix."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from pilot_space.application.services.issue.activity_service import (
    ActivityService,
    CreateActivityPayload,
)
from pilot_space.infrastructure.database.models.activity import (
    Activity,
    ActivityType,
)


@pytest.fixture
def activity_repo() -> AsyncMock:
    """Mock activity repository."""
    repo = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda entity: entity)
    return repo


@pytest.fixture
def activity_service(activity_repo: AsyncMock) -> ActivityService:
    """Activity service with mocked repository."""
    return ActivityService(activity_repository=activity_repo)


class TestActivityServiceCreate:
    """Tests for ActivityService.create method."""

    @pytest.mark.asyncio
    async def test_create_sets_activity_metadata(
        self,
        activity_service: ActivityService,
        activity_repo: AsyncMock,
    ) -> None:
        """Activity metadata should use activity_metadata attribute, not metadata."""
        metadata = {"key": "value", "enhancement_type": "test"}
        payload = CreateActivityPayload(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            activity_type=ActivityType.AI_ENHANCED,
            metadata=metadata,
        )

        result = await activity_service.create(payload)

        assert result.activity_metadata == metadata
        activity_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_comment_without_metadata(
        self,
        activity_service: ActivityService,
    ) -> None:
        """Comment creation should work without metadata."""
        payload = CreateActivityPayload(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            activity_type=ActivityType.COMMENT_ADDED,
            comment="Test comment",
        )

        result = await activity_service.create(payload)

        assert result.comment == "Test comment"
        assert result.activity_metadata is None

    @pytest.mark.asyncio
    async def test_add_comment(
        self,
        activity_service: ActivityService,
    ) -> None:
        """add_comment should create COMMENT_ADDED activity."""
        workspace_id = uuid.uuid4()
        issue_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        result = await activity_service.add_comment(
            workspace_id=workspace_id,
            issue_id=issue_id,
            actor_id=actor_id,
            comment_text="Hello world",
        )

        assert result.activity_type == ActivityType.COMMENT_ADDED
        assert result.comment == "Hello world"
        assert result.workspace_id == workspace_id
        assert result.issue_id == issue_id

    @pytest.mark.asyncio
    async def test_add_comment_strips_whitespace(
        self,
        activity_service: ActivityService,
    ) -> None:
        """add_comment should strip whitespace from comment text."""
        result = await activity_service.add_comment(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            comment_text="  trimmed  ",
        )

        assert result.comment == "trimmed"

    @pytest.mark.asyncio
    async def test_add_comment_rejects_empty(
        self,
        activity_service: ActivityService,
    ) -> None:
        """add_comment should reject empty comment text."""
        with pytest.raises(ValueError, match="Comment text is required"):
            await activity_service.add_comment(
                workspace_id=uuid.uuid4(),
                issue_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                comment_text="",
            )

    @pytest.mark.asyncio
    async def test_add_comment_rejects_whitespace_only(
        self,
        activity_service: ActivityService,
    ) -> None:
        """add_comment should reject whitespace-only comment text."""
        with pytest.raises(ValueError, match="Comment text is required"):
            await activity_service.add_comment(
                workspace_id=uuid.uuid4(),
                issue_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                comment_text="   ",
            )


class TestActivityModelMetadata:
    """Tests verifying Activity model uses activity_metadata attribute."""

    def test_activity_constructor_uses_activity_metadata(self) -> None:
        """Activity() should accept activity_metadata kwarg."""
        metadata = {"old_state_id": "abc", "new_state_id": "def"}
        activity = Activity(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            activity_type=ActivityType.STATE_CHANGED,
            activity_metadata=metadata,
        )

        assert activity.activity_metadata == metadata

    def test_activity_factory_create_for_issue_creation(self) -> None:
        """Factory method should set activity_metadata correctly."""
        activity = Activity.create_for_issue_creation(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            ai_enhanced=True,
        )

        assert activity.activity_metadata == {"ai_enhanced": True}

    def test_activity_factory_create_for_state_change(self) -> None:
        """Factory method should set activity_metadata with state IDs."""
        old_id = uuid.uuid4()
        new_id = uuid.uuid4()
        activity = Activity.create_for_state_change(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            old_state_id=old_id,
            old_state_name="Backlog",
            new_state_id=new_id,
            new_state_name="In Progress",
        )

        assert activity.activity_metadata == {
            "old_state_id": str(old_id),
            "new_state_id": str(new_id),
        }
