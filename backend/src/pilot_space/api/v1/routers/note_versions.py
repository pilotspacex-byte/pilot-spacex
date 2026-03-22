"""Note Versions API router — 11 endpoints for Feature 017.

Endpoints:
  POST   /workspaces/{ws_id}/notes/{note_id}/versions                    — manual snapshot
  GET    /workspaces/{ws_id}/notes/{note_id}/versions                    — paginated list
  GET    /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}             — single version
  GET    /workspaces/{ws_id}/notes/{note_id}/versions/{v1}/diff/{v2}     — block diff
  POST   /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}/restore     — non-destructive restore
  GET    /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}/digest      — AI digest
  GET    /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}/impact      — impact analysis
  PUT    /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}/pin         — pin/unpin
  DELETE /workspaces/{ws_id}/notes/{note_id}/versions/{v_id}             — delete (if not pinned)
  POST   /workspaces/{ws_id}/notes/{note_id}/versions/undo-ai            — undo AI changes (GAP-04)

GAP-02: trigger field exposes 'ai_before'|'ai_after' (not a boolean) + ai_before_version_id
        pairing on ai_after responses for trust UI.
GAP-04: /undo-ai fast-path restores the closest ai_before snapshot in one call.

Feature 017: Note Versioning — Sprint 1 (T-214)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from pilot_space.api.v1.schemas.base import DeleteResponse
from pilot_space.api.v1.schemas.note_version import (
    BlockDiffResponse,
    CreateVersionRequest,
    DiffResponse,
    DigestResponse,
    EntityReferenceResponse,
    ImpactResponse,
    NoteVersionListResponse,
    NoteVersionResponse,
    PinVersionRequest,
    RestoreResponse,
    RestoreVersionRequest,
    UndoAiRequest,
    UndoAiResponse,
)
from pilot_space.application.services.version.diff_service import VersionDiffService
from pilot_space.application.services.version.digest_service import VersionDigestService
from pilot_space.application.services.version.impact_service import ImpactAnalysisService
from pilot_space.application.services.version.restore_service import (
    ConcurrentRestoreError,
    RestorePayload,
    VersionRestoreService,
)
from pilot_space.application.services.version.snapshot_service import (
    SnapshotPayload,
    VersionSnapshotService,
)
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member
from pilot_space.domain.note_version import VersionTrigger
from pilot_space.infrastructure.database.models.note_version import (
    NoteVersion as NoteVersionModel,
    VersionTrigger as ModelTrigger,
)
from pilot_space.infrastructure.database.repositories.note_repository import NoteRepository
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

WorkspaceIdPath = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note UUID")]
VersionIdPath = Annotated[UUID, Path(description="Version UUID")]


def _version_to_response(
    v: NoteVersionModel,
    ai_before_version_id: UUID | None = None,
) -> NoteVersionResponse:
    """Map ORM model to response schema.

    Args:
        v: NoteVersionModel ORM instance.
        ai_before_version_id: UUID of the paired ai_before snapshot.
            Only set when v.trigger == ai_after (GAP-02).
    """
    return NoteVersionResponse(
        id=v.id,
        note_id=v.note_id,
        workspace_id=v.workspace_id,
        trigger=v.trigger.value,
        label=v.label,
        pinned=v.pinned,
        digest=v.digest,
        digest_cached_at=v.digest_cached_at,
        created_by=v.created_by,
        version_number=v.version_number,
        created_at=v.created_at,
        ai_before_version_id=ai_before_version_id,
    )


async def _resolve_ai_before_id(
    v: NoteVersionModel,
    version_repo: NoteVersionRepository,
) -> UUID | None:
    """For ai_after versions, look up the paired ai_before snapshot UUID (GAP-02).

    Returns None for non-ai_after triggers.
    """
    if v.trigger != ModelTrigger.AI_AFTER:
        return None
    paired = await version_repo.get_ai_before_for_after(
        note_id=v.note_id,
        workspace_id=v.workspace_id,
        ai_after_created_at=v.created_at,
    )
    return paired.id if paired and paired.id else None


async def _resolve_workspace_id(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepository,
) -> UUID:
    """Resolve workspace UUID from slug or UUID string."""
    try:
        return UUID(workspace_id_or_slug)
    except ValueError:
        pass
    ws = await workspace_repo.get_by_slug(workspace_id_or_slug)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws.id


@router.post(
    "/{workspace_id}/notes/{note_id}/versions",
    response_model=NoteVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual version snapshot",
    tags=["Note Versions"],
)
async def create_version(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    request: CreateVersionRequest,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteVersionResponse:
    """Manually create a point-in-time version snapshot of the note."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    note_repo = NoteRepository(session)
    version_repo = NoteVersionRepository(session)
    svc = VersionSnapshotService(session, note_repo, version_repo)

    try:
        result = await svc.execute(
            SnapshotPayload(
                note_id=note_id,
                workspace_id=ws_uuid,
                trigger=VersionTrigger.MANUAL,
                created_by=user_id,
                label=request.label,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await session.commit()

    # Fetch persisted model for response
    if result.version.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Version ID missing after create",
        )
    saved = await version_repo.get_by_id_for_note(result.version.id, note_id, ws_uuid)
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Version not found after create",
        )
    ai_before_id = await _resolve_ai_before_id(saved, version_repo)
    return _version_to_response(saved, ai_before_version_id=ai_before_id)


