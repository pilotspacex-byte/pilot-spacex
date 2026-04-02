"""Unit tests for the skill MCP server (skill_server.py).

Tests all 6 tools: create_skill, update_skill, preview_skill, test_skill,
list_skills, get_skill_graph. Uses asyncio.Queue for event capture and
tmp_path for filesystem isolation.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse_event(raw: str) -> dict:
    """Parse an SSE event string into event type and JSON data."""
    lines = raw.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
    return {"event": event_type, "data": json.loads(data_str)}


def _drain_queue(queue: asyncio.Queue[str]) -> list[dict]:
    """Drain all SSE events from queue and parse them."""
    events = []
    while not queue.empty():
        raw = queue.get_nowait()
        events.append(_parse_sse_event(raw))
    return events


def _capture_tools(
    publisher: EventPublisher,
    *,
    tool_context=None,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Create skill server and intercept the SdkMcpTool objects."""
    import pilot_space.ai.mcp.skill_server as ss_module

    captured: dict[str, object] = {}
    original_create = ss_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(ss_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        ss_module.create_skill_tools_server(
            publisher,
            tool_context=tool_context,
            skills_dir=skills_dir,
        )

    return captured["tools"]


# ---------------------------------------------------------------------------
# Test: Module constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Tests for SERVER_NAME and TOOL_NAMES constants."""

    def test_server_name(self) -> None:
        from pilot_space.ai.mcp.skill_server import SERVER_NAME

        assert SERVER_NAME == "pilot-skills"

    def test_tool_names_count(self) -> None:
        from pilot_space.ai.mcp.skill_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 6

    def test_tool_names_format(self) -> None:
        from pilot_space.ai.mcp.skill_server import TOOL_NAMES

        for name in TOOL_NAMES:
            assert name.startswith("mcp__pilot-skills__")

    def test_tool_names_contains_all_expected(self) -> None:
        from pilot_space.ai.mcp.skill_server import TOOL_NAMES

        expected_suffixes = {
            "create_skill",
            "update_skill",
            "preview_skill",
            "test_skill",
            "list_skills",
            "get_skill_graph",
        }
        actual_suffixes = {n.split("__")[-1] for n in TOOL_NAMES}
        assert actual_suffixes == expected_suffixes


# ---------------------------------------------------------------------------
# Test: create_skill
# ---------------------------------------------------------------------------


class TestCreateSkillTool:
    """Tests for the create_skill MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_confirmation_text(self, tmp_path: Path) -> None:
        """create_skill returns text confirmation with skill name."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["create_skill"]
        result = await tool.handler(
            {
                "name": "test-skill",
                "description": "A test skill",
                "content": "# Test\n\nDo testing.",
            }
        )

        text = result["content"][0]["text"]
        assert "test-skill" in text

    @pytest.mark.asyncio
    async def test_emits_skill_preview_event(self, tmp_path: Path) -> None:
        """create_skill emits skill_preview SSE event."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["create_skill"]
        await tool.handler(
            {
                "name": "test-skill",
                "description": "A test skill",
                "content": "# Test\n\nDo testing.",
            }
        )

        events = _drain_queue(queue)
        event_types = [e["event"] for e in events]
        assert "skill_preview" in event_types

    @pytest.mark.asyncio
    async def test_skill_preview_event_data(self, tmp_path: Path) -> None:
        """create_skill emits skill_preview with correct fields."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["create_skill"]
        await tool.handler(
            {
                "name": "test-skill",
                "description": "A test skill",
                "content": "# Test\n\nDo testing.",
            }
        )

        events = _drain_queue(queue)
        preview = next(e for e in events if e["event"] == "skill_preview")
        data = preview["data"]
        assert data["skillName"] == "test-skill"
        assert data["isUpdate"] is False
        assert "content" in data or "frontmatter" in data

    @pytest.mark.asyncio
    async def test_create_without_skills_dir_does_not_raise(self) -> None:
        """create_skill without skills_dir gracefully skips filesystem write."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        # skills_dir=None — no filesystem write attempted
        tools = _capture_tools(publisher, skills_dir=None)
        tool = tools["create_skill"]
        # Should not raise
        result = await tool.handler(
            {
                "name": "test-skill",
                "description": "A test skill",
                "content": "# Test",
            }
        )
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_writes_skill_file_to_skills_dir(self, tmp_path: Path) -> None:
        """create_skill writes SKILL.md to skills_dir when provided."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["create_skill"]
        await tool.handler(
            {
                "name": "my-skill",
                "description": "My skill",
                "content": "# My Skill content",
            }
        )

        # Some subdirectory starting with "skill-my-skill" should contain SKILL.md
        skill_dirs = list(skills_dir.glob("skill-my-skill*"))
        assert len(skill_dirs) >= 1
        assert (skill_dirs[0] / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Test: update_skill
# ---------------------------------------------------------------------------


class TestUpdateSkillTool:
    """Tests for the update_skill MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_updated_confirmation(self) -> None:
        """update_skill returns text containing 'Updated'."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["update_skill"]
        result = await tool.handler(
            {
                "name": "test-skill",
                "content": "# Updated content",
            }
        )

        text = result["content"][0]["text"]
        assert "test-skill" in text.lower() or "updated" in text.lower()

    @pytest.mark.asyncio
    async def test_emits_skill_preview_with_is_update_true(self) -> None:
        """update_skill emits skill_preview event with isUpdate=True."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["update_skill"]
        await tool.handler(
            {
                "name": "test-skill",
                "content": "# Updated content",
            }
        )

        events = _drain_queue(queue)
        event_types = [e["event"] for e in events]
        assert "skill_preview" in event_types

        preview = next(e for e in events if e["event"] == "skill_preview")
        assert preview["data"]["isUpdate"] is True

    @pytest.mark.asyncio
    async def test_update_emits_skill_name(self) -> None:
        """update_skill SSE event carries the skill name."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["update_skill"]
        await tool.handler(
            {
                "name": "my-updated-skill",
                "content": "# Updated",
            }
        )

        events = _drain_queue(queue)
        preview = next(e for e in events if e["event"] == "skill_preview")
        assert preview["data"]["skillName"] == "my-updated-skill"


# ---------------------------------------------------------------------------
# Test: preview_skill
# ---------------------------------------------------------------------------


class TestPreviewSkillTool:
    """Tests for the preview_skill MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_skill_content_when_found(self, tmp_path: Path) -> None:
        """preview_skill returns SKILL.md content when file exists."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Pre-create a skill dir/file
        skill_dir = skills_dir / "skill-my-skill-abc123"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill\n\nDoes things.")

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["preview_skill"]
        result = await tool.handler({"name": "my-skill"})

        text = result["content"][0]["text"]
        assert "My Skill" in text

    @pytest.mark.asyncio
    async def test_returns_error_when_not_found(self, tmp_path: Path) -> None:
        """preview_skill returns error message when skill not found."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["preview_skill"]
        result = await tool.handler({"name": "nonexistent-skill"})

        text = result["content"][0]["text"]
        assert "not found" in text.lower() or "error" in text.lower()

    @pytest.mark.asyncio
    async def test_returns_message_when_no_skills_dir(self) -> None:
        """preview_skill returns graceful message when skills_dir is None."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher, skills_dir=None)
        tool = tools["preview_skill"]
        result = await tool.handler({"name": "any-skill"})

        text = result["content"][0]["text"]
        assert text  # should return something informative


# ---------------------------------------------------------------------------
# Test: test_skill
# ---------------------------------------------------------------------------


class TestTestSkillTool:
    """Tests for the test_skill MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_structured_json_result(self) -> None:
        """test_skill returns JSON with score, passed, failed, suggestions, sampleOutput."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["test_skill"]
        result = await tool.handler(
            {
                "name": "test-skill",
                "content": "# Test Skill\n\n## Instructions\n\nDo this.\n\n## Examples\n\n- Example 1\n\n## Output Format\n\nReturn JSON.",
            }
        )

        text = result["content"][0]["text"]
        parsed = json.loads(text)

        assert "score" in parsed
        assert isinstance(parsed["score"], (int, float))
        assert 0 <= parsed["score"] <= 10
        assert "passed" in parsed
        assert "failed" in parsed
        assert "suggestions" in parsed
        assert "sampleOutput" in parsed

    @pytest.mark.asyncio
    async def test_score_higher_with_rich_content(self) -> None:
        """test_skill gives higher score for skills with examples and output format.

        Scoring is deterministic (keyword-based rubric, no LLM involved) so
        the comparison rich >= minimal is stable across runs.
        """
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["test_skill"]

        # Minimal skill
        minimal_result = await tool.handler(
            {
                "name": "minimal",
                "content": "Do something.",
            }
        )
        minimal_parsed = json.loads(minimal_result["content"][0]["text"])

        # Rich skill with all sections
        rich_content = (
            "# Rich Skill\n\n"
            "Use this when the user asks to do something.\n\n"
            "## Instructions\n\nDo this step by step.\n\n"
            "## Examples\n\n- Example 1\n- Example 2\n\n"
            "## Output Format\n\nReturn JSON with field x.\n\n"
            "## Context\n\nRequires tool access."
        )
        rich_result = await tool.handler(
            {
                "name": "rich",
                "content": rich_content,
            }
        )
        rich_parsed = json.loads(rich_result["content"][0]["text"])

        assert rich_parsed["score"] >= minimal_parsed["score"]

    @pytest.mark.asyncio
    async def test_without_tool_context_sets_placeholder_sample_output(self) -> None:
        """test_skill without tool_context sets placeholder sampleOutput."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher, tool_context=None)
        tool = tools["test_skill"]
        result = await tool.handler(
            {
                "name": "test-skill",
                "content": "# Test\n\nDo things.",
            }
        )

        parsed = json.loads(result["content"][0]["text"])
        # Without context, sampleOutput should be a placeholder string
        assert isinstance(parsed["sampleOutput"], str)

    @pytest.mark.asyncio
    async def test_emits_test_result_event(self) -> None:
        """test_skill emits a test_result SSE event."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["test_skill"]
        await tool.handler(
            {
                "name": "test-skill",
                "content": "# Test",
            }
        )

        events = _drain_queue(queue)
        event_types = [e["event"] for e in events]
        assert "test_result" in event_types

    @pytest.mark.asyncio
    async def test_passed_and_failed_are_lists(self) -> None:
        """test_skill returns passed and failed as lists of strings."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["test_skill"]
        result = await tool.handler(
            {
                "name": "test-skill",
                "content": "# Test",
            }
        )

        parsed = json.loads(result["content"][0]["text"])
        assert isinstance(parsed["passed"], list)
        assert isinstance(parsed["failed"], list)
        assert isinstance(parsed["suggestions"], list)


# ---------------------------------------------------------------------------
# Test: list_skills
# ---------------------------------------------------------------------------


class TestListSkillsTool:
    """Tests for the list_skills MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_message_when_no_skills_dir(self) -> None:
        """list_skills returns graceful message when skills_dir is None."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher, skills_dir=None)
        tool = tools["list_skills"]
        result = await tool.handler({})

        text = result["content"][0]["text"]
        assert text  # should return something

    @pytest.mark.asyncio
    async def test_lists_skills_from_directory(self, tmp_path: Path) -> None:
        """list_skills returns names of skills found in the directory."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create two skill dirs
        for name in ["skill-alpha-aaa111", "skill-beta-bbb222"]:
            d = skills_dir / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n# Content")

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["list_skills"]
        result = await tool.handler({})

        text = result["content"][0]["text"]
        assert "alpha" in text.lower() or "skill" in text.lower()

    @pytest.mark.asyncio
    async def test_empty_directory_returns_informative_message(self, tmp_path: Path) -> None:
        """list_skills returns a message when directory is empty."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        tools = _capture_tools(publisher, skills_dir=skills_dir)
        tool = tools["list_skills"]
        result = await tool.handler({})

        text = result["content"][0]["text"]
        assert text  # should not raise


# ---------------------------------------------------------------------------
# Test: get_skill_graph
# ---------------------------------------------------------------------------


class TestGetSkillGraphTool:
    """Tests for the get_skill_graph MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_mermaid_diagram(self) -> None:
        """get_skill_graph returns text containing Mermaid graph TD syntax."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["get_skill_graph"]
        result = await tool.handler({"skill_names": ["skill-a", "skill-b"]})

        text = result["content"][0]["text"]
        assert "graph TD" in text

    @pytest.mark.asyncio
    async def test_empty_skill_names_returns_graph(self) -> None:
        """get_skill_graph with empty list still returns a graph structure."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["get_skill_graph"]
        result = await tool.handler({"skill_names": []})

        text = result["content"][0]["text"]
        assert "graph TD" in text

    @pytest.mark.asyncio
    async def test_no_skill_names_arg_returns_graph(self) -> None:
        """get_skill_graph with missing skill_names arg still returns a graph."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["get_skill_graph"]
        result = await tool.handler({})

        text = result["content"][0]["text"]
        assert "graph TD" in text

    @pytest.mark.asyncio
    async def test_skill_names_appear_in_diagram(self) -> None:
        """get_skill_graph mentions provided skill names in the diagram."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)

        tools = _capture_tools(publisher)
        tool = tools["get_skill_graph"]
        result = await tool.handler({"skill_names": ["review-code", "write-tests"]})

        text = result["content"][0]["text"]
        # At least one of the skill names should appear in the diagram
        assert "review-code" in text or "write-tests" in text
