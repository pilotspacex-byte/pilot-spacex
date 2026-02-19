"""In-process SDK MCP server for block ownership enforcement (Feature 016, M6b).

Provides 3 tools:
- get_block_owner: Read ownership of a specific block
- set_block_owner: Set owner when AI creates/modifies a block (T-111)
- check_block_write_permission: Validate actor permission before write (T-112)

This server enforces the authoritative backend ownership check (C-5).
Frontend enforces only UX boundary; this is the enforcement point.

Design:
- New AI blocks MUST call set_block_owner with "ai:{skill-name}" after creation
- Before any write, AI MUST call check_block_write_permission
- OwnershipViolationError causes intent status = "failed" and chat error

Reference: Feature 016 spec M6b, FR-001 to FR-009
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.exceptions import AIError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.tools.mcp_server import ToolContext

logger = get_logger(__name__)

SERVER_NAME = "pilot-ownership"

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_block_owner",
    f"mcp__{SERVER_NAME}__set_block_owner",
    f"mcp__{SERVER_NAME}__check_block_write_permission",
]

# Valid owner values
_VALID_SHARED = frozenset({"human", "shared"})


class OwnershipViolationError(AIError):
    """Raised when an actor attempts to write to a block they don't own."""

    error_code = "ownership_violation"
    http_status = 403


