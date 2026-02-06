"""Integration tests for GetOnboardingService auto-sync step detection.

Tests use real DB sessions (auto-rollback) instead of mocks to verify
actual SQLAlchemy behavior, including JSONB mutation detection.

Requires PostgreSQL (TEST_DATABASE_URL env var). Skipped on SQLite
because models use PostgreSQL-specific DDL (JSONB, gen_random_uuid).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.onboarding.get_onboarding_service import (
    GetOnboardingService,
)
from pilot_space.application.services.onboarding.types import OnboardingStepsResult
from pilot_space.infrastructure.database.models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.models.ai_configuration import (
    AIConfiguration,
)
from pilot_space.infrastructure.database.models.onboarding import WorkspaceOnboarding
from pilot_space.infrastructure.database.models.workspace_api_key import (
    WorkspaceAPIKey,
)

from ...factories import UserFactory, WorkspaceFactory

_requires_postgres = pytest.mark.skipif(
    "sqlite" in os.environ.get("TEST_DATABASE_URL", "sqlite"),
    reason="Requires PostgreSQL (JSONB, gen_random_uuid)",
)


async def _seed_workspace(db_session: AsyncSession) -> tuple[User, Workspace]:
    """Create a user and workspace in the DB, return (user, workspace)."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner_id=owner.id)
    db_session.add(owner)
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.flush()
    return owner, workspace


@_requires_postgres
class TestGetOnboardingAutoSync:
    """Integration tests for auto-sync step detection in GetOnboardingService."""

    @pytest.mark.asyncio
    async def test_auto_sync_marks_ai_providers_when_api_key_exists(
        self,
        db_session: AsyncSession,
    ) -> None:
        """ai_providers step should be marked True when WorkspaceAPIKey exists."""
        owner, workspace = await _seed_workspace(db_session)

        # Add an API key for this workspace
        api_key = WorkspaceAPIKey(
            workspace_id=workspace.id,
            provider="anthropic",
            encrypted_key="encrypted-test-key",
            is_valid=True,
        )
        db_session.add(api_key)
        await db_session.flush()

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        assert result.workspace_id == workspace.id
        assert result.steps.ai_providers is True

    @pytest.mark.asyncio
    async def test_auto_sync_marks_ai_providers_via_ai_configuration_fallback(
        self,
        db_session: AsyncSession,
    ) -> None:
        """ai_providers step should be marked True via AIConfiguration when no API key."""
        owner, workspace = await _seed_workspace(db_session)

        # No WorkspaceAPIKey, but add an active AIConfiguration
        ai_config = AIConfiguration(
            workspace_id=workspace.id,
            provider="anthropic",
            api_key_encrypted="encrypted-test-key",
            is_active=True,
        )
        db_session.add(ai_config)
        await db_session.flush()

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        assert result.steps.ai_providers is True

    @pytest.mark.asyncio
    async def test_auto_sync_marks_invite_members_when_multiple_members(
        self,
        db_session: AsyncSession,
    ) -> None:
        """invite_members step should be marked True when >1 member exists."""
        owner, workspace = await _seed_workspace(db_session)

        # Add a second member to the workspace
        second_user = UserFactory()
        db_session.add(second_user)
        await db_session.flush()

        second_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=second_user.id,
            role=WorkspaceRole.MEMBER,
        )
        db_session.add(second_member)
        await db_session.flush()

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        assert result.steps.invite_members is True

    @pytest.mark.asyncio
    async def test_auto_sync_skips_already_completed_steps(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Already-completed steps should not be re-checked or overwritten."""
        owner, workspace = await _seed_workspace(db_session)

        # Pre-create onboarding with steps already marked True
        onboarding = WorkspaceOnboarding(
            workspace_id=workspace.id,
            steps={"ai_providers": True, "invite_members": True, "first_note": False},
        )
        db_session.add(onboarding)
        await db_session.flush()

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        # Steps that were already True should remain True
        assert result.steps.ai_providers is True
        assert result.steps.invite_members is True
        assert result.steps.first_note is False

    @pytest.mark.asyncio
    async def test_auto_sync_no_keys_no_members_stays_incomplete(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Steps should remain False when no keys or extra members exist."""
        owner, workspace = await _seed_workspace(db_session)

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        assert result.steps.ai_providers is False
        assert result.steps.invite_members is False

    @pytest.mark.asyncio
    async def test_returns_correct_result_shape(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Result should contain all expected fields with correct types."""
        owner, workspace = await _seed_workspace(db_session)

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        assert result.workspace_id == workspace.id
        assert isinstance(result.steps, OnboardingStepsResult)
        assert result.id is not None
        assert result.dismissed_at is None
        assert result.completed_at is None
        assert result.completion_percentage == 0
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_upsert_creates_record_if_not_exists(
        self,
        db_session: AsyncSession,
    ) -> None:
        """GetOnboardingService should auto-create onboarding record for new workspace."""
        owner, workspace = await _seed_workspace(db_session)

        service = GetOnboardingService(session=db_session)
        result = await service.execute(workspace.id)

        # Verify record was created
        assert result.workspace_id == workspace.id
        assert result.steps.ai_providers is False
        assert result.steps.invite_members is False
        assert result.steps.first_note is False

    @pytest.mark.asyncio
    async def test_jsonb_step_update_persists_correctly(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify JSONB mutation detection: step updates are actually persisted.

        This test catches the P0 bug where in-place dict mutations
        were invisible to SQLAlchemy (fixed with dict replacement + flag_modified).
        """
        owner, workspace = await _seed_workspace(db_session)

        # Add API key to trigger ai_providers auto-sync
        api_key = WorkspaceAPIKey(
            workspace_id=workspace.id,
            provider="anthropic",
            encrypted_key="encrypted-test-key",
            is_valid=True,
        )
        db_session.add(api_key)
        await db_session.flush()

        # First call: auto-sync should mark ai_providers True
        service = GetOnboardingService(session=db_session)
        result1 = await service.execute(workspace.id)
        assert result1.steps.ai_providers is True

        # Second call: should still be True (persisted, not lost)
        result2 = await service.execute(workspace.id)
        assert result2.steps.ai_providers is True
