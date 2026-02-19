"""Block ownership API router (Feature 016, M6b — Ownership Engine).

Endpoints:
- GET  /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/owner
- POST /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/approve
- POST /workspaces/{workspace_id}/notes/{note_id}/blocks/{block_id}/reject

T-113: Block approve/reject API

Human-in-the-loop ownership actions:
- Approve: human accepts AI block content (optionally converts to "shared")
- Reject: human removes AI block from note
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.schemas.block_ownership import (
    BlockApproveRequest,
    BlockApproveResponse,
    BlockOwnerResponse,
    BlockRejectResponse,
)
from pilot_space.dependencies.auth import SessionDep, WorkspaceMemberId
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
NoteIdPath = Annotated[UUID, Path(description="Note UUID")]
BlockIdPath = Annotated[str, Path(description="Block UUID (from BlockIdExtension)")]


async def _resolve_workspace_and_note(
    workspace_id: UUID,
    note_id: UUID,
    workspace_repo: WorkspaceRepositoryDep,
    session: SessionDep,
) -> tuple[Any, Any]:
    """Verify workspace and note exist and note belongs to workspace.

    Returns (workspace, note) models.
    Raises HTTPException 404 if not found.
    """
    from pilot_space.infrastructure.database.repositories.note_repository import NoteRepository

    ws = await workspace_repo.get_by_id_scalar(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )

    repo = NoteRepository(session)
    note = await repo.get_by_id(note_id)
    if note is None or str(note.workspace_id) != str(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found in workspace {workspace_id}",
        )
    return ws, note


def _find_block(blocks: list[dict[str, Any]], block_id: str) -> dict[str, Any] | None:
    """Recursively find a block by ID in TipTap content tree."""
    for node in blocks:
        if node.get("attrs", {}).get("id") == block_id:
            return node
        nested = node.get("content", [])
        if nested:
            found = _find_block(nested, block_id)
            if found is not None:
                return found
    return None


def _remove_block(blocks: list[dict[str, Any]], block_id: str) -> bool:
    """Remove a block by ID from TipTap content tree. Returns True if removed."""
    for i, node in enumerate(blocks):
        if node.get("attrs", {}).get("id") == block_id:
            blocks.pop(i)
            return True
        nested = node.get("content", [])
        if nested and _remove_block(nested, block_id):
            return True
    return False


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
    workspace_repo: WorkspaceRepositoryDep,
    current_user: WorkspaceMemberId,
) -> BlockOwnerResponse:
    """Get the current owner of a specific block.

    Returns the owner string: 'human', 'shared', or 'ai:{skill-name}'.
    Blocks without an explicit owner default to 'human' (FR-009).
    """
    _, note = await _resolve_workspace_and_note(workspace_id, note_id, workspace_repo, session)

    content = note.content or {}
    blocks = content.get("content", [])
    block = _find_block(blocks, block_id)

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found in note {note_id}",
        )

    owner = block.get("attrs", {}).get("owner", "human")

    logger.debug(
        "[BlockOwnership] get_owner: note=%s block=%s owner=%s",
        note_id,
        block_id,
        owner,
    )

    return BlockOwnerResponse(
        block_id=block_id,
        note_id=str(note_id),
        owner=owner,
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
    workspace_repo: WorkspaceRepositoryDep,
    current_user: WorkspaceMemberId,
) -> BlockApproveResponse:
    """Approve an AI-owned block.

    Human accepts the AI block content. If convert_to_shared=True, the block
    becomes 'shared' (editable by both). Otherwise, retains 'ai:{skill}' label.

    Only applicable to AI-owned blocks (ai:{skill}). Approving a human or shared
    block is a no-op.
    """
    _, note = await _resolve_workspace_and_note(workspace_id, note_id, workspace_repo, session)

    content = note.content or {}
    blocks = content.get("content", [])
    block = _find_block(blocks, block_id)

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found in note {note_id}",
        )

    current_owner = block.get("attrs", {}).get("owner", "human")

    if not current_owner.startswith("ai:"):
        # Block is already human or shared — approve is a no-op
        return BlockApproveResponse(
            block_id=block_id,
            note_id=str(note_id),
            action="approved",
            owner=current_owner,
        )

    # Determine new owner after approval
    new_owner = "shared" if request.convert_to_shared else current_owner

    # Update block attrs in place
    if "attrs" not in block:
        block["attrs"] = {}
    block["attrs"]["owner"] = new_owner

    note.content = content
    await session.flush()

    logger.info(
        "[BlockOwnership] approve: note=%s block=%s old_owner=%s new_owner=%s user=%s",
        note_id,
        block_id,
        current_owner,
        new_owner,
        current_user,
    )

    return BlockApproveResponse(
        block_id=block_id,
        note_id=str(note_id),
        action="approved",
        owner=new_owner,
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
    workspace_repo: WorkspaceRepositoryDep,
    current_user: WorkspaceMemberId,
) -> BlockRejectResponse:
    """Reject an AI-owned block.

    Removes the block from the note. The frontend should offer an undo toast.
    Only AI-owned blocks can be rejected. Human and shared blocks return 422.
    """
    _, note = await _resolve_workspace_and_note(workspace_id, note_id, workspace_repo, session)

    content = note.content or {}
    blocks = content.get("content", [])
    block = _find_block(blocks, block_id)

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found in note {note_id}",
        )

    current_owner = block.get("attrs", {}).get("owner", "human")

    if not current_owner.startswith("ai:"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Block {block_id} is not an AI block (owner: '{current_owner}'). "
            "Only AI blocks can be rejected.",
        )

    removed = _remove_block(blocks, block_id)
    if removed:
        note.content = content
        await session.flush()

    logger.info(
        "[BlockOwnership] reject: note=%s block=%s owner=%s removed=%s user=%s",
        note_id,
        block_id,
        current_owner,
        removed,
        current_user,
    )

    return BlockRejectResponse(
        block_id=block_id,
        note_id=str(note_id),
        action="rejected",
        removed=removed,
    )
