"""Unit tests for build_contextual_message().

Tests the context enrichment logic that prepends note content and selected text
to user messages before sending to the Claude SDK.

Reference: backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

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


class TestBuildContextualMessage:
    """Test suite for build_contextual_message function."""

    def test_no_context_returns_original_message(self) -> None:
        """Empty context dict should return raw message unchanged."""
        # Arrange
        input_data = ChatInput(message="What is the weather?", context={})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert result == "What is the weather?"

    def test_note_context_prepends_markdown(self, tiptap_content: dict[str, Any]) -> None:
        """Note with TipTap content should prepend XML-wrapped markdown."""
        # Arrange
        note = SimpleNamespace(title="Meeting Notes", content=tiptap_content)
        input_data = ChatInput(message="Summarize this note", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert result.startswith("<note_context>\n# Meeting Notes\n\n")
        assert "Hello world" in result
        assert result.endswith("</note_context>\n\nSummarize this note")

    def test_selected_text_wrapped(self) -> None:
        """Selected text should be wrapped in XML tags."""
        # Arrange
        input_data = ChatInput(
            message="Explain this code",
            context={"selected_text": "def hello():\n    return 'world'"},
        )

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert result.startswith("<selected_text>\n")
        assert "def hello():" in result
        assert result.endswith("</selected_text>\n\nExplain this code")

    def test_note_and_selection_combined(self, tiptap_content: dict[str, Any]) -> None:
        """Both note and selection contexts should be prepended with message at end."""
        # Arrange
        note = SimpleNamespace(title="Design Doc", content=tiptap_content)
        input_data = ChatInput(
            message="How does this relate?",
            context={
                "note": note,
                "selected_text": "class UserService:\n    pass",
            },
        )

        # Act
        result = build_contextual_message(input_data)

        # Assert
        # Should have both contexts in order: note, then selected_text
        assert "<note_context>\n# Design Doc" in result
        assert "Hello world" in result
        assert "</note_context>" in result
        assert "<selected_text>\nclass UserService:" in result
        assert "</selected_text>" in result
        assert result.endswith("\n\nHow does this relate?")
        # Verify order: note context comes before selected text
        note_pos = result.index("<note_context>")
        selection_pos = result.index("<selected_text>")
        assert note_pos < selection_pos

    def test_empty_note_content_skipped(self) -> None:
        """Note with empty content dict should show (empty note) placeholder."""
        # Arrange
        note = SimpleNamespace(title="Empty Note", content={})
        input_data = ChatInput(message="What should I do?", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<note_context>\n# Empty Note\n\n(empty note)\n</note_context>" in result
        assert result.endswith("\n\nWhat should I do?")

    def test_note_without_title_uses_untitled(self, tiptap_content: dict[str, Any]) -> None:
        """Note with None title should use 'Untitled' as fallback."""
        # Arrange
        note = SimpleNamespace(title=None, content=tiptap_content)
        input_data = ChatInput(message="Review this note", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<note_context>\n# Untitled\n\n" in result
        assert "Hello world" in result
        assert result.endswith("</note_context>\n\nReview this note")

    def test_note_with_empty_string_title_uses_untitled(
        self, tiptap_content: dict[str, Any]
    ) -> None:
        """Note with empty string title should use 'Untitled' as fallback."""
        # Arrange
        note = SimpleNamespace(title="", content=tiptap_content)
        input_data = ChatInput(message="Create action items", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<note_context>\n# Untitled\n\n" in result
        assert "Hello world" in result

    def test_note_with_complex_markdown_content(self) -> None:
        """Note with multiple blocks should convert correctly to markdown."""
        # Arrange
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
                        {"type": "text", "text": " with OAuth2."},
                    ],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "User login"}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Token refresh"}],
                                }
                            ],
                        },
                    ],
                },
            ],
        }
        note = SimpleNamespace(title="Auth Spec", content=complex_content)
        input_data = ChatInput(message="Generate implementation plan", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<note_context>\n# Auth Spec\n\n" in result
        assert "## Project Requirements" in result
        assert "**authentication**" in result
        assert "- User login" in result
        assert "- Token refresh" in result
        assert result.endswith("</note_context>\n\nGenerate implementation plan")

    def test_whitespace_only_markdown_skipped(self) -> None:
        """Note with content that converts to whitespace-only markdown is skipped."""
        # Arrange
        # TipTap doc with only empty paragraphs
        whitespace_content = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": []},
                {"type": "paragraph", "content": []},
            ],
        }
        note = SimpleNamespace(title="Empty Doc", content=whitespace_content)
        input_data = ChatInput(message="Process this", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        # Should skip because markdown is empty after strip()
        assert result == "Process this"
        assert "<note_context>" not in result

    def test_note_missing_content_attribute(self) -> None:
        """Note object without content attribute should show (empty note) placeholder."""
        # Arrange
        note = SimpleNamespace(title="Incomplete Note")
        # Note: no content attribute
        input_data = ChatInput(message="Handle this gracefully", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        # Should handle gracefully and show empty note placeholder
        assert "<note_context>\n# Incomplete Note\n\n(empty note)\n</note_context>" in result
        assert result.endswith("\n\nHandle this gracefully")

    def test_selected_text_preserves_newlines(self) -> None:
        """Selected text with multiple lines should preserve line breaks."""
        # Arrange
        multiline_selection = "line 1\nline 2\nline 3"
        input_data = ChatInput(
            message="Format this",
            context={"selected_text": multiline_selection},
        )

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<selected_text>\nline 1\nline 2\nline 3\n</selected_text>" in result

    def test_empty_selected_text_not_wrapped(self) -> None:
        """Empty selected text string should not create XML wrapper."""
        # Arrange
        input_data = ChatInput(message="No selection", context={"selected_text": ""})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        # Empty strings are falsy in Python, so should be skipped
        assert result == "No selection"
        assert "<selected_text>" not in result

    def test_none_selected_text_skipped(self) -> None:
        """None value for selected_text should be skipped."""
        # Arrange
        input_data = ChatInput(message="Nothing selected", context={"selected_text": None})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert result == "Nothing selected"
        assert "<selected_text>" not in result

    def test_note_with_code_block(self) -> None:
        """Note with code block should render as fenced markdown."""
        # Arrange
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
        input_data = ChatInput(message="Optimize this function", context={"note": note})

        # Act
        result = build_contextual_message(input_data)

        # Assert
        assert "<note_context>\n# Code Example\n\n" in result
        assert "```python\ndef calculate(x):\n    return x * 2\n```" in result
        assert result.endswith("</note_context>\n\nOptimize this function")
