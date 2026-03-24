"""VersionSnapshotService — capture note snapshots.

Creates NoteVersion records for auto/manual/ai_before/ai_after triggers.
Called by skill executor before/after AI operations (T-213).

Feature 017: Note Versioning — Sprint 1 (T-206)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from pilot_space.domain.exceptions import ConflictError, NotFoundError
from pilot_space.domain.note_version import NoteVersion, VersionTrigger
from pilot_space.infrastructure.database.repositories.note_repository import NoteRepository
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_MAX_VERSION_RETRIES = 3


@dataclass
class SnapshotPayload:
    """Input for VersionSnapshotService."""

    note_id: UUID
    workspace_id: UUID
    trigger: VersionTrigger
    created_by: UUID | None = None
    label: str | None = None


@dataclass
class SnapshotResult:
    """Output from VersionSnapshotService."""

    version: NoteVersion


class VersionSnapshotService:
    """Captures a point-in-time snapshot of a note's content.

    Used by:
    - Manual "Save Version" (trigger=manual, created_by=user)
    - Auto-version job (trigger=auto, created_by=None)
    - Skill executor before AI op (trigger=ai_before)
    - Skill executor after AI op (trigger=ai_after)
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

    async def execute(self, payload: SnapshotPayload) -> SnapshotResult:
        """Create a version snapshot of the current note content.

        Args:
            payload: Snapshot request with note_id, workspace_id, trigger, etc.

        Returns:
            SnapshotResult with the created NoteVersion.

        Raises:
            ValueError: If note not found or doesn't belong to workspace.
        """
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note or str(note.workspace_id) != str(payload.workspace_id):
            msg = f"Note {payload.note_id} not found in workspace {payload.workspace_id}"
            raise NotFoundError(msg)

        label = payload.label or _default_label(payload.trigger)

        from pilot_space.infrastructure.database.models.note_version import (
            NoteVersion as NoteVersionModel,
            VersionTrigger as ModelTrigger,
        )

        for attempt in range(_MAX_VERSION_RETRIES):
            # Re-read max_version on each retry to handle concurrent inserts
            max_version = await self._version_repo.get_max_version_number(
                payload.note_id, payload.workspace_id
            )
            next_version_number = max_version + 1

            db_version = NoteVersionModel(
                note_id=payload.note_id,
                workspace_id=payload.workspace_id,
                trigger=ModelTrigger(payload.trigger.value),
                content=note.content,
                label=label,
                pinned=False,
                created_by=payload.created_by,
                version_number=next_version_number,
            )
            self._session.add(db_version)
            try:
                await self._session.flush()
            except IntegrityError:
                await self._session.rollback()
                if attempt >= _MAX_VERSION_RETRIES - 1:
                    raise
                continue

            await self._session.refresh(db_version)

            return SnapshotResult(
                version=NoteVersion(
                    id=db_version.id,
                    note_id=db_version.note_id,
                    workspace_id=db_version.workspace_id,
                    trigger=VersionTrigger(db_version.trigger.value),
                    content=db_version.content,
                    label=db_version.label,
                    pinned=db_version.pinned,
                    created_by=db_version.created_by,
                    version_number=db_version.version_number,
                    created_at=db_version.created_at,
                )
            )

        msg = f"Failed to create snapshot for note {payload.note_id} after {_MAX_VERSION_RETRIES} retries"
        raise ConflictError(msg)


def _default_label(trigger: VersionTrigger) -> str:
    """Generate a default label for a trigger type."""
    labels = {
        VersionTrigger.AUTO: "Auto-save",
        VersionTrigger.MANUAL: "Manual save",
        VersionTrigger.AI_BEFORE: "Before AI edit",
        VersionTrigger.AI_AFTER: "After AI edit",
    }
    return labels.get(trigger, "Snapshot")
