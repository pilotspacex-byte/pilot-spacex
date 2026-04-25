"""Unit tests for TopicTreeService (Phase 93 Plan 02).

Covers the typed-exception translation contract:

    | Sentinel              | Domain exception              |
    |-----------------------|-------------------------------|
    | topic_not_found       | NotFoundError                 |
    | parent_not_found      | NotFoundError                 |
    | cross_workspace_move  | ForbiddenError                |
    | topic_cycle           | TopicCycleError               |
    | topic_max_depth       | TopicMaxDepthExceededError    |

Mocks ``NoteRepository`` — these tests verify the translation layer, NOT
repository internals (those are covered by 93-01's 17 repo tests).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.note.topic_tree_service import (
    GetChildrenPayload,
    TopicTreeService,
)
from pilot_space.domain.exceptions import (
    ForbiddenError,
    NotFoundError,
    TopicCycleError,
    TopicMaxDepthExceededError,
)
from pilot_space.infrastructure.database.models.note import Note

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_repo() -> MagicMock:
    """Build a NoteRepository mock with the three topic-tree methods."""
    repo = MagicMock()
    repo.list_topic_children = AsyncMock()
    repo.list_topic_ancestors = AsyncMock()
    repo.move_topic = AsyncMock()
    return repo


def _service(repo: MagicMock) -> TopicTreeService:
    return TopicTreeService(session=MagicMock(), note_repository=repo)


def _make_note(*, parent_topic_id=None, topic_depth: int = 0, title: str = "T") -> Note:
    """Build a minimal Note ORM instance (no DB)."""
    return Note(
        id=uuid4(),
        workspace_id=uuid4(),
        owner_id=uuid4(),
        title=title,
        content={},
        parent_topic_id=parent_topic_id,
        topic_depth=topic_depth,
    )


# ── get_children ─────────────────────────────────────────────────────────────


class TestGetChildren:
    async def test_returns_paginated_result_object(self) -> None:
        """get_children wraps repo (rows, total) in GetChildrenResult."""
        ws_id, parent_id = uuid4(), uuid4()
        rows = [_make_note(), _make_note()]
        repo = _mock_repo()
        repo.list_topic_children.return_value = (rows, 7)
        svc = _service(repo)

        result = await svc.get_children(
            GetChildrenPayload(
                workspace_id=ws_id,
                parent_topic_id=parent_id,
                page=2,
                page_size=20,
            )
        )

        assert list(result.rows) == rows
        assert result.total == 7
        repo.list_topic_children.assert_awaited_once_with(
            ws_id, parent_id, page=2, page_size=20
        )

    async def test_root_listing_passes_none_parent(self) -> None:
        ws_id = uuid4()
        repo = _mock_repo()
        repo.list_topic_children.return_value = ([], 0)
        svc = _service(repo)

        await svc.get_children(
            GetChildrenPayload(workspace_id=ws_id, parent_topic_id=None)
        )
        # Default page=1, page_size=20.
        repo.list_topic_children.assert_awaited_once_with(
            ws_id, None, page=1, page_size=20
        )


# ── get_ancestors ────────────────────────────────────────────────────────────


class TestGetAncestors:
    async def test_returns_chain_root_to_leaf(self) -> None:
        repo = _mock_repo()
        chain = [_make_note(title="root"), _make_note(title="middle"), _make_note(title="leaf")]
        repo.list_topic_ancestors.return_value = chain
        svc = _service(repo)

        leaf_id = chain[-1].id
        result = await svc.get_ancestors(leaf_id)

        assert result == chain
        repo.list_topic_ancestors.assert_awaited_once_with(leaf_id)

    async def test_empty_chain_when_note_not_found(self) -> None:
        """Repo returns empty list for missing/soft-deleted note → service returns []."""
        repo = _mock_repo()
        repo.list_topic_ancestors.return_value = []
        svc = _service(repo)

        assert await svc.get_ancestors(uuid4()) == []


# ── move_topic — happy path ──────────────────────────────────────────────────


class TestMoveTopicHappyPath:
    async def test_returns_repository_result_unchanged(self) -> None:
        """No exception → service hands back the repo's Note as-is."""
        moved = _make_note(parent_topic_id=uuid4(), topic_depth=1)
        repo = _mock_repo()
        repo.move_topic.return_value = moved
        svc = _service(repo)

        result = await svc.move_topic(moved.id, moved.parent_topic_id)

        assert result is moved
        repo.move_topic.assert_awaited_once_with(moved.id, moved.parent_topic_id)

    async def test_move_to_root_passes_none_parent(self) -> None:
        moved = _make_note(parent_topic_id=None, topic_depth=0)
        repo = _mock_repo()
        repo.move_topic.return_value = moved
        svc = _service(repo)

        await svc.move_topic(moved.id, None)
        repo.move_topic.assert_awaited_once_with(moved.id, None)


