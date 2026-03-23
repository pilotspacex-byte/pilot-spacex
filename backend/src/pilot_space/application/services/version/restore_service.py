"""VersionRestoreService — non-destructive restore with optimistic locking.

Implements C-9: restore acquires a PostgreSQL advisory lock on note_id,
checks version_number for concurrency, creates a new version (non-destructive),
then replaces note content. Returns 409 Conflict on concurrent restore.

Feature 017: Note Versioning — Sprint 1 (T-209)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import ConflictError, NotFoundError
from pilot_space.domain.note_version import NoteVersion, VersionTrigger
from pilot_space.infrastructure.database.repositories.note_repository import NoteRepository
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class RestorePayload:
    """Input for VersionRestoreService."""

    version_id: UUID
    note_id: UUID
    workspace_id: UUID
    restored_by: UUID
    # Optimistic lock token (C-9): must match current max version_number
    expected_version_number: int


@dataclass
class RestoreResult:
    """Output from VersionRestoreService."""

    new_version: NoteVersion
    restored_from_version_id: UUID


class ConcurrentRestoreError(ConflictError):
    """Raised when a concurrent restore is detected (C-9, FR-039-C)."""

    def __init__(self, competing_version_number: int) -> None:
        self.competing_version_number = competing_version_number
        super().__init__(
            f"Concurrent restore detected. Current version_number: {competing_version_number}"
        )


class VersionRestoreService:
    """Restores a note to a historical version (non-destructive).

    Restore flow (C-9):
    1. Acquire PostgreSQL advisory lock on note_id (prevents concurrent restores).
    2. Check current max version_number == expected_version_number (optimistic lock).
    3. If mismatch: raise ConcurrentRestoreError → caller returns 409 Conflict.
    4. Create new version with trigger='manual', label='Restored from {original_label}'.
    5. Replace note content with restored version's content.
    6. Release advisory lock (automatic on transaction end).
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repo: NoteRepository,
        version_repo: NoteVersionRepository,
    ) -> None:
        self._session = session
        self._note_repo = note_repo
        self._version_repo = version_repo

    async def execute(self, payload: RestorePayload) -> RestoreResult:
        """Execute a non-destructive restore.

        Args:
            payload: RestorePayload with target version and lock token.

        Returns:
            RestoreResult with newly created version.

        Raises:
            ValueError: If version or note not found.
            ConcurrentRestoreError: If concurrent restore detected (C-9).
        """
        # Fetch the version to restore
        target_version = await self._version_repo.get_by_id_for_note(
            payload.version_id, payload.note_id, payload.workspace_id
        )
        if not target_version:
            msg = f"Version {payload.version_id} not found for note {payload.note_id}"
            raise NotFoundError(msg)

        note = await self._note_repo.get_by_id(payload.note_id)
        if not note or str(note.workspace_id) != str(payload.workspace_id):
            msg = f"Note {payload.note_id} not found"
            raise NotFoundError(msg)

        # C-9: Acquire PostgreSQL advisory lock on note_id (numeric hash of UUID).
        # The lock is released automatically when the transaction ends.
        note_lock_key = _uuid_to_advisory_key(payload.note_id)
        await self._session.execute(
            __import__("sqlalchemy", fromlist=["text"]).text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": note_lock_key},
        )

        # C-9: Optimistic locking — verify version_number hasn't advanced.
        current_max = await self._version_repo.get_max_version_number(
            payload.note_id, payload.workspace_id
        )
        if current_max != payload.expected_version_number:
            raise ConcurrentRestoreError(competing_version_number=current_max)

        # Build label for the restore snapshot
        original_label = target_version.label or str(target_version.created_at.date())
        restore_label = f"Restored from: {original_label}"[:100]

        # Create new version (non-destructive — original is preserved)
        from pilot_space.infrastructure.database.models.note_version import (
            NoteVersion as NoteVersionModel,
            VersionTrigger as ModelTrigger,
        )

        next_version_number = current_max + 1
        db_version = NoteVersionModel(
            note_id=payload.note_id,
            workspace_id=payload.workspace_id,
            trigger=ModelTrigger.MANUAL,
            content=target_version.content,
            label=restore_label,
            pinned=False,
            created_by=payload.restored_by,
            version_number=next_version_number,
        )
        self._session.add(db_version)
        await self._session.flush()
        await self._session.refresh(db_version)

        # Replace note content with the restored content (FR-039-E: direct DB write)
        note.content = target_version.content
        await self._session.flush()

        new_version = NoteVersion(
            id=db_version.id,
            note_id=db_version.note_id,
            workspace_id=db_version.workspace_id,
            trigger=VersionTrigger.MANUAL,
            content=db_version.content,
            label=db_version.label,
            pinned=db_version.pinned,
            created_by=db_version.created_by,
            version_number=db_version.version_number,
            created_at=db_version.created_at,
        )
        return RestoreResult(
            new_version=new_version,
            restored_from_version_id=payload.version_id,
        )


def _uuid_to_advisory_key(uid: UUID) -> int:
    """Convert UUID to a 63-bit integer for pg_advisory_xact_lock.

    Uses the first 8 bytes of the UUID as a big-endian int, masked to 63 bits.

    Args:
        uid: UUID to convert.

    Returns:
        Integer advisory lock key.
    """
    raw = uid.bytes[:8]
    key = int.from_bytes(raw, "big")
    # Mask to 63 bits (PostgreSQL advisory locks use bigint)
    return key & 0x7FFFFFFFFFFFFFFF