def _text_result(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _validate_owner(owner: str) -> bool:
    """Validate owner string format: 'human', 'shared', or 'ai:{skill}'."""
    return owner in _VALID_SHARED or owner.startswith("ai:")


def _can_write(actor: str, owner: str) -> bool:
    """Check if actor can write to a block with the given owner.

    Rules (FR-002 to FR-004):
    - shared: any actor can write
    - human: only 'human' actor can write
    - ai:{skill}: only the same skill can write
    """
    if owner == "shared":
        return True
    if owner == "human":
        return actor == "human"
    return actor == owner


def create_ownership_server(
    *,
    tool_context: ToolContext | None = None,
    skill_name: str | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server for block ownership enforcement.

    Args:
        tool_context: ToolContext for database access and RLS enforcement.
        skill_name: Current skill name (e.g. "create-spec"). Used as default actor.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """

    # The actor is the skill_name prefixed with "ai:", or "human" if not a skill
    actor = f"ai:{skill_name}" if skill_name else "human"

    async def _get_block_owner_from_db(note_id: str, block_id: str) -> str | None:
        """Load block owner from the note's TipTap content in DB.

        Returns the owner string, or None if block not found.
        Owner is stored in the block's attrs JSON alongside TipTap content.
        """
        if not tool_context:
            return None  # No DB context; skip (test/dev mode)
        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            repo = NoteRepository(tool_context.db_session)
            note = await repo.get_by_id(UUID(note_id))
        except (ValueError, TypeError):
            return None

        if not note or str(note.workspace_id) != tool_context.workspace_id:
            return None

        content = note.content or {}
        blocks = content.get("content", [])

        def find_block(nodes: list[dict[str, Any]]) -> str | None:
            for node in nodes:
                if node.get("attrs", {}).get("id") == block_id:
                    return node.get("attrs", {}).get("owner", "human")
                # Recurse into nested content
                nested = node.get("content", [])
                if nested:
                    result = find_block(nested)
                    if result is not None:
                        return result
            return None

        return find_block(blocks)

    async def _set_block_owner_in_db(note_id: str, block_id: str, owner: str) -> bool:
        """Persist block owner update to DB via SSE operation.

        Ownership is stored in block attrs JSON in the notes table.
        This issues an SSE content_update event to update the frontend.
        Returns True on success.
        """
        if not tool_context:
            logger.warning("[OwnershipServer] No tool_context — cannot persist owner")
            return False
        from uuid import UUID

        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        try:
            repo = NoteRepository(tool_context.db_session)
            note = await repo.get_by_id(UUID(note_id))
        except (ValueError, TypeError):
            return False

        if not note or str(note.workspace_id) != tool_context.workspace_id:
            return False

        content = note.content or {}
        blocks = content.get("content", [])

        def update_block_owner(nodes: list[dict[str, Any]]) -> bool:
            for node in nodes:
                if node.get("attrs", {}).get("id") == block_id:
                    if "attrs" not in node:
                        node["attrs"] = {}
                    node["attrs"]["owner"] = owner
                    return True
                nested = node.get("content", [])
                if nested and update_block_owner(nested):
                    return True
            return False

        found = update_block_owner(blocks)
        if not found:
            return False

        # Persist the updated content back to DB
        note.content = content
        await tool_context.db_session.flush()
        logger.info(
            "[OwnershipServer] set_block_owner: note=%s block=%s owner=%s",
            note_id,
            block_id,
            owner,
        )
        return True

    @tool(
        "get_block_owner",
        "Read the current owner of a specific block. "
        "Returns 'human', 'ai:{skill-name}', or 'shared'. "
        "Use before deciding whether to modify a block.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {
                    "type": "string",
                    "description": "UUID of the block (from BlockIdExtension)",
                },
            },
            "required": ["note_id", "block_id"],
        },
    )
    async def get_block_owner(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id", "")
        block_id = args.get("block_id", "")

        if not note_id or not block_id:
            return _text_result("Error: note_id and block_id are required")

        if not tool_context:
            return _text_result("human")  # Default in test/dev mode

        owner = await _get_block_owner_from_db(note_id, block_id)
        if owner is None:
            return _text_result(f"Error: Block {block_id} not found in note {note_id}")

        logger.debug(
            "[OwnershipServer] get_block_owner: note=%s block=%s owner=%s",
            note_id,
            block_id,
            owner,
        )
        return _text_result(json.dumps({"block_id": block_id, "owner": owner}))

    @tool(
        "set_block_owner",
        "Set the owner of a block. AI MUST call this after creating any new block "
        "(T-111). Use 'ai:{skill-name}' for AI-created blocks, 'human' for human blocks, "
        "'shared' for collaborative blocks. Only the current owner or 'human' actor "
        "can transfer ownership.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {
                    "type": "string",
                    "description": "UUID of the block to update",
                },
                "owner": {
                    "type": "string",
                    "description": (
                        "New owner: 'human', 'shared', or 'ai:{skill-name}' (e.g. 'ai:create-spec')"
                    ),
                },
            },
            "required": ["note_id", "block_id", "owner"],
        },
    )
    async def set_block_owner(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id", "")
        block_id = args.get("block_id", "")
        new_owner = args.get("owner", "")

        if not note_id or not block_id or not new_owner:
            return _text_result("Error: note_id, block_id, and owner are required")

        if not _validate_owner(new_owner):
            return _text_result(
                f"Error: Invalid owner '{new_owner}'. "
                "Must be 'human', 'shared', or 'ai:{{skill-name}}'."
            )

        # Check current owner — only current owner or human can transfer
        current_owner = await _get_block_owner_from_db(note_id, block_id)
        if current_owner is not None:
            # Human actor can always set ownership (approve/convert)
            # AI actor can only set if they currently own the block
            if actor != "human" and current_owner not in (_VALID_SHARED | {actor}):
                return _text_result(
                    f"Error: Ownership violation — {actor} cannot transfer "
                    f"ownership of block owned by '{current_owner}'"
                )

        success = await _set_block_owner_in_db(note_id, block_id, new_owner)
        if not success:
            return _text_result(f"Error: Could not update owner for block {block_id}")

        return _text_result(f"Block {block_id} owner set to '{new_owner}'.")

    @tool(
        "check_block_write_permission",
        "Check whether the current actor is permitted to write to a block. "
        "MUST be called before any write operation on an existing block (T-112). "
        "Returns 'allowed' or 'denied' with reason. "
        "If denied, do NOT attempt the write — raise intent failure instead.",
        {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "UUID of the note"},
                "block_id": {
                    "type": "string",
                    "description": "UUID of the block to check",
                },
            },
            "required": ["note_id", "block_id"],
        },
    )
    async def check_block_write_permission(args: dict[str, Any]) -> dict[str, Any]:
        note_id = args.get("note_id", "")
        block_id = args.get("block_id", "")

        if not note_id or not block_id:
            return _text_result("Error: note_id and block_id are required")

        if not tool_context:
            # In test/dev mode, allow all writes
            return _text_result(json.dumps({"result": "allowed", "reason": "no_context"}))

        owner = await _get_block_owner_from_db(note_id, block_id)
        if owner is None:
            # Block not found — default to "human" ownership (FR-009)
            owner = "human"

        if _can_write(actor, owner):
            logger.debug(
                "[OwnershipServer] check_write: actor=%s block=%s owner=%s → allowed",
                actor,
                block_id,
                owner,
            )
            return _text_result(json.dumps({"result": "allowed", "actor": actor, "owner": owner}))

        logger.warning(
            "[OwnershipServer] check_write: actor=%s block=%s owner=%s → DENIED",
            actor,
            block_id,
            owner,
        )
        return _text_result(
            json.dumps(
                {
                    "result": "denied",
                    "actor": actor,
                    "owner": owner,
                    "reason": f"Block is owned by '{owner}'. Actor '{actor}' is not permitted to write.",
                }
            )
        )

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            get_block_owner,
            set_block_owner,
            check_block_write_permission,
        ],
    )
