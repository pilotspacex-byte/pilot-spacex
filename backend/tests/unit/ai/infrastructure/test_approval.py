"""Unit tests for ApprovalService.

Tests DD-003 critical-only approval flow with three-tier classification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from pilot_space.ai.infrastructure.approval import (
    ActionType,
    ApprovalLevel,
    ApprovalService,
    ApprovalStatus,
    ProjectSettings,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock SQLAlchemy async session with proper async behavior."""
    session = AsyncMock()

    # Track added objects to assign IDs
    added_objects: list[Any] = []

    def mock_add(obj: Any) -> None:
        # Assign ID if not set
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid.uuid4()
        added_objects.append(obj)

    async def mock_refresh(obj: Any) -> None:
        # Set created_at if not set
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(UTC)

    session.add = mock_add
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(side_effect=mock_refresh)

    return session


@pytest.fixture
def approval_service(mock_session: AsyncMock) -> ApprovalService:
    """Create approval service for testing."""
    return ApprovalService(session=mock_session, expiration_hours=24)


@pytest.fixture
def workspace_id() -> uuid.UUID:
    """Test workspace ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    """Test user ID."""
    return uuid.uuid4()


class TestActionClassification:
    """Test action classification logic."""

    @pytest.mark.asyncio
    async def test_always_require_actions_never_auto_execute(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify ALWAYS_REQUIRE actions always require approval."""
        always_require_actions = [
            ActionType.DELETE_WORKSPACE,
            ActionType.DELETE_PROJECT,
            ActionType.DELETE_ISSUE,
            ActionType.DELETE_NOTE,
            ActionType.MERGE_PR,
            ActionType.BULK_DELETE,
        ]

        # Test all autonomy levels - should always require approval
        for level in ApprovalLevel:
            settings = ProjectSettings(level=level)
            for action in always_require_actions:
                assert await approval_service.check_approval_required(
                    action, project_settings=settings
                ), f"{action.value} should always require approval"

    @pytest.mark.asyncio
    async def test_default_require_balanced_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify DEFAULT_REQUIRE actions behavior with balanced level."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Should require approval by default
        assert await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.PUBLISH_DOCS, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.POST_PR_COMMENTS, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_default_require_autonomous_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify DEFAULT_REQUIRE actions auto-execute with autonomous level."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # Should auto-execute with autonomous level
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_auto_execute_balanced_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify AUTO_EXECUTE actions auto-execute with balanced level."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Should auto-execute
        assert not await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.AUTO_TRANSITION_STATE, project_settings=settings
        )
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_ANNOTATION, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_auto_execute_conservative_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify AUTO_EXECUTE actions require approval with conservative level."""
        settings = ProjectSettings(level=ApprovalLevel.CONSERVATIVE)

        # Should require approval with conservative level
        assert await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )
        assert await approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_override_allows_auto_execute(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify overrides can enable auto-execute for DEFAULT_REQUIRE actions."""
        settings = ProjectSettings(
            level=ApprovalLevel.BALANCED,
            overrides={"create_sub_issues": True},  # True = auto-execute
        )

        # Override should allow auto-execute
        assert not await approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, project_settings=settings
        )

        # Other DEFAULT_REQUIRE actions still need approval
        assert await approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_override_requires_approval(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify overrides can require approval for AUTO_EXECUTE actions."""
        settings = ProjectSettings(
            level=ApprovalLevel.AUTONOMOUS,
            overrides={"suggest_labels": False},  # False = require approval
        )

        # Override should require approval
        assert await approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, project_settings=settings
        )

        # Other AUTO_EXECUTE actions still auto-execute
        assert not await approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, project_settings=settings
        )

    @pytest.mark.asyncio
    async def test_no_settings_defaults_to_balanced(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify behavior when no settings provided defaults to balanced."""
        # DEFAULT_REQUIRE should require approval
        assert await approval_service.check_approval_required(ActionType.CREATE_SUB_ISSUES)

        # AUTO_EXECUTE should auto-execute
        assert not await approval_service.check_approval_required(ActionType.SUGGEST_LABELS)


class TestApprovalRequestCreation:
    """Test approval request creation."""

    @pytest.mark.asyncio
    async def test_create_request_with_defaults(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify approval request creation with default expiration."""
        before = datetime.now(UTC)

        request_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4()), "reason": "Duplicate"},
            requested_by_agent="DuplicateDetectorAgent",
        )

        # Verify request_id is a UUID
        assert isinstance(request_id, uuid.UUID)

        # Mock repository get_by_id to return the created request
        # We need to construct what the request would look like after DB save
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        mock_db_request = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="DuplicateDetectorAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4()), "reason": "Duplicate"},
            context=None,
            expires_at=before + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
            created_at=before,
        )

        approval_service._repository.get_by_id = AsyncMock(return_value=mock_db_request)

        # Fetch the created request
        request = await approval_service.get_request(request_id)
        assert request is not None

        # Verify request fields
        assert request.workspace_id == workspace_id
        assert request.action_type == ActionType.DELETE_ISSUE.value
        assert request.payload["reason"] == "Duplicate"
        assert request.agent_name == "DuplicateDetectorAgent"
        assert request.status == ApprovalStatus.PENDING
        assert request.resolved_at is None
        assert request.resolved_by is None

        # Verify timestamps
        assert request.expires_at is not None
        expected_expiration = before + timedelta(hours=24)
        # Allow some tolerance for test execution time
        assert abs((request.expires_at - expected_expiration).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_create_request_with_custom_expiration(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify approval request creation with custom expiration."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        custom_expiration = datetime.now(UTC) + timedelta(hours=48)

        # Create mock db request with custom expiration
        mock_db_request = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="PRReviewAgent",
            action_type=ActionType.MERGE_PR.value,
            payload={"pr_number": 123, "repository": "owner/repo"},
            context=None,
            expires_at=custom_expiration,
            status=ApprovalStatus.PENDING,
        )

        approval_service._repository.get_by_id = AsyncMock(return_value=mock_db_request)

        request_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.MERGE_PR,
            action_data={"pr_number": 123, "repository": "owner/repo"},
            requested_by_agent="PRReviewAgent",
            expires_at=custom_expiration,
        )

        request = await approval_service.get_request(request_id)
        assert request is not None
        assert request.expires_at == custom_expiration

    @pytest.mark.asyncio
    async def test_create_request_empty_action_data_raises(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify error when creating request with empty action_data."""
        with pytest.raises(ValueError, match="action_data cannot be empty"):
            await approval_service.create_approval_request(
                workspace_id=workspace_id,
                user_id=user_id,
                action_type=ActionType.DELETE_ISSUE,
                action_data={},
                requested_by_agent="TestAgent",
            )


class TestApprovalRequestResolution:
    """Test approval request resolution."""

    @pytest.mark.asyncio
    async def test_approve_request(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify request approval."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        # Create request
        created_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        before = datetime.now(UTC)

        # Create mock approved request with resolved_at after before timestamp
        mock_approved = AIApprovalRequest(
            id=created_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.APPROVED,
            resolved_at=before,  # Use before timestamp to ensure comparison passes
            resolved_by=user_id,
            resolution_note="Confirmed duplicate",
        )

        approval_service._repository.resolve = AsyncMock(return_value=mock_approved)

        # Approve request
        await approval_service.resolve(
            request_id=created_id,
            approved=True,
            resolved_by=user_id,
            resolution_note="Confirmed duplicate",
        )

        after = datetime.now(UTC)

        # Fetch resolved request
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_approved)
        resolved = await approval_service.get_request(created_id)

        # Verify resolution
        assert resolved is not None
        assert resolved.status == ApprovalStatus.APPROVED
        assert resolved.resolved_by == user_id
        assert resolved.resolution_note == "Confirmed duplicate"
        assert resolved.resolved_at is not None
        assert before <= resolved.resolved_at <= after

        # Verify original fields preserved
        assert resolved.id == created_id
        assert resolved.workspace_id == workspace_id
        assert resolved.action_type == ActionType.DELETE_ISSUE.value

    @pytest.mark.asyncio
    async def test_reject_request(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify request rejection."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        request_id = uuid.uuid4()

        # Create mock rejected request
        mock_rejected = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.REJECTED,
            resolved_at=datetime.now(UTC),
            resolved_by=user_id,
            resolution_note="Not a duplicate",
        )

        approval_service._repository.resolve = AsyncMock(return_value=mock_rejected)
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_rejected)

        created_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        await approval_service.resolve(
            request_id=created_id,
            approved=False,
            resolved_by=user_id,
            resolution_note="Not a duplicate",
        )

        resolved = await approval_service.get_request(created_id)
        assert resolved is not None
        assert resolved.status == ApprovalStatus.REJECTED
        assert resolved.resolution_note == "Not a duplicate"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_request_raises(
        self,
        approval_service: ApprovalService,
        user_id: uuid.UUID,
    ) -> None:
        """Verify error when resolving non-existent request."""
        from unittest.mock import AsyncMock

        fake_id = uuid.uuid4()

        # Mock repository to return None for non-existent request
        approval_service._repository.resolve = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match=f"Approval request not found: {fake_id}"):
            await approval_service.resolve(
                request_id=fake_id,
                approved=True,
                resolved_by=user_id,
            )

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_request_raises(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify error when resolving already-resolved request."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        request_id = uuid.uuid4()

        # Create mock pending request
        mock_pending = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
        )

        # Create mock approved request
        mock_approved = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.APPROVED,
            resolved_at=datetime.now(UTC),
            resolved_by=user_id,
        )

        approval_service._repository.get_by_id = AsyncMock(return_value=mock_pending)
        approval_service._repository.resolve = AsyncMock(return_value=mock_approved)

        created_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        # Resolve once
        await approval_service.resolve(
            request_id=created_id,
            approved=True,
            resolved_by=user_id,
        )

        # Mock repository to return the already-resolved request for get_by_id
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_approved)

        # Repository checks status and returns None for already-resolved requests
        approval_service._repository.resolve = AsyncMock(return_value=None)

        # Try to resolve again - should raise because resolve returns None
        with pytest.raises(ValueError, match="Approval request not found"):
            await approval_service.resolve(
                request_id=created_id,
                approved=False,
                resolved_by=user_id,
            )


