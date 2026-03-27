"""Block ownership service — approve/reject AI-owned blocks in TipTap notes.

Feature 016, M6b — Ownership Engine.

Extracts tree traversal, state mutation, and validation logic from the
block_ownership router into a proper service layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


# -- Payloads / Results --------------------------------------------------------


@dataclass(frozen=True)
class BlockOwnerResult:
    """Result of a block owner lookup."""

    block_id: str
    note_id: str
    owner: str


@dataclass(frozen=True)
class BlockApproveResult:
    """Result of approving a block."""

    block_id: str
    note_id: str
    action: str  # always "approved"
    owner: str


@dataclass(frozen=True)
class BlockRejectResult:
    """Result of rejecting a block."""

    block_id: str
    note_id: str
    action: str  # always "rejected"
    removed: bool


# -- Service -------------------------------------------------------------------


class BlockOwnershipService:
    """Business logic for block ownership actions (approve/reject).

    Owns tree traversal, block lookup, and state mutation of TipTap content.
    """

    def __init__(self, session: AsyncSession, note_repository: NoteRepository) -> None:
        self._session = session
        self._note_repo = note_repository

    # -- Public API ------------------------------------------------------------

    async def get_block_owner(
        self,
        workspace_id: UUID,
        note_id: UUID,
        block_id: str,
    ) -> BlockOwnerResult:
        """Get the current owner string for a specific block."""
        note = await self._resolve_note(workspace_id, note_id)
        block = self._find_block_or_raise(note, note_id, block_id)
        owner = block.get("attrs", {}).get("owner", "human")

        logger.debug(
            "[BlockOwnership] get_owner: note=%s block=%s owner=%s",
            note_id,
            block_id,
            owner,
        )

        return BlockOwnerResult(block_id=block_id, note_id=str(note_id), owner=owner)

    async def approve_block(
        self,
        workspace_id: UUID,
        note_id: UUID,
        block_id: str,
        *,
        convert_to_shared: bool = False,
        user_id: UUID | None = None,
    ) -> BlockApproveResult:
        """Approve an AI-owned block.

        If ``convert_to_shared`` is True the block becomes ``shared``.
        Approving a non-AI block is a no-op.
        """
        note = await self._resolve_note(workspace_id, note_id)
        content = note.content or {}
        blocks = content.get("content", [])
        block = self._find_block_or_raise_from_list(blocks, note_id, block_id)

        current_owner = block.get("attrs", {}).get("owner", "human")

        if not current_owner.startswith("ai:"):
            return BlockApproveResult(
                block_id=block_id,
                note_id=str(note_id),
                action="approved",
                owner=current_owner,
            )

        new_owner = "shared" if convert_to_shared else current_owner

        if "attrs" not in block:
            block["attrs"] = {}
        block["attrs"]["owner"] = new_owner

        note.content = content
        await self._session.flush()

        logger.info(
            "[BlockOwnership] approve: note=%s block=%s old_owner=%s new_owner=%s user=%s",
            note_id,
            block_id,
            current_owner,
            new_owner,
            user_id,
        )

        return BlockApproveResult(
            block_id=block_id,
            note_id=str(note_id),
            action="approved",
            owner=new_owner,
        )

    async def reject_block(
        self,
        workspace_id: UUID,
        note_id: UUID,
        block_id: str,
        *,
        user_id: UUID | None = None,
    ) -> BlockRejectResult:
        """Reject an AI-owned block (removes it from note content).

        Only AI blocks can be rejected; human/shared blocks raise ValidationError.
        """
        note = await self._resolve_note(workspace_id, note_id)
        content = note.content or {}
        blocks = content.get("content", [])
        block = self._find_block_or_raise_from_list(blocks, note_id, block_id)

        current_owner = block.get("attrs", {}).get("owner", "human")

        if not current_owner.startswith("ai:"):
            raise ValidationError(
                f"Block {block_id} is not an AI block (owner: '{current_owner}'). "
                "Only AI blocks can be rejected.",
                error_code="not_ai_block",
            )

        removed = self._remove_block(blocks, block_id)
        if removed:
            note.content = content
            await self._session.flush()

        logger.info(
            "[BlockOwnership] reject: note=%s block=%s owner=%s removed=%s user=%s",
            note_id,
            block_id,
            current_owner,
            removed,
            user_id,
        )

        return BlockRejectResult(
            block_id=block_id,
            note_id=str(note_id),
            action="rejected",
            removed=removed,
        )

    # -- Private helpers -------------------------------------------------------

    async def _resolve_note(self, workspace_id: UUID, note_id: UUID) -> Any:
        """Load a note and verify it belongs to the workspace."""
        note = await self._note_repo.get_by_id(note_id)
        if note is None or str(note.workspace_id) != str(workspace_id):
            raise NotFoundError(f"Note {note_id} not found in workspace {workspace_id}")
        return note

    def _find_block_or_raise(self, note: Any, note_id: UUID, block_id: str) -> dict[str, Any]:
        content = note.content or {}
        blocks = content.get("content", [])
        return self._find_block_or_raise_from_list(blocks, note_id, block_id)

    def _find_block_or_raise_from_list(
        self, blocks: list[dict[str, Any]], note_id: UUID, block_id: str
    ) -> dict[str, Any]:
        block = self._find_block(blocks, block_id)
        if block is None:
            raise NotFoundError(f"Block {block_id} not found in note {note_id}")
        return block

    @staticmethod
    def _find_block(blocks: list[dict[str, Any]], block_id: str) -> dict[str, Any] | None:
        """Recursively find a block by ID in TipTap content tree."""
        for node in blocks:
            if node.get("attrs", {}).get("id") == block_id:
                return node
            nested = node.get("content", [])
            if nested:
                found = BlockOwnershipService._find_block(nested, block_id)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _remove_block(blocks: list[dict[str, Any]], block_id: str) -> bool:
        """Remove a block by ID from TipTap content tree. Returns True if removed."""
        for i, node in enumerate(blocks):
            if node.get("attrs", {}).get("id") == block_id:
                blocks.pop(i)
                return True
            nested = node.get("content", [])
            if nested and BlockOwnershipService._remove_block(nested, block_id):
                return True
        return False
