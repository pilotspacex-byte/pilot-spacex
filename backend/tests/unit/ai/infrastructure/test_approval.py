"""Unit tests for ApprovalService.

Tests DD-003 critical-only approval flow with three-tier classification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
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
    """Mock SQLAlchemy async session."""
    return AsyncMock()


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

    def test_always_require_actions_never_auto_execute(
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
                assert approval_service.check_approval_required(
                    action, settings
                ), f"{action.value} should always require approval"

    def test_default_require_balanced_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify DEFAULT_REQUIRE actions behavior with balanced level."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Should require approval by default
        assert approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, settings
        )
        assert approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, settings
        )
        assert approval_service.check_approval_required(
            ActionType.PUBLISH_DOCS, settings
        )
        assert approval_service.check_approval_required(
            ActionType.POST_PR_COMMENTS, settings
        )

    def test_default_require_autonomous_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify DEFAULT_REQUIRE actions auto-execute with autonomous level."""
        settings = ProjectSettings(level=ApprovalLevel.AUTONOMOUS)

        # Should auto-execute with autonomous level
        assert not approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, settings
        )
        assert not approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, settings
        )

    def test_auto_execute_balanced_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify AUTO_EXECUTE actions auto-execute with balanced level."""
        settings = ProjectSettings(level=ApprovalLevel.BALANCED)

        # Should auto-execute
        assert not approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, settings
        )
        assert not approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, settings
        )
        assert not approval_service.check_approval_required(
            ActionType.AUTO_TRANSITION_STATE, settings
        )
        assert not approval_service.check_approval_required(
            ActionType.CREATE_ANNOTATION, settings
        )

    def test_auto_execute_conservative_level(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify AUTO_EXECUTE actions require approval with conservative level."""
        settings = ProjectSettings(level=ApprovalLevel.CONSERVATIVE)

        # Should require approval with conservative level
        assert approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, settings
        )
        assert approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, settings
        )

    def test_override_allows_auto_execute(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify overrides can enable auto-execute for DEFAULT_REQUIRE actions."""
        settings = ProjectSettings(
            level=ApprovalLevel.BALANCED,
            overrides={"create_sub_issues": True},  # True = auto-execute
        )

        # Override should allow auto-execute
        assert not approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, settings
        )

        # Other DEFAULT_REQUIRE actions still need approval
        assert approval_service.check_approval_required(
            ActionType.EXTRACT_ISSUES, settings
        )

    def test_override_requires_approval(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify overrides can require approval for AUTO_EXECUTE actions."""
        settings = ProjectSettings(
            level=ApprovalLevel.AUTONOMOUS,
            overrides={"suggest_labels": False},  # False = require approval
        )

        # Override should require approval
        assert approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, settings
        )

        # Other AUTO_EXECUTE actions still auto-execute
        assert not approval_service.check_approval_required(
            ActionType.SUGGEST_PRIORITY, settings
        )

    def test_no_settings_defaults_to_balanced(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify behavior when no settings provided defaults to balanced."""
        # DEFAULT_REQUIRE should require approval
        assert approval_service.check_approval_required(
            ActionType.CREATE_SUB_ISSUES, None
        )

        # AUTO_EXECUTE should auto-execute
        assert not approval_service.check_approval_required(
            ActionType.SUGGEST_LABELS, None
        )


class TestApprovalRequestCreation:
    """Test approval request creation."""

    @pytest.mark.asyncio
    async def test_create_request_with_defaults(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify approval request creation with default expiration."""
        before = datetime.now(UTC)

        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4()), "reason": "Duplicate"},
            requested_by_agent="DuplicateDetectorAgent",
        )

        after = datetime.now(UTC)

        # Verify request fields
        assert request.workspace_id == workspace_id
        assert request.action_type == ActionType.DELETE_ISSUE
        assert request.action_data["reason"] == "Duplicate"
        assert request.requested_by_agent == "DuplicateDetectorAgent"
        assert request.status == ApprovalStatus.PENDING
        assert request.resolved_at is None
        assert request.resolved_by is None

        # Verify timestamps
        assert before <= request.requested_at <= after
        assert request.expires_at is not None
        expected_expiration = request.requested_at + timedelta(hours=24)
        assert abs((request.expires_at - expected_expiration).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_create_request_with_custom_expiration(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify approval request creation with custom expiration."""
        custom_expiration = datetime.now(UTC) + timedelta(hours=48)

        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.MERGE_PR,
            action_data={"pr_number": 123, "repository": "owner/repo"},
            requested_by_agent="PRReviewAgent",
            expires_at=custom_expiration,
        )

        assert request.expires_at == custom_expiration

    @pytest.mark.asyncio
    async def test_create_request_empty_action_data_raises(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify error when creating request with empty action_data."""
        with pytest.raises(ValueError, match="action_data cannot be empty"):
            await approval_service.create_approval_request(
                workspace_id=workspace_id,
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
        # Create request
        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        before = datetime.now(UTC)

        # Approve request
        resolved = await approval_service.resolve(
            request_id=request.id,
            approved=True,
            resolved_by=user_id,
            resolution_comment="Confirmed duplicate",
        )

        after = datetime.now(UTC)

        # Verify resolution
        assert resolved.status == ApprovalStatus.APPROVED
        assert resolved.resolved_by == user_id
        assert resolved.resolution_comment == "Confirmed duplicate"
        assert before <= resolved.resolved_at <= after  # type: ignore[operator]

        # Verify original fields preserved
        assert resolved.id == request.id
        assert resolved.workspace_id == workspace_id
        assert resolved.action_type == ActionType.DELETE_ISSUE

    @pytest.mark.asyncio
    async def test_reject_request(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify request rejection."""
        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        resolved = await approval_service.resolve(
            request_id=request.id,
            approved=False,
            resolved_by=user_id,
            resolution_comment="Not a duplicate",
        )

        assert resolved.status == ApprovalStatus.REJECTED
        assert resolved.resolution_comment == "Not a duplicate"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_request_raises(
        self,
        approval_service: ApprovalService,
        user_id: uuid.UUID,
    ) -> None:
        """Verify error when resolving non-existent request."""
        fake_id = uuid.uuid4()

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
        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        # Resolve once
        await approval_service.resolve(
            request_id=request.id,
            approved=True,
            resolved_by=user_id,
        )

        # Try to resolve again
        with pytest.raises(ValueError, match="Cannot resolve request with status"):
            await approval_service.resolve(
                request_id=request.id,
                approved=False,
                resolved_by=user_id,
            )


class TestPendingRequestsQuery:
    """Test querying pending requests."""

    @pytest.mark.asyncio
    async def test_get_pending_for_workspace(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify fetching pending requests for workspace."""
        # Create multiple requests
        request1 = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "1"},
            requested_by_agent="Agent1",
        )

        request2 = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.MERGE_PR,
            action_data={"pr_number": 123},
            requested_by_agent="Agent2",
        )

        # Resolve one request
        await approval_service.resolve(
            request_id=request1.id,
            approved=True,
            resolved_by=user_id,
        )

        # Get pending requests
        pending = await approval_service.get_pending_for_workspace(workspace_id)

        # Should only return unresolved request
        assert len(pending) == 1
        assert pending[0].id == request2.id
        assert pending[0].status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_pending_sorted_by_requested_at(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify pending requests are sorted by requested_at descending."""
        # Create three requests
        request1 = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "1"},
            requested_by_agent="Agent1",
        )

        request2 = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "2"},
            requested_by_agent="Agent2",
        )

        request3 = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "3"},
            requested_by_agent="Agent3",
        )

        pending = await approval_service.get_pending_for_workspace(workspace_id)

        # Should be sorted newest first
        assert len(pending) == 3
        assert pending[0].id == request3.id
        assert pending[1].id == request2.id
        assert pending[2].id == request1.id

    @pytest.mark.asyncio
    async def test_get_pending_filters_by_workspace(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify pending requests filtered by workspace."""
        workspace1 = uuid.uuid4()
        workspace2 = uuid.uuid4()

        # Create requests in different workspaces
        await approval_service.create_approval_request(
            workspace_id=workspace1,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "1"},
            requested_by_agent="Agent1",
        )

        await approval_service.create_approval_request(
            workspace_id=workspace2,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": "2"},
            requested_by_agent="Agent2",
        )

        # Each workspace should only see its own requests
        pending1 = await approval_service.get_pending_for_workspace(workspace1)
        pending2 = await approval_service.get_pending_for_workspace(workspace2)

        assert len(pending1) == 1
        assert len(pending2) == 1
        assert pending1[0].workspace_id == workspace1
        assert pending2[0].workspace_id == workspace2


class TestRequestExpiration:
    """Test approval request expiration."""

    @pytest.mark.asyncio
    async def test_expire_stale_requests(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify stale requests are marked as expired."""
        # Create request with past expiration
        past_expiration = datetime.now(UTC) - timedelta(hours=1)

        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
            expires_at=past_expiration,
        )

        # Expire stale requests
        expired_count = await approval_service.expire_stale_requests()

        assert expired_count == 1

        # Verify request is expired
        expired_request = await approval_service.get_request(request.id)
        assert expired_request is not None
        assert expired_request.status == ApprovalStatus.EXPIRED
        assert expired_request.resolution_comment == "Request expired without response"

    @pytest.mark.asyncio
    async def test_expire_does_not_affect_future_requests(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify future requests are not expired."""
        future_expiration = datetime.now(UTC) + timedelta(hours=48)

        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
            expires_at=future_expiration,
        )

        expired_count = await approval_service.expire_stale_requests()

        assert expired_count == 0

        # Request should still be pending
        pending_request = await approval_service.get_request(request.id)
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
        past_expiration = datetime.now(UTC) - timedelta(hours=1)

        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
            expires_at=past_expiration,
        )

        # Resolve before expiration
        await approval_service.resolve(
            request_id=request.id,
            approved=True,
            resolved_by=user_id,
        )

        expired_count = await approval_service.expire_stale_requests()

        # Should not expire resolved request
        assert expired_count == 0

        resolved_request = await approval_service.get_request(request.id)
        assert resolved_request is not None
        assert resolved_request.status == ApprovalStatus.APPROVED


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_get_request(
        self,
        approval_service: ApprovalService,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify getting request by ID."""
        request = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            action_type=ActionType.DELETE_ISSUE,
            action_data={"issue_id": str(uuid.uuid4())},
            requested_by_agent="TestAgent",
        )

        fetched = await approval_service.get_request(request.id)

        assert fetched is not None
        assert fetched.id == request.id
        assert fetched.action_type == request.action_type

    @pytest.mark.asyncio
    async def test_get_nonexistent_request_returns_none(
        self,
        approval_service: ApprovalService,
    ) -> None:
        """Verify getting non-existent request returns None."""
        fake_id = uuid.uuid4()
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
            approval_service.get_action_classification(ActionType.SUGGEST_LABELS)
            == "auto_execute"
        )
