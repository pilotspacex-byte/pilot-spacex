"""Unit tests for Phase 1 SDK features: Memory (T57), Citations (T58), Config (T59).

Tests verify SSE event emission for memory updates, citation extraction from
assistant messages, and SDK configuration passthrough for memory/citations flags.

References:
- T57: Enable cross-session Memory tool
- T58: Enable Citations for source attribution
- T59: Enable partial message streaming (config passthrough)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    _extract_citation,
    transform_sdk_message,
)
from pilot_space.ai.sdk.sandbox_config import configure_sdk_for_space
from pilot_space.spaces.base import SpaceContext


def _make_message(class_name: str, **attrs: Any) -> MagicMock:
    """Create a mock SDK message with the given class name and attributes."""
    msg = MagicMock()
    msg.__class__.__name__ = class_name
    for key, value in attrs.items():
        setattr(msg, key, value)
    return msg


def _holder() -> dict[str, str | None]:
    return {"_current_message_id": None}


class TestMemoryUpdateEvent:
    """T57: Memory update SSE events from SystemMessage with subtype=memory."""

    def test_memory_update_event_emitted(self) -> None:
        message = _make_message(
            "SystemMessage",
            data={
                "type": "system",
                "subtype": "memory",
                "operation": "write",
                "key": "preference",
                "value": "TypeScript",
            },
        )

        result = transform_sdk_message(message, _holder())

        assert result is not None
        assert result.startswith("event: memory_update\n")
        payload = json.loads(result.split("data: ", 1)[1].strip())
        assert payload["operation"] == "write"
        assert payload["key"] == "preference"
        assert payload["value"] == "TypeScript"

    def test_memory_event_ignored_for_non_memory_subtypes(self) -> None:
        message = _make_message(
            "SystemMessage",
            data={
                "type": "system",
                "subtype": "other",
                "operation": "write",
                "key": "foo",
                "value": "bar",
            },
        )

        result = transform_sdk_message(message, _holder())

        assert result is None

    def test_memory_event_defaults_operation_to_write(self) -> None:
        message = _make_message(
            "SystemMessage",
            data={
                "type": "system",
                "subtype": "memory",
                "key": "lang",
                "value": "Python",
            },
        )

        result = transform_sdk_message(message, _holder())

        assert result is not None
        payload = json.loads(result.split("data: ", 1)[1].strip())
        assert payload["operation"] == "write"

    def test_memory_event_handles_delete_operation(self) -> None:
        message = _make_message(
            "SystemMessage",
            data={
                "type": "system",
                "subtype": "memory",
                "operation": "delete",
                "key": "preference",
                "value": None,
            },
        )

        result = transform_sdk_message(message, _holder())

        assert result is not None
        payload = json.loads(result.split("data: ", 1)[1].strip())
        assert payload["operation"] == "delete"
        assert payload["key"] == "preference"
        assert payload["value"] is None

    def test_memory_update_includes_message_id(self) -> None:
        holder = _holder()
        holder["_current_message_id"] = "msg-123"

        message = _make_message(
            "SystemMessage",
            data={
                "type": "system",
                "subtype": "memory",
                "operation": "write",
                "key": "pref",
                "value": "dark",
            },
        )

        result = transform_sdk_message(message, holder)

        assert result is not None
        payload = json.loads(result.split("data: ", 1)[1].strip())
        assert payload["messageId"] == "msg-123"


class TestCitationBlocks:
    """T58: Citation SSE events from AssistantMessage content blocks."""

    def test_citation_blocks_extracted(self) -> None:
        holder = _holder()
        holder["_current_message_id"] = "msg-001"

        citation_block = {
            "type": "citation",
            "source": {
                "type": "document",
                "id": "note-123",
                "title": "Test Note",
            },
            "cited_text": "some text",
        }
        text_block = {"type": "text", "text": "Here is the answer."}
        message = _make_message(
            "AssistantMessage",
            content=[text_block, citation_block],
        )

        result = transform_sdk_message(message, holder)

        assert result is not None
        assert "event: citation\n" in result

        # Extract the citation event data
        for segment in result.split("event: "):
            if segment.startswith("citation\n"):
                data_line = segment.split("data: ", 1)[1].strip()
                citation_payload = json.loads(data_line)
                break
        else:
            raise AssertionError("citation event not found in result")

        assert citation_payload["messageId"] == "msg-001"
        assert len(citation_payload["citations"]) == 1
        cite = citation_payload["citations"][0]
        assert cite["sourceType"] == "document"
        assert cite["sourceId"] == "note-123"
        assert cite["sourceTitle"] == "Test Note"
        assert cite["citedText"] == "some text"

    def test_multiple_citation_blocks_aggregated(self) -> None:
        holder = _holder()
        holder["_current_message_id"] = "msg-002"

        blocks: list[dict[str, Any]] = [
            {"type": "text", "text": "Answer with sources."},
            {
                "type": "citation",
                "source": {"type": "document", "id": "doc-1", "title": "Doc A"},
                "cited_text": "first quote",
            },
            {
                "type": "citation",
                "source": {"type": "document", "id": "doc-2", "title": "Doc B"},
                "cited_text": "second quote",
            },
        ]
        message = _make_message("AssistantMessage", content=blocks)

        result = transform_sdk_message(message, holder)

        assert result is not None
        assert "event: citation\n" in result

        for segment in result.split("event: "):
            if segment.startswith("citation\n"):
                data_line = segment.split("data: ", 1)[1].strip()
                citation_payload = json.loads(data_line)
                break
        else:
            raise AssertionError("citation event not found")

        assert len(citation_payload["citations"]) == 2
        assert citation_payload["citations"][0]["sourceId"] == "doc-1"
        assert citation_payload["citations"][1]["sourceId"] == "doc-2"

    def test_no_citation_event_when_no_citation_blocks(self) -> None:
        holder = _holder()
        holder["_current_message_id"] = "msg-003"

        message = _make_message(
            "AssistantMessage",
            content=[{"type": "text", "text": "Plain response."}],
        )

        result = transform_sdk_message(message, holder)

        assert result is not None
        assert "event: citation" not in result


class TestExtractCitationHelper:
    """T58: Direct tests for _extract_citation() helper."""

    def test_extract_citation_from_dict(self) -> None:
        block = {
            "type": "citation",
            "source": {
                "type": "document",
                "id": "note-456",
                "title": "Architecture Note",
                "start_index": 10,
                "end_index": 50,
            },
            "cited_text": "important detail",
        }

        result = _extract_citation(block)

        assert result is not None
        assert result["sourceType"] == "document"
        assert result["sourceId"] == "note-456"
        assert result["sourceTitle"] == "Architecture Note"
        assert result["citedText"] == "important detail"
        assert result["startIndex"] == 10
        assert result["endIndex"] == 50

    def test_extract_citation_from_object(self) -> None:
        block = MagicMock()
        block.source = {
            "type": "web",
            "id": "url-789",
            "title": "External Source",
        }
        block.cited_text = "referenced passage"
        # Ensure isinstance(block, dict) is False
        assert not isinstance(block, dict)

        result = _extract_citation(block)

        assert result is not None
        assert result["sourceType"] == "web"
        assert result["sourceId"] == "url-789"
        assert result["citedText"] == "referenced passage"

    def test_extract_citation_returns_none_for_empty_block(self) -> None:
        block = {"type": "citation", "source": {}, "cited_text": ""}

        result = _extract_citation(block)

        assert result is None

    def test_extract_citation_defaults_missing_source_fields(self) -> None:
        block = {
            "type": "citation",
            "source": {"type": "note"},
            "cited_text": "some text",
        }

        result = _extract_citation(block)

        assert result is not None
        assert result["sourceType"] == "note"
        assert result["sourceId"] == ""
        assert result["sourceTitle"] == ""
        assert "startIndex" not in result
        assert "endIndex" not in result

    def test_extract_citation_omits_none_indices(self) -> None:
        block = {
            "type": "citation",
            "source": {
                "type": "document",
                "id": "doc-999",
                "title": "Test Doc",
            },
            "cited_text": "quoted text",
        }

        result = _extract_citation(block)

        assert result is not None
        assert result["sourceType"] == "document"
        assert result["sourceId"] == "doc-999"
        assert result["citedText"] == "quoted text"
        assert "startIndex" not in result
        assert "endIndex" not in result


class TestConfigureSDKMemoryAndCitations:
    """T57/T58/T59: Verify configure_sdk_for_space passes memory and citations flags."""

    def test_configure_sdk_passes_memory_and_citations(self, tmp_path: Path) -> None:
        space_context = SpaceContext(
            id="test-space-001",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            memory_enabled=True,
            citations_enabled=True,
        )

        params = config.to_sdk_params()
        assert params["memory"] is True
        assert params["citations"] is True

    def test_configure_sdk_omits_flags_when_disabled(self, tmp_path: Path) -> None:
        space_context = SpaceContext(
            id="test-space-002",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            memory_enabled=False,
            citations_enabled=False,
        )

        params = config.to_sdk_params()
        assert "memory" not in params
        assert "citations" not in params

    def test_configure_sdk_defaults_flags_to_false(self, tmp_path: Path) -> None:
        space_context = SpaceContext(
            id="test-space-003",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(space_context)

        params = config.to_sdk_params()
        assert "memory" not in params
        assert "citations" not in params
