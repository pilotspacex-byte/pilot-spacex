"""Workspace-scoped editor plugin CRUD router.

Endpoints (mounted under /api/v1/workspaces/{workspace_id}/editor-plugins):
  GET    ""                   -> list all plugins (any member)
  GET    "/enabled"           -> list enabled plugins only (any member)
  POST   ""                   -> upload plugin (admin/owner only, multipart)
  PATCH  "/{plugin_id}/status" -> toggle enable/disable (admin/owner)
  DELETE "/{plugin_id}"       -> delete plugin (admin/owner)

Gotchas applied:
  - session: SessionDep declared on every handler (Gotcha #1)
  - Root collection routes use "" not "/" (project memory)
  - Uses direct instantiation pattern (not @inject DI)

Source: Phase 45, PLUG-01..03
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel as PydanticBaseModel

from pilot_space.dependencies.auth import (
    CurrentUserId,
    SessionDep,
    WorkspaceAdminId,
    WorkspaceMemberId,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/editor-plugins",
    tags=["Editor Plugins"],
)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EditorPluginResponse(PydanticBaseModel):
    """API response for an editor plugin."""

    id: UUID
    workspace_id: UUID
    name: str
    version: str
    display_name: str
    description: str
    author: str
    status: str
    manifest: dict  # type: ignore[type-arg]
    storage_path: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PluginStatusUpdate(PydanticBaseModel):
    """Request body for toggling plugin status."""

    status: str  # 'enabled' | 'disabled'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plugin_to_response(plugin: object) -> EditorPluginResponse:
    """Convert ORM model to response schema."""
    from pilot_space.infrastructure.database.models.editor_plugin import EditorPlugin

    p: EditorPlugin = plugin  # type: ignore[assignment]
    return EditorPluginResponse(
        id=p.id,
        workspace_id=p.workspace_id,
        name=p.name,
        version=p.version,
        display_name=p.display_name,
        description=p.description,
        author=p.author,
        status=p.status,
        manifest=p.manifest,
        storage_path=p.storage_path,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


def _get_service(session: SessionDep):  # type: ignore[no-untyped-def]
    """Create an EditorPluginService with repository and storage client."""
    from pilot_space.application.services.editor_plugin import EditorPluginService
    from pilot_space.infrastructure.database.repositories.editor_plugin_repository import (
        EditorPluginRepository,
    )
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

    repo = EditorPluginRepository(session)
    storage = SupabaseStorageClient()
    return EditorPluginService(
        session=session,
        editor_plugin_repo=repo,
        storage_client=storage,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[EditorPluginResponse],
    summary="List all editor plugins",
)
async def list_editor_plugins(
    workspace_id: UUID,
    session: SessionDep,
    _member: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> list[EditorPluginResponse]:
    """Return all installed editor plugins for this workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
    svc = _get_service(session)
    plugins = await svc.list_plugins(workspace_id)
    return [_plugin_to_response(p) for p in plugins]


@router.get(
    "/enabled",
    response_model=list[EditorPluginResponse],
    summary="List enabled editor plugins",
)
async def list_enabled_editor_plugins(
    workspace_id: UUID,
    session: SessionDep,
    _member: WorkspaceMemberId,
    current_user_id: CurrentUserId,
) -> list[EditorPluginResponse]:
    """Return enabled editor plugins for this workspace (editor bootstrap)."""
    await set_rls_context(session, current_user_id, workspace_id)
    svc = _get_service(session)
    plugins = await svc.get_enabled_plugins(workspace_id)
    return [_plugin_to_response(p) for p in plugins]


@router.post(
    "",
    response_model=EditorPluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload editor plugin",
)
async def upload_editor_plugin(
    workspace_id: UUID,
    manifest: str,
    bundle: UploadFile,
    session: SessionDep,
    _admin: WorkspaceAdminId,
    current_user_id: CurrentUserId,
) -> EditorPluginResponse:
    """Upload a new editor plugin (multipart form: manifest JSON + JS bundle).

    Args:
        workspace_id: Target workspace UUID.
        manifest: JSON string of the plugin manifest.
        bundle: JS bundle file upload (max 1MB).
        session: DB session (Gotcha #1).
        _admin: Admin guard.
        current_user_id: Authenticated user.

    Returns:
        Created EditorPluginResponse (201).
    """
    await set_rls_context(session, current_user_id, workspace_id)

    # Parse manifest JSON
    try:
        manifest_dict = json.loads(manifest)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid manifest JSON: {exc}",
        ) from exc

    if not isinstance(manifest_dict, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manifest must be a JSON object",
        )

    # Read bundle bytes
    js_content = await bundle.read()
    if not js_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bundle file is empty",
        )

    svc = _get_service(session)
    try:
        plugin = await svc.upload_plugin(
            workspace_id=workspace_id,
            manifest_dict=manifest_dict,
            js_content=js_content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    logger.info(
        "editor_plugin_uploaded",
        workspace_id=str(workspace_id),
        plugin_name=manifest_dict.get("name"),
    )
    return _plugin_to_response(plugin)


@router.patch(
    "/{plugin_id}/status",
    response_model=EditorPluginResponse,
    summary="Toggle editor plugin status",
)
async def toggle_editor_plugin(
    workspace_id: UUID,
    plugin_id: UUID,
    body: PluginStatusUpdate,
    session: SessionDep,
    _admin: WorkspaceAdminId,
    current_user_id: CurrentUserId,
) -> EditorPluginResponse:
    """Enable or disable an editor plugin."""
    await set_rls_context(session, current_user_id, workspace_id)
    svc = _get_service(session)
    try:
        plugin = await svc.toggle_plugin(plugin_id, body.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Verify workspace ownership
    if plugin.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found",
        )

    return _plugin_to_response(plugin)


@router.delete(
    "/{plugin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete editor plugin",
)
async def delete_editor_plugin(
    workspace_id: UUID,
    plugin_id: UUID,
    session: SessionDep,
    _admin: WorkspaceAdminId,
    current_user_id: CurrentUserId,
) -> None:
    """Delete an editor plugin and remove its bundle from storage."""
    await set_rls_context(session, current_user_id, workspace_id)

    # Verify plugin belongs to workspace before deleting
    from pilot_space.infrastructure.database.repositories.editor_plugin_repository import (
        EditorPluginRepository,
    )

    repo = EditorPluginRepository(session)
    plugin = await repo.get_by_id(plugin_id)
    if plugin is None or plugin.is_deleted or plugin.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found",
        )

    svc = _get_service(session)
    try:
        await svc.delete_plugin(plugin_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    logger.info(
        "editor_plugin_deleted",
        workspace_id=str(workspace_id),
        plugin_id=str(plugin_id),
    )


__all__ = ["router"]
