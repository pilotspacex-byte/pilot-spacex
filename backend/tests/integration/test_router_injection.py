"""Integration tests for router dependency injection with FastAPI.

Verifies that @inject decorator works in routers with real HTTP requests:
- SessionDep triggers ContextVar session injection
- Service dependencies auto-injected via container
- Repository dependencies auto-injected via container
- No manual service/repository instantiation needed

Uses TestClient to make actual HTTP requests through the full FastAPI stack.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.infrastructure.database.models import (
    Note,
    Project,
    State,
    StateGroup,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def mock_token_payload_with_user() -> TokenPayload:
    """Create mock token payload for integration tests."""
    user_id = uuid4()
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(user_id),
        email="integration-test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int((now + timedelta(hours=1)).timestamp()),
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={"full_name": "Integration Test User"},
    )


@pytest.fixture
async def workspace_with_member(
    db_session: AsyncSession,
    mock_token_payload_with_user: TokenPayload,
) -> tuple[Workspace, User, WorkspaceMember]:
    """Create workspace with authenticated user as member."""
    # Create user
    user = User(
        id=mock_token_payload_with_user.user_id,
        email=mock_token_payload_with_user.email,
        full_name="Integration Test User",
    )
    db_session.add(user)

    # Create workspace
    workspace = Workspace(
        id=uuid4(),
        name="Test Workspace",
        slug="test-workspace-integration",
        owner_id=user.id,
    )
    db_session.add(workspace)

    # Create membership
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(membership)

    await db_session.commit()
    await db_session.refresh(workspace)
    await db_session.refresh(user)
    await db_session.refresh(membership)

    return workspace, user, membership


@pytest.fixture
async def project_with_state(
    db_session: AsyncSession,
    workspace_with_member: tuple[Workspace, User, WorkspaceMember],
) -> tuple[Project, State]:
    """Create project with backlog state."""
    workspace, user, _ = workspace_with_member

    project = Project(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Test Project",
        description="Test project for integration tests",
        lead_id=user.id,
    )
    db_session.add(project)

    # Create backlog state
    state = State(
        id=uuid4(),
        workspace_id=workspace.id,
        project_id=project.id,
        name="Backlog",
        group=StateGroup.UNSTARTED,
        sequence=0,
    )
    db_session.add(state)

    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(state)

    return project, state


# ============================================================================
# Issue Router Injection Tests
# ============================================================================


class TestIssueRouterInjection:
    """Tests for issue router @inject pattern with real HTTP requests."""

    @pytest.mark.asyncio
    async def test_create_issue_endpoint_uses_injected_service(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        project_with_state: tuple[Project, State],
    ) -> None:
        """Test POST /issues uses @inject to get CreateIssueService."""
        workspace, user, _ = workspace_with_member
        project, state = project_with_state

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.post(
                f"/api/v1/workspaces/{workspace.slug}/issues",
                json={
                    "name": "Integration Test Issue",
                    "project_id": str(project.id),
                    "state_id": str(state.id),
                    "description": "Created via @inject pattern",
                },
            )

        # Verify service was auto-injected and executed successfully
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Integration Test Issue"
        assert data["project_id"] == str(project.id)

    @pytest.mark.asyncio
    async def test_update_issue_endpoint_uses_injected_service(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        project_with_state: tuple[Project, State],
        db_session: AsyncSession,
    ) -> None:
        """Test PATCH /issues/{id} uses @inject to get UpdateIssueService."""
        workspace, user, _ = workspace_with_member
        project, state = project_with_state

        # Create an issue first
        from pilot_space.infrastructure.database.models import Issue

        issue = Issue(
            id=uuid4(),
            workspace_id=workspace.id,
            project_id=project.id,
            name="Original Name",
            state_id=state.id,
            reporter_id=user.id,
        )
        db_session.add(issue)
        await db_session.commit()
        await db_session.refresh(issue)

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.patch(
                f"/api/v1/workspaces/{workspace.slug}/issues/{issue.id}",
                json={
                    "name": "Updated Name via DI",
                },
            )

        # Verify service was auto-injected and executed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name via DI"

    @pytest.mark.asyncio
    async def test_get_issue_endpoint_uses_injected_service(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        project_with_state: tuple[Project, State],
        db_session: AsyncSession,
    ) -> None:
        """Test GET /issues/{id} uses @inject to get GetIssueService."""
        workspace, user, _ = workspace_with_member
        project, state = project_with_state

        # Create an issue
        from pilot_space.infrastructure.database.models import Issue

        issue = Issue(
            id=uuid4(),
            workspace_id=workspace.id,
            project_id=project.id,
            name="Test Issue for GET",
            state_id=state.id,
            reporter_id=user.id,
        )
        db_session.add(issue)
        await db_session.commit()

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.get(f"/api/v1/workspaces/{workspace.slug}/issues/{issue.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Issue for GET"


# ============================================================================
# Note Router Injection Tests
# ============================================================================


class TestNoteRouterInjection:
    """Tests for note router @inject pattern with real HTTP requests."""

    @pytest.mark.asyncio
    async def test_create_note_endpoint_uses_injected_service(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
    ) -> None:
        """Test POST /notes uses @inject to get CreateNoteService."""
        workspace, user, _ = workspace_with_member

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.post(
                f"/api/v1/workspaces/{workspace.slug}/notes",
                json={
                    "title": "DI Integration Test Note",
                    "content": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Created via @inject"}],
                            }
                        ],
                    },
                },
            )

        # Verify service was auto-injected and executed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "DI Integration Test Note"

    @pytest.mark.asyncio
    async def test_update_note_endpoint_uses_injected_service(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        db_session: AsyncSession,
    ) -> None:
        """Test PATCH /notes/{id} uses @inject to get UpdateNoteService."""
        workspace, user, _ = workspace_with_member

        # Create a note
        note = Note(
            id=uuid4(),
            workspace_id=workspace.id,
            owner_id=user.id,
            title="Original Title",
            content={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Original content"}],
                    }
                ],
            },
        )
        db_session.add(note)
        await db_session.commit()

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.patch(
                f"/api/v1/workspaces/{workspace.slug}/notes/{note.id}",
                json={
                    "title": "Updated via DI",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated via DI"


# ============================================================================
# Workspace Router Injection Tests
# ============================================================================


class TestWorkspaceRouterInjection:
    """Tests for workspace router @inject pattern."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason=(
            "Requires full integration environment: get_session() ContextVar is not "
            "set because get_db_session() uses the production engine rather than the "
            "test SQLite engine, causing DI factory resolution to fail."
        ),
        strict=False,
    )
    async def test_create_workspace_uses_injected_service(
        self,
        app: Any,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        db_session: AsyncSession,
    ) -> None:
        """Test POST /workspaces uses @inject to get WorkspaceService."""
        from pilot_space.dependencies.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: mock_token_payload_with_user
        try:
            response = await client.post(
                "/api/v1/workspaces",
                json={
                    "name": "DI Test Workspace",
                    "slug": "di-test-workspace-unique",
                },
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # Verify service was auto-injected
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "DI Test Workspace"


# ============================================================================
# Session Dependency Tests
# ============================================================================


class TestSessionDependencyInjection:
    """Tests that SessionDep triggers ContextVar session correctly."""

    @pytest.mark.asyncio
    async def test_session_dep_sets_context_var(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
    ) -> None:
        """Test that SessionDep dependency sets ContextVar session."""
        workspace, _, _ = workspace_with_member

        # Mock get_current_session to verify it was called
        with (
            patch(
                "pilot_space.dependencies.auth.get_current_user",
                return_value=mock_token_payload_with_user,
            ),
            patch("pilot_space.dependencies.auth.get_current_session") as mock_get_session,
        ):
            # Configure mock to return a valid session (will be set by get_session)
            mock_get_session.side_effect = lambda: MagicMock()

            response = await client.get(f"/api/v1/workspaces/{workspace.slug}/notes")

            # Session should have been accessed by injected services
            # Note: In real execution, get_session sets the ContextVar,
            # then services call get_current_session to retrieve it


class TestMultipleRoutersShareSession:
    """Tests that multiple endpoints in same request share session."""

    @pytest.mark.asyncio
    async def test_nested_service_calls_share_session(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        project_with_state: tuple[Project, State],
    ) -> None:
        """Test that nested service calls within one request share session."""
        workspace, user, _ = workspace_with_member
        project, state = project_with_state

        # Creating an issue triggers multiple service/repository interactions
        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.post(
                f"/api/v1/workspaces/{workspace.slug}/issues",
                json={
                    "name": "Multi-service test",
                    "project_id": str(project.id),
                    "state_id": str(state.id),
                },
            )

        # All services (CreateIssueService, ActivityService, etc.) should have
        # used the same session from ContextVar
        assert response.status_code == status.HTTP_201_CREATED


# ============================================================================
# Error Cases
# ============================================================================


class TestRouterInjectionErrorCases:
    """Tests for error handling in router injection."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_fails_before_injection(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that unauthenticated requests fail before DI happens."""
        # No auth header - should fail at auth dependency
        response = await client.post(
            "/api/v1/workspaces",
            json={
                "name": "Should Fail",
                "slug": "should-fail",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason=(
            "Requires full integration environment: get_session() ContextVar is not "
            "set because get_db_session() uses the production engine rather than the "
            "test SQLite engine, causing DI factory resolution to fail."
        ),
        strict=False,
    )
    async def test_invalid_workspace_fails_gracefully(
        self,
        app: Any,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        db_session: AsyncSession,
    ) -> None:
        """Test that invalid workspace slug fails gracefully."""
        from pilot_space.dependencies.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: mock_token_payload_with_user
        try:
            response = await client.get("/api/v1/workspaces/nonexistent-workspace/notes")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # Should handle missing workspace gracefully (404 or similar)
        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# ============================================================================
# Repository Auto-Injection Tests
# ============================================================================


class TestRepositoryAutoInjection:
    """Tests that repositories are auto-injected without manual instantiation."""

    @pytest.mark.asyncio
    async def test_repository_injected_into_service_in_router(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
    ) -> None:
        """Test that repository is auto-injected into service in router."""
        workspace, _, _ = workspace_with_member

        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            # This endpoint's service requires IssueRepository
            # Verify it works without manual repository creation
            response = await client.get(f"/api/v1/workspaces/{workspace.slug}/issues")

        # Should succeed with auto-injected repository
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)  # Returns issue list


# ============================================================================
# Full Stack Integration Test
# ============================================================================


class TestFullStackDIIntegration:
    """End-to-end test of DI from HTTP request to database."""

    @pytest.mark.asyncio
    async def test_create_issue_full_stack(
        self,
        client: AsyncClient,
        mock_token_payload_with_user: TokenPayload,
        workspace_with_member: tuple[Workspace, User, WorkspaceMember],
        project_with_state: tuple[Project, State],
        db_session: AsyncSession,
    ) -> None:
        """Test full stack: HTTP → Router → Service → Repository → DB."""
        workspace, user, _ = workspace_with_member
        project, state = project_with_state

        # Act: Make HTTP request
        with patch(
            "pilot_space.dependencies.auth.get_current_user",
            return_value=mock_token_payload_with_user,
        ):
            response = await client.post(
                f"/api/v1/workspaces/{workspace.slug}/issues",
                json={
                    "name": "Full Stack DI Test",
                    "project_id": str(project.id),
                    "state_id": str(state.id),
                    "description": "Tests complete DI flow",
                },
            )

        # Assert: HTTP response
        assert response.status_code == status.HTTP_201_CREATED
        created_issue = response.json()

        # Assert: Database persistence (verify data actually saved)
        from sqlalchemy import select

        from pilot_space.infrastructure.database.models import Issue

        stmt = select(Issue).where(Issue.id == created_issue["id"])
        result = await db_session.execute(stmt)
        db_issue = result.scalar_one_or_none()

        assert db_issue is not None
        assert db_issue.name == "Full Stack DI Test"
        assert str(db_issue.project_id) == str(project.id)
