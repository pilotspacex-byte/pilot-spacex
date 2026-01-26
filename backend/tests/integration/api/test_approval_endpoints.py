"""Integration tests for approval queue endpoints.

T078: Integration tests for GET/POST approval endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.ai_approval_request import (
    AIApprovalRequest,
)


@pytest.fixture
async def test_workspace(db_session: AsyncSession) -> dict[str, Any]:
    """Create test workspace with ID and slug.

    Args:
        db_session: Database session.

    Returns:
        Workspace data dict.
    """
    from pilot_space.infrastructure.database.models.workspace import Workspace

    workspace = Workspace(
        name="Test Workspace Approval",
        slug="test-workspace-approval-integration",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return {"id": str(workspace.id), "slug": workspace.slug}


@pytest.fixture
async def test_user(db_session: AsyncSession) -> uuid.UUID:
    """Create test user.

    Args:
        db_session: Database session.

    Returns:
        User ID.
    """
    from pilot_space.infrastructure.database.models.user import User

    user = User(
        email="test-approval-api@example.com",
        name="Test API User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


@pytest.fixture
async def test_approval(
    db_session: AsyncSession,
    test_workspace: dict[str, Any],
    test_user: uuid.UUID,
) -> AIApprovalRequest:
    """Create test approval request.

    Args:
        db_session: Database session.
        test_workspace: Workspace data.
        test_user: User ID.

    Returns:
        Created approval request.
    """
    approval = AIApprovalRequest(
        workspace_id=uuid.UUID(test_workspace["id"]),
        user_id=test_user,
        agent_name="issue_extractor",
        action_type="extract_issues",
        payload={"issues": [{"title": "Test Issue", "description": "Test"}]},
        context={"note_id": "123"},
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)
    return approval


@pytest.fixture
def auth_headers(test_workspace: dict[str, Any]) -> dict[str, str]:
    """Create authorization headers for testing.

    Args:
        test_workspace: Workspace data.

    Returns:
        Headers dict with workspace ID.
    """
    # In real tests, would include proper JWT token
    # For now, using demo mode
    return {
        "X-Workspace-ID": test_workspace["id"],
        "Authorization": "Bearer demo-token",
    }


class TestListApprovals:
    """Tests for GET /ai/approvals endpoint."""

    @pytest.mark.asyncio
    async def test_list_pending_approvals(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify listing pending approval requests."""
        response = client.get(
            "/api/v1/ai/approvals",
            headers=auth_headers,
            params={"status": "pending"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "requests" in data
        assert "total" in data
        assert "pending_count" in data
        assert data["pending_count"] > 0

        # Verify request structure
        if data["requests"]:
            request_data = data["requests"][0]
            assert "id" in request_data
            assert "agent_name" in request_data
            assert "action_type" in request_data
            assert "status" in request_data
            assert "created_at" in request_data
            assert "expires_at" in request_data
            assert "requested_by" in request_data
            assert "context_preview" in request_data

    @pytest.mark.asyncio
    async def test_list_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify pagination works."""
        response = client.get(
            "/api/v1/ai/approvals",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["requests"]) <= 10

    @pytest.mark.asyncio
    async def test_list_without_workspace_fails(
        self,
        client: TestClient,
    ) -> None:
        """Verify request without workspace ID fails."""
        response = client.get(
            "/api/v1/ai/approvals",
            headers={"Authorization": "Bearer demo-token"},
        )

        assert response.status_code == 400


class TestGetApprovalDetail:
    """Tests for GET /ai/approvals/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_approval_details(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify getting full approval details."""
        response = client.get(
            f"/api/v1/ai/approvals/{test_approval.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_approval.id)
        assert data["agent_name"] == "issue_extractor"
        assert data["action_type"] == "extract_issues"
        assert data["status"] == "pending"
        assert "payload" in data
        assert "context" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_approval_fails(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify getting nonexistent approval returns 404."""
        fake_id = uuid.uuid4()
        response = client.get(
            f"/api/v1/ai/approvals/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestResolveApproval:
    """Tests for POST /ai/approvals/{id}/resolve endpoint."""

    @pytest.mark.asyncio
    async def test_approve_executes_action(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify approving executes the action."""
        response = client.post(
            f"/api/v1/ai/approvals/{test_approval.id}/resolve",
            headers=auth_headers,
            json={"approved": True, "note": "Looks good"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["approved"] is True
        assert "action_result" in data

    @pytest.mark.asyncio
    async def test_reject_discards_action(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
    ) -> None:
        """Verify rejecting discards the action."""
        response = client.post(
            f"/api/v1/ai/approvals/{test_approval.id}/resolve",
            headers=auth_headers,
            json={"approved": False, "note": "Not needed"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["approved"] is False
        assert data.get("action_result") is None

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_fails(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_approval: AIApprovalRequest,
        db_session: AsyncSession,
    ) -> None:
        """Verify resolving already-resolved request fails."""
        # First resolution
        response = client.post(
            f"/api/v1/ai/approvals/{test_approval.id}/resolve",
            headers=auth_headers,
            json={"approved": True},
        )
        assert response.status_code == 200

        # Second resolution should fail
        response = client.post(
            f"/api/v1/ai/approvals/{test_approval.id}/resolve",
            headers=auth_headers,
            json={"approved": False},
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_fails(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify resolving nonexistent request fails."""
        fake_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/ai/approvals/{fake_id}/resolve",
            headers=auth_headers,
            json={"approved": True},
        )

        assert response.status_code == 404


class TestExpirationJob:
    """Tests for approval expiration background job."""

    @pytest.mark.asyncio
    async def test_expire_pending_approvals(
        self,
        db_session: AsyncSession,
        test_workspace: dict[str, Any],
        test_user: uuid.UUID,
    ) -> None:
        """Verify expiration job marks old requests."""
        from pilot_space.infrastructure.jobs.expire_approvals import (
            expire_pending_approvals,
        )

        # Create an expired approval
        expired_approval = AIApprovalRequest(
            workspace_id=uuid.UUID(test_workspace["id"]),
            user_id=test_user,
            agent_name="test_agent",
            action_type="test_action",
            payload={"test": "data"},
            expires_at=datetime.now(UTC) - timedelta(hours=2),  # Expired 2 hours ago
        )
        db_session.add(expired_approval)
        await db_session.commit()

        # Run expiration job
        count = await expire_pending_approvals(db_session)

        assert count >= 1

        # Verify status updated
        await db_session.refresh(expired_approval)
        assert expired_approval.status.value == "expired"
        assert expired_approval.resolved_at is not None
        assert expired_approval.resolution_note == "Request expired without response"
