"""NoteAIUpdateService for AI-initiated note content updates.

Implements CQRS-lite command pattern for AI-driven note updates.
Provides audit trail and conflict detection separate from user autosave.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


class AIUpdateOperation(StrEnum):
    """AI update operation types."""

    REPLACE_BLOCK = "replace_block"
    APPEND_BLOCKS = "append_blocks"
    INSERT_INLINE_ISSUE = "insert_inline_issue"
    INSERT_BLOCKS = "insert_blocks"
    REMOVE_BLOCK = "remove_block"
    REMOVE_CONTENT = "remove_content"
    REPLACE_CONTENT = "replace_content"


@dataclass(slots=True)
class AIUpdatePayload:
    """Payload for AI-initiated note updates.

    Attributes:
        note_id: The note ID to update.
        operation: Type of update operation.
        block_id: Target block ID (for replace/insert operations).
        content: New content (block or blocks).
        after_block_id: Insert position for append operations.
        issue_data: Issue node data for inline issue insertion.
        agent_session_id: Optional agent session ID for audit trail.
        source_tool: Optional MCP tool that triggered this update.
        user_id: Optional user ID for audit.
    """

    note_id: UUID
    operation: AIUpdateOperation
    block_id: str | None = None
    content: dict[str, Any] | None = None
    after_block_id: str | None = None
    issue_data: dict[str, Any] | None = None
    agent_session_id: str | None = None
    source_tool: str | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AIUpdateResult:
    """Result from AI update operation.

    Attributes:
        success: Whether the update succeeded.
        note_id: The updated note ID.
        affected_block_ids: List of block IDs that were modified.
        updated_content: The complete updated content.
        conflict: Whether a conflict was detected.
        conflict_block_ids: Block IDs with conflicts (if any).
    """

    success: bool
    note_id: UUID
    affected_block_ids: list[str]
    updated_content: dict[str, Any]
    conflict: bool = False
    conflict_block_ids: list[str] | None = None


class NoteAIUpdateService:
    """Service for AI-initiated note content updates.

    Handles structured updates to note content from AI agents,
    providing audit trail and conflict detection.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
    ) -> None:
        """Initialize NoteAIUpdateService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: AIUpdatePayload) -> AIUpdateResult:
        """Execute AI update operation.

        Args:
            payload: The update payload.

        Returns:
            AIUpdateResult with updated note and metadata.

        Raises:
            ValueError: If note not found, validation fails, or invalid operation.
        """
        # Fetch note
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            msg = f"Note with ID {payload.note_id} not found"
            raise ValueError(msg)

        # Route to operation handler
        if payload.operation == AIUpdateOperation.REPLACE_BLOCK:
            return await self._replace_block(note, payload)
        if payload.operation == AIUpdateOperation.APPEND_BLOCKS:
            return await self._append_blocks(note, payload)
        if payload.operation == AIUpdateOperation.INSERT_INLINE_ISSUE:
            return await self._insert_inline_issue(note, payload)
        msg = f"Unknown operation: {payload.operation}"
        raise ValueError(msg)

    async def _replace_block(
        self,
        note: Note,
        payload: AIUpdatePayload,
    ) -> AIUpdateResult:
        """Replace a block's content.

        Args:
            note: The note to update.
            payload: The update payload.

        Returns:
            AIUpdateResult.

        Raises:
            ValueError: If block_id not found or content is invalid.
        """
        if not payload.block_id:
            msg = "block_id is required for replace_block operation"
            raise ValueError(msg)

        if not payload.content:
            msg = "content is required for replace_block operation"
            raise ValueError(msg)

        # Find and replace the block
        content = note.content
        blocks = content.get("content", [])
        replaced = False
        affected_ids: list[str] = []

        new_blocks: list[dict[str, Any]] = []
        for block in blocks:
            block_id = block.get("attrs", {}).get("id")
            if block_id == payload.block_id:
                new_blocks.append(payload.content)
                affected_ids.append(payload.block_id)
                replaced = True
            else:
                new_blocks.append(block)

        if not replaced:
            msg = f"Block with ID {payload.block_id} not found in note {payload.note_id}"
            raise ValueError(msg)

        # Update note content
        updated_content = {"type": "doc", "content": new_blocks}
        note.content = updated_content

        # Save
        await self._note_repo.update(note)

        return AIUpdateResult(
            success=True,
            note_id=note.id,
            affected_block_ids=affected_ids,
            updated_content=updated_content,
            conflict=False,
        )

    async def _append_blocks(
        self,
        note: Note,
        payload: AIUpdatePayload,
    ) -> AIUpdateResult:
        """Append blocks after a specified position.

        Args:
            note: The note to update.
            payload: The update payload.

        Returns:
            AIUpdateResult.

        Raises:
            ValueError: If content is invalid.
        """
        if not payload.content:
            msg = "content is required for append_blocks operation"
            raise ValueError(msg)

        # Extract new blocks
        new_blocks_data = payload.content.get("blocks", [])
        if not isinstance(new_blocks_data, list):
            new_blocks_data = [payload.content]

        # Find insertion point
        content = note.content
        blocks = content.get("content", [])

        if payload.after_block_id:
            # Insert after specified block
            insert_index = -1
            for i, block in enumerate(blocks):
                block_id = block.get("attrs", {}).get("id")
                if block_id == payload.after_block_id:
                    insert_index = i + 1
                    break

            if insert_index == -1:
                msg = f"Block with ID {payload.after_block_id} not found"
                raise ValueError(msg)

            new_blocks = blocks[:insert_index] + new_blocks_data + blocks[insert_index:]
        else:
            # Append at end
            new_blocks = blocks + new_blocks_data

        # Track affected IDs
        affected_ids: list[str] = []
        for block in new_blocks_data:
            block_id = block.get("attrs", {}).get("id")
            if block_id:
                affected_ids.append(block_id)

        # Update note content
        updated_content = {"type": "doc", "content": new_blocks}
        note.content = updated_content

        # Save
        await self._note_repo.update(note)

        return AIUpdateResult(
            success=True,
            note_id=note.id,
            affected_block_ids=affected_ids,
            updated_content=updated_content,
            conflict=False,
        )

    async def _insert_inline_issue(
        self,
        note: Note,
        payload: AIUpdatePayload,
    ) -> AIUpdateResult:
        """Insert an inline issue node into a block.

        Args:
            note: The note to update.
            payload: The update payload.

        Returns:
            AIUpdateResult.

        Raises:
            ValueError: If block_id not found or issue_data is invalid.
        """
        if not payload.block_id:
            msg = "block_id is required for insert_inline_issue operation"
            raise ValueError(msg)

        if not payload.issue_data:
            msg = "issue_data is required for insert_inline_issue operation"
            raise ValueError(msg)

        # Find the target block
        content = note.content
        blocks = content.get("content", [])
        found = False
        affected_ids: list[str] = []

        new_blocks: list[dict[str, Any]] = []
        for block in blocks:
            block_id = block.get("attrs", {}).get("id")
            if block_id == payload.block_id:
                # Add inline issue to block's content
                block_content = block.get("content", [])
                block_content.append(payload.issue_data)
                block["content"] = block_content
                affected_ids.append(payload.block_id)
                found = True

            new_blocks.append(block)

        if not found:
            msg = f"Block with ID {payload.block_id} not found in note {payload.note_id}"
            raise ValueError(msg)

        # Update note content
        updated_content = {"type": "doc", "content": new_blocks}
        note.content = updated_content

        # Save
        await self._note_repo.update(note)

        return AIUpdateResult(
            success=True,
            note_id=note.id,
            affected_block_ids=affected_ids,
            updated_content=updated_content,
            conflict=False,
        )
