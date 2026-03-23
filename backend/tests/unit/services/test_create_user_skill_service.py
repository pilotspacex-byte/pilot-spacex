"""Unit tests for CreateUserSkillService.

Tests template-based user skill creation with AI personalization,
duplicate detection, and error handling.

Source: Phase 20, P20-08
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.user_skill.create_user_skill_service import (
    CreateUserSkillService,
)
from pilot_space.domain.exceptions import ValidationError


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> CreateUserSkillService:
    """Create CreateUserSkillService with mock session."""
    return CreateUserSkillService(mock_session)


pytestmark = pytest.mark.asyncio


class TestCreateUserSkill:
    """Tests for CreateUserSkillService.create."""

    async def test_creates_skill_from_template(self, service: CreateUserSkillService) -> None:
        """Creates a user skill with AI-personalized content from template."""
        user_id = uuid4()
        workspace_id = uuid4()
        template_id = uuid4()

        mock_template = MagicMock()
        mock_template.id = template_id
        mock_template.workspace_id = workspace_id
        mock_template.name = "Developer"
        mock_template.skill_content = "# Developer Template\n\nDefault content."
        mock_template.is_active = True
        mock_template.is_deleted = False
        mock_template.role_type = "developer"

        mock_created_skill = MagicMock()
        mock_created_skill.id = uuid4()

        with (
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
            ) as MockTemplateRepo,
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.UserSkillRepository"
            ) as MockUserSkillRepo,
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.GenerateRoleSkillService"
            ) as MockGenService,
        ):
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            mock_skill_repo = AsyncMock()
            mock_skill_repo.get_by_user_workspace_template = AsyncMock(return_value=None)
            mock_skill_repo.create = AsyncMock(return_value=mock_created_skill)
            MockUserSkillRepo.return_value = mock_skill_repo

            mock_gen = AsyncMock()
            mock_gen_result = MagicMock()
            mock_gen_result.skill_content = "# My Developer Skill\n\nPersonalized."
            mock_gen.execute = AsyncMock(return_value=mock_gen_result)
            MockGenService.return_value = mock_gen

            result = await service.create(
                user_id=user_id,
                workspace_id=workspace_id,
                template_id=template_id,
                experience_description="10 years Python experience",
            )

            assert result == mock_created_skill
            mock_skill_repo.create.assert_called_once()
            call_kwargs = mock_skill_repo.create.call_args[1]
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["workspace_id"] == workspace_id
            assert call_kwargs["template_id"] == template_id
            assert call_kwargs["skill_content"] == "# My Developer Skill\n\nPersonalized."
            assert call_kwargs["experience_description"] == "10 years Python experience"

    async def test_raises_on_template_not_found(self, service: CreateUserSkillService) -> None:
        """Raises ValueError if template doesn't exist."""
        with patch(
            "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
        ) as MockTemplateRepo:
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=None)
            MockTemplateRepo.return_value = mock_tmpl_repo

            with pytest.raises(ValidationError, match="Template not found"):
                await service.create(
                    user_id=uuid4(),
                    workspace_id=uuid4(),
                    template_id=uuid4(),
                    experience_description="test",
                )

    async def test_raises_on_inactive_template(self, service: CreateUserSkillService) -> None:
        """Raises ValueError if template is inactive."""
        workspace_id = uuid4()
        mock_template = MagicMock()
        mock_template.is_active = False
        mock_template.is_deleted = False
        mock_template.workspace_id = workspace_id

        with patch(
            "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
        ) as MockTemplateRepo:
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            with pytest.raises(ValidationError, match="not active"):
                await service.create(
                    user_id=uuid4(),
                    workspace_id=workspace_id,
                    template_id=uuid4(),
                    experience_description="test",
                )

    async def test_raises_on_deleted_template(self, service: CreateUserSkillService) -> None:
        """Raises ValueError if template is soft-deleted."""
        workspace_id = uuid4()
        mock_template = MagicMock()
        mock_template.is_active = True
        mock_template.is_deleted = True
        mock_template.workspace_id = workspace_id

        with patch(
            "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
        ) as MockTemplateRepo:
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            with pytest.raises(ValidationError, match="not active"):
                await service.create(
                    user_id=uuid4(),
                    workspace_id=workspace_id,
                    template_id=uuid4(),
                    experience_description="test",
                )

    async def test_raises_on_duplicate_user_skill(self, service: CreateUserSkillService) -> None:
        """Raises ValueError if user already has skill from this template."""
        template_id = uuid4()
        user_id = uuid4()
        workspace_id = uuid4()

        mock_template = MagicMock()
        mock_template.id = template_id
        mock_template.workspace_id = workspace_id
        mock_template.is_active = True
        mock_template.is_deleted = False

        existing_skill = MagicMock()

        with (
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
            ) as MockTemplateRepo,
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.UserSkillRepository"
            ) as MockUserSkillRepo,
        ):
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            mock_skill_repo = AsyncMock()
            mock_skill_repo.get_by_user_workspace_template = AsyncMock(return_value=existing_skill)
            MockUserSkillRepo.return_value = mock_skill_repo

            with pytest.raises(ValidationError, match="already has a skill"):
                await service.create(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    template_id=template_id,
                    experience_description="test",
                )

    async def test_skips_ai_when_skill_content_provided_with_template(
        self, service: CreateUserSkillService
    ) -> None:
        """Uses provided skill_content instead of AI generation when both template_id and skill_content are given."""
        user_id = uuid4()
        workspace_id = uuid4()
        template_id = uuid4()

        mock_template = MagicMock()
        mock_template.id = template_id
        mock_template.workspace_id = workspace_id
        mock_template.name = "Developer"
        mock_template.is_active = True
        mock_template.is_deleted = False

        mock_created_skill = MagicMock()
        mock_created_skill.id = uuid4()

        with (
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
            ) as MockTemplateRepo,
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.UserSkillRepository"
            ) as MockUserSkillRepo,
            patch(
                "pilot_space.application.services.user_skill.create_user_skill_service.GenerateRoleSkillService"
            ) as MockGenService,
        ):
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            mock_skill_repo = AsyncMock()
            mock_skill_repo.get_by_user_workspace_template = AsyncMock(return_value=None)
            mock_skill_repo.create = AsyncMock(return_value=mock_created_skill)
            MockUserSkillRepo.return_value = mock_skill_repo

            mock_gen = AsyncMock()
            MockGenService.return_value = mock_gen

            pre_generated = "# Engineering Lead\n\nAlready generated and edited by user."
            result = await service.create(
                user_id=user_id,
                workspace_id=workspace_id,
                template_id=template_id,
                experience_description="10 years Python",
                skill_content=pre_generated,
            )

            assert result == mock_created_skill
            # AI generation must NOT be called
            mock_gen.execute.assert_not_called()
            # Provided content must be used as-is
            call_kwargs = mock_skill_repo.create.call_args[1]
            assert call_kwargs["skill_content"] == pre_generated

    async def test_raises_on_wrong_workspace(self, service: CreateUserSkillService) -> None:
        """Raises ValueError if template belongs to different workspace."""
        mock_template = MagicMock()
        mock_template.workspace_id = uuid4()
        mock_template.is_active = True
        mock_template.is_deleted = False

        with patch(
            "pilot_space.application.services.user_skill.create_user_skill_service.SkillTemplateRepository"
        ) as MockTemplateRepo:
            mock_tmpl_repo = AsyncMock()
            mock_tmpl_repo.get_by_id = AsyncMock(return_value=mock_template)
            MockTemplateRepo.return_value = mock_tmpl_repo

            with pytest.raises(ValidationError, match="not active"):
                await service.create(
                    user_id=uuid4(),
                    workspace_id=uuid4(),
                    template_id=uuid4(),
                    experience_description="test",
                )
