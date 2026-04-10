"""Phase 70 Wave 2 (PROD-03) — pr_review_finding memory producer tests.

Contract:

    1. One ``pr_review_finding`` memory payload per ``ReviewComment``. Each
       payload carries ``workspace_id``, ``actor_user_id``, ``repo``,
       ``pr_number``, ``file_path``, ``line_number`` (all stringified under
       ``properties`` so the migration 107 partial unique index casts cleanly).
    2. A failing enqueue for one comment does NOT abort the rest of the
       batch — producer is fire-and-forget per comment.
    3. ``enabled=False`` short-circuits the batch with a single
       ``dropped{reason=opt_out}`` record.
    4. Multiple findings on the same file at different lines each produce
       their own enqueue (the partial unique index is keyed on line).
    5. The ``PRReviewSubagent.emit_review_findings`` seam schedules the
       producer as a background task without awaiting it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.memory.producers.pr_review_finding_producer import (
    enqueue_pr_review_findings,
)
from pilot_space.ai.telemetry.memory_metrics import (
    get_producer_counters,
    reset_producer_counters,
)
from pilot_space.api.v1.schemas.pr_review import (
    ReviewCategory,
    ReviewComment,
    ReviewSeverity,
)


def _comment(file_path: str = "src/foo.py", line_number: int = 10) -> ReviewComment:
    return ReviewComment(
        file_path=file_path,
        line_number=line_number,
        end_line=None,
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.QUALITY,
        message=f"issue at {file_path}:{line_number}",
        suggestion="fix it",
        code_snippet=None,
    )


@pytest.fixture(autouse=True)
def _reset_counters() -> None:
    reset_producer_counters()
    yield
    reset_producer_counters()


async def test_subagent_emits_one_finding_per_review_comment() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock(return_value="msg-id")

    workspace_id = uuid4()
    actor_user_id = uuid4()
    comments = [
        _comment("src/a.py", 1),
        _comment("src/b.py", 42),
        _comment("src/c.py", 7),
    ]

    await enqueue_pr_review_findings(
        queue_client=queue_client,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        repo="owner/repo",
        pr_number=123,
        comments=comments,
    )

    assert queue_client.enqueue.await_count == 3
    counters = get_producer_counters()
    assert counters["enqueued"].get("pr_review_finding") == 3

    # Inspect first payload for required keys + types.
    first_call = queue_client.enqueue.await_args_list[0]
    _queue_name, payload = first_call.args
    assert payload["memory_type"] == "pr_review_finding"
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["actor_user_id"] == str(actor_user_id)
    assert payload["task_type"] == "kg_populate"
    assert payload["content"] == "issue at src/a.py:1"

    props = payload["properties"]
    # Stringified to match migration 107 partial index cast semantics.
    assert props["repo"] == "owner/repo"
    assert props["pr_number"] == "123"
    assert props["file_path"] == "src/a.py"
    assert props["line_number"] == "1"
    assert props["severity"] == ReviewSeverity.WARNING.value
    assert props["category"] == ReviewCategory.QUALITY.value


async def test_empty_comment_list_enqueues_nothing() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()

    await enqueue_pr_review_findings(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        repo="owner/repo",
        pr_number=1,
        comments=[],
    )

    queue_client.enqueue.assert_not_awaited()
    assert get_producer_counters()["enqueued"].get("pr_review_finding") is None


async def test_disabled_drops_entire_batch_as_opt_out() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock()

    await enqueue_pr_review_findings(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        repo="owner/repo",
        pr_number=1,
        comments=[_comment(), _comment("src/z.py", 99)],
        enabled=False,
    )

    queue_client.enqueue.assert_not_awaited()
    counters = get_producer_counters()
    assert counters["dropped"].get("pr_review_finding::opt_out") == 1


async def test_failing_enqueue_for_one_comment_does_not_stop_others() -> None:
    queue_client = MagicMock()

    # First call raises; second and third succeed.
    queue_client.enqueue = AsyncMock(
        side_effect=[RuntimeError("boom"), "ok-2", "ok-3"]
    )

    await enqueue_pr_review_findings(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        repo="owner/repo",
        pr_number=9,
        comments=[
            _comment("src/a.py", 1),
            _comment("src/b.py", 2),
            _comment("src/c.py", 3),
        ],
    )

    assert queue_client.enqueue.await_count == 3
    counters = get_producer_counters()
    assert counters["enqueued"].get("pr_review_finding") == 2
    assert counters["dropped"].get("pr_review_finding::enqueue_error") == 1


async def test_same_file_different_lines_produce_separate_enqueues() -> None:
    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock(return_value="ok")

    await enqueue_pr_review_findings(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        repo="owner/repo",
        pr_number=5,
        comments=[
            _comment("src/shared.py", 10),
            _comment("src/shared.py", 20),
            _comment("src/shared.py", 30),
        ],
    )

    assert queue_client.enqueue.await_count == 3
    lines = [
        call.args[1]["properties"]["line_number"]
        for call in queue_client.enqueue.await_args_list
    ]
    assert lines == ["10", "20", "30"]


async def test_subagent_emit_review_findings_schedules_background_task() -> None:
    """The subagent seam dispatches the producer without awaiting it."""
    from pilot_space.ai.agents.agent_base import AgentContext
    from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

    queue_client = MagicMock()
    queue_client.enqueue = AsyncMock(return_value="ok")

    subagent = PRReviewSubagent.__new__(PRReviewSubagent)  # type: ignore[call-arg]
    subagent._queue_client = queue_client  # type: ignore[attr-defined]

    context = AgentContext(workspace_id=uuid4(), user_id=uuid4())
    comments = [_comment("src/a.py", 1), _comment("src/b.py", 2)]

    task = subagent.emit_review_findings(
        context=context,
        repo="owner/repo",
        pr_number=77,
        comments=comments,
    )
    assert task is not None
    await task  # drain the background task in tests

    assert queue_client.enqueue.await_count == 2
