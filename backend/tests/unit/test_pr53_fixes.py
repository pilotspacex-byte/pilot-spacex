"""Unit tests for PR #53 review comment fixes.

Covers:
- Prompt assembler skill text sanitization
- Prompt assembler empty skill name fallback
- UserSkillCreate model validator
- ConversationExtractionPayload model_name field
- extract_and_persist_to_graph Ollama keyless path
- GenerateRoleSkillService JSON parse guard for non-dict payloads
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestSanitizeSkillText:
    """Tests for _sanitize_skill_text in prompt_assembler."""

    def test_strips_newlines_and_collapses_whitespace(self) -> None:
        """Newlines and multiple spaces are collapsed to single space."""
        from pilot_space.ai.prompt.prompt_assembler import _sanitize_skill_text

        result = _sanitize_skill_text("Hello\nWorld\t\tFoo   Bar", 80)
        assert result == "Hello World Foo Bar"

    def test_truncates_to_max_length(self) -> None:
        """Output is truncated at max_length."""
        from pilot_space.ai.prompt.prompt_assembler import _sanitize_skill_text

        long_text = "a" * 200
        result = _sanitize_skill_text(long_text, 80)
        assert len(result) == 80

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        from pilot_space.ai.prompt.prompt_assembler import _sanitize_skill_text

        result = _sanitize_skill_text("  hello world  ", 80)
        assert result == "hello world"

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        from pilot_space.ai.prompt.prompt_assembler import _sanitize_skill_text

        result = _sanitize_skill_text("", 80)
        assert result == ""


class TestSkillNameFallback:
    """Tests for empty skill name fallback in _build_skills_section."""

    def test_whitespace_only_name_uses_fallback(self) -> None:
        """Whitespace-only skill name should render as 'Unnamed Skill'."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import _build_skills_section

        config = PromptLayerConfig(
            user_skills=[{"name": "   \n\t  ", "description": "test description"}],
        )
        result = _build_skills_section(config)
        assert result is not None
        assert "**Unnamed Skill**" in result

    def test_empty_name_uses_fallback(self) -> None:
        """Empty string skill name should render as 'Unnamed Skill'."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import _build_skills_section

        config = PromptLayerConfig(
            user_skills=[{"name": "", "description": "test"}],
        )
        result = _build_skills_section(config)
        assert result is not None
        assert "**Unnamed Skill**" in result

    def test_normal_name_preserved(self) -> None:
        """Normal skill name should be preserved."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import _build_skills_section

        config = PromptLayerConfig(
            user_skills=[{"name": "My Skill", "description": "does things"}],
        )
        result = _build_skills_section(config)
        assert result is not None
        assert "**My Skill**" in result


class TestGenerateRoleSkillJsonGuard:
    """Tests for JSON parse guard against non-dict payloads."""

    def test_json_list_does_not_crash(self) -> None:
        """Valid JSON that's a list should not raise AttributeError."""
        from unittest.mock import AsyncMock

        from pilot_space.application.services.role_skill.generate_role_skill_service import (
            GenerateRoleSkillService,
        )

        svc = GenerateRoleSkillService(session=AsyncMock())
        # A valid JSON list (not dict) should be handled gracefully
        result = svc._parse_ai_response('["item1", "item2"]', "Developer", None, "test-model")
        # Should return None (no valid skill_content extracted)
        assert result is None

    def test_json_string_does_not_crash(self) -> None:
        """Valid JSON string should not raise AttributeError."""
        from unittest.mock import AsyncMock

        from pilot_space.application.services.role_skill.generate_role_skill_service import (
            GenerateRoleSkillService,
        )

        svc = GenerateRoleSkillService(session=AsyncMock())
        result = svc._parse_ai_response('"just a string"', "Developer", None, "test-model")
        # Raw text too short (< 50 chars), so returns None
        assert result is None


