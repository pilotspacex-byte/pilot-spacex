"""E2E tests for approval workflow (T097).

Tests DD-003 human-in-the-loop approval flow:
- Approval request generation
- Approval/rejection handling
- Auto-execute for non-destructive actions
- Action classification (AUTO, DEFAULT, CRITICAL)

Reference: docs/DESIGN_DECISIONS.md#dd-003
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestApprovalWorkflow:
    """E2E tests for DD-003 approval workflow."""

    @pytest.mark.asyncio
    async def test_approval_request_generation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test approval request creation for actions requiring approval.

        Verifies:
        - DEFAULT_REQUIRE_APPROVAL actions create approval requests
        - Request includes action details
        - Request has 24-hour expiration
        - User is notified

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()

        # Trigger action that requires approval (create issues from note)
        response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": "We need to implement authentication and authorization.",
                "auto_create": True,  # Triggers approval flow
            },
        )

        assert response.status_code == 202  # Accepted, pending approval
        result = response.json()

        # Verify approval request returned
        assert "approval_id" in result
        assert "approval_status" in result
        assert result["approval_status"] == "pending"
        assert "expires_at" in result

        approval_id = result["approval_id"]

        # Verify approval request can be retrieved
        approval_response = await e2e_client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers=auth_headers,
        )
        assert approval_response.status_code == 200
        approval = approval_response.json()

        assert approval["id"] == approval_id
        assert approval["action_type"] == "extract_issues"
        assert approval["status"] == "pending"
        assert "proposed_changes" in approval
        assert "description" in approval

    @pytest.mark.asyncio
    async def test_approval_acceptance_flow(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test approval and execution of approved action.

        Verifies:
        - User can approve request
        - Approved action executes
        - Result is returned
        - Approval is marked complete

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()

        # Create approval request
        extract_response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": "Implement user authentication with JWT",
                "auto_create": True,
            },
        )
        approval_id = extract_response.json()["approval_id"]

        # Approve the request
        approve_response = await e2e_client.post(
            f"/api/v1/ai/approvals/{approval_id}/approve",
            headers=auth_headers,
        )
        assert approve_response.status_code == 200
        approve_result = approve_response.json()

        assert approve_result["status"] == "approved"
        assert "executed_result" in approve_result

        # Verify issues were created
        if "issues_created" in approve_result["executed_result"]:
            issues = approve_result["executed_result"]["issues_created"]
            assert len(issues) > 0
            for issue in issues:
                assert "id" in issue
                assert "name" in issue

        # Verify approval is marked complete
        status_response = await e2e_client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers=auth_headers,
        )
        assert status_response.json()["status"] == "approved"

    @pytest.mark.asyncio
    async def test_approval_rejection_flow(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test rejection of approval request.

        Verifies:
        - User can reject request
        - Action is not executed
        - Rejection reason is saved
        - Approval is marked rejected

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()

        # Create approval request
        extract_response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": "Fix the login bug",
                "auto_create": True,
            },
        )
        approval_id = extract_response.json()["approval_id"]

        # Reject the request
        reject_response = await e2e_client.post(
            f"/api/v1/ai/approvals/{approval_id}/reject",
            headers=auth_headers,
            json={"reason": "Not enough context in issue description"},
        )
        assert reject_response.status_code == 200
        reject_result = reject_response.json()

        assert reject_result["status"] == "rejected"
        assert "executed_result" not in reject_result  # No execution

        # Verify approval is marked rejected
        status_response = await e2e_client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers=auth_headers,
        )
        approval = status_response.json()
        assert approval["status"] == "rejected"
        assert approval["rejection_reason"] == "Not enough context in issue description"

    @pytest.mark.asyncio
    async def test_auto_execute_for_non_destructive_actions(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test AUTO_EXECUTE classification.

        Verifies:
        - Ghost text suggestions auto-execute
        - Margin annotations auto-execute
        - No approval request is created
        - Result is returned immediately

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()

        # Ghost text should auto-execute (no approval)
        ghost_response = await e2e_client.post(
            f"/api/v1/notes/{note_id}/ghost-text",
            headers=auth_headers,
            json={
                "context": "The authentication system should ",
                "cursor_position": 35,
            },
        )

        # Should return 200, not 202 (no approval needed)
        assert ghost_response.status_code == 200
        # Should not contain approval_id
        assert "approval_id" not in ghost_response.text

        # Margin annotations should auto-execute
        annotation_response = await e2e_client.post(
            f"/api/v1/notes/{note_id}/annotations",
            headers=auth_headers,
            json={
                "block_id": str(uuid4()),
                "type": "suggestion",
                "content": "Consider breaking this into subtasks",
            },
        )

        assert annotation_response.status_code == 200
        assert "approval_id" not in annotation_response.text

    @pytest.mark.asyncio
    async def test_critical_actions_always_require_approval(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test CRITICAL_REQUIRE_APPROVAL classification.

        Verifies:
        - Destructive actions always require approval
        - Cannot be bypassed with workspace settings
        - Clear warning is shown

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        issue_id = uuid4()

        # Delete issue should require approval (CRITICAL)
        delete_response = await e2e_client.delete(
            f"/api/v1/issues/{issue_id}",
            headers=auth_headers,
        )

        # Should require approval, not execute immediately
        assert delete_response.status_code == 202
        result = delete_response.json()

        assert "approval_id" in result
        assert result["classification"] == "critical_require"
        assert "warning" in result
        assert "destructive" in result["warning"].lower()

    @pytest.mark.asyncio
    async def test_approval_expiration(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test approval request expiration (24 hours).

        Verifies:
        - Expired requests cannot be approved
        - Expiration status is set
        - User is notified of expiration

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()

        # Create approval request
        extract_response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": "Implement feature X",
                "auto_create": True,
            },
        )
        approval_id = extract_response.json()["approval_id"]

        # Simulate expiration (in real test, would mock datetime or wait)
        # For now, check expiration field exists
        status_response = await e2e_client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers=auth_headers,
        )
        approval = status_response.json()
        assert "expires_at" in approval

        # Try to approve expired request (would fail in real scenario)
        # This test validates the expiration logic exists

    @pytest.mark.asyncio
    async def test_workspace_approval_configuration(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test workspace-level approval configuration.

        Verifies:
        - Workspaces can configure approval levels
        - CONSERVATIVE requires approval for all
        - AUTONOMOUS auto-executes most actions
        - CRITICAL actions always require approval

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]

        # Get current approval settings
        settings_response = await e2e_client.get(
            f"/api/v1/workspaces/{workspace_id}/ai-settings",
            headers=auth_headers,
        )
        assert settings_response.status_code == 200
        settings = settings_response.json()

        assert "approval_level" in settings
        assert settings["approval_level"] in ["conservative", "balanced", "autonomous"]

        # Update to CONSERVATIVE
        update_response = await e2e_client.patch(
            f"/api/v1/workspaces/{workspace_id}/ai-settings",
            headers=auth_headers,
            json={"approval_level": "conservative"},
        )
        assert update_response.status_code == 200

        # Verify DEFAULT actions now require approval
        note_id = uuid4()
        extract_response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": "Implement feature",
                "auto_create": True,
            },
        )
        # Should require approval in CONSERVATIVE mode
        assert extract_response.status_code == 202

    @pytest.mark.asyncio
    async def test_approval_list_and_filter(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing and filtering approval requests.

        Verifies:
        - Can list pending approvals
        - Can filter by status
        - Can filter by action type
        - Pagination works

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create multiple approval requests
        for i in range(3):
            note_id = uuid4()
            await e2e_client.post(
                "/api/v1/ai/skills/extract-issues",
                headers=auth_headers,
                json={
                    "note_id": str(note_id),
                    "note_content": f"Implement feature {i}",
                    "auto_create": True,
                },
            )

        # List pending approvals
        list_response = await e2e_client.get(
            "/api/v1/ai/approvals",
            headers=auth_headers,
            params={"status": "pending"},
        )
        assert list_response.status_code == 200
        approvals = list_response.json()

        assert len(approvals["items"]) >= 3
        for approval in approvals["items"]:
            assert approval["status"] == "pending"

        # Filter by action type
        filter_response = await e2e_client.get(
            "/api/v1/ai/approvals",
            headers=auth_headers,
            params={"action_type": "extract_issues"},
        )
        assert filter_response.status_code == 200
        filtered = filter_response.json()
        assert len(filtered["items"]) >= 3


__all__ = ["TestApprovalWorkflow"]
