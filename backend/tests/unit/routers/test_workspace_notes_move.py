"""Unit tests for move_workspace_note endpoint in workspace_notes router.

Covers all conditional branches in the move_workspace_note handler:
- successful move to a project (move_data.project_id is set)
- successful move to root workspace (move_data.project_id is None)
- note not found (note_repo returns None)
- note workspace mismatch (note.workspace_id != workspace.id)
- project not found (project_repo returns None when project_id provided)
- project workspace mismatch (project.workspace_id != workspace.id)
- NotFoundError raised by UpdateNoteService.execute → JSONResponse 404
- workspace not found (workspace_repo returns None) → HTTPException 404

Handler under test:
    pilot_space.api.v1.routers.workspace_notes.move_workspace_note
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from pilot_space.api.v1.routers.workspace_notes import move_workspace_note
from pilot_space.api.v1.schemas.note import NoteMove, NoteResponse
from pilot_space.application.services.note.update_note_service import UpdateNoteResult

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(workspace_id: UUID, project_id: UUID | None = None) -> MagicMock:
    """Build a minimal Note mock compatible with _note_to_response."""
    now = datetime.now(UTC)
    note = MagicMock()
    note.id = uuid4()
    note.created_at = now
    note.updated_at = now
    note.workspace_id = workspace_id
    note.project_id = project_id
    note.title = "Test Note"
    note.is_pinned = False
    note.word_count = 10
    note.owner_id = uuid4()
    note.icon_emoji = None
    return note


def _make_workspace(workspace_id: UUID | None = None) -> MagicMock:
    ws = MagicMock()
    ws.id = workspace_id or uuid4()
    return ws


def _make_project(workspace_id: UUID) -> MagicMock:
    project = MagicMock()
    project.id = uuid4()
    project.workspace_id = workspace_id
    return project


def _workspace_repo(workspace: MagicMock) -> AsyncMock:
    """Repo that returns workspace from both scalar and non-scalar lookups."""
    repo = AsyncMock()
    # _resolve_workspace calls get_by_id_scalar / get_by_slug_scalar
    repo.get_by_id_scalar.return_value = workspace
    repo.get_by_slug_scalar.return_value = workspace
    return repo


def _note_repo(note: MagicMock | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id.return_value = note
    return repo


def _project_repo(project: MagicMock | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id.return_value = project
    return repo


def _update_service(
    result: UpdateNoteResult | None = None,
    raises: Exception | None = None,
) -> AsyncMock:
    svc = AsyncMock()
    if raises is not None:
        svc.execute.side_effect = raises
    else:
        svc.execute.return_value = result
    return svc


def _result(note: MagicMock) -> UpdateNoteResult:
    return UpdateNoteResult(
        note=note,
        word_count=note.word_count,
        reading_time_mins=1,
        fields_updated=["project_id"],
    )


# Patch target for set_rls_context used inside the router module
_RLS_PATCH = "pilot_space.api.v1.routers.workspace_notes.set_rls_context"


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


class TestMoveToProject:
    """move_data.project_id is set — project lookup branch executed."""

    async def test_returns_note_response_with_project_id(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        project = _make_project(ws_id)
        note = _make_note(ws_id)
        updated = _make_note(ws_id, project_id=project.id)

        svc = _update_service(result=_result(updated))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=project.id),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(project),
            )

        assert isinstance(response, NoteResponse)
        assert response.project_id == project.id
        svc.execute.assert_awaited_once()

    async def test_payload_has_correct_project_id_and_clear_false(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        project = _make_project(ws_id)
        note = _make_note(ws_id)
        updated = _make_note(ws_id, project_id=project.id)

        svc = _update_service(result=_result(updated))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=project.id),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(project),
            )

        payload = svc.execute.call_args.args[0]
        assert payload.project_id == project.id
        assert payload.clear_project_id is False

    async def test_project_repo_queried_with_move_data_project_id(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        project = _make_project(ws_id)
        note = _make_note(ws_id)

        proj_repo = _project_repo(project)
        svc = _update_service(result=_result(_make_note(ws_id, project_id=project.id)))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=project.id),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=proj_repo,
            )

        proj_repo.get_by_id.assert_awaited_once_with(project.id)


class TestMoveToRoot:
    """move_data.project_id is None — project lookup branch skipped."""

    async def test_returns_note_response_with_no_project(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id, project_id=uuid4())
        updated = _make_note(ws_id, project_id=None)

        proj_repo = _project_repo()
        svc = _update_service(result=_result(updated))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=proj_repo,
            )

        assert isinstance(response, NoteResponse)
        assert response.project_id is None

    async def test_project_repo_not_called_when_project_id_none(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)
        updated = _make_note(ws_id, project_id=None)

        proj_repo = _project_repo()
        svc = _update_service(result=_result(updated))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=proj_repo,
            )

        proj_repo.get_by_id.assert_not_awaited()

    async def test_payload_has_clear_project_id_true(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)
        updated = _make_note(ws_id, project_id=None)

        svc = _update_service(result=_result(updated))

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(),
            )

        payload = svc.execute.call_args.args[0]
        assert payload.clear_project_id is True
        assert payload.project_id is None

    async def test_logger_info_called_on_success(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)
        updated = _make_note(ws_id, project_id=None)

        svc = _update_service(result=_result(updated))

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            patch("pilot_space.api.v1.routers.workspace_notes.logger") as mock_logger,
        ):
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(),
            )

        mock_logger.info.assert_called_once()
        assert "Note moved" in mock_logger.info.call_args.args[0]


# ---------------------------------------------------------------------------
# JSONResponse 404 branches — note validation
# ---------------------------------------------------------------------------


class TestNoteNotFound:
    """note_repo.get_by_id returns None → JSONResponse 404."""

    async def test_returns_json_response_404(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=uuid4(),
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(None),  # note missing
                project_repo=_project_repo(),
            )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        body = json.loads(response.body)
        assert "Note not found" in body.get("detail", "")


class TestNoteWorkspaceMismatch:
    """note.workspace_id != workspace.id → JSONResponse 404."""

    async def test_returns_json_response_404(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        # Note belongs to a *different* workspace
        note = _make_note(workspace_id=uuid4())

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(),
            )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        body = json.loads(response.body)
        assert "Note not found" in body.get("detail", "")


# ---------------------------------------------------------------------------
# JSONResponse 404 branches — project validation
# ---------------------------------------------------------------------------


class TestProjectNotFound:
    """project_repo.get_by_id returns None when project_id provided → JSONResponse 404."""

    async def test_returns_json_response_404(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=uuid4()),  # project_id is set
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(None),  # project missing
            )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        body = json.loads(response.body)
        assert "Project not found" in body.get("detail", "")


class TestProjectWorkspaceMismatch:
    """project.workspace_id != workspace.id → JSONResponse 404."""

    async def test_returns_json_response_404(self) -> None:
        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)
        # Project belongs to a *different* workspace
        project = _make_project(workspace_id=uuid4())

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            response = await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=project.id),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(project),
            )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        body = json.loads(response.body)
        assert "Project not found" in body.get("detail", "")


# ---------------------------------------------------------------------------
# HTTPException 404 — workspace resolution (raised by _resolve_workspace)
# ---------------------------------------------------------------------------


class TestWorkspaceNotFound:
    """_resolve_workspace raises HTTPException 404 when workspace is missing."""

    async def test_uuid_workspace_not_found_raises_404(self) -> None:
        ws_repo = AsyncMock()
        ws_repo.get_by_id_scalar.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await move_workspace_note(
                workspace_id=str(uuid4()),
                note_id=uuid4(),
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=ws_repo,
                note_repo=_note_repo(),
                project_repo=_project_repo(),
            )

        assert exc_info.value.status_code == 404
        assert "Workspace not found" in exc_info.value.detail

    async def test_slug_workspace_not_found_raises_404(self) -> None:
        ws_repo = AsyncMock()
        ws_repo.get_by_slug_scalar.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await move_workspace_note(
                workspace_id="my-nonexistent-workspace",  # slug path
                note_id=uuid4(),
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=_update_service(),
                workspace_repo=ws_repo,
                note_repo=_note_repo(),
                project_repo=_project_repo(),
            )

        assert exc_info.value.status_code == 404
        assert "Workspace not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# NotFoundError from UpdateNoteService.execute
# ---------------------------------------------------------------------------


class TestServiceNotFoundError:
    """NotFoundError raised by update_service.execute → propagates to global handler."""

    async def test_raises_not_found_error(self) -> None:
        from pilot_space.domain.exceptions import NotFoundError

        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)

        svc = _update_service(raises=NotFoundError("Note does not exist"))

        with patch(_RLS_PATCH, new_callable=AsyncMock), pytest.raises(NotFoundError) as exc_info:
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(),
            )

        assert exc_info.value.http_status == 404

    async def test_not_found_error_detail_propagated(self) -> None:
        from pilot_space.domain.exceptions import NotFoundError

        ws_id = uuid4()
        workspace = _make_workspace(ws_id)
        note = _make_note(ws_id)
        error_msg = "note record missing from database"

        svc = _update_service(raises=NotFoundError(error_msg))

        with patch(_RLS_PATCH, new_callable=AsyncMock), pytest.raises(NotFoundError) as exc_info:
            await move_workspace_note(
                workspace_id=str(ws_id),
                note_id=note.id,
                move_data=NoteMove(project_id=None),
                current_user_id=uuid4(),
                session=AsyncMock(),
                update_service=svc,
                workspace_repo=_workspace_repo(workspace),
                note_repo=_note_repo(note),
                project_repo=_project_repo(),
            )

        assert error_msg in exc_info.value.message
