"""Smoke tests for Phase 69-05 Task 02: MemoryRecallService seam swap.

Covers:
- recall_graph_context delegates to MemoryRecallService when one is provided
  and converts MemoryItem results to the legacy list-of-dict shape with
  added provenance fields (source_type, source_id, node_id).
- Graceful fallback when MemoryRecallService raises.
- format_graph_context renders a <memory> XML block with provenance
  attributes when entries exist, and an empty string when empty.
- HTML escaping inside <item> bodies.

Full end-to-end streaming is out of scope (pgvector + SDK required); we
mock the service and exercise the seam + renderer in isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_intent_pipeline import recall_graph_context
from pilot_space.ai.prompt.prompt_assembler import format_graph_context
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryItem,
    RecallResult,
)

# ---------------------------------------------------------------------------
# recall_graph_context seam
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_graph_context_delegates_to_memory_recall_service() -> None:
    """When memory_recall_service is provided, it is used and items are
    converted to the legacy dict shape with provenance fields."""
    workspace_id = uuid4()
    items = [
        MemoryItem(
            source_type="note_summary",
            source_id="note-abc",
            node_id="node-1",
            score=0.87,
            snippet="Short note snippet",
            created_at="2026-04-07T00:00:00Z",
        ),
        MemoryItem(
            source_type="decision",
            source_id="dec-xyz",
            node_id="node-2",
            score=0.82,
            snippet="Chose option A over B",
            created_at="2026-04-07T00:00:00Z",
        ),
    ]
    fake_service = AsyncMock()
    fake_service.recall = AsyncMock(
        return_value=RecallResult(items=items, cache_hit=False, elapsed_ms=12.3)
    )

    result = await recall_graph_context(
        workspace_id=workspace_id,
        user_id=None,
        query="what did we decide about auth?",
        graph_search_service=None,
        memory_recall_service=fake_service,
    )

    fake_service.recall.assert_awaited_once()
    assert len(result) == 2
    assert result[0]["source_type"] == "note_summary"
    assert result[0]["source_id"] == "note-abc"
    assert result[0]["node_id"] == "node-1"
    assert result[0]["content"] == "Short note snippet"
    assert result[0]["score"] == pytest.approx(0.87)
    assert result[1]["source_type"] == "decision"
    assert result[1]["source_id"] == "dec-xyz"


@pytest.mark.asyncio
async def test_recall_graph_context_falls_back_on_service_error() -> None:
    """When MemoryRecallService raises, we fall through gracefully (empty
    result if no legacy graph_search_service is provided)."""
    fake_service = AsyncMock()
    fake_service.recall = AsyncMock(side_effect=RuntimeError("boom"))

    result = await recall_graph_context(
        workspace_id=uuid4(),
        user_id=None,
        query="q",
        graph_search_service=None,
        memory_recall_service=fake_service,
    )
    assert result == []


@pytest.mark.asyncio
async def test_recall_graph_context_no_service_returns_empty() -> None:
    """No recall service AND no graph_search_service → empty list."""
    result = await recall_graph_context(
        workspace_id=uuid4(),
        user_id=None,
        query="q",
        graph_search_service=None,
        memory_recall_service=None,
    )
    assert result == []


# ---------------------------------------------------------------------------
# format_graph_context → <memory> XML block
# ---------------------------------------------------------------------------


def test_format_graph_context_empty_returns_empty_string() -> None:
    """No memory → no <memory> block (avoid polluting UI / wasting tokens)."""
    assert format_graph_context([]) == ""


def test_format_graph_context_renders_memory_block_with_provenance() -> None:
    """With items, renders a <memory> XML block with type/id/score attrs."""
    entries = [
        {
            "source_type": "note_summary",
            "source_id": "note-abc",
            "node_id": "node-1",
            "content": "Shipped new header",
            "score": 0.87,
        },
        {
            "source_type": "decision",
            "source_id": "dec-xyz",
            "node_id": "node-2",
            "content": "Use Supabase Auth",
            "score": 0.82,
        },
    ]
    out = format_graph_context(entries)
    assert out.startswith("<memory>")
    assert out.rstrip().endswith("</memory>")
    assert 'type="note_summary"' in out
    assert 'id="note-abc"' in out
    assert 'score="0.87"' in out
    assert "Shipped new header" in out
    assert 'type="decision"' in out
    assert 'id="dec-xyz"' in out
    assert 'score="0.82"' in out
    assert "Use Supabase Auth" in out


def test_format_graph_context_escapes_html_in_content() -> None:
    """Item content must be HTML-escaped to prevent <memory> block injection."""
    entries = [
        {
            "source_type": "note_summary",
            "source_id": "n1",
            "content": 'Evil <item type="hack"> & </item> payload',
            "score": 0.5,
        }
    ]
    out = format_graph_context(entries)
    # Raw unescaped injection must not appear
    assert '<item type="hack">' not in out
    # Escaped form must appear
    assert "&lt;item type=&quot;hack&quot;&gt;" in out
    assert "&amp;" in out


def test_format_graph_context_falls_back_to_legacy_node_type_key() -> None:
    """Back-compat: entries without source_type use node_type/label fallback."""
    entries = [
        {
            "node_type": "skill_outcome",
            "label": "legacy-id",
            "content": "legacy path",
            "score": 0.7,
        }
    ]
    out = format_graph_context(entries)
    assert 'type="skill_outcome"' in out
    assert 'id="legacy-id"' in out
    assert "legacy path" in out
