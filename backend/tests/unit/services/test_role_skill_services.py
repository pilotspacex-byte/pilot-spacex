"""Unit tests for role skill services.

Tests CQRS-lite services: create, update, delete, list, generate.
Uses SQLite in-memory database via db_session fixture.

Source: 011-role-based-skills, T014
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.role_skill import (
    CreateRoleSkillPayload,
    CreateRoleSkillService,
    DeleteRoleSkillPayload,
    DeleteRoleSkillService,
    GenerateRoleSkillPayload,
    GenerateRoleSkillService,
    ListRoleSkillsPayload,
    ListRoleSkillsService,
    UpdateRoleSkillPayload,
    UpdateRoleSkillService,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import (
    User,
    Workspace,
)
from pilot_space.infrastructure.database.models.user_role_skill import (
    RoleTemplate,
    UserRoleSkill,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(
        id=uuid4(),
        name="Service Test Workspace",
        slug="svc-test-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a user for tests."""
    u = User(id=uuid4(), email="svc-user@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second user for ownership tests."""
    u = User(id=uuid4(), email="other-svc@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def developer_template(db_session: AsyncSession) -> RoleTemplate:
    """Seed a developer template."""
    t = RoleTemplate(
        id=uuid4(),
        role_type="developer",
        display_name="Developer",
        description="Code quality",
        default_skill_content="# Developer\n\nDefault content.",
        icon="Code",
        sort_order=1,
        version=2,
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def existing_skill(
    db_session: AsyncSession,
    user: User,
    workspace: Workspace,
) -> UserRoleSkill:
    """Create an existing developer role skill."""
    skill = UserRoleSkill(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace.id,
        role_type="developer",
        role_name="Senior Developer",
        skill_content="# Developer\n\nExisting content.",
        is_primary=True,
        template_version=1,
    )
    db_session.add(skill)
    await db_session.flush()
    return skill


# ============================================================================
# CreateRoleSkillService Tests
# ============================================================================


@pytest.mark.asyncio
class TestCreateRoleSkillService:
    """Tests for CreateRoleSkillService."""

    async def test_create_success(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        developer_template: RoleTemplate,
    ) -> None:
        """Create a role skill successfully."""
        service = CreateRoleSkillService(db_session)
        result = await service.execute(
            CreateRoleSkillPayload(
                user_id=user.id,
                workspace_id=workspace.id,
                role_type="developer",
                role_name="Senior Dev",
                skill_content="# Dev\n\nContent here.",
            )
        )

        assert result.id is not None
        assert result.role_type == "developer"
        assert result.role_name == "Senior Dev"
        assert result.template_version == 2  # from developer_template

    async def test_create_custom_role(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Create a custom role skill (no template)."""
        service = CreateRoleSkillService(db_session)
        result = await service.execute(
            CreateRoleSkillPayload(
                user_id=user.id,
                workspace_id=workspace.id,
                role_type="custom",
                role_name="My Custom Role",
                skill_content="# Custom\n\nCustom content.",
            )
        )

        assert result.role_type == "custom"
        assert result.template_version is None

    async def test_create_rejects_invalid_role_type(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Reject invalid role type."""
        service = CreateRoleSkillService(db_session)
        with pytest.raises(ValidationError, match="Invalid role type"):
            await service.execute(
                CreateRoleSkillPayload(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    role_type="invalid_role",
                    role_name="Bad Role",
                    skill_content="Content",
                )
            )

    async def test_create_rejects_max_roles(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Reject when user has 3 roles already."""
        service = CreateRoleSkillService(db_session)

        # Create 3 roles
        for role_type in ["developer", "tester", "architect"]:
            db_session.add(
                UserRoleSkill(
                    id=uuid4(),
                    user_id=user.id,
                    workspace_id=workspace.id,
                    role_type=role_type,
                    role_name=f"{role_type} role",
                    skill_content=f"# {role_type}",
                )
            )
        await db_session.flush()

        with pytest.raises(ValidationError, match="Maximum 3 roles"):
            await service.execute(
                CreateRoleSkillPayload(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    role_type="custom",
                    role_name="Fourth Role",
                    skill_content="Content",
                )
            )

    async def test_create_allows_duplicate_role_type(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Allow duplicate role_type in same workspace (constraint dropped in migration 087)."""
        service = CreateRoleSkillService(db_session)
        result = await service.execute(
            CreateRoleSkillPayload(
                user_id=user.id,
                workspace_id=workspace.id,
                role_type="developer",
                role_name="Another Dev",
                skill_content="Content",
            )
        )
        assert result.role_type == "developer"
        assert result.role_name == "Another Dev"

    async def test_create_primary_demotes_existing(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Setting is_primary=True demotes existing primary."""
        service = CreateRoleSkillService(db_session)
        new_skill = await service.execute(
            CreateRoleSkillPayload(
                user_id=user.id,
                workspace_id=workspace.id,
                role_type="tester",
                role_name="QA Engineer",
                skill_content="# Tester",
                is_primary=True,
            )
        )

        assert new_skill.is_primary is True

        # Refresh existing skill to check demotion
        await db_session.refresh(existing_skill)
        assert existing_skill.is_primary is False


# ============================================================================
# UpdateRoleSkillService Tests
# ============================================================================


@pytest.mark.asyncio
class TestUpdateRoleSkillService:
    """Tests for UpdateRoleSkillService."""

    async def test_update_success(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Update skill content successfully."""
        service = UpdateRoleSkillService(db_session)
        result = await service.execute(
            UpdateRoleSkillPayload(
                user_id=user.id,
                skill_id=existing_skill.id,
                workspace_id=workspace.id,
                skill_content="# Developer\n\nUpdated content.",
            )
        )

        assert "Updated content" in result.skill_content

    async def test_update_rejects_wrong_owner(
        self,
        db_session: AsyncSession,
        other_user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Reject update from non-owner."""
        service = UpdateRoleSkillService(db_session)
        with pytest.raises(ForbiddenError, match="Not authorized"):
            await service.execute(
                UpdateRoleSkillPayload(
                    user_id=other_user.id,
                    skill_id=existing_skill.id,
                    workspace_id=workspace.id,
                    skill_content="Hijacked",
                )
            )

    async def test_update_rejects_nonexistent_skill(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Reject update of non-existent skill."""
        service = UpdateRoleSkillService(db_session)
        with pytest.raises(NotFoundError, match="not found"):
            await service.execute(
                UpdateRoleSkillPayload(
                    user_id=user.id,
                    skill_id=uuid4(),
                    workspace_id=workspace.id,
                    skill_content="Content",
                )
            )

    async def test_update_primary_demotes_existing(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Setting is_primary=True demotes existing primary."""
        # Create a secondary skill
        secondary = UserRoleSkill(
            id=uuid4(),
            user_id=user.id,
            workspace_id=workspace.id,
            role_type="tester",
            role_name="Tester",
            skill_content="# Tester",
            is_primary=False,
        )
        db_session.add(secondary)
        await db_session.flush()

        service = UpdateRoleSkillService(db_session)
        result = await service.execute(
            UpdateRoleSkillPayload(
                user_id=user.id,
                skill_id=secondary.id,
                workspace_id=workspace.id,
                is_primary=True,
            )
        )

        assert result.is_primary is True
        await db_session.refresh(existing_skill)
        assert existing_skill.is_primary is False

    async def test_update_wrong_workspace(
        self,
        db_session: AsyncSession,
        user: User,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Reject update with wrong workspace_id."""
        service = UpdateRoleSkillService(db_session)
        with pytest.raises(ForbiddenError, match="does not belong"):
            await service.execute(
                UpdateRoleSkillPayload(
                    user_id=user.id,
                    skill_id=existing_skill.id,
                    workspace_id=uuid4(),
                    skill_content="Content",
                )
            )


# ============================================================================
# DeleteRoleSkillService Tests
# ============================================================================


@pytest.mark.asyncio
class TestDeleteRoleSkillService:
    """Tests for DeleteRoleSkillService."""

    async def test_delete_success(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Delete skill successfully via soft-delete."""
        service = DeleteRoleSkillService(db_session)
        await service.execute(
            DeleteRoleSkillPayload(
                user_id=user.id,
                skill_id=existing_skill.id,
                workspace_id=workspace.id,
            )
        )

        await db_session.refresh(existing_skill)
        assert existing_skill.is_deleted is True

    async def test_delete_rejects_wrong_owner(
        self,
        db_session: AsyncSession,
        other_user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """Reject delete from non-owner."""
        service = DeleteRoleSkillService(db_session)
        with pytest.raises(ForbiddenError, match="Not authorized"):
            await service.execute(
                DeleteRoleSkillPayload(
                    user_id=other_user.id,
                    skill_id=existing_skill.id,
                    workspace_id=workspace.id,
                )
            )

    async def test_delete_rejects_nonexistent(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Reject delete of non-existent skill."""
        service = DeleteRoleSkillService(db_session)
        with pytest.raises(NotFoundError, match="not found"):
            await service.execute(
                DeleteRoleSkillPayload(
                    user_id=user.id,
                    skill_id=uuid4(),
                    workspace_id=workspace.id,
                )
            )


# ============================================================================
# ListRoleSkillsService Tests
# ============================================================================


@pytest.mark.asyncio
class TestListRoleSkillsService:
    """Tests for ListRoleSkillsService."""

    async def test_list_returns_skills_with_word_count(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
    ) -> None:
        """List returns skills with computed word_count."""
        service = ListRoleSkillsService(db_session)
        result = await service.execute(
            ListRoleSkillsPayload(user_id=user.id, workspace_id=workspace.id)
        )

        assert len(result.skills) == 1
        assert result.skills[0].word_count > 0
        assert result.skills[0].role_type == "developer"

    async def test_list_detects_template_update(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
        existing_skill: UserRoleSkill,
        developer_template: RoleTemplate,
    ) -> None:
        """Detects when template has newer version."""
        service = ListRoleSkillsService(db_session)
        result = await service.execute(
            ListRoleSkillsPayload(user_id=user.id, workspace_id=workspace.id)
        )

        # existing_skill has template_version=1, template has version=2
        assert result.skills[0].template_update_available is True

    async def test_list_empty_for_no_skills(
        self,
        db_session: AsyncSession,
        user: User,
        workspace: Workspace,
    ) -> None:
        """Returns empty list when no skills exist."""
        service = ListRoleSkillsService(db_session)
        result = await service.execute(
            ListRoleSkillsPayload(user_id=user.id, workspace_id=workspace.id)
        )

        assert len(result.skills) == 0


# ============================================================================
# GenerateRoleSkillService Tests
# ============================================================================


@pytest.mark.asyncio
class TestGenerateRoleSkillService:
    """Tests for GenerateRoleSkillService."""

    @pytest.fixture(autouse=True)
    def mock_no_llm_config(self) -> None:
        """Ensure no LLM provider is resolved so tests use template fallback."""
        with patch(
            "pilot_space.application.services.role_skill.generate_role_skill_service.resolve_workspace_llm_config",
            new=AsyncMock(return_value=None),
        ):
            yield

    async def test_generate_with_template(
        self,
        db_session: AsyncSession,
        developer_template: RoleTemplate,
    ) -> None:
        """Generate content using template as base."""
        service = GenerateRoleSkillService(db_session)
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="developer",
                experience_description="5 years Python, TypeScript, React",
            )
        )

        assert len(result.skill_content) > 0
        assert result.word_count > 0
        assert result.generation_model == "template-v1"
        assert result.generation_time_ms >= 0
        assert "Developer" in result.suggested_role_name

    async def test_generate_custom_role(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Generate content for custom role type."""
        service = GenerateRoleSkillService(db_session)
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="custom",
                experience_description="10 years in security auditing and compliance",
                role_name="Security Auditor",
            )
        )

        assert "Security Auditor" in result.skill_content
        assert result.suggested_role_name == "Security Auditor"

    async def test_generate_rejects_invalid_role(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Reject generation for invalid role type."""
        service = GenerateRoleSkillService(db_session)
        with pytest.raises(ValidationError, match="Invalid role type"):
            await service.execute(
                GenerateRoleSkillPayload(
                    role_type="nonexistent",
                    experience_description="Some experience description text",
                )
            )

    async def test_generate_suggests_senior_name(
        self,
        db_session: AsyncSession,
        developer_template: RoleTemplate,
    ) -> None:
        """Suggests 'Senior' prefix for experienced users."""
        service = GenerateRoleSkillService(db_session)
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="developer",
                experience_description="Senior developer with 10+ years experience",
            )
        )

        assert "Senior" in result.suggested_role_name

    async def test_generate_includes_experience_in_content(
        self,
        db_session: AsyncSession,
        developer_template: RoleTemplate,
    ) -> None:
        """Generated content includes the experience description."""
        service = GenerateRoleSkillService(db_session)
        experience = "Expert in distributed systems and Kubernetes"
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="developer",
                experience_description=experience,
            )
        )

        assert experience in result.skill_content


# ============================================================================
# GenerateRoleSkillService: AI Integration & Rate Limiting Tests
# ============================================================================


@pytest.mark.asyncio
class TestGenerateRoleSkillAI:
    """Tests for AI generation, fallback, rate limiting, and response parsing."""

    @pytest.fixture(autouse=True)
    def mock_no_llm_config(self) -> None:
        """Ensure no LLM provider is resolved so tests use template fallback."""
        with patch(
            "pilot_space.application.services.role_skill.generate_role_skill_service.resolve_workspace_llm_config",
            new=AsyncMock(return_value=None),
        ):
            yield

    async def test_fallback_to_template_without_api_key(
        self,
        db_session: AsyncSession,
        developer_template: RoleTemplate,
    ) -> None:
        """Falls back to template when no API key available."""
        service = GenerateRoleSkillService(db_session)
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="developer",
                experience_description="5 years Python",
                workspace_id=uuid4(),
                user_id=uuid4(),
            )
        )

        # Should use template fallback since no API key exists
        assert result.generation_model == "template-v1"
        assert result.word_count > 0

    async def test_rate_limit_enforced(
        self,
        db_session: AsyncSession,
    ) -> None:
        """FR-003: Rate limit of _RATE_LIMIT_MAX generations/hour/user is enforced."""
        from pilot_space.application.services.role_skill.generate_role_skill_service import (
            _RATE_LIMIT_MAX,
            SkillGenerationRateLimitError,
            _rate_limit_store,
        )

        user_id = uuid4()
        # Clear any existing rate limit state for this user
        _rate_limit_store.pop(str(user_id), None)

        service = GenerateRoleSkillService(db_session)

        # First _RATE_LIMIT_MAX should succeed
        for _ in range(_RATE_LIMIT_MAX):
            result = await service.execute(
                GenerateRoleSkillPayload(
                    role_type="custom",
                    experience_description="Test experience",
                    user_id=user_id,
                )
            )
            assert result.generation_model == "template-v1"

        # Next one should raise rate limit error
        with pytest.raises(SkillGenerationRateLimitError):
            await service.execute(
                GenerateRoleSkillPayload(
                    role_type="custom",
                    experience_description="Test experience",
                    user_id=user_id,
                )
            )

        # Clean up
        _rate_limit_store.pop(str(user_id), None)

    async def test_no_rate_limit_without_user_id(
        self,
        db_session: AsyncSession,
    ) -> None:
        """No rate limit check when user_id is not provided."""
        service = GenerateRoleSkillService(db_session)

        # Should succeed unlimited times without user_id
        for _ in range(7):
            result = await service.execute(
                GenerateRoleSkillPayload(
                    role_type="custom",
                    experience_description="Test experience",
                )
            )
            assert result.generation_model == "template-v1"

    async def test_payload_accepts_workspace_and_user_ids(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Payload properly accepts optional workspace_id and user_id."""
        from pilot_space.application.services.role_skill.generate_role_skill_service import (
            _rate_limit_store,
        )

        ws_id = uuid4()
        user_id = uuid4()
        _rate_limit_store.pop(str(user_id), None)

        service = GenerateRoleSkillService(db_session)
        result = await service.execute(
            GenerateRoleSkillPayload(
                role_type="custom",
                experience_description="Testing with IDs",
                workspace_id=ws_id,
                user_id=user_id,
            )
        )

        assert result.generation_model == "template-v1"
        assert result.word_count > 0

        _rate_limit_store.pop(str(user_id), None)


# ============================================================================
# AI Response Parsing & Prompt Building (sync, no pytestmark)
# ============================================================================


class TestAIResponseParsing:
    """Sync tests for AI response parsing and prompt building.

    These tests do not need DB or async so they are in a separate class
    to avoid the module-level pytestmark = pytest.mark.asyncio.
    """

    def test_parse_ai_response_valid_json(self) -> None:
        """Parses valid JSON AI response correctly."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        raw = (
            '{"skill_content": "# Senior Dev\\n\\nExpertise in Python and distributed'
            " systems. Focus on clean code and maintainable architecture. More than 50"
            ' characters of content here.", "suggested_role_name": "Senior Developer"}'
        )
        result = service._parse_ai_response(raw, "Developer", None, "claude-sonnet-4")

        assert result is not None
        skill_content, name, model, _tags, _usage = result
        assert "Senior Dev" in skill_content
        assert name == "Senior Developer"
        assert model == "claude-sonnet-4"

    def test_parse_ai_response_with_markdown_fences(self) -> None:
        """Strips markdown code fences from AI response."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        raw = (
            "```json\n"
            '{"skill_content": "# Dev Role\\n\\nA thorough and detailed skill content'
            ' that is definitely more than fifty characters long for validation.",'
            ' "suggested_role_name": "Dev"}\n```'
        )
        result = service._parse_ai_response(raw, "Developer", None, "claude-sonnet-4")

        assert result is not None
        skill_content, name, *_ = result
        assert "Dev Role" in skill_content
        assert name == "Dev"

    def test_parse_ai_response_with_literal_newlines(self) -> None:
        """Parses JSON with literal (unescaped) newlines in string values.

        Some models (Ollama/kimi) return JSON with actual newline bytes instead
        of \\n escape sequences. strict=False handles this.
        """
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        # Build JSON with literal newlines inside the skill_content value
        raw = (
            '{"skill_content": "# Senior Developer\n\n'
            "## Context\n\n"
            "This skill is configured for a **Developer** role.\n\n"
            "## Experience & Background\n\n"
            "10 years of full-stack development with Python and TypeScript.\n\n"
            "## Expertise Areas\n\n"
            '- Backend: Python, FastAPI, SQLAlchemy", '
            '"suggested_role_name": "Senior Full-Stack Developer"}'
        )
        result = service._parse_ai_response(raw, "Developer", None, "test-model")

        assert result is not None
        skill_content, name, model, _tags, _usage = result
        assert "Senior Developer" in skill_content
        assert name == "Senior Full-Stack Developer"
        assert model == "test-model"

    def test_parse_ai_response_rejects_leaked_json_wrapper(self) -> None:
        """Raw JSON with skill_content key must not leak as skill content.

        When all JSON parsing attempts fail (e.g. unescaped quotes inside
        values), the fallback must NOT return the raw JSON blob as markdown.
        """
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        # JSON with unescaped quotes that breaks all parsers
        raw = (
            '{"skill_content": "# Role with "emphasis" in the title and '
            "enough text to pass the 50-char threshold easily for content "
            'validation purposes", "suggested_role_name": "Dev"}'
        )
        result = service._parse_ai_response(raw, "Developer", None, "test-model")

        # Should either parse successfully or return None — never the raw JSON
        if result is not None:
            skill_content, *_ = result
            assert not skill_content.startswith("{")
            assert '"skill_content"' not in skill_content

    def test_parse_ai_response_invalid_json(self) -> None:
        """Returns None for unparseable AI response."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        result = service._parse_ai_response(
            "This is not JSON at all", "Developer", None, "claude-sonnet-4"
        )
        assert result is None

    def test_parse_ai_response_insufficient_content(self) -> None:
        """Returns None when AI returns too-short skill content."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        raw = '{"skill_content": "Too short", "suggested_role_name": "Dev"}'
        result = service._parse_ai_response(raw, "Developer", None, "claude-sonnet-4")

        assert result is None

    def test_build_generation_prompt(self) -> None:
        """Prompt includes all required context, including tags and usage output requirements."""
        from pilot_space.ai.prompts.skill_generation import build_skill_generation_prompt

        prompt = build_skill_generation_prompt(
            role_type="developer",
            display_name="Developer",
            template_content="# Developer\n\n## Expertise\n\nCode quality.",
            experience_description="10 years Python backend",
            role_name="Senior Dev",
        )

        assert "developer" in prompt
        assert "Developer" in prompt
        assert "Senior Dev" in prompt
        assert "10 years Python backend" in prompt
        assert "Code quality" in prompt
        assert "JSON" in prompt
        assert "suggested_tags" in prompt
        assert "suggested_usage" in prompt

    def test_parse_ai_response_returns_tags_and_usage(self) -> None:
        """Parses suggested_tags and suggested_usage from JSON AI response."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        raw = (
            '{"skill_content": "# Senior Dev\\n\\nExpertise in Python and distributed'
            " systems. Focus on clean code and maintainable architecture. More than 50"
            ' characters of content here.", "suggested_role_name": "Senior Developer",'
            ' "suggested_tags": ["Python", "FastAPI", "Clean Architecture"],'
            ' "suggested_usage": "Use when reviewing Python backend code."}'
        )
        result = service._parse_ai_response(raw, "Developer", None, "claude-sonnet-4")

        assert result is not None
        skill_content, name, model, tags, usage = result
        assert tags == ["Python", "FastAPI", "Clean Architecture"]
        assert usage == "Use when reviewing Python backend code."

    def test_parse_ai_response_defaults_when_tags_missing(self) -> None:
        """Defaults to empty tags and None usage when fields are absent."""
        service = GenerateRoleSkillService.__new__(GenerateRoleSkillService)

        raw = (
            '{"skill_content": "# Senior Dev\\n\\nExpertise in Python and distributed'
            " systems. Focus on clean code and maintainable architecture. More than 50"
            ' characters of content here.", "suggested_role_name": "Senior Developer"}'
        )
        result = service._parse_ai_response(raw, "Developer", None, "claude-sonnet-4")

        assert result is not None
        _skill_content, _name, _model, tags, usage = result
        assert tags == []
        assert usage is None
