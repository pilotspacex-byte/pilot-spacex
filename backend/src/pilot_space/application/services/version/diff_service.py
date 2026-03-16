"""VersionDiffService — block-level diff between two note versions.

Computes a structured diff between two TipTap JSON documents at block granularity.
Blocks are identified by their TipTap block ID attribute.

Feature 017: Note Versioning — Sprint 1 (T-208)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DiffType(StrEnum):
    """Type of change for a block."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class BlockDiff:
    """Diff result for a single TipTap block."""

    block_id: str
    diff_type: DiffType
    old_content: dict[str, Any] | None = None
    new_content: dict[str, Any] | None = None


@dataclass
class DiffResult:
    """Structured diff between two note versions."""

    version1_id: UUID
    version2_id: UUID
    blocks: list[BlockDiff]

    @property
    def added_count(self) -> int:
        return sum(1 for b in self.blocks if b.diff_type == DiffType.ADDED)

    @property
    def removed_count(self) -> int:
        return sum(1 for b in self.blocks if b.diff_type == DiffType.REMOVED)

    @property
    def modified_count(self) -> int:
        return sum(1 for b in self.blocks if b.diff_type == DiffType.MODIFIED)

    @property
    def has_changes(self) -> bool:
        return self.added_count + self.removed_count + self.modified_count > 0


class VersionDiffService:
    """Computes block-level diffs between two note version snapshots."""

    def __init__(
        self,
        session: AsyncSession,
        version_repo: NoteVersionRepository,
    ) -> None:
        self._session = session
        self._version_repo = version_repo

    async def execute(
        self,
        v1_id: UUID,
        v2_id: UUID,
        note_id: UUID,
        workspace_id: UUID,
    ) -> DiffResult:
        """Compute block-level diff between two versions.

        Args:
            v1_id: Older version UUID.
            v2_id: Newer version UUID.
            note_id: Parent note UUID (ownership check).
            workspace_id: Workspace UUID (RLS).

        Returns:
            DiffResult with per-block change breakdown.

        Raises:
            ValueError: If either version is not found.
        """
        v1 = await self._version_repo.get_by_id_for_note(v1_id, note_id, workspace_id)
        if not v1:
            msg = f"Version {v1_id} not found"
            raise ValueError(msg)

        v2 = await self._version_repo.get_by_id_for_note(v2_id, note_id, workspace_id)
        if not v2:
            msg = f"Version {v2_id} not found"
            raise ValueError(msg)

        blocks_v1 = _extract_blocks(v1.content)
        blocks_v2 = _extract_blocks(v2.content)

        diffs = _compute_block_diff(blocks_v1, blocks_v2)
        return DiffResult(version1_id=v1_id, version2_id=v2_id, blocks=diffs)


def _extract_blocks(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract TipTap blocks as {block_id: block_node} map.

    Falls back to positional index as ID if block has no attrs.id.

    Args:
        content: TipTap JSON document.

    Returns:
        Ordered dict mapping block ID to block node.
    """
    blocks: dict[str, dict[str, Any]] = {}
    top_level = content.get("content", [])
    for idx, block in enumerate(top_level):
        attrs = block.get("attrs") or {}
        block_id = attrs.get("id") or f"pos:{idx}"
        blocks[block_id] = block
    return blocks


def _block_hash(block: dict[str, Any]) -> str:
    """Compute stable hash of a block for change detection."""
    canonical = json.dumps(block, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _compute_block_diff(
    old_blocks: dict[str, dict[str, Any]],
    new_blocks: dict[str, dict[str, Any]],
) -> list[BlockDiff]:
    """Compute per-block diff between two block maps."""
    diffs: list[BlockDiff] = []
    all_ids = list(old_blocks.keys()) + [k for k in new_blocks if k not in old_blocks]

    for block_id in all_ids:
        in_old = block_id in old_blocks
        in_new = block_id in new_blocks

        if in_old and not in_new:
            diffs.append(
                BlockDiff(
                    block_id=block_id,
                    diff_type=DiffType.REMOVED,
                    old_content=old_blocks[block_id],
                    new_content=None,
                )
            )
        elif in_new and not in_old:
            diffs.append(
                BlockDiff(
                    block_id=block_id,
                    diff_type=DiffType.ADDED,
                    old_content=None,
                    new_content=new_blocks[block_id],
                )
            )
        else:
            old_hash = _block_hash(old_blocks[block_id])
            new_hash = _block_hash(new_blocks[block_id])
            diff_type = DiffType.UNCHANGED if old_hash == new_hash else DiffType.MODIFIED
            diffs.append(
                BlockDiff(
                    block_id=block_id,
                    diff_type=diff_type,
                    old_content=old_blocks[block_id],
                    new_content=new_blocks[block_id],
                )
            )

    return diffs
