"""Unit tests for ApprovalService.

T077: Unit tests for approval service functionality.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
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

    @pytest.mark.asyncio
    async def test_always_require_actions(self, approval_service: ApprovalService) -> None:
        """Verify critical actions always require approval."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # All critical actions should require approval regardless of settings
        assert await approval_service.check_approval_required(
            ActionType.DELETE_WORKSPACE, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.DELETE_PROJECT, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.DELETE_ISSUE, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.MERGE_PR, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_auto_execute_actions(self, approval_service: ApprovalService) -> None:
        """Verify safe actions auto-execute in balanced mode."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Safe actions should auto-execute in balanced mode
        assert not await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_ANNOTATION, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_conservative_requires_all(self, approval_service: ApprovalService) -> None:
        """Verify conservative mode requires approval for all non-critical actions."""
        settings = ProjectSettings(level=ApprovalLevel.CONSERVATIVE)

        # Conservative mode should require approval even for safe actions
        assert await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_autonomous_auto_executes_more(self, approval_service: ApprovalService) -> None:
        """Verify autonomous mode auto-executes more actions."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # Autonomous should auto-execute DEFAULT_REQUIRE actions
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, project_settings=settings
        )

        # But still require approval for critical
        assert await approval_service.check_approval_required(
            ActionType.DELETE_WORKSPACE, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_override_settings(self, approval_service: ApprovalService) -> None:
        """Verify action-specific overrides work."""
        settings = ProjectSettings(
            level=ApprovalLevel.BALANCED,
            overrides={
                "suggest_labels": False,  # Require approval even for safe action
                "create_sub_issues": True,  # Auto-execute instead of approve
            },
        )

        # Override should force approval for normally safe action
        assert await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )

        # Override should allow auto-execute for normally approved action
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )


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


# ============================================================================
# Real Database Tests
# ============================================================================


@pytest.mark.skipif(
    "sqlite" in os.getenv("TEST_DATABASE_URL", "sqlite"),
    reason="Requires PostgreSQL for JSONB columns and server defaults",
)
class TestApprovalServiceDB:
    """Tests for ApprovalService CRUD using real PostgreSQL sessions."""

    @pytest.fixture
    async def db_workspace_id(self, db_session_committed: AsyncSession) -> uuid.UUID:
        """Create a real workspace in the database."""
        from pilot_space.infrastructure.database.models import Workspace

        workspace = Workspace(name="Test Workspace", slug=f"test-ws-{uuid.uuid4().hex[:8]}")
        db_session_committed.add(workspace)
        await db_session_committed.commit()
        await db_session_committed.refresh(workspace)
        return workspace.id

    @pytest.fixture
    async def db_user_id(self, db_session_committed: AsyncSession) -> uuid.UUID:
        """Create a real user in the database."""
        from pilot_space.infrastructure.database.models import User

        user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com", full_name="Test User")
        db_session_committed.add(user)
        await db_session_committed.commit()
        await db_session_committed.refresh(user)
        return user.id

    @pytest.fixture
    def db_approval_service(self, db_session_committed: AsyncSession) -> ApprovalService:
        """Create ApprovalService backed by a real database session."""
        return ApprovalService(db_session_committed)

    @pytest.fixture
    async def persisted_approval(
        self,
        db_session_committed: AsyncSession,
        db_workspace_id: uuid.UUID,
        db_user_id: uuid.UUID,
    ) -> AIApprovalRequest:
        """Create and persist an approval request in the database."""
        approval = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=db_workspace_id,
            user_id=db_user_id,
            agent_name="test_agent",
            action_type="create_issues",
            description="Test action description",
            payload={"issues": [{"title": "Test Issue"}]},
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session_committed.add(approval)
        await db_session_committed.commit()
        await db_session_committed.refresh(approval)
        return approval

    @pytest.mark.asyncio
    async def test_list_requests(
        self,
        db_approval_service: ApprovalService,
        db_workspace_id: uuid.UUID,
        persisted_approval: AIApprovalRequest,
    ) -> None:
        """Verify listing requests for workspace."""
        requests, total = await db_approval_service.list_requests(
            workspace_id=db_workspace_id,
            limit=10,
            offset=0,
        )

        assert total >= 1
        assert len(requests) >= 1
        assert any(r.id == persisted_approval.id for r in requests)

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        db_approval_service: ApprovalService,
        db_workspace_id: uuid.UUID,
        persisted_approval: AIApprovalRequest,
    ) -> None:
        """Verify status filtering works."""
        requests, _total = await db_approval_service.list_requests(
            workspace_id=db_workspace_id,
            status="pending",
            limit=10,
            offset=0,
        )

        assert all(r.status == ApprovalStatus.PENDING for r in requests)

    @pytest.mark.asyncio
    async def test_count_pending(
        self,
        db_approval_service: ApprovalService,
        db_workspace_id: uuid.UUID,
        persisted_approval: AIApprovalRequest,
    ) -> None:
        """Verify pending count."""
        count = await db_approval_service.count_pending(db_workspace_id)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_resolve_approval(
        self,
        db_approval_service: ApprovalService,
        persisted_approval: AIApprovalRequest,
        db_user_id: uuid.UUID,
    ) -> None:
        """Verify resolving an approval request."""
        await db_approval_service.resolve(
            request_id=persisted_approval.id,
            resolved_by=db_user_id,
            approved=True,
            resolution_note="Looks good",
        )

        updated = await db_approval_service.get_request(persisted_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.resolved_by == db_user_id
        assert updated.resolution_note == "Looks good"
        assert updated.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_with_rejection(
        self,
        db_approval_service: ApprovalService,
        persisted_approval: AIApprovalRequest,
        db_user_id: uuid.UUID,
    ) -> None:
        """Verify rejecting an approval request."""
        await db_approval_service.resolve(
            request_id=persisted_approval.id,
            resolved_by=db_user_id,
            approved=False,
            resolution_note="Not needed",
        )

        updated = await db_approval_service.get_request(persisted_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_fails(
        self,
        db_approval_service: ApprovalService,
        db_user_id: uuid.UUID,
    ) -> None:
        """Verify resolving nonexistent request fails."""
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Approval request not found"):
            await db_approval_service.resolve(
                request_id=fake_id,
                resolved_by=db_user_id,
                approved=True,
            )

    @pytest.mark.asyncio
    async def test_expire_stale_requests(
        self,
        db_approval_service: ApprovalService,
        db_session_committed: AsyncSession,
        db_workspace_id: uuid.UUID,
        db_user_id: uuid.UUID,
    ) -> None:
        """Verify expiring stale requests."""
        expired_approval = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=db_workspace_id,
            user_id=db_user_id,
            agent_name="test_agent",
            action_type="test_action",
            description="Expired action description",
            payload={"test": "data"},
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session_committed.add(expired_approval)
        await db_session_committed.commit()
        await db_session_committed.refresh(expired_approval)

        count = await db_approval_service.expire_stale_requests()

        assert count >= 1

        updated = await db_approval_service.get_request(expired_approval.id)
        assert updated is not None
        assert updated.status == ApprovalStatus.EXPIRED