@router.get(
    "/{workspace_id}/notes/{note_id}/versions",
    response_model=NoteVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List note versions",
    tags=["Note Versions"],
)
async def list_versions(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NoteVersionListResponse:
    """List versions for a note, newest first."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    versions = await version_repo.list_by_note(note_id, ws_uuid, limit=limit, offset=offset)
    total = await version_repo.count_by_note(note_id, ws_uuid)

    # GAP-02: batch-resolve ai_before pairings in a single query (avoids N+1)
    ai_after_versions = [v for v in versions if v.trigger == ModelTrigger.AI_AFTER]
    ai_before_map: dict[datetime, UUID] = {}
    if ai_after_versions:
        ai_before_map = await version_repo.get_ai_before_map_for_versions(
            note_id=note_id,
            workspace_id=ws_uuid,
            ai_after_timestamps=[v.created_at for v in ai_after_versions],
        )
    responses = [
        _version_to_response(v, ai_before_version_id=ai_before_map.get(v.created_at))
        for v in versions
    ]

    return NoteVersionListResponse(
        versions=responses,
        total=total,
        note_id=note_id,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}",
    response_model=NoteVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single version",
    tags=["Note Versions"],
)
async def get_version(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteVersionResponse:
    """Get a single version by ID."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    version = await version_repo.get_by_id_for_note(version_id, note_id, ws_uuid)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    ai_before_id = await _resolve_ai_before_id(version, version_repo)
    return _version_to_response(version, ai_before_version_id=ai_before_id)


@router.get(
    "/{workspace_id}/notes/{note_id}/versions/{version1_id}/diff/{version2_id}",
    response_model=DiffResponse,
    status_code=status.HTTP_200_OK,
    summary="Block-level diff between two versions",
    tags=["Note Versions"],
)
async def diff_versions(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version1_id: Annotated[UUID, Path(description="Older version UUID")],
    version2_id: Annotated[UUID, Path(description="Newer version UUID")],
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> DiffResponse:
    """Compute block-level diff between two versions."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    svc = VersionDiffService(session, version_repo)

    try:
        result = await svc.execute(version1_id, version2_id, note_id, ws_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DiffResponse(
        version1_id=result.version1_id,
        version2_id=result.version2_id,
        blocks=[
            BlockDiffResponse(
                block_id=b.block_id,
                diff_type=b.diff_type.value,
                old_content=b.old_content,
                new_content=b.new_content,
            )
            for b in result.blocks
        ],
        added_count=result.added_count,
        removed_count=result.removed_count,
        modified_count=result.modified_count,
        has_changes=result.has_changes,
    )


@router.post(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}/restore",
    response_model=RestoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore note to historical version (non-destructive, C-9)",
    tags=["Note Versions"],
)
async def restore_version(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    request: RestoreVersionRequest,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> RestoreResponse:
    """Restore note to a historical version.

    Creates a new version (non-destructive). Uses optimistic locking (C-9):
    version_number must match current max. Returns 409 if concurrent restore detected.
    """
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    note_repo = NoteRepository(session)
    version_repo = NoteVersionRepository(session)
    svc = VersionRestoreService(session, note_repo, version_repo)

    try:
        result = await svc.execute(
            RestorePayload(
                version_id=version_id,
                note_id=note_id,
                workspace_id=ws_uuid,
                restored_by=user_id,
                expected_version_number=request.version_number,
            )
        )
    except ConcurrentRestoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Another restore was applied. Reload to see current state.",
                "current_version_number": exc.competing_version_number,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await session.commit()

    # Re-fetch the new version for response
    if result.new_version.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Version ID missing after restore",
        )
    new_v = await version_repo.get_by_id_for_note(result.new_version.id, note_id, ws_uuid)
    if not new_v:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restore version not found after create",
        )

    ai_before_id = await _resolve_ai_before_id(new_v, version_repo)
    return RestoreResponse(
        new_version=_version_to_response(new_v, ai_before_version_id=ai_before_id),
        restored_from_version_id=result.restored_from_version_id,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}/digest",
    response_model=DigestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get or generate AI change digest",
    tags=["Note Versions"],
)
async def get_digest(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> DigestResponse:
    """Get AI-generated change digest for a version (cached, <3s for 95%)."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    settings = get_settings()
    anthropic_key: str | None = None
    if hasattr(settings, "anthropic_api_key") and settings.anthropic_api_key:
        secret = settings.anthropic_api_key
        anthropic_key = (
            secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
        )

    version_repo = NoteVersionRepository(session)
    svc = VersionDigestService(session, version_repo, anthropic_api_key=anthropic_key)

    try:
        result = await svc.execute(version_id, note_id, ws_uuid, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await session.commit()
    return DigestResponse(
        version_id=result.version_id,
        digest=result.digest,
        from_cache=result.from_cache,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}/impact",
    response_model=ImpactResponse,
    status_code=status.HTTP_200_OK,
    summary="Impact analysis — detect entity references",
    tags=["Note Versions"],
)
async def get_impact(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> ImpactResponse:
    """Scan version content for entity references (issues, notes)."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    svc = ImpactAnalysisService(session, version_repo)

    try:
        result = await svc.execute(version_id, note_id, ws_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ImpactResponse(
        version_id=result.version_id,
        references=[
            EntityReferenceResponse(
                reference_type=r.reference_type.value,
                identifier=r.identifier,
                raw_text=r.raw_text,
            )
            for r in result.references
        ],
        issue_count=len(result.issue_references),
        note_count=len(result.note_references),
    )


@router.put(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}/pin",
    response_model=NoteVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Pin or unpin a version",
    tags=["Note Versions"],
)
async def pin_version(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    request: PinVersionRequest,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> NoteVersionResponse:
    """Pin or unpin a version. Pinned versions are exempt from retention cleanup."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    version = await version_repo.get_by_id_for_note(version_id, note_id, ws_uuid)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    version.pinned = request.pinned
    await session.flush()
    await session.commit()
    await session.refresh(version)

    return _version_to_response(version)


@router.delete(
    "/{workspace_id}/notes/{note_id}/versions/{version_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a version (if not pinned)",
    tags=["Note Versions"],
)
async def delete_version(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    version_id: VersionIdPath,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> DeleteResponse:
    """Delete a version. Pinned versions cannot be deleted."""
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    version = await version_repo.get_by_id_for_note(version_id, note_id, ws_uuid)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    if version.pinned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pinned versions cannot be deleted. Unpin first.",
        )

    await version_repo.batch_delete([version_id])
    await session.commit()

    return DeleteResponse(id=version_id)


@router.post(
    "/{workspace_id}/notes/{note_id}/versions/undo-ai",
    response_model=UndoAiResponse,
    status_code=status.HTTP_200_OK,
    summary="Undo AI changes — restore to closest ai_before snapshot (GAP-04)",
    tags=["Note Versions"],
)
async def undo_ai_changes(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    request: UndoAiRequest,
    session: SessionDep,
    user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> UndoAiResponse:
    """Fast-path: restore the note to the most recent ai_before snapshot.

    Designed for the "Undo AI" button in the version history UI (GAP-04).
    Finds the latest ai_before version and triggers a non-destructive restore.
    Returns 404 if no ai_before snapshot exists (no AI has edited this note).
    Returns 409 if concurrent write detected (C-9 optimistic lock).
    """
    workspace_repo = WorkspaceRepository(session)
    ws_uuid = await _resolve_workspace_id(workspace_id, workspace_repo)

    version_repo = NoteVersionRepository(session)
    ai_before = await version_repo.get_latest_ai_before(note_id, ws_uuid)
    if not ai_before:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI-before snapshot found. AI has not edited this note yet.",
        )
    note_repo = NoteRepository(session)
    restore_svc = VersionRestoreService(session, note_repo, version_repo)

    try:
        result = await restore_svc.execute(
            RestorePayload(
                version_id=ai_before.id,
                note_id=note_id,
                workspace_id=ws_uuid,
                restored_by=user_id,
                expected_version_number=request.version_number,
            )
        )
    except ConcurrentRestoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Another change was applied. Reload to see current state.",
                "current_version_number": exc.competing_version_number,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await session.commit()

    if result.new_version.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Version ID missing after undo-ai restore",
        )
    new_v = await version_repo.get_by_id_for_note(result.new_version.id, note_id, ws_uuid)
    if not new_v:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restored version not found",
        )

    return UndoAiResponse(
        new_version=_version_to_response(new_v),
        restored_from_version_id=result.restored_from_version_id,
    )
