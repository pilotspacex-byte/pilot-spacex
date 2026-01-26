"""Test approval request expiration.

T323: Tests approval expiration prevents late resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.infrastructure.approval import (
    ActionType,
    ApprovalService,
    ApprovalStatus,
)


class MockApprovalRepository:
    """Mock repository for approval testing."""

    def __init__(self) -> None:
        """Initialize mock repository."""
        self._requests: dict[Any, dict[str, Any]] = {}

    async def resolve(
        self,
        request_id: Any,
        approved: bool,
        resolved_by: Any,
        resolution_note: str | None = None,
    ) -> Any | None:
        """Resolve an approval request.

        Args:
            request_id: Request ID.
            approved: Whether approved.
            resolved_by: User resolving.
            resolution_note: Optional note.

        Returns:
            Resolved request or None if not found/expired.
        """
        if request_id not in self._requests:
            return None

        request = self._requests[request_id]

        # Check expiration
        if request["expires_at"] < datetime.now(UTC):
            # Request expired
            raise ValueError(f"Approval request {request_id} has expired")

        # Update status
        request["status"] = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request["resolved_at"] = datetime.now(UTC)
        request["resolved_by"] = resolved_by
        request["resolution_note"] = resolution_note

        return MagicMock(
            id=request_id,
            status=request["status"],
            resolved_at=request["resolved_at"],
            resolved_by=resolved_by,
        )

    def add_request(
        self,
        request_id: Any,
        workspace_id: Any,
        user_id: Any,
        action_type: str,
        expires_at: datetime,
    ) -> None:
        """Add a mock request for testing.

        Args:
            request_id: Request ID.
            workspace_id: Workspace ID.
            user_id: User ID.
            action_type: Action type.
            expires_at: Expiration time.
        """
        self._requests[request_id] = {
            "id": request_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "action_type": action_type,
            "status": ApprovalStatus.PENDING,
            "expires_at": expires_at,
            "resolved_at": None,
            "resolved_by": None,
        }


class TestApprovalExpiration:
    """Test approval request expiration behavior."""

    @pytest.mark.asyncio
    async def test_expired_request_cannot_be_resolved(self) -> None:
        """Verify expired approval request cannot be resolved."""
        # Create mock session
        mock_session = AsyncMock()

        # Create repository
        mock_repo = MockApprovalRepository()

        # Create service with mock repository
        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        # Create an expired request
        request_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        resolved_by = uuid4()

        # Set expiration to 1 second ago
        expires_at = datetime.now(UTC) - timedelta(seconds=1)

        mock_repo.add_request(
            request_id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.CREATE_SUB_ISSUES.value,
            expires_at=expires_at,
        )

        # Attempt to resolve should raise error
        with pytest.raises(ValueError, match="expired"):
            await approval_service.resolve(
                request_id=request_id,
                approved=True,
                resolved_by=resolved_by,
            )

    @pytest.mark.asyncio
    async def test_valid_request_can_be_resolved(self) -> None:
        """Verify non-expired request can be resolved successfully."""
        mock_session = AsyncMock()
        mock_repo = MockApprovalRepository()

        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        # Create a valid request (expires in future)
        request_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        resolved_by = uuid4()

        expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_repo.add_request(
            request_id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.CREATE_SUB_ISSUES.value,
            expires_at=expires_at,
        )

        # Should resolve successfully
        await approval_service.resolve(
            request_id=request_id,
            approved=True,
            resolved_by=resolved_by,
            resolution_note="Looks good",
        )

        # Verify request was marked as approved
        request = mock_repo._requests[request_id]
        assert request["status"] == ApprovalStatus.APPROVED
        assert request["resolved_by"] == resolved_by

    @pytest.mark.asyncio
    async def test_request_expires_exactly_at_threshold(self) -> None:
        """Verify request that expired exactly now cannot be resolved."""
        mock_session = AsyncMock()
        mock_repo = MockApprovalRepository()

        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        request_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        resolved_by = uuid4()

        # Set expiration to exactly now (or slightly in past)
        expires_at = datetime.now(UTC) - timedelta(microseconds=100)

        mock_repo.add_request(
            request_id=request_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.EXTRACT_ISSUES.value,
            expires_at=expires_at,
        )

        with pytest.raises(ValueError, match="expired"):
            await approval_service.resolve(
                request_id=request_id,
                approved=False,
                resolved_by=resolved_by,
            )

    @pytest.mark.asyncio
    async def test_rejection_also_respects_expiration(self) -> None:
        """Verify rejection also checks expiration time."""
        mock_session = AsyncMock()
        mock_repo = MockApprovalRepository()

        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        request_id = uuid4()
        expires_at = datetime.now(UTC) - timedelta(hours=1)

        mock_repo.add_request(
            request_id=request_id,
            workspace_id=uuid4(),
            user_id=uuid4(),
            action_type=ActionType.POST_PR_COMMENTS.value,
            expires_at=expires_at,
        )

        # Rejection should also fail for expired request
        with pytest.raises(ValueError, match="expired"):
            await approval_service.resolve(
                request_id=request_id,
                approved=False,  # Rejecting
                resolved_by=uuid4(),
                resolution_note="Too late",
            )

    @pytest.mark.asyncio
    async def test_multiple_expired_requests(self) -> None:
        """Verify multiple expired requests all fail appropriately."""
        mock_session = AsyncMock()
        mock_repo = MockApprovalRepository()

        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        # Create multiple expired requests
        request_ids = [uuid4() for _ in range(3)]
        expires_at = datetime.now(UTC) - timedelta(minutes=5)

        for req_id in request_ids:
            mock_repo.add_request(
                request_id=req_id,
                workspace_id=uuid4(),
                user_id=uuid4(),
                action_type=ActionType.CREATE_SUB_ISSUES.value,
                expires_at=expires_at,
            )

        # All should fail
        for req_id in request_ids:
            with pytest.raises(ValueError, match="expired"):
                await approval_service.resolve(
                    request_id=req_id,
                    approved=True,
                    resolved_by=uuid4(),
                )

    @pytest.mark.asyncio
    async def test_request_about_to_expire_still_works(self) -> None:
        """Verify request expiring very soon still works if not past threshold."""
        mock_session = AsyncMock()
        mock_repo = MockApprovalRepository()

        approval_service = ApprovalService(
            session=mock_session,
            expiration_hours=24,
        )
        approval_service._repository = mock_repo

        request_id = uuid4()

        # Expires in 1 second (still future)
        expires_at = datetime.now(UTC) + timedelta(seconds=1)

        mock_repo.add_request(
            request_id=request_id,
            workspace_id=uuid4(),
            user_id=uuid4(),
            action_type=ActionType.SUGGEST_LABELS.value,
            expires_at=expires_at,
        )

        # Should still work
        await approval_service.resolve(
            request_id=request_id,
            approved=True,
            resolved_by=uuid4(),
        )

        request = mock_repo._requests[request_id]
        assert request["status"] == ApprovalStatus.APPROVED


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Provide mock database session."""
    return AsyncMock()
