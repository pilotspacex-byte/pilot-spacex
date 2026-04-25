"""Unit tests for the workspace_notes_topic_tree router (Phase 93 Plan 02).

Covers all three endpoints + the service-exception → RFC 7807 contract:

  * ``GET  /workspaces/{ws}/notes/{id}/children``  (paginated)
  * ``GET  /workspaces/{ws}/notes/{id}/ancestors`` (root → leaf)
  * ``POST /workspaces/{ws}/notes/{id}/move``      (cycle / max-depth / cross-ws / not-found)

The handlers themselves are exercised directly with mocked deps (no HTTP
layer) because RLS context + httpx + DI overrides for the move endpoint
would require committed-session integration tests against a real Postgres,
which is out of scope per CLAUDE.md gotcha #5 (test DB is SQLite). The
exception-translation contract is fully verified at the service-layer in
``tests/application/services/test_topic_tree_service.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.workspace_notes_topic_tree import (
    list_topic_ancestors,
    list_topic_children,
    move_topic,
)
from pilot_space.api.v1.schemas.base import PaginatedResponse
from pilot_space.api.v1.schemas.note import MoveTopicRequest, NoteResponse
from pilot_space.application.services.note.topic_tree_service import (
    GetChildrenPayload,
    GetChildrenResult,
)
from pilot_space.domain.exceptions import (
    ForbiddenError,
    NotFoundError,
    TopicCycleError,
    TopicMaxDepthExceededError,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


_RLS_PATCH = "pilot_space.api.v1.routers.workspace_notes_topic_tree.set_rls_context"


def _make_note(
    workspace_id: UUID,
    *,
    parent_topic_id: UUID | None = None,
    topic_depth: int = 0,
    title: str = "Topic",
) -> MagicMock:
    """Build a minimal ORM-ish note mock for _note_to_response."""
    now = datetime.now(UTC)
    note = MagicMock()
    note.id = uuid4()
    note.created_at = now
    note.updated_at = now
    note.workspace_id = workspace_id
    note.project_id = None
    note.title = title
    note.is_pinned = False
    note.word_count = 0
    note.owner_id = uuid4()
    note.icon_emoji = None
    note.parent_topic_id = parent_topic_id
    note.topic_depth = topic_depth
    return note


def _make_workspace(ws_id: UUID | None = None) -> MagicMock:
    ws = MagicMock()
    ws.id = ws_id or uuid4()
    return ws


def _workspace_repo(ws: MagicMock) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id_scalar.return_value = ws
    repo.get_by_slug_scalar.return_value = ws
    return repo


def _topic_tree_service(
    *,
    children_result: GetChildrenResult | None = None,
    ancestors_result: list | None = None,
    move_result: MagicMock | None = None,
    move_raises: Exception | None = None,
) -> AsyncMock:
    svc = AsyncMock()
    svc.get_children.return_value = children_result
    svc.get_ancestors.return_value = ancestors_result or []
    if move_raises is not None:
        svc.move_topic.side_effect = move_raises
    else:
        svc.move_topic.return_value = move_result
    return svc


# ── GET /children ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListTopicChildren:
    async def test_returns_paginated_response_with_camelcase_keys(self) -> None:
        ws = _make_workspace()
        note_id = uuid4()
        child1 = _make_note(ws.id, parent_topic_id=note_id, topic_depth=1)
        child2 = _make_note(ws.id, parent_topic_id=note_id, topic_depth=1)
        svc = _topic_tree_service(
            children_result=GetChildrenResult(rows=[child1, child2], total=5)
        )

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await list_topic_children(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=note_id,
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
                page=1,
                page_size=2,
            )

        assert isinstance(response, PaginatedResponse)
        assert response.total == 5
        assert response.page_size == 2
        assert response.has_next is True
        assert response.has_prev is False
        assert len(response.items) == 2
        # camelCase aliases on the wire (topicDepth / parentTopicId)
        dumped = response.model_dump(by_alias=True)
        assert "items" in dumped
        first_item = dumped["items"][0]
        assert "topicDepth" in first_item
        assert "parentTopicId" in first_item

    async def test_passes_resolved_workspace_id_and_note_id_to_service(self) -> None:
        ws = _make_workspace()
        note_id = uuid4()
        svc = _topic_tree_service(children_result=GetChildrenResult(rows=[], total=0))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await list_topic_children(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=note_id,
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
                page=3,
                page_size=10,
            )

        payload: GetChildrenPayload = svc.get_children.call_args.args[0]
        assert payload.workspace_id == ws.id
        assert payload.parent_topic_id == note_id
        assert payload.page == 3
        assert payload.page_size == 10

    async def test_empty_children_returns_empty_items(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(children_result=GetChildrenResult(rows=[], total=0))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await list_topic_children(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        assert response.items == []
        assert response.total == 0
        assert response.has_next is False


# ── GET /ancestors ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListTopicAncestors:
    async def test_returns_root_to_leaf_chain(self) -> None:
        ws = _make_workspace()
        root = _make_note(ws.id, parent_topic_id=None, topic_depth=0, title="root")
        middle = _make_note(ws.id, parent_topic_id=root.id, topic_depth=1, title="middle")
        leaf = _make_note(ws.id, parent_topic_id=middle.id, topic_depth=2, title="leaf")
        svc = _topic_tree_service(ancestors_result=[root, middle, leaf])

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await list_topic_ancestors(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=leaf.id,
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        assert len(response) == 3
        # Order preserved: root → leaf
        assert response[0].title == "root"
        assert response[1].title == "middle"
        assert response[2].title == "leaf"
        # Topic-tree fields surfaced
        assert response[0].topic_depth == 0
        assert response[2].topic_depth == 2

    async def test_returns_empty_list_when_note_missing(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(ancestors_result=[])

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await list_topic_ancestors(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        assert response == []


# ── POST /move ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMoveTopicSuccess:
    async def test_move_to_root_sets_parent_id_null(self) -> None:
        ws = _make_workspace()
        note_id = uuid4()
        moved = _make_note(ws.id, parent_topic_id=None, topic_depth=0)
        svc = _topic_tree_service(move_result=moved)

        session = AsyncMock()
        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_topic(
                session=session,
                workspace_id=str(ws.id),
                note_id=note_id,
                payload=MoveTopicRequest(parent_id=None),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        assert isinstance(response, NoteResponse)
        assert response.parent_topic_id is None
        assert response.topic_depth == 0
        svc.move_topic.assert_awaited_once_with(note_id, None)
        session.commit.assert_awaited_once()

    async def test_move_to_parent_sets_parent_and_depth(self) -> None:
        ws = _make_workspace()
        note_id = uuid4()
        new_parent_id = uuid4()
        moved = _make_note(ws.id, parent_topic_id=new_parent_id, topic_depth=2)
        svc = _topic_tree_service(move_result=moved)

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_topic(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=note_id,
                payload=MoveTopicRequest(parent_id=new_parent_id),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        assert response.parent_topic_id == new_parent_id
        assert response.topic_depth == 2
        svc.move_topic.assert_awaited_once_with(note_id, new_parent_id)


# ── Service exceptions propagate (no try/except in router) ───────────────────


@pytest.mark.asyncio
class TestMoveTopicExceptionsPropagate:
    """Router does NOT wrap service exceptions — they propagate to the global
    app_error_handler which produces RFC 7807 problem+json. These tests assert
    the router doesn't accidentally catch + remap them.
    """

    async def test_topic_cycle_error_propagates(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(move_raises=TopicCycleError())

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(TopicCycleError) as exc_info,
        ):
            await move_topic(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                payload=MoveTopicRequest(parent_id=uuid4()),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )
        assert exc_info.value.error_code == "topic_cycle_rejected"
        assert exc_info.value.http_status == 409

    async def test_max_depth_exceeded_error_propagates(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(move_raises=TopicMaxDepthExceededError())

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(TopicMaxDepthExceededError) as exc_info,
        ):
            await move_topic(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                payload=MoveTopicRequest(parent_id=uuid4()),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )
        assert exc_info.value.error_code == "topic_max_depth_exceeded"
        assert exc_info.value.http_status == 409

    async def test_cross_workspace_forbidden_propagates(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(
            move_raises=ForbiddenError(
                "Cannot move a topic across workspaces",
                error_code="cross_workspace_move",
            )
        )

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(ForbiddenError) as exc_info,
        ):
            await move_topic(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                payload=MoveTopicRequest(parent_id=uuid4()),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )
        assert exc_info.value.error_code == "cross_workspace_move"
        assert exc_info.value.http_status == 403

    async def test_topic_not_found_propagates(self) -> None:
        ws = _make_workspace()
        svc = _topic_tree_service(
            move_raises=NotFoundError("Topic not found", error_code="topic_not_found")
        )

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(NotFoundError) as exc_info,
        ):
            await move_topic(
                session=AsyncMock(),
                workspace_id=str(ws.id),
                note_id=uuid4(),
                payload=MoveTopicRequest(parent_id=None),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )
        assert exc_info.value.error_code == "topic_not_found"
        assert exc_info.value.http_status == 404

    async def test_session_not_committed_when_service_raises(self) -> None:
        """If the service raises, the router must NOT call session.commit().

        The repository's begin_nested savepoint already rolled back; an extra
        outer commit would persist whatever the rest of the request had
        accumulated. Defensive-by-design.
        """
        ws = _make_workspace()
        svc = _topic_tree_service(move_raises=TopicCycleError())
        session = AsyncMock()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(TopicCycleError),
        ):
            await move_topic(
                session=session,
                workspace_id=str(ws.id),
                note_id=uuid4(),
                payload=MoveTopicRequest(parent_id=uuid4()),
                current_user_id=uuid4(),
                topic_tree=svc,
                workspace_repo=_workspace_repo(ws),
            )

        session.commit.assert_not_awaited()


# ── MoveTopicRequest schema sanity (sync) ────────────────────────────────────
# Module-level functions (not class) so they don't inherit the asyncio mark.


def test_move_topic_request_accepts_camelcase_parentId_alias() -> None:
    """Frontend sends ``parentId`` (camelCase); BaseSchema accepts both."""
    pid = uuid4()
    req = MoveTopicRequest.model_validate({"parentId": str(pid)})
    assert req.parent_id == pid


def test_move_topic_request_accepts_snake_case_parent_id() -> None:
    pid = uuid4()
    req = MoveTopicRequest.model_validate({"parent_id": str(pid)})
    assert req.parent_id == pid


def test_move_topic_request_default_parent_id_is_none() -> None:
    req = MoveTopicRequest()
    assert req.parent_id is None
