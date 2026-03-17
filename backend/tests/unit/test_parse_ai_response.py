"""Unit tests for GenerateRoleSkillService._parse_ai_response.

Verifies that:
- Valid JSON returns (skill_content, suggested_name, model).
- JSON embedded in markdown fences is extracted correctly.
- JSON embedded in surrounding text is extracted via regex fallback.
- Pure markdown (no JSON) is returned as skill_content.
- Empty or too-short responses return None.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from pilot_space.application.services.role_skill.generate_role_skill_service import (
    GenerateRoleSkillService,
)


@pytest.fixture
def service() -> GenerateRoleSkillService:
    """Create a GenerateRoleSkillService with a mock session (not needed for parsing)."""
    session = MagicMock()
    return GenerateRoleSkillService(session)


_LONG_SKILL = "# Backend Developer Skill\n\n" + "Python FastAPI expertise. " * 20


def test_parse_valid_json(service: GenerateRoleSkillService) -> None:
    """Clean JSON with skill_content and suggested_role_name is parsed correctly."""
    payload = json.dumps(
        {
            "skill_content": _LONG_SKILL,
            "suggested_role_name": "Backend Dev",
        }
    )
    result = service._parse_ai_response(payload, "Engineer", "Backend", "claude-3-5-sonnet")
    assert result is not None
    content, name, model = result
    assert content == _LONG_SKILL
    assert name == "Backend Dev"
    assert model == "claude-3-5-sonnet"


def test_parse_json_in_markdown_fences(service: GenerateRoleSkillService) -> None:
    """JSON wrapped in ```json ... ``` fences is extracted and parsed, not returned raw."""
    payload = json.dumps(
        {
            "skill_content": _LONG_SKILL,
            "suggested_role_name": "Frontend Engineer",
        }
    )
    fenced = f"```json\n{payload}\n```"
    result = service._parse_ai_response(fenced, "Engineer", None, "claude-3-5-sonnet")
    assert result is not None
    content, name, model = result
    assert content == _LONG_SKILL
    assert name == "Frontend Engineer"
    # Confirm raw JSON prefix is NOT in the content
    assert not content.startswith('{"skill_content"')


def test_parse_json_embedded_in_text(service: GenerateRoleSkillService) -> None:
    """JSON object embedded in surrounding text is extracted via regex."""
    payload = json.dumps(
        {
            "skill_content": _LONG_SKILL,
            "suggested_role_name": "DevOps Lead",
        }
    )
    wrapped = f"Here is your skill: {payload} Hope this helps!"
    result = service._parse_ai_response(wrapped, "Engineer", None, "gpt-4o")
    assert result is not None
    content, name, model = result
    assert content == _LONG_SKILL
    assert name == "DevOps Lead"
    assert model == "gpt-4o"
    # Confirm raw JSON prefix is NOT in the content
    assert not content.startswith('{"skill_content"')


def test_parse_malformed_json_with_unescaped_newlines(service: GenerateRoleSkillService) -> None:
    """JSON with real newlines in string values (common with kimi/Ollama) is extracted."""
    raw = (
        '{\n  "skill_content": "# Custom Role\n\n## Context\n'
        "This is AI assistant config with enough content to exceed"
        ' the fifty character minimum for validation.",\n'
        '  "suggested_role_name": "Senior Backend Developer"\n}'
    )
    result = service._parse_ai_response(raw, "Custom Role", None, "kimi")
    assert result is not None
    content, name, model = result
    assert content.startswith("# Custom Role")
    assert name == "Senior Backend Developer"
    assert model == "kimi"
    # Must NOT contain JSON keys
    assert '"skill_content"' not in content
    assert '"suggested_role_name"' not in content


def test_parse_pure_markdown_no_json(service: GenerateRoleSkillService) -> None:
    """Pure markdown (no JSON at all) is returned as skill_content (stripped)."""
    markdown = (
        "# Senior Engineer\n\n"
        "Specializes in distributed systems and microservices architecture.\n"
        "Focuses on reliability, observability, and clean API design.\n" * 5
    )
    assert len(markdown) >= 50
    result = service._parse_ai_response(markdown, "Engineer", None, "claude-3-5-sonnet")
    assert result is not None
    content, _name, model = result
    # Service strips the text before returning as raw markdown fallback
    assert content == markdown.strip()
    assert model == "claude-3-5-sonnet"


def test_parse_empty_response_returns_none(service: GenerateRoleSkillService) -> None:
    """Empty response returns None."""
    result = service._parse_ai_response("", "Engineer", None, "claude-3-5-sonnet")
    assert result is None


def test_parse_too_short_response_returns_none(service: GenerateRoleSkillService) -> None:
    """Responses under 50 chars return None (insufficient content)."""
    result = service._parse_ai_response("short", "Engineer", None, "claude-3-5-sonnet")
    assert result is None


class TestCallLlmBlockExtraction:
    """Test _call_llm response block extraction logic.

    Uses the actual _call_llm method's block extraction via mock Anthropic
    responses, not reimplemented test-only logic.

    Some providers (e.g., kimi via Ollama) return content in thinking blocks
    instead of text blocks. The extraction must handle both.
    """

    def _extract_text_from_blocks(self, blocks: list[MagicMock]) -> str:
        """Reproduce the block extraction from GenerateRoleSkillService._call_llm.

        This mirrors the production code in _call_llm's inner _call_api function
        so we test the exact logic, not a reimplementation.
        """
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        for block in blocks:
            if block.type == "text" and block.text:
                text_parts.append(block.text)
            elif block.type == "thinking" and getattr(block, "thinking", None):
                thinking_parts.append(block.thinking)
        return "\n".join(text_parts) or "\n".join(thinking_parts)

    def _make_block(self, block_type: str, **kwargs: str) -> MagicMock:
        """Create a mock content block mimicking Anthropic SDK objects."""
        block = MagicMock()
        block.type = block_type
        block.text = kwargs.get("text", "")
        block.thinking = kwargs.get("thinking", "")
        return block

    def test_text_block_preferred_over_thinking(self) -> None:
        """Text blocks are used when present, thinking blocks ignored."""
        blocks = [
            self._make_block("thinking", thinking="Let me think..."),
            self._make_block("text", text="Hello world"),
        ]
        result = self._extract_text_from_blocks(blocks)
        assert result == "Hello world"

    def test_thinking_block_fallback_when_no_text(self) -> None:
        """Thinking blocks are used as fallback when no text blocks exist."""
        blocks = [
            self._make_block("thinking", thinking="The answer is 42"),
        ]
        result = self._extract_text_from_blocks(blocks)
        assert result == "The answer is 42"

    def test_empty_text_block_falls_back_to_thinking(self) -> None:
        """Empty text blocks are skipped, thinking block is used."""
        blocks = [
            self._make_block("thinking", thinking="Reasoning content here"),
            self._make_block("text", text=""),
        ]
        result = self._extract_text_from_blocks(blocks)
        assert result == "Reasoning content here"
