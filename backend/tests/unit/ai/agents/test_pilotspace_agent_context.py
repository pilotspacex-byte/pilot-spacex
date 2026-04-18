"""Unit tests for build_contextual_message().

Tests the context enrichment logic that prepends active_context metadata
pointers and selected text to user messages before sending to the Claude SDK.

Phase 81: build_contextual_message() now generates lightweight <active_context>
pointers (~50 tokens) instead of eager <note_context>/<issue_context> XML blocks.
Full content is fetched on-demand via MCP tools.

Reference: backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent import ChatInput
from pilot_space.ai.agents.pilotspace_agent_helpers import build_contextual_message


@pytest.fixture
def tiptap_content() -> dict[str, Any]:
    """TipTap JSON content for testing."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello world"}],
            }
        ],
    }


@pytest.fixture
def note_id() -> str:
    """Stable note UUID for assertions."""
    return str(uuid4())


class TestBuildContextualMessage:
    """Test suite for build_contextual_message function."""

    def test_no_context_returns_original_message(self) -> None:
        """Empty context dict should return raw message unchanged."""
        input_data = ChatInput(message="What is the weather?", context={})
        result = build_contextual_message(input_data)
        assert result == "What is the weather?"

    def test_note_context_generates_active_context_pointer(
        self, tiptap_content: dict[str, Any], note_id: str
    ) -> None:
        """Note with TipTap content should generate <active_context> pointer, NOT full markdown."""
        note = SimpleNamespace(title="Meeting Notes", content=tiptap_content)
        input_data = ChatInput(
            message="Summarize this note",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        # Must have <active_context> with note metadata
        assert "<active_context>" in result
        assert f'id="{note_id}"' in result
        assert 'title="Meeting Notes"' in result
        assert "</active_context>" in result
        # Must NOT have full content (Phase 81: no eager loading)
        assert "Hello world" not in result
        assert "<note_context>" not in result
        assert result.endswith("Summarize this note")

    def test_selected_text_wrapped(self) -> None:
        """Selected text should be wrapped in XML tags (kept inline, not a pointer).

        When only selected_text is in context (no note/issue), build_active_context_pointers
        still emits a <selection preview="..."/> pointer inside <active_context>.
        The full selected_text is also kept inline in its own block.
        """
        input_data = ChatInput(
            message="Explain this code",
            context={"selected_text": "def hello():\n    return 'world'"},
        )
        result = build_contextual_message(input_data)

        # active_context with selection preview
        assert "<active_context>" in result
        assert "<selection preview=" in result
        # Full selected text inline
        assert "<selected_text>\ndef hello():" in result
        assert "return 'world'" in result
        assert result.endswith("</selected_text>\n\nExplain this code")

    def test_note_and_selection_combined(
        self, tiptap_content: dict[str, Any], note_id: str
    ) -> None:
        """Both note and selection contexts should produce <active_context> + <selected_text>."""
        note = SimpleNamespace(title="Design Doc", content=tiptap_content)
        input_data = ChatInput(
            message="How does this relate?",
            context={
                "note": note,
                "note_id": note_id,
                "selected_text": "class UserService:\n    pass",
            },
        )
        result = build_contextual_message(input_data)

        # active_context with note pointer
        assert "<active_context>" in result
        assert 'title="Design Doc"' in result
        # selection pointer also in active_context
        assert '<selection preview="class UserService:' in result
        # selected_text still inline
        assert "<selected_text>\nclass UserService:" in result
        assert "</selected_text>" in result
        assert result.endswith("\n\nHow does this relate?")
        # NO full note content
        assert "Hello world" not in result
        assert "<note_context>" not in result
        # Verify order: active_context comes before selected_text
        ac_pos = result.index("<active_context>")
        sel_pos = result.index("<selected_text>")
        assert ac_pos < sel_pos

    def test_empty_note_content_generates_pointer(self, note_id: str) -> None:
        """Note with empty content should still generate <active_context> pointer."""
        note = SimpleNamespace(title="Empty Note", content={})
        input_data = ChatInput(
            message="What should I do?",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        # Pointer with metadata, not full content
        assert "<active_context>" in result
        assert 'title="Empty Note"' in result
        # No <note_context> or "(empty note)" placeholder
        assert "<note_context>" not in result
        assert "(empty note)" not in result
        assert result.endswith("What should I do?")

    def test_note_without_title_uses_untitled(
        self, tiptap_content: dict[str, Any], note_id: str
    ) -> None:
        """Note with None title should use 'Untitled' as fallback in pointer."""
        note = SimpleNamespace(title=None, content=tiptap_content)
        input_data = ChatInput(
            message="Review this note",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        assert 'title="Untitled"' in result
        assert "Hello world" not in result

    def test_note_with_empty_string_title_uses_untitled(
        self, tiptap_content: dict[str, Any], note_id: str
    ) -> None:
        """Note with empty string title should use 'Untitled' as fallback in pointer."""
        note = SimpleNamespace(title="", content=tiptap_content)
        input_data = ChatInput(
            message="Create action items",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        assert 'title="Untitled"' in result

    def test_note_with_complex_content_not_leaked(self, note_id: str) -> None:
        """Note with complex TipTap content should NOT leak any content into message."""
        complex_content = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Project Requirements"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "We need to implement "},
                        {
                            "type": "text",
                            "text": "authentication",
                            "marks": [{"type": "bold"}],
                        },
                    ],
                },
            ],
        }
        note = SimpleNamespace(title="Auth Spec", content=complex_content)
        input_data = ChatInput(
            message="Generate implementation plan",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        # Pointer only — no content
        assert "<active_context>" in result
        assert 'title="Auth Spec"' in result
        assert "Project Requirements" not in result
        assert "authentication" not in result

    def test_whitespace_only_markdown_still_generates_pointer(self, note_id: str) -> None:
        """Note with content that would be whitespace markdown still gets a pointer."""
        whitespace_content = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": []},
            ],
        }
        note = SimpleNamespace(title="Empty Doc", content=whitespace_content)
        input_data = ChatInput(
            message="Process this",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        # Phase 81: always pointer when note context exists
        assert "<active_context>" in result
        assert 'title="Empty Doc"' in result

    def test_note_missing_content_attribute_generates_pointer(self, note_id: str) -> None:
        """Note object without content attribute should still generate pointer."""
        note = SimpleNamespace(title="Incomplete Note")
        input_data = ChatInput(
            message="Handle this gracefully",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        assert 'title="Incomplete Note"' in result
        assert "<note_context>" not in result

    def test_selected_text_preserves_newlines(self) -> None:
        """Selected text with multiple lines should preserve line breaks."""
        multiline_selection = "line 1\nline 2\nline 3"
        input_data = ChatInput(
            message="Format this",
            context={"selected_text": multiline_selection},
        )
        result = build_contextual_message(input_data)

        assert "<selected_text>\nline 1\nline 2\nline 3\n</selected_text>" in result

    def test_empty_selected_text_not_wrapped(self) -> None:
        """Empty selected text string should not create XML wrapper."""
        input_data = ChatInput(message="No selection", context={"selected_text": ""})
        result = build_contextual_message(input_data)

        assert result == "No selection"
        assert "<selected_text>" not in result

    def test_none_selected_text_skipped(self) -> None:
        """None value for selected_text should be skipped."""
        input_data = ChatInput(message="Nothing selected", context={"selected_text": None})
        result = build_contextual_message(input_data)

        assert result == "Nothing selected"
        assert "<selected_text>" not in result

    def test_note_with_code_block_not_leaked(self, note_id: str) -> None:
        """Note with code block should NOT leak code into message."""
        code_content = {
            "type": "doc",
            "content": [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [
                        {
                            "type": "text",
                            "text": "def calculate(x):\n    return x * 2",
                        }
                    ],
                }
            ],
        }
        note = SimpleNamespace(title="Code Example", content=code_content)
        input_data = ChatInput(
            message="Optimize this function",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        assert 'title="Code Example"' in result
        assert "def calculate" not in result
        assert "<note_context>" not in result

    def test_issue_context_generates_active_context_pointer(self) -> None:
        """Issue context should generate <active_context> pointer with metadata."""
        state = SimpleNamespace(name="In Progress")
        issue = SimpleNamespace(
            name="Login Bug",
            identifier="PS-42",
            state=state,
            description="Users cannot log in",
            priority=None,
        )
        input_data = ChatInput(
            message="Fix this issue",
            context={"issue": issue},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        assert 'name="Login Bug"' in result
        assert 'identifier="PS-42"' in result
        assert 'state="In Progress"' in result
        # Must NOT have full description content
        assert "Users cannot log in" not in result
        assert "<issue_context>" not in result
        assert result.endswith("Fix this issue")

    def test_note_and_issue_combined_in_active_context(self, note_id: str) -> None:
        """Both note and issue should appear as pointers in <active_context>."""
        note = SimpleNamespace(title="Sprint Plan", content={})
        state = SimpleNamespace(name="Todo")
        issue = SimpleNamespace(
            name="Auth Feature",
            identifier="PS-10",
            state=state,
            description="Implement OAuth",
            priority=None,
        )
        input_data = ChatInput(
            message="What is the plan?",
            context={"note": note, "note_id": note_id, "issue": issue},
        )
        result = build_contextual_message(input_data)

        assert "<active_context>" in result
        # Note pointer
        assert f'<note id="{note_id}" title="Sprint Plan"' in result
        # Issue pointer
        assert 'name="Auth Feature"' in result
        assert 'identifier="PS-10"' in result
        # No full content
        assert "Implement OAuth" not in result
        assert "<note_context>" not in result
        assert "<issue_context>" not in result

    def test_slash_command_stripped(self) -> None:
        """Slash command prefix should be stripped from user message."""
        input_data = ChatInput(
            message="/skill-name Do something useful",
            context={},
        )
        result = build_contextual_message(input_data)
        assert result == "Do something useful"

    def test_backslash_command_stripped(self) -> None:
        """Backslash command prefix should also be stripped."""
        input_data = ChatInput(
            message="\\skill-name Do something useful",
            context={},
        )
        result = build_contextual_message(input_data)
        assert result == "Do something useful"

    def test_active_context_not_present_when_no_entities(self) -> None:
        """Empty context dict should yield no <active_context> tag."""
        input_data = ChatInput(message="Hello", context={})
        result = build_contextual_message(input_data)

        assert "<active_context>" not in result
        assert result == "Hello"

    def test_note_content_not_leaked(
        self, tiptap_content: dict[str, Any], note_id: str
    ) -> None:
        """When note has content, the content text must NOT appear in the message."""
        note = SimpleNamespace(title="Secret Meeting", content=tiptap_content)
        input_data = ChatInput(
            message="Tell me about it",
            context={"note": note, "note_id": note_id},
        )
        result = build_contextual_message(input_data)

        # "Hello world" is the TipTap content — must not appear
        assert "Hello world" not in result
        # Only metadata should appear
        assert 'title="Secret Meeting"' in result
        assert "<active_context>" in result

    def test_note_without_note_id_skips_note_pointer(
        self, tiptap_content: dict[str, Any]
    ) -> None:
        """Note without note_id should not generate a note pointer in active_context."""
        note = SimpleNamespace(title="No ID Note", content=tiptap_content)
        input_data = ChatInput(
            message="Process",
            context={"note": note},  # no note_id
        )
        result = build_contextual_message(input_data)

        # No note pointer (build_active_context_pointers requires note_id)
        assert '<note id=' not in result
