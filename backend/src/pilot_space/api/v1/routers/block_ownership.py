"""Block ownership API router (Feature 016, M6b -- Ownership Engine).

Endpoints:
- GET  /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/owner
- POST /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/approve
- POST /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/reject

T-113: Block approve/reject API

Thin HTTP shell -- all business logic delegated to BlockOwnershipService.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from pilot_space.api.v1.dependencies import BlockOwnershipServiceDep
from pilot_space.api.v1.schemas.block_ownership import (
    BlockApproveRequest,
    BlockApproveResponse,
    BlockOwnerResponse,
    BlockRejectResponse,
)
from pilot_space.dependencies.auth import SessionDep, WorkspaceMemberId

router = APIRouter()

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
NoteIdPath = Annotated[UUID, Path(description="Note UUID")]
BlockIdPath = Annotated[str, Path(description="Block UUID (from BlockIdExtension)")]


@router.get(
    "/{workspace_id}/notes/{note_id}/blocks/{block_id}/owner",
    response_model=BlockOwnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get block owner",
)
async def get_block_owner(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    block_id: BlockIdPath,
    session: SessionDep,
    service: BlockOwnershipServiceDep,
    current_user: WorkspaceMemberId,
) -> BlockOwnerResponse:
    """Get the current owner of a specific block."""
    result = await service.get_block_owner(workspace_id, note_id, block_id)
    return BlockOwnerResponse(
        block_id=result.block_id,
        note_id=result.note_id,
        owner=result.owner,
    )


@router.post(
    "/{workspace_id}/notes/{note_id}/blocks/{block_id}/approve",
    response_model=BlockApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve an AI block",
)
async def approve_block(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    block_id: BlockIdPath,
    request: BlockApproveRequest,
    session: SessionDep,
    service: BlockOwnershipServiceDep,
    current_user: WorkspaceMemberId,
) -> BlockApproveResponse:
    """Approve an AI-owned block."""
    result = await service.approve_block(
        workspace_id,
        note_id,
        block_id,
        convert_to_shared=request.convert_to_shared,
        user_id=current_user,
    )
    return BlockApproveResponse(
        block_id=result.block_id,
        note_id=result.note_id,
        action="approved",
        owner=result.owner,
    )


@router.post(
    "/{workspace_id}/notes/{note_id}/blocks/{block_id}/reject",
    response_model=BlockRejectResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject and remove an AI block",
)
async def reject_block(
    workspace_id: WorkspaceIdPath,
    note_id: NoteIdPath,
    block_id: BlockIdPath,
    session: SessionDep,
    service: BlockOwnershipServiceDep,
    current_user: WorkspaceMemberId,
) -> BlockRejectResponse:
    """Reject an AI-owned block (removes from note)."""
    result = await service.reject_block(
        workspace_id,
        note_id,
        block_id,
        user_id=current_user,
    )
    return BlockRejectResponse(
        block_id=result.block_id,
        note_id=result.note_id,
        action="rejected",
        removed=result.removed,
    )
