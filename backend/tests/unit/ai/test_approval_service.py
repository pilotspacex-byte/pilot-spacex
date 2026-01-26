"""Unit tests for ApprovalService.

T077: Unit tests for approval service functionality.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.infrastructure.approval import (
    ActionType,
    ApprovalLevel,
    ApprovalService,
    ProjectSettings,
)
from pilot_space.infrastructure.database.models.ai_approval_request import (
    AIApprovalRequest,
    ApprovalStatus,
)


@pytest.fixture
def approval_service() -> ApprovalService:
    """Create approval service fixture.

    Returns:
        Configured ApprovalService instance with mock session.
    """
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    return ApprovalService(mock_session)


@pytest.fixture
def test_workspace() -> uuid.UUID:
    """Create test workspace ID.

    Returns:
        Workspace ID.
    """
    return uuid.uuid4()


@pytest.fixture
def test_user() -> uuid.UUID:
    """Create test user ID.

    Returns:
        User ID.
    """
    return uuid.uuid4()


@pytest.fixture
def test_approval(
    test_workspace: uuid.UUID,
    test_user: uuid.UUID,
) -> AIApprovalRequest:
    """Create test approval request.

    Args:
        test_workspace: Workspace ID.
        test_user: User ID.

    Returns:
        Created approval request.
    """
    return AIApprovalRequest(
        workspace_id=test_workspace,
        user_id=test_user,
        agent_name="test_agent",
        action_type="create_issues",
        payload={"issues": [{"title": "Test Issue"}]},
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )


class TestApprovalClassification:
    """Tests for action classification logic."""

    def test_always_require_actions(self, approval_service: ApprovalService) -> None:
        """Verify critical actions always require approval."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # All critical actions should require approval regardless of settings
        assert approval_service.check_approval_required(ActionType.DELETE_WORKSPACE, settings)
        assert approval_service.check_approval_required(ActionType.DELETE_PROJECT, settings)
        assert approval_service.check_approval_required(ActionType.DELETE_ISSUE, settings)
        assert approval_service.check_approval_required(ActionType.MERGE_PR, settings)

    def test_auto_execute_actions(self, approval_service: ApprovalService) -> None:
        """Verify safe actions auto-execute in balanced mode."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Safe actions should auto-execute in balanced mode
        assert not approval_service.check_approval_required(ActionType.SUGGEST_LABELS, settings)
        assert not approval_service.check_approval_required(ActionType.SUGGEST_PRIORITY, settings)
        assert not approval_service.check_approval_required(ActionType.CREATE_ANNOTATION, settings)

    def test_conservative_requires_all(self, approval_service: ApprovalService) -> None:
        """Verify conservative mode requires approval for all non-critical actions."""
        settings = ProjectSettings(level=ApprovalLevel.CONSERVATIVE)

        # Conservative mode should require approval even for safe actions
        assert approval_service.check_approval_required(ActionType.SUGGEST_LABELS, settings)
        assert approval_service.check_approval_required(ActionType.CREATE_SUB_ISSUES, settings)

    def test_autonomous_auto_executes_more(self, approval_service: ApprovalService) -> None:
        """Verify autonomous mode auto-executes more actions."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # Autonomous should auto-execute DEFAULT_REQUIRE actions
        assert not approval_service.check_approval_required(ActionType.CREATE_SUB_ISSUES, settings)
        assert not approval_service.check_approval_required(ActionType.EXTRACT_ISSUES, settings)

        # But still require approval for critical
        assert approval_service.check_approval_required(ActionType.DELETE_WORKSPACE, settings)

    def test_override_settings(self, approval_service: ApprovalService) -> None:
        """Verify action-specific overrides work."""
        settings = ProjectSettings(
            level=ApprovalLevel.BALANCED,
            overrides={
                "suggest_labels": False,  # Require approval even for safe action
                "create_sub_issues": True,  # Auto-execute instead of approve
            },
        )

        # Override should force approval for normally safe action
        assert approval_service.check_approval_required(ActionType.SUGGEST_LABELS, settings)

        # Override should allow auto-execute for normally approved action
        assert not approval_service.check_approval_required(ActionType.CREATE_SUB_ISSUES, settings)


