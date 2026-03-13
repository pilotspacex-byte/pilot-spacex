"""Unit tests for SeedTemplatesService.

Tests workspace template seeding from RoleTemplates, idempotency,
and non-fatal error handling.

Source: Phase 20, P20-07
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.skill_template.seed_templates_service import (
    SeedTemplatesService,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> SeedTemplatesService:
    """Create SeedTemplatesService with mock session."""
    return SeedTemplatesService(mock_session)


pytestmark = pytest.mark.asyncio


class TestSeedWorkspace:
    """Tests for SeedTemplatesService.seed_workspace."""

    async def test_seeds_templates_from_role_templates(self, service: SeedTemplatesService) -> None:
        """Copies all RoleTemplates into skill_templates as built_in."""
        workspace_id = uuid4()

        mock_role_template = MagicMock()
        mock_role_template.role_type = "developer"
        mock_role_template.display_name = "Developer"
        mock_role_template.description = "Full-stack developer"
        mock_role_template.default_skill_content = "# Developer\n\nDefault content."
        mock_role_template.icon = "Code"
        mock_role_template.sort_order = 1

        with (
            patch(
                "pilot_space.application.services.skill_template.seed_templates_service.RoleTemplateRepository"
            ) as MockRoleRepo,
            patch(
                "pilot_space.application.services.skill_template.seed_templates_service.SkillTemplateRepository"
            ) as MockSkillRepo,
        ):
            mock_role_repo = AsyncMock()
            mock_role_repo.get_all_ordered = AsyncMock(return_value=[mock_role_template])
            MockRoleRepo.return_value = mock_role_repo

            mock_skill_repo = AsyncMock()
            mock_skill_repo.has_built_in_templates = AsyncMock(return_value=False)
            mock_skill_repo.create = AsyncMock()
            MockSkillRepo.return_value = mock_skill_repo

            await service.seed_workspace(workspace_id)

            mock_skill_repo.create.assert_called_once_with(
                workspace_id=workspace_id,
                name="Developer",
                description="Full-stack developer",
                skill_content="# Developer\n\nDefault content.",
                source="built_in",
                icon="Code",
                sort_order=1,
                role_type="developer",
            )

    async def test_idempotent_skips_if_already_seeded(self, service: SeedTemplatesService) -> None:
        """Skips seeding if workspace already has built_in templates."""
        workspace_id = uuid4()

        existing_template = MagicMock()
        existing_template.source = "built_in"

        with patch(
            "pilot_space.application.services.skill_template.seed_templates_service.SkillTemplateRepository"
        ) as MockSkillRepo:
            mock_skill_repo = AsyncMock()
            mock_skill_repo.has_built_in_templates = AsyncMock(return_value=True)
            MockSkillRepo.return_value = mock_skill_repo

            await service.seed_workspace(workspace_id)

            mock_skill_repo.create.assert_not_called()

    async def test_non_fatal_on_exception(self, service: SeedTemplatesService) -> None:
        """Exceptions are caught and logged, never propagated."""
        workspace_id = uuid4()

        with patch(
            "pilot_space.application.services.skill_template.seed_templates_service.SkillTemplateRepository"
        ) as MockSkillRepo:
            mock_skill_repo = AsyncMock()
            mock_skill_repo.has_built_in_templates = AsyncMock(
                side_effect=RuntimeError("DB connection lost")
            )
            MockSkillRepo.return_value = mock_skill_repo

            # Should NOT raise
            await service.seed_workspace(workspace_id)

    async def test_seeds_multiple_templates(self, service: SeedTemplatesService) -> None:
        """Seeds multiple role templates in one call."""
        workspace_id = uuid4()

        templates = []
        for role_type, name, order in [
            ("developer", "Developer", 1),
            ("tester", "QA Engineer", 2),
            ("designer", "UX Designer", 3),
        ]:
            t = MagicMock()
            t.role_type = role_type
            t.display_name = name
            t.description = f"{name} description"
            t.default_skill_content = f"# {name}"
            t.icon = "Wand2"
            t.sort_order = order
            templates.append(t)

        with (
            patch(
                "pilot_space.application.services.skill_template.seed_templates_service.RoleTemplateRepository"
            ) as MockRoleRepo,
            patch(
                "pilot_space.application.services.skill_template.seed_templates_service.SkillTemplateRepository"
            ) as MockSkillRepo,
        ):
            mock_role_repo = AsyncMock()
            mock_role_repo.get_all_ordered = AsyncMock(return_value=templates)
            MockRoleRepo.return_value = mock_role_repo

            mock_skill_repo = AsyncMock()
            mock_skill_repo.has_built_in_templates = AsyncMock(return_value=False)
            mock_skill_repo.create = AsyncMock()
            MockSkillRepo.return_value = mock_skill_repo

            await service.seed_workspace(workspace_id)

            assert mock_skill_repo.create.call_count == 3
