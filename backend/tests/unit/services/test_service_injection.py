"""Unit tests for service dependency injection.

Verifies that services can be instantiated via container with correct
repository instances and session injection.

Tests cover:
- Service instantiation from container
- Repository dependency injection
- Session propagation through dependency chain
- Service method execution with injected dependencies
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from pilot_space.application.services.issue import (
    CreateIssuePayload,
)
from pilot_space.application.services.note import (
    CreateNotePayload,
)
from pilot_space.container import create_container
from pilot_space.dependencies.auth import _request_session_ctx
from pilot_space.infrastructure.database.models import (
    Project,
    State,
    StateGroup,
    User,
    Workspace,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Issue Service Injection Tests
# ============================================================================


class TestCreateIssueServiceInjection:
    """Tests for CreateIssueService dependency injection."""

    def test_service_can_be_instantiated_from_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test CreateIssueService instantiation via container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_issue_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)

    def test_service_receives_correct_repository_instances(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service receives correct repository instances."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_issue_service()

            # Verify dependencies were injected
            assert hasattr(service, "_issue_repo")
            assert service._issue_repo is not None
            assert hasattr(service, "_activity_repo")
            assert service._activity_repo is not None
            assert hasattr(service, "_label_repo")
            assert service._label_repo is not None
        finally:
            _request_session_ctx.reset(token)

    def test_service_repositories_use_same_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that all repositories in service use same session."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_issue_service()

            # All repositories should share the same session
            assert service._issue_repo.session is db_session
            assert service._activity_repo.session is db_session
            assert service._label_repo.session is db_session
        finally:
            _request_session_ctx.reset(token)

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason=(
            "Requires full PostgreSQL schema (workspace_encryption_keys, "
            "ai_contexts, activities, etc.). Use TEST_DATABASE_URL for integration tests."
        )
    )
    async def test_service_execute_with_injected_dependencies(
        self,
        db_session: AsyncSession,
        sample_workspace: Workspace,
        sample_project: Project,
        sample_user: User,
    ) -> None:
        """Test service.execute() works with injected dependencies."""
        # Arrange: Persist required entities
        db_session.add(sample_workspace)
        db_session.add(sample_user)
        db_session.add(sample_project)

        # Create backlog state
        backlog_state = State(
            id=uuid4(),
            workspace_id=sample_workspace.id,
            project_id=sample_project.id,
            name="Backlog",
            group=StateGroup.UNSTARTED,
            sequence=0,
        )
        db_session.add(backlog_state)
        await db_session.flush()

        # Set up container with session context
        container = create_container()
        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_issue_service()

            payload = CreateIssuePayload(
                workspace_id=sample_workspace.id,
                project_id=sample_project.id,
                name="Test Issue",
                state_id=backlog_state.id,
                reporter_id=sample_user.id,
                description="Test description",
            )

            # Act
            result = await service.execute(payload)

            # Assert
            assert result is not None
            assert result.name == "Test Issue"
            assert result.project_id == sample_project.id
        finally:
            _request_session_ctx.reset(token)


class TestUpdateIssueServiceInjection:
    """Tests for UpdateIssueService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test UpdateIssueService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.update_issue_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)

    def test_service_has_required_dependencies(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that UpdateIssueService has all required dependencies."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.update_issue_service()

            # Verify dependencies
            assert hasattr(service, "_issue_repo")
            assert hasattr(service, "_activity_repo")
            assert hasattr(service, "_label_repo")
        finally:
            _request_session_ctx.reset(token)


class TestGetIssueServiceInjection:
    """Tests for GetIssueService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test GetIssueService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.get_issue_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)


class TestListIssuesServiceInjection:
    """Tests for ListIssuesService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test ListIssuesService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.list_issues_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Note Service Injection Tests
# ============================================================================


class TestCreateNoteServiceInjection:
    """Tests for CreateNoteService dependency injection."""

    def test_service_can_be_instantiated_from_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test CreateNoteService instantiation via container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_note_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)

    def test_service_receives_repository_instances(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service receives repository instances."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_note_service()

            # Verify dependencies
            assert hasattr(service, "_note_repo")
            assert service._note_repo is not None
            assert hasattr(service, "_template_repo")
            assert service._template_repo is not None
        finally:
            _request_session_ctx.reset(token)

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason=(
            "Requires full PostgreSQL schema (workspace_encryption_keys, "
            "audit_log, etc.). Use TEST_DATABASE_URL for integration tests."
        )
    )
    async def test_service_execute_with_injected_dependencies(
        self,
        db_session: AsyncSession,
        sample_workspace: Workspace,
        sample_user: User,
    ) -> None:
        """Test service.execute() works with injected dependencies."""
        # Arrange
        db_session.add(sample_workspace)
        db_session.add(sample_user)
        await db_session.flush()

        container = create_container()
        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_note_service()

            payload = CreateNotePayload(
                workspace_id=sample_workspace.id,
                owner_id=sample_user.id,
                title="Test Note",
                content={
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Test content"}],
                        }
                    ],
                },
            )

            # Act
            result = await service.execute(payload)

            # Assert
            assert result is not None
            assert result.note.title == "Test Note"
            assert result.note.owner_id == sample_user.id
        finally:
            _request_session_ctx.reset(token)


