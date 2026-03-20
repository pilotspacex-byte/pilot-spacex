"""Unit tests for Knowledge Graph regeneration endpoints.

Covers:
- POST /issues/{issue_id}/knowledge-graph/regenerate
- POST /projects/{project_id}/knowledge-graph/regenerate
- Queue unavailable → 503
- Entity not found → 404
- Happy path: correct jobs enqueued
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.knowledge_graph import (
    regenerate_issue_knowledge_graph,
    regenerate_project_knowledge_graph,
)
from tests.fixtures.knowledge_graph import (
    RLS_PATCH as _RLS_PATCH,
    make_session as _make_session,
)

pytestmark = pytest.mark.asyncio

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_ISSUE_ID = UUID("dddddddd-0000-0000-0000-000000000004")
TEST_PROJECT_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")


class TestRegenerateIssue:
    async def test_queue_unavailable_returns_503(self) -> None:
        from fastapi import HTTPException

        session = _make_session()
        issue_repo = AsyncMock()

        with patch(_RLS_PATCH), pytest.raises(HTTPException) as exc_info:
            await regenerate_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                issue_repo=issue_repo,
                queue_client=None,
            )
        assert exc_info.value.status_code == 503

    async def test_issue_not_found_returns_404(self) -> None:
        from fastapi import HTTPException

        session = _make_session()
        issue_repo = AsyncMock()
        issue_repo.get_by_id = AsyncMock(return_value=None)
        queue = AsyncMock()

        with patch(_RLS_PATCH), pytest.raises(HTTPException) as exc_info:
            await regenerate_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                issue_repo=issue_repo,
                queue_client=queue,
            )
        assert exc_info.value.status_code == 404

    async def test_deleted_issue_returns_404(self) -> None:
        from fastapi import HTTPException

        session = _make_session()
        issue = MagicMock()
        issue.is_deleted = True
        issue_repo = AsyncMock()
        issue_repo.get_by_id = AsyncMock(return_value=issue)
        queue = AsyncMock()

        with patch(_RLS_PATCH), pytest.raises(HTTPException) as exc_info:
            await regenerate_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                issue_repo=issue_repo,
                queue_client=queue,
            )
        assert exc_info.value.status_code == 404

    async def test_happy_path_enqueues_job(self) -> None:
        session = _make_session()
        issue = MagicMock()
        issue.is_deleted = False
        issue.id = TEST_ISSUE_ID
        issue.project_id = TEST_PROJECT_ID
        issue.workspace_id = TEST_WORKSPACE_ID
        issue_repo = AsyncMock()
        issue_repo.get_by_id = AsyncMock(return_value=issue)
        queue = AsyncMock()
        queue.enqueue = AsyncMock()

        with patch(_RLS_PATCH):
            result = await regenerate_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                issue_repo=issue_repo,
                queue_client=queue,
            )

        assert result.enqueued == 1
        queue.enqueue.assert_called_once()
        payload = queue.enqueue.call_args[0][1]
        assert payload["task_type"] == "kg_populate"
        assert payload["entity_type"] == "issue"
        assert payload["entity_id"] == str(TEST_ISSUE_ID)


class TestRegenerateProject:
    async def test_queue_unavailable_returns_503(self) -> None:
        from fastapi import HTTPException

        session = _make_session()
        project_repo = AsyncMock()

        with patch(_RLS_PATCH), pytest.raises(HTTPException) as exc_info:
            await regenerate_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                project_repo=project_repo,
                queue_client=None,
            )
        assert exc_info.value.status_code == 503

    async def test_project_not_found_returns_404(self) -> None:
        from fastapi import HTTPException

        session = _make_session()
        project_repo = AsyncMock()
        project_repo.get_by_id = AsyncMock(return_value=None)
        queue = AsyncMock()

        with patch(_RLS_PATCH), pytest.raises(HTTPException) as exc_info:
            await regenerate_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                project_repo=project_repo,
                queue_client=queue,
            )
        assert exc_info.value.status_code == 404

    async def test_happy_path_enqueues_all_entities(self) -> None:
        session = _make_session()
        project = MagicMock()
        project.is_deleted = False
        project.workspace_id = TEST_WORKSPACE_ID
        project_repo = AsyncMock()
        project_repo.get_by_id = AsyncMock(return_value=project)
        queue = AsyncMock()
        queue.enqueue = AsyncMock()

        issue_id_1 = uuid4()
        issue_id_2 = uuid4()
        note_id_1 = uuid4()
        cycle_id_1 = uuid4()

        # Mock session.execute for the 3 entity queries
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Issues
                result.all.return_value = [(issue_id_1,), (issue_id_2,)]
            elif call_count == 2:
                # Notes
                result.all.return_value = [(note_id_1,)]
            else:
                # Cycles
                result.all.return_value = [(cycle_id_1,)]
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        with patch(_RLS_PATCH):
            result = await regenerate_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                project_repo=project_repo,
                queue_client=queue,
            )

        # 1 project + 2 issues + 1 note + 1 cycle = 5
        assert result.enqueued == 5

        # Verify all enqueue calls
        calls = queue.enqueue.call_args_list
        assert len(calls) == 5

        entity_types = [c[0][1]["entity_type"] for c in calls]
        assert entity_types[0] == "project"
        assert entity_types[1] == "issue"
        assert entity_types[2] == "issue"
        assert entity_types[3] == "note"
        assert entity_types[4] == "cycle"

    async def test_empty_project_enqueues_only_project(self) -> None:
        session = _make_session()
        project = MagicMock()
        project.is_deleted = False
        project.workspace_id = TEST_WORKSPACE_ID
        project_repo = AsyncMock()
        project_repo.get_by_id = AsyncMock(return_value=project)
        queue = AsyncMock()
        queue.enqueue = AsyncMock()

        # All entity queries return empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        with patch(_RLS_PATCH):
            result = await regenerate_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                _member=TEST_WORKSPACE_ID,
                project_repo=project_repo,
                queue_client=queue,
            )

        # Only the project itself
        assert result.enqueued == 1
        payload = queue.enqueue.call_args[0][1]
        assert payload["entity_type"] == "project"