class TestUserSkillCreateValidator:
    """Tests for UserSkillCreate model_validator."""

    def test_template_id_alone_is_valid(self) -> None:
        """Having only template_id should pass validation."""
        from uuid import uuid4

        from pilot_space.api.v1.schemas.user_skill import UserSkillCreate

        model = UserSkillCreate(template_id=uuid4())
        assert model.template_id is not None

    def test_skill_content_alone_is_valid(self) -> None:
        """Having only skill_content should pass validation."""
        from pilot_space.api.v1.schemas.user_skill import UserSkillCreate

        model = UserSkillCreate(skill_content="Some skill content")
        assert model.skill_content is not None

    def test_neither_raises_validation_error(self) -> None:
        """Missing both template_id and skill_content raises ValidationError."""
        from pilot_space.api.v1.schemas.user_skill import UserSkillCreate

        with pytest.raises(ValidationError, match="template_id or skill_content"):
            UserSkillCreate()

    def test_both_provided_is_valid(self) -> None:
        """Both template_id and skill_content is valid (template-based with pre-gen content)."""
        from uuid import uuid4

        from pilot_space.api.v1.schemas.user_skill import UserSkillCreate

        model = UserSkillCreate(template_id=uuid4(), skill_content="pre-generated content")
        assert model.template_id is not None
        assert model.skill_content is not None


class TestConversationExtractionPayloadModelName:
    """Tests for model_name field on ConversationExtractionPayload."""

    def test_model_name_default_is_none(self) -> None:
        """model_name defaults to None."""
        from uuid import uuid4

        from pilot_space.application.services.memory.graph_extraction_service import (
            ConversationExtractionPayload,
        )

        payload = ConversationExtractionPayload(
            messages=[{"role": "user", "content": "test"}],
            workspace_id=uuid4(),
        )
        assert payload.model_name is None

    def test_model_name_is_threaded(self) -> None:
        """model_name can be set and is accessible."""
        from uuid import uuid4

        from pilot_space.application.services.memory.graph_extraction_service import (
            ConversationExtractionPayload,
        )

        payload = ConversationExtractionPayload(
            messages=[{"role": "user", "content": "test"}],
            workspace_id=uuid4(),
            model_name="kimi-k2.5:cloud",
        )
        assert payload.model_name == "kimi-k2.5:cloud"


class TestExtractAndPersistOllamaPath:
    """Tests for extract_and_persist_to_graph Ollama keyless path."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_key_and_no_base_url(self) -> None:
        """Should return False when neither api_key nor base_url provided."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from pilot_space.ai.agents.pilotspace_intent_pipeline import (
            extract_and_persist_to_graph,
        )

        mock_write_svc = MagicMock()
        result = await extract_and_persist_to_graph(
            graph_write_service=mock_write_svc,
            workspace_id=uuid4(),
            user_id=None,
            messages=[{"role": "user", "content": "test"}],
            anthropic_api_key=None,
            base_url=None,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_proceeds_when_base_url_set_without_key(self) -> None:
        """Should attempt extraction when base_url is set (Ollama path)."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4

        from pilot_space.ai.agents.pilotspace_intent_pipeline import (
            extract_and_persist_to_graph,
        )

        mock_write_svc = AsyncMock()
        mock_extraction_result = MagicMock()
        mock_extraction_result.nodes = []  # No nodes -> returns False
        mock_extraction_result.edges = []

        # Patch at the source module — the lazy import inside the function
        # resolves from the source module at import time
        with patch(
            "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService"
        ) as MockSvc:
            mock_instance = AsyncMock()
            mock_instance.execute = AsyncMock(return_value=mock_extraction_result)
            MockSvc.return_value = mock_instance

            result = await extract_and_persist_to_graph(
                graph_write_service=mock_write_svc,
                workspace_id=uuid4(),
                user_id=None,
                messages=[{"role": "user", "content": "test"}],
                anthropic_api_key=None,
                base_url="http://localhost:11434",
            )
            # Returns False because extraction produced no nodes, but it didn't short-circuit
            assert result is False
            mock_instance.execute.assert_called_once()


class TestCreateUserSkillWhitespaceRejection:
    """Tests for whitespace-only skill_content rejection."""

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_content(self) -> None:
        """Should raise ValidationError for whitespace-only skill_content."""
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from pilot_space.application.services.user_skill.create_user_skill_service import (
            CreateUserSkillService,
        )
        from pilot_space.domain.exceptions import ValidationError as AppValidationError

        svc = CreateUserSkillService(session=AsyncMock())
        with pytest.raises(AppValidationError, match="skill_content is required"):
            await svc.create(
                user_id=uuid4(),
                workspace_id=uuid4(),
                template_id=None,
                experience_description="test",
                skill_content="   \n\t  ",
            )
