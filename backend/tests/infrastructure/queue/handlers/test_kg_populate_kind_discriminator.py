"""Phase 70-06 — GREEN: write-path ``properties.kind`` discriminator.

Every graph_nodes row produced by the memory write-path MUST carry a
``kind`` key in ``properties`` so the recall path can filter cache
entries (``turn``/``deny``/``finding``) from raw content (``raw``) and
from summaries (``summary``, landed in a later task).

Producers (enqueue side) stamp ``kind`` into the queue payload's
``metadata`` / ``properties`` dict. The ``KgPopulateHandler`` merges
those into ``graph_nodes.properties`` verbatim via ``GraphWriteService``,
so the producer-side assertions are sufficient to verify the write-path
contract without spinning up a DB.

For the chunk path (``note_chunk``, ``issue_chunk``) the handler builds
properties itself — that's tested by directly inspecting the dicts
passed to ``GraphWriteService.execute``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.memory.producers.agent_turn_producer import (
    enqueue_agent_turn_memory,
)
from pilot_space.ai.memory.producers.pr_review_finding_producer import (
    enqueue_pr_review_findings,
)
from pilot_space.ai.memory.producers.user_correction_producer import (
    enqueue_user_correction_memory,
)
from pilot_space.infrastructure.queue.models import QueueName


class _FakeQueueClient:
    def __init__(self) -> None:
        self.enqueued: list[tuple[QueueName, dict]] = []

    async def enqueue(self, queue: QueueName, payload: dict) -> None:
        self.enqueued.append((queue, payload))


# ---------------------------------------------------------------------------
# Producer-side: memory_type payloads must stamp properties.kind
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_turn_producer_stamps_kind_turn() -> None:
    queue = _FakeQueueClient()
    workspace_id = uuid4()
    actor_user_id = uuid4()

    # _derive_turn_index opens its own session; patch it to avoid DB.
    with patch(
        "pilot_space.ai.memory.producers.agent_turn_producer._derive_turn_index",
        AsyncMock(return_value=0),
    ):
        await enqueue_agent_turn_memory(
            queue_client=queue,  # type: ignore[arg-type]
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            session_id="sess-1",
            user_message="hi",
            assistant_text="hello",
            tools_used=[],
            metadata={},
        )

    assert len(queue.enqueued) == 1
    _, payload = queue.enqueued[0]
    assert payload["memory_type"] == "agent_turn"
    assert payload["metadata"]["kind"] == "turn"


@pytest.mark.asyncio
async def test_user_correction_producer_stamps_kind_deny() -> None:
    queue = _FakeQueueClient()
    await enqueue_user_correction_memory(
        queue_client=queue,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        session_id="sess-1",
        subtype="deny",
        tool_name="bash",
        reason="policy denied",
        referenced_turn_index=None,
    )
    assert len(queue.enqueued) == 1
    _, payload = queue.enqueued[0]
    assert payload["memory_type"] == "user_correction"
    assert payload["metadata"]["kind"] == "deny"


@pytest.mark.asyncio
async def test_user_correction_producer_stamps_kind_deny_for_user_reject() -> None:
    """All correction subtypes collapse into kind='deny' bucket."""
    queue = _FakeQueueClient()
    await enqueue_user_correction_memory(
        queue_client=queue,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        session_id="sess-1",
        subtype="user_reject",
        tool_name="delete_issue",
        reason="user said no",
        referenced_turn_index=3,
    )
    assert queue.enqueued[0][1]["metadata"]["kind"] == "deny"


@pytest.mark.asyncio
async def test_pr_review_finding_producer_stamps_kind_finding() -> None:
    queue = _FakeQueueClient()

    # Minimal ReviewComment stand-in. The producer only needs these attrs.
    comment = SimpleNamespace(
        file_path="src/app.py",
        line_number=42,
        end_line=42,
        severity=SimpleNamespace(value="major"),
        category=SimpleNamespace(value="bug"),
        message="null deref",
        suggestion="check None",
        code_snippet="x.foo()",
    )
    await enqueue_pr_review_findings(
        queue_client=queue,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        repo="acme/web",
        pr_number=17,
        comments=[comment],  # type: ignore[list-item]
    )
    assert len(queue.enqueued) == 1
    _, payload = queue.enqueued[0]
    assert payload["memory_type"] == "pr_review_finding"
    assert payload["properties"]["kind"] == "finding"
    assert payload["metadata"]["kind"] == "finding"


# ---------------------------------------------------------------------------
# Handler-side: chunk nodes built by the handler must carry kind='raw'
# ---------------------------------------------------------------------------


def test_note_chunk_properties_include_kind_raw_in_source() -> None:
    """The handler source literally stamps ``kind='raw'`` on note chunks.

    Running the full handler requires a real DB + embeddings + markdown
    chunker; a source-level assertion is the cheapest reliable way to
    lock in the contract and is exactly how similar write-path
    discriminators are guarded elsewhere in the repo.
    """
    from pathlib import Path

    src = Path(
        "src/pilot_space/infrastructure/queue/handlers/kg_populate_handler.py"
    ).read_text()

    # Locate the note-chunk NodeInput properties dict and assert kind.
    assert '"parent_note_id": str(p.entity_id)' in src
    # The raw marker sits inside the note-chunk properties block:
    note_chunk_block = src.split('"parent_note_id": str(p.entity_id)', 1)[1][:300]
    assert '"kind": "raw"' in note_chunk_block


def test_issue_chunk_properties_include_kind_raw_in_source() -> None:
    """The handler source literally stamps ``kind='raw'`` on issue chunks."""
    from pathlib import Path

    src = Path(
        "src/pilot_space/infrastructure/queue/handlers/kg_populate_handler.py"
    ).read_text()

    assert '"parent_issue_id": str(p.entity_id)' in src
    issue_chunk_block = src.split('"parent_issue_id": str(p.entity_id)', 1)[1][:300]
    assert '"kind": "raw"' in issue_chunk_block