class TestUpdateNoteServiceInjection:
    """Tests for UpdateNoteService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test UpdateNoteService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.update_note_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)


class TestGetNoteServiceInjection:
    """Tests for GetNoteService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test GetNoteService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.get_note_service()

            assert service is not None
            assert hasattr(service, "get_by_id")  # GetNoteService uses get_by_id, not execute
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Cycle Service Injection Tests
# ============================================================================


class TestCreateCycleServiceInjection:
    """Tests for CreateCycleService dependency injection."""

    def test_service_can_be_instantiated_from_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test CreateCycleService instantiation via container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_cycle_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)

    def test_service_receives_repository_instances(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service receives repository instances."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.create_cycle_service()

            # Verify dependencies
            assert hasattr(service, "_cycle_repo")
            assert service._cycle_repo is not None
        finally:
            _request_session_ctx.reset(token)


class TestUpdateCycleServiceInjection:
    """Tests for UpdateCycleService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test UpdateCycleService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.update_cycle_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)


class TestGetCycleServiceInjection:
    """Tests for GetCycleService dependency injection."""

    def test_service_instantiation_via_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test GetCycleService can be instantiated from container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.get_cycle_service()

            assert service is not None
            assert hasattr(service, "execute")
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Workspace Service Injection Tests
# ============================================================================


class TestWorkspaceServiceInjection:
    """Tests for WorkspaceService dependency injection."""

    def test_service_can_be_instantiated_from_container(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test WorkspaceService instantiation via container."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.workspace_service()

            assert service is not None
            assert hasattr(service, "create_workspace")
        finally:
            _request_session_ctx.reset(token)

    def test_service_receives_repository_instances(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that service receives repository instances."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            service = container.workspace_service()

            # Verify dependencies (WorkspaceService uses public attributes, not _prefixed)
            assert hasattr(service, "workspace_repo")
            assert service.workspace_repo is not None
            assert hasattr(service, "user_repo")
            assert service.user_repo is not None
            assert hasattr(service, "invitation_repo")
            assert service.invitation_repo is not None
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Multiple Services with Shared Dependencies
# ============================================================================


class TestMultipleServicesWithSharedDependencies:
    """Tests for multiple services sharing repository instances."""

    def test_different_services_get_same_session(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that different services share the same session."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            issue_service = container.create_issue_service()
            note_service = container.create_note_service()
            cycle_service = container.create_cycle_service()

            # All services should use the same session
            assert issue_service._issue_repo.session is db_session
            assert note_service._note_repo.session is db_session
            assert cycle_service._cycle_repo.session is db_session
        finally:
            _request_session_ctx.reset(token)

    def test_services_with_common_repository_type(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that services using same repository type get different instances."""
        container = create_container()

        token = _request_session_ctx.set(db_session)
        try:
            create_service = container.create_issue_service()
            update_service = container.update_issue_service()

            # Different service instances
            assert create_service is not update_service

            # Different repository instances (Factory pattern)
            assert create_service._issue_repo is not update_service._issue_repo

            # But same session
            assert create_service._issue_repo.session is update_service._issue_repo.session
        finally:
            _request_session_ctx.reset(token)


# ============================================================================
# Error Cases
# ============================================================================


class TestServiceInjectionErrorCases:
    """Tests for error handling in service injection."""

    def test_service_instantiation_fails_without_session(self) -> None:
        """Test that service instantiation fails without session context."""
        container = create_container()

        # Clear session context
        _request_session_ctx.set(None)

        with pytest.raises(RuntimeError, match="No session in current context"):
            container.create_issue_service()

    def test_service_repository_access_fails_without_session(self) -> None:
        """Test that repository access fails without session."""
        container = create_container()

        # Clear session context
        _request_session_ctx.set(None)

        with pytest.raises(RuntimeError):
            # Should fail when trying to inject session into repository
            container.create_note_service()