# ── move_topic — sentinel translations ───────────────────────────────────────


class TestMoveTopicTranslations:
    async def test_topic_cycle_sentinel_becomes_TopicCycleError(self) -> None:
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("topic_cycle")
        svc = _service(repo)

        with pytest.raises(TopicCycleError) as exc_info:
            await svc.move_topic(uuid4(), uuid4())

        assert exc_info.value.error_code == "topic_cycle_rejected"
        assert exc_info.value.http_status == 409

    async def test_topic_max_depth_sentinel_becomes_TopicMaxDepthExceededError(self) -> None:
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("topic_max_depth")
        svc = _service(repo)

        with pytest.raises(TopicMaxDepthExceededError) as exc_info:
            await svc.move_topic(uuid4(), uuid4())

        assert exc_info.value.error_code == "topic_max_depth_exceeded"
        assert exc_info.value.http_status == 409

    async def test_cross_workspace_sentinel_becomes_ForbiddenError(self) -> None:
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("cross_workspace_move")
        svc = _service(repo)

        with pytest.raises(ForbiddenError) as exc_info:
            await svc.move_topic(uuid4(), uuid4())

        assert exc_info.value.error_code == "cross_workspace_move"
        assert exc_info.value.http_status == 403

    async def test_topic_not_found_sentinel_becomes_NotFoundError(self) -> None:
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("topic_not_found")
        svc = _service(repo)

        with pytest.raises(NotFoundError) as exc_info:
            await svc.move_topic(uuid4(), None)

        assert exc_info.value.error_code == "topic_not_found"
        assert exc_info.value.http_status == 404

    async def test_parent_not_found_sentinel_becomes_NotFoundError(self) -> None:
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("parent_not_found")
        svc = _service(repo)

        with pytest.raises(NotFoundError) as exc_info:
            await svc.move_topic(uuid4(), uuid4())

        assert exc_info.value.error_code == "parent_not_found"
        assert exc_info.value.http_status == 404

    async def test_unknown_sentinel_propagates_unchanged(self) -> None:
        """Defensive: a ValueError that doesn't match the locked sentinels
        re-raises as-is so it surfaces in logs / 500 path rather than being
        silently swallowed."""
        repo = _mock_repo()
        repo.move_topic.side_effect = ValueError("some_unexpected_thing")
        svc = _service(repo)

        with pytest.raises(ValueError, match="some_unexpected_thing"):
            await svc.move_topic(uuid4(), uuid4())

    async def test_translation_chains_original_value_error(self) -> None:
        """Translated typed exceptions preserve __cause__ for tracebacks."""
        repo = _mock_repo()
        original = ValueError("topic_cycle")
        repo.move_topic.side_effect = original
        svc = _service(repo)

        with pytest.raises(TopicCycleError) as exc_info:
            await svc.move_topic(uuid4(), uuid4())

        assert exc_info.value.__cause__ is original