class TestApprovalService:
    """Tests for ApprovalService CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_approval_request(
        self,
        approval_service: ApprovalService,
        test_workspace: uuid.UUID,
        test_user: uuid.UUID,
    ) -> None:
        """Verify approval request creation."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the database session operations
        mock_request = MagicMock()
        mock_request.id = uuid.uuid4()
        approval_service.session.add = MagicMock()
        approval_service.session.commit = AsyncMock()
        approval_service.session.refresh = AsyncMock()

        # Patch the model creation to return our mock
        with patch(
            "pilot_space.infrastructure.database.models.ai_approval_request.AIApprovalRequest",
            return_value=mock_request,
        ):
            request_id = await approval_service.create_approval_request(
                workspace_id=test_workspace,
                user_id=test_user,
                action_type=ActionType.EXTRACT_ISSUES,
                action_data={"issues": [{"title": "Test"}]},
                requested_by_agent="issue_extractor",
            )

            assert request_id is not None
            assert request_id == mock_request.id
            approval_service.session.add.assert_called_once()
            approval_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_empty_data_fails(
        self,
        approval_service: ApprovalService,
        test_workspace: uuid.UUID,
        test_user: uuid.UUID,
    ) -> None:
        """Verify empty action_data raises error."""
        with pytest.raises(ValueError, match="action_data cannot be empty"):
            await approval_service.create_approval_request(
                workspace_id=test_workspace,
                user_id=test_user,
                requested_by_agent="test_agent",
                action_type=ActionType.SUGGEST_LABELS,
                action_data={},
            )

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    async def test_list_requests(
        self,
        approval_service: ApprovalService,
        test_workspace: uuid.UUID,
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify listing requests for workspace."""
        requests, total = await approval_service.list_requests(
            workspace_id=test_workspace,
            limit=10,
            offset=0,
        )

        assert total >= 1
        assert len(requests) >= 1
        assert any(r.id == test_approval.id for r in requests)

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("test_approval")
    async def test_list_with_status_filter(
        self,
        approval_service: ApprovalService,
        test_workspace: uuid.UUID,
    ) -> None:
        """Verify status filtering works."""
        # Filter by pending
        requests, _total = await approval_service.list_requests(
            workspace_id=test_workspace,
            status="pending",
            limit=10,
            offset=0,
        )

        assert all(r.status == ApprovalStatus.PENDING for r in requests)

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("test_approval")
    async def test_count_pending(
        self,
        approval_service: ApprovalService,
        test_workspace: uuid.UUID,
    ) -> None:
        """Verify pending count."""
        count = await approval_service.count_pending(test_workspace)
        assert count >= 1

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    async def test_resolve_approval(
        self,
        approval_service: ApprovalService,
        test_approval: AIApprovalRequest,
        test_user: uuid.UUID,
    ) -> None:
        """Verify resolving an approval request."""
        await approval_service.resolve(
            approval_id=test_approval.id,
            resolved_by=test_user,
            approved=True,
            resolution_note="Looks good",
        )

        # Verify status updated
        updated = await approval_service.get_request(test_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.resolved_by == test_user
        assert updated.resolution_note == "Looks good"
        assert updated.resolved_at is not None

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    async def test_resolve_with_rejection(
        self,
        approval_service: ApprovalService,
        test_approval: AIApprovalRequest,
        test_user: uuid.UUID,
    ) -> None:
        """Verify rejecting an approval request."""
        await approval_service.resolve(
            approval_id=test_approval.id,
            resolved_by=test_user,
            approved=False,
            resolution_note="Not needed",
        )

        updated = await approval_service.get_request(test_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.REJECTED

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_fails(
        self,
        approval_service: ApprovalService,
        test_user: uuid.UUID,
    ) -> None:
        """Verify resolving nonexistent request fails."""
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Approval request not found"):
            await approval_service.resolve(
                approval_id=fake_id,
                resolved_by=test_user,
                approved=True,
            )

    @pytest.mark.skip(reason="Requires real database session")
    @pytest.mark.asyncio
    async def test_expire_stale_requests(
        self,
        approval_service: ApprovalService,
        db_session: AsyncSession,
        test_workspace: uuid.UUID,
        test_user: uuid.UUID,
    ) -> None:
        """Verify expiring stale requests."""
        # Create an already-expired request
        expired_approval = AIApprovalRequest(
            workspace_id=test_workspace,
            user_id=test_user,
            agent_name="test_agent",
            action_type="test_action",
            payload={"test": "data"},
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Already expired
        )
        db_session.add(expired_approval)
        await db_session.commit()
        await db_session.refresh(expired_approval)

        # Run expiration
        count = await approval_service.expire_stale_requests()

        assert count >= 1

        # Verify it was marked as expired
        updated = await approval_service.get_request(expired_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.EXPIRED