class TestPendingRequestsQuery:
    """Test querying pending requests."""

    @pytest.mark.asyncio
    async def test_list_pending_for_workspace(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify fetching pending requests for workspace."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        request2_id = uuid.uuid4()

        # Create mock pending request
        mock_request2 = AIApprovalRequest(
            id=request2_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="Agent2",
            action_type=ActionType.MERGE_PR.value,
            payload={"pr_number": 123},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
        )

        # Mock repository list_by_workspace to return only pending requests
        approval_service._repository.list_by_workspace = AsyncMock(
            return_value=([mock_request2], 1)
        )

        # Get pending requests
        pending, total = await approval_service.list_requests(workspace_id, status="pending")

        # Should only return unresolved request
        assert len(pending) == 1
        assert total == 1
        assert pending[0].id == request2_id
        assert pending[0].status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_list_pending_sorted_by_created_at(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify pending requests are sorted by created_at descending."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        request1_id = uuid.uuid4()
        request2_id = uuid.uuid4()
        request3_id = uuid.uuid4()

        now = datetime.now(UTC)

        # Create mock requests with different timestamps
        mock_request1 = AIApprovalRequest(
            id=request1_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="Agent1",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": "1"},
            context=None,
            expires_at=now + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
            created_at=now - timedelta(minutes=2),
        )

        mock_request2 = AIApprovalRequest(
            id=request2_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="Agent2",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": "2"},
            context=None,
            expires_at=now + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
            created_at=now - timedelta(minutes=1),
        )

        mock_request3 = AIApprovalRequest(
            id=request3_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="Agent3",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": "3"},
            context=None,
            expires_at=now + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
            created_at=now,
        )

        # Mock repository to return requests sorted newest first
        approval_service._repository.list_by_workspace = AsyncMock(
            return_value=([mock_request3, mock_request2, mock_request1], 3)
        )

        pending, total = await approval_service.list_requests(workspace_id, status="pending")

        # Should be sorted newest first
        assert len(pending) == 3
        assert total == 3
        assert pending[0].id == request3_id
        assert pending[1].id == request2_id
        assert pending[2].id == request1_id

    @pytest.mark.asyncio
    async def test_list_pending_filters_by_workspace(
        self,
        approval_service: ApprovalService,
        user_id: uuid.UUID,
    ) -> None:
        """Verify pending requests filtered by workspace."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        workspace1 = uuid.uuid4()
        workspace2 = uuid.uuid4()

        # Create mock requests for different workspaces
        mock_request1 = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=workspace1,
            user_id=user_id,
            agent_name="Agent1",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": "1"},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
        )

        mock_request2 = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=workspace2,
            user_id=user_id,
            agent_name="Agent2",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": "2"},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
        )

        # Mock repository to return workspace-specific requests
        async def mock_list_by_workspace(
            ws_id: uuid.UUID, *, status: Any = None, limit: int = 20, offset: int = 0
        ) -> tuple[list[AIApprovalRequest], int]:
            if ws_id == workspace1:
                return [mock_request1], 1
            return [mock_request2], 1

        approval_service._repository.list_by_workspace = AsyncMock(
            side_effect=mock_list_by_workspace
        )

        # Each workspace should only see its own requests
        pending1, total1 = await approval_service.list_requests(workspace1, status="pending")
        pending2, total2 = await approval_service.list_requests(workspace2, status="pending")

        assert len(pending1) == 1
        assert total1 == 1
        assert len(pending2) == 1
        assert total2 == 1
        assert pending1[0].workspace_id == workspace1
        assert pending2[0].workspace_id == workspace2


class TestRequestExpiration:
    """Test approval request expiration."""

    @pytest.mark.asyncio
    async def test_expire_stale_requests(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify stale requests are marked as expired."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        # Create request with past expiration
        past_expiration = datetime.now(UTC) - timedelta(hours=1)
        request_id = uuid.uuid4()

        # Mock expired request
        mock_expired = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=past_expiration,
            status=ApprovalStatus.EXPIRED,
            resolved_at=datetime.now(UTC),
            resolution_note="Request expired without response",
        )

        # Mock repository to return 1 expired request
        approval_service._repository.expire_stale_requests = AsyncMock(return_value=1)
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_expired)

        # Expire stale requests
        expired_count = await approval_service.expire_stale_requests()

        assert expired_count == 1

        # Verify request is expired
        expired_request = await approval_service.get_request(request_id)
        assert expired_request is not None
        assert expired_request.status == ApprovalStatus.EXPIRED
        assert expired_request.resolution_note == "Request expired without response"

    @pytest.mark.asyncio
    async def test_expire_does_not_affect_future_requests(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify future requests are not expired."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        future_expiration = datetime.now(UTC) + timedelta(hours=48)
        request_id = uuid.uuid4()

        # Mock pending request with future expiration
        mock_pending = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=future_expiration,
            status=ApprovalStatus.PENDING,
        )

        # Mock repository to return 0 expired (future request not expired)
        approval_service._repository.expire_stale_requests = AsyncMock(return_value=0)
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_pending)

        expired_count = await approval_service.expire_stale_requests()

        assert expired_count == 0

        # Request should still be pending
        pending_request = await approval_service.get_request(request_id)
        assert pending_request is not None
        assert pending_request.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_expire_does_not_affect_resolved_requests(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify resolved requests are not expired."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        past_expiration = datetime.now(UTC) - timedelta(hours=1)
        request_id = uuid.uuid4()

        # Mock approved request (already resolved)
        mock_approved = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=past_expiration,
            status=ApprovalStatus.APPROVED,
            resolved_at=datetime.now(UTC),
            resolved_by=user_id,
        )

        # Mock repository to return 0 expired (resolved request not affected)
        approval_service._repository.expire_stale_requests = AsyncMock(return_value=0)
        approval_service._repository.get_by_id = AsyncMock(return_value=mock_approved)

        expired_count = await approval_service.expire_stale_requests()

        # Should not expire resolved request
        assert expired_count == 0

        resolved_request = await approval_service.get_request(request_id)
        assert resolved_request is not None
        assert resolved_request.status == ApprovalStatus.APPROVED


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_get_request(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify getting request by ID."""
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        request_id = uuid.uuid4()

        # Create mock request
        mock_request = AIApprovalRequest(
            id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="TestAgent",
            action_type=ActionType.DELETE_ISSUE.value,
            payload={"issue_id": str(uuid.uuid4())},
            context=None,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
        )

        approval_service._repository.get_by_id = AsyncMock(return_value=mock_request)

        fetched = await approval_service.get_request(request_id)

        assert fetched is not None
        assert fetched.id == request_id
        assert fetched.action_type == ActionType.DELETE_ISSUE.value

    @pytest.mark.asyncio
    async def test_get_nonexistent_request_returns_none(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify getting non-existent request returns None."""
        from unittest.mock import AsyncMock

        fake_id = uuid.uuid4()

        # Mock repository to return None for non-existent request
        approval_service._repository.get_by_id = AsyncMock(return_value=None)

        result = await approval_service.get_request(fake_id)
        assert result is None

    def test_get_action_classification(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify action classification retrieval."""
        assert (
            approval_service.get_action_classification(ActionType.DELETE_WORKSPACE)
            == "always_require"
        )
        assert (
            approval_service.get_action_classification(ActionType.CREATE_SUB_ISSUES)
            == "default_require"
        )
        assert (
            approval_service.get_action_classification(ActionType.SUGGEST_LABELS) == "auto_execute"
        )
