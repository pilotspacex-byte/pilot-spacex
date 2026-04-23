"""Unit tests for build_active_context_pointers().

Tests the lightweight <active_context> XML metadata generation that provides
entity pointers (note, issue, selection) for the agent's on-demand context
retrieval via MCP tools (Phase 81 lazy context).

Reference: backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py
"""

from __future__ import annotations

from types import SimpleNamespace

from pilot_space.ai.agents.pilotspace_agent import ChatInput
from pilot_space.ai.agents.pilotspace_agent_helpers import build_active_context_pointers


class TestBuildActiveContextPointers:
    """Test suite for build_active_context_pointers function."""

    def test_no_context_returns_empty_string(self) -> None:
        """Empty context dict should return empty string."""
        input_data = ChatInput(message="Hello", context={})
        result = build_active_context_pointers(input_data)
        assert result == ""

    def test_note_pointer_includes_id_and_title(self) -> None:
        """Note with note_id should produce <note> pointer with id and title."""
        note = SimpleNamespace(title="Sprint Planning")
        input_data = ChatInput(
            message="Summarize",
            context={"note": note, "note_id": "abc-123"},
        )
        result = build_active_context_pointers(input_data)
        assert "<active_context>" in result
        assert '<note id="abc-123" title="Sprint Planning" />' in result
        assert "</active_context>" in result

    def test_note_pointer_without_note_id_returns_empty(self) -> None:
        """Note object but no note_id should produce no pointer."""
        note = SimpleNamespace(title="Some Note")
        input_data = ChatInput(
            message="Hello",
            context={"note": note},
        )
        result = build_active_context_pointers(input_data)
        assert result == ""

    def test_issue_pointer_includes_name_and_identifier_and_state(self) -> None:
        """Issue with name, identifier, and state should include all attributes."""
        state = SimpleNamespace(name="In Progress")
        issue = SimpleNamespace(name="Fix auth bug", identifier="PILOT-42", state=state)
        input_data = ChatInput(
            message="What about this issue?",
            context={"issue": issue},
        )
        result = build_active_context_pointers(input_data)
        assert "<active_context>" in result
        assert 'name="Fix auth bug"' in result
        assert 'identifier="PILOT-42"' in result
        assert 'state="In Progress"' in result

    def test_issue_pointer_without_identifier_omits_it(self) -> None:
        """Issue without identifier should omit identifier attribute."""
        issue = SimpleNamespace(name="Draft task", identifier=None, state=None)
        input_data = ChatInput(
            message="Tell me more",
            context={"issue": issue},
        )
        result = build_active_context_pointers(input_data)
        assert 'name="Draft task"' in result
        assert "identifier=" not in result
        assert "state=" not in result

    def test_selected_text_pointer_truncates_to_80_chars(self) -> None:
        """Selected text preview should be truncated to 80 characters."""
        long_text = "A" * 200
        input_data = ChatInput(
            message="Explain this",
            context={"selected_text": long_text},
        )
        result = build_active_context_pointers(input_data)
        assert "<selection" in result
        # The preview attribute value should be at most 80 chars
        # (before HTML escaping, which doesn't add length for plain text)
        assert 'preview="' in result
        # Extract preview value: find content between preview=" and " />
        import re

        match = re.search(r'preview="([^"]*)"', result)
        assert match is not None
        preview_value = match.group(1)
        assert len(preview_value) == 80

    def test_combined_note_issue_selection(self) -> None:
        """All three context types present should produce three pointers."""
        note = SimpleNamespace(title="Arch Notes")
        state = SimpleNamespace(name="Todo")
        issue = SimpleNamespace(name="Task A", identifier="PS-1", state=state)
        input_data = ChatInput(
            message="Help me",
            context={
                "note": note,
                "note_id": "note-uuid-1",
                "issue": issue,
                "selected_text": "some selected text",
            },
        )
        result = build_active_context_pointers(input_data)
        assert "<note" in result
        assert "<issue" in result
        assert "<selection" in result
        # Should have all three wrapped in <active_context>
        assert result.startswith("<active_context>")
        assert result.endswith("</active_context>")

    def test_html_special_chars_escaped(self) -> None:
        """Titles with <, >, &, and " should be HTML-escaped in attributes."""
        note = SimpleNamespace(title='Notes <draft> & "final"')
        input_data = ChatInput(
            message="Check",
            context={"note": note, "note_id": "id-1"},
        )
        result = build_active_context_pointers(input_data)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
        # Raw characters must NOT appear in attribute values
        assert 'title="Notes <' not in result

    def test_output_under_50_tokens(self) -> None:
        """Typical active_context output should be under 50 tokens (~200 chars)."""
        note = SimpleNamespace(title="Sprint Plan")
        state = SimpleNamespace(name="Open")
        issue = SimpleNamespace(name="Auth fix", identifier="PS-5", state=state)
        input_data = ChatInput(
            message="Help",
            context={
                "note": note,
                "note_id": "uuid-123",
                "issue": issue,
            },
        )
        result = build_active_context_pointers(input_data)
        # ~4 chars per token is a rough estimate
        estimated_tokens = len(result) // 4
        assert estimated_tokens < 50, f"Expected <50 tokens, got ~{estimated_tokens} ({len(result)} chars)"
