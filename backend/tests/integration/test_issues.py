"""Integration tests for issue management.

Tests issue CRUD operations, state machine transitions, AI enhancement,
duplicate detection, activity logging, and filtering/pagination.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from pilot_space.domain.models import Activity, Issue, Label

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.domain.models import Project, User


pytestmark = pytest.mark.asyncio


class TestIssueCRUD:
    """Test issue CRUD operations."""

    @pytest.mark.usefixtures("_db_session", "_test_workspace")
    async def test_create_issue_success(
        self,
        client: AsyncClient,
        authenticated_user: User,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating an issue with valid data."""
        payload = {
            "title": "Fix authentication bug",
            "description": "Users cannot log in with Google OAuth",
            "project_id": str(test_project.id),
            "priority": "high",
        }

        response = await client.post(
            "/api/v1/issues",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["state"] == "backlog"  # Default state
        assert data["identifier"] is not None  # Auto-generated
        assert data["creator_id"] == str(authenticated_user.id)

    async def test_create_issue_without_title_fails(
        self,
        client: AsyncClient,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that creating an issue without title fails."""
        payload = {
            "description": "Missing title",
            "project_id": str(test_project.id),
        }

        response = await client.post(
            "/api/v1/issues",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_get_issue_by_id(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test retrieving an issue by ID."""
        response = await client.get(
            f"/api/v1/issues/{test_issue.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_issue.id)
        assert data["title"] == test_issue.title

    async def test_get_issue_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test retrieving non-existent issue returns 404."""
        fake_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/issues/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_issue_title(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating issue title."""
        payload = {"title": "Updated Title"}

        response = await client.patch(
            f"/api/v1/issues/{test_issue.id}",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    async def test_delete_issue_soft_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that deleting an issue performs soft delete."""
        response = await client.delete(
            f"/api/v1/issues/{test_issue.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify soft deleted
        stmt = select(Issue).where(Issue.id == test_issue.id)
        result = await db_session.execute(stmt)
        issue = result.scalar_one_or_none()
        assert issue is not None
        assert issue.deleted_at is not None


class TestIssueStateMachine:
    """Test issue state machine transitions."""

    @pytest.mark.parametrize(
        ("from_state", "to_state", "expected_success"),
        [
            ("backlog", "todo", True),
            ("todo", "in_progress", True),
            ("in_progress", "in_review", True),
            ("in_review", "done", True),
            ("done", "cancelled", True),
            ("backlog", "done", False),  # Invalid transition
            ("done", "backlog", False),  # Invalid transition
            ("cancelled", "todo", True),  # Reopening
        ],
    )
    async def test_state_transitions(
        self,
        client: AsyncClient,
        test_issue_factory,
        auth_headers: dict[str, str],
        from_state: str,
        to_state: str,
        expected_success: bool,
    ) -> None:
        """Test valid and invalid state transitions."""
        issue = await test_issue_factory(state=from_state)

        response = await client.patch(
            f"/api/v1/issues/{issue.id}",
            json={"state": to_state},
            headers=auth_headers,
        )

        if expected_success:
            assert response.status_code == 200
            assert response.json()["state"] == to_state
        else:
            assert response.status_code in (400, 422)

    async def test_state_transition_creates_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that state transitions create activity logs."""
        response = await client.patch(
            f"/api/v1/issues/{test_issue.id}",
            json={"state": "todo"},
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Check activity was created
        stmt = select(Activity).where(
            Activity.entity_id == test_issue.id,
            Activity.action == "state_changed",
        )
        result = await db_session.execute(stmt)
        activity = result.scalar_one_or_none()
        assert activity is not None


class TestIssueAIEnhancement:
    """Test AI-enhanced issue features."""

    async def test_create_issue_with_ai_enhancement(
        self,
        client: AsyncClient,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test creating an issue with AI enhancement enabled."""
        with patch(
            "pilot_space.ai.agents.issue_enhancer_agent.IssueEnhancerAgent.enhance"
        ) as mock_enhance:
            mock_enhance.return_value = AsyncMock(
                return_value={
                    "enhanced_description": "Enhanced: Users cannot log in...",
                    "suggested_labels": ["bug", "auth"],
                    "estimated_complexity": "medium",
                }
            )

            payload = {
                "title": "Fix authentication bug",
                "description": "Users cannot log in",
                "project_id": str(test_project.id),
                "enhance_with_ai": True,
            }

            response = await client.post(
                "/api/v1/issues",
                json=payload,
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert "ai_metadata" in data

    async def test_enhance_existing_issue(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test enhancing an existing issue with AI."""
        with patch(
            "pilot_space.ai.agents.issue_enhancer_agent.IssueEnhancerAgent.enhance"
        ) as mock_enhance:
            mock_enhance.return_value = {
                "enhanced_description": "Enhanced description",
                "suggested_labels": ["enhancement"],
            }

            response = await client.post(
                f"/api/v1/issues/{test_issue.id}/enhance",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestIssueDuplicateDetection:
    """Test duplicate issue detection."""

    async def test_detect_duplicate_on_create(
        self,
        client: AsyncClient,
        test_issue: Issue,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test duplicate detection when creating similar issue."""
        with patch(
            "pilot_space.ai.agents.duplicate_detector_agent.DuplicateDetectorAgent.detect"
        ) as mock_detect:
            mock_detect.return_value = {
                "is_duplicate": True,
                "confidence": 0.92,
                "similar_issues": [{"id": str(test_issue.id), "similarity": 0.92}],
            }

            payload = {
                "title": test_issue.title,  # Same title
                "description": test_issue.description,
                "project_id": str(test_project.id),
            }

            response = await client.post(
                "/api/v1/issues",
                json=payload,
                headers=auth_headers,
            )

            # Should still create but include duplicate warning
            assert response.status_code == 201
            data = response.json()
            assert "duplicate_warning" in data or "similar_issues" in data

    async def test_find_similar_issues(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test finding similar issues endpoint."""
        with patch(
            "pilot_space.ai.agents.duplicate_detector_agent.DuplicateDetectorAgent.find_similar"
        ) as mock_find:
            mock_find.return_value = [
                {"id": str(test_issue.id), "similarity": 0.85, "title": test_issue.title}
            ]

            response = await client.post(
                "/api/v1/issues/find-similar",
                json={"title": "Similar issue", "description": "Similar description"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestIssueActivityLogging:
    """Test activity logging for issues."""

    async def test_create_issue_logs_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that creating an issue logs activity."""
        payload = {
            "title": "New issue for activity test",
            "project_id": str(test_project.id),
        }

        response = await client.post(
            "/api/v1/issues",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        issue_id = response.json()["id"]

        # Check activity log
        stmt = select(Activity).where(
            Activity.entity_id == uuid.UUID(issue_id),
            Activity.action == "created",
        )
        result = await db_session.execute(stmt)
        activity = result.scalar_one_or_none()
        assert activity is not None

    async def test_get_issue_activities(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test retrieving activity log for an issue."""
        response = await client.get(
            f"/api/v1/issues/{test_issue.id}/activities",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.usefixtures("authenticated_user")
    async def test_activity_includes_user_info(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that activity includes user information."""
        # Make a change to create activity
        await client.patch(
            f"/api/v1/issues/{test_issue.id}",
            json={"title": "Updated for activity test"},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/issues/{test_issue.id}/activities",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        if data:
            assert "actor_id" in data[0] or "user" in data[0]


class TestIssueFilteringAndPagination:
    """Test issue filtering and pagination."""

    @pytest.mark.usefixtures("test_issue")
    async def test_list_issues_by_project(
        self,
        client: AsyncClient,
        test_project: Project,
        auth_headers: dict[str, str],
    ) -> None:
        """Test filtering issues by project."""
        response = await client.get(
            f"/api/v1/issues?project_id={test_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.usefixtures("test_issue")
    async def test_list_issues_by_state(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test filtering issues by state."""
        response = await client.get(
            "/api/v1/issues?state=backlog",
            headers=auth_headers,
        )

        assert response.status_code == 200

    async def test_list_issues_by_assignee(
        self,
        client: AsyncClient,
        authenticated_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test filtering issues by assignee."""
        response = await client.get(
            f"/api/v1/issues?assignee_id={authenticated_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    async def test_list_issues_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test pagination parameters."""
        response = await client.get(
            "/api/v1/issues?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        if "items" in data:
            assert len(data["items"]) <= 10

    async def test_list_issues_sorting(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test sorting issues."""
        response = await client.get(
            "/api/v1/issues?sort_by=created_at&sort_order=desc",
            headers=auth_headers,
        )

        assert response.status_code == 200

    async def test_search_issues_by_title(
        self,
        client: AsyncClient,
        test_issue: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test searching issues by title."""
        response = await client.get(
            f"/api/v1/issues?search={test_issue.title[:10]}",
            headers=auth_headers,
        )

        assert response.status_code == 200


class TestIssueLabels:
    """Test issue label management."""

    async def test_add_labels_to_issue(
        self,
        client: AsyncClient,
        test_issue: Issue,
        test_label: Label,
        auth_headers: dict[str, str],
    ) -> None:
        """Test adding labels to an issue."""
        response = await client.post(
            f"/api/v1/issues/{test_issue.id}/labels",
            json={"label_ids": [str(test_label.id)]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert any(label["id"] == str(test_label.id) for label in data.get("labels", []))

    async def test_remove_label_from_issue(
        self,
        client: AsyncClient,
        test_issue_with_labels: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test removing a label from an issue."""
        label_id = test_issue_with_labels.labels[0].id

        response = await client.delete(
            f"/api/v1/issues/{test_issue_with_labels.id}/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200


class TestIssueAssignment:
    """Test issue assignment."""

    async def test_assign_issue_to_user(
        self,
        client: AsyncClient,
        test_issue: Issue,
        authenticated_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test assigning an issue to a user."""
        response = await client.patch(
            f"/api/v1/issues/{test_issue.id}",
            json={"assignee_id": str(authenticated_user.id)},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assignee_id"] == str(authenticated_user.id)

    async def test_unassign_issue(
        self,
        client: AsyncClient,
        test_issue_with_assignee: Issue,
        auth_headers: dict[str, str],
    ) -> None:
        """Test unassigning an issue."""
        response = await client.patch(
            f"/api/v1/issues/{test_issue_with_assignee.id}",
            json={"assignee_id": None},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assignee_id"] is None


class TestIssueBulkOperations:
    """Test bulk issue operations."""

    async def test_bulk_update_state(
        self,
        client: AsyncClient,
        test_issues: list[Issue],
        auth_headers: dict[str, str],
    ) -> None:
        """Test bulk updating issue states."""
        issue_ids = [str(issue.id) for issue in test_issues[:3]]

        response = await client.post(
            "/api/v1/issues/bulk-update",
            json={
                "issue_ids": issue_ids,
                "updates": {"state": "todo"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 3

    async def test_bulk_delete(
        self,
        client: AsyncClient,
        test_issues: list[Issue],
        auth_headers: dict[str, str],
    ) -> None:
        """Test bulk deleting issues (soft delete)."""
        issue_ids = [str(issue.id) for issue in test_issues[:2]]

        response = await client.post(
            "/api/v1/issues/bulk-delete",
            json={"issue_ids": issue_ids},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
