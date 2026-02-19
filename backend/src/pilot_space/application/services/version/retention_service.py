"""RetentionService — clean up old note versions.

Deletes versions that exceed the configured max count or age,
while always exempting pinned versions (FR-074, FR-075).

Feature 017: Note Versioning — Sprint 1 (T-212)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Default retention limits per workspace config (overridable)
DEFAULT_MAX_COUNT = 50
DEFAULT_MAX_AGE_DAYS = 90


@dataclass
class RetentionPayload:
    """Input for RetentionService."""

    note_id: UUID
    workspace_id: UUID
    max_count: int = DEFAULT_MAX_COUNT
    max_age_days: int = DEFAULT_MAX_AGE_DAYS


@dataclass
class RetentionResult:
    """Output from RetentionService."""

    deleted_count: int
    retained_count: int


class RetentionService:
    """Enforces retention limits on note versions.

    Rules:
    - Pinned versions are ALWAYS exempt.
    - At most max_count unpinned versions are kept (newest first).
    - Unpinned versions older than max_age_days are deleted.
    """

    def __init__(
        self,
        session: AsyncSession,
        version_repo: NoteVersionRepository,
    ) -> None:
        self._session = session
        self._version_repo = version_repo

    async def execute(self, payload: RetentionPayload) -> RetentionResult:
        """Run retention cleanup for a note.

        Args:
            payload: RetentionPayload with note_id, workspace_id, and limits.

        Returns:
            RetentionResult with deleted and retained counts.
        """
        candidates = await self._version_repo.find_retention_candidates(
            note_id=payload.note_id,
            workspace_id=payload.workspace_id,
            max_count=payload.max_count,
            max_age_days=payload.max_age_days,
        )

        if not candidates:
            total = await self._version_repo.count_by_note(payload.note_id, payload.workspace_id)
            return RetentionResult(deleted_count=0, retained_count=total)

        candidate_ids = [v.id for v in candidates]
        deleted = await self._version_repo.batch_delete(candidate_ids)

        retained = await self._version_repo.count_by_note(payload.note_id, payload.workspace_id)
        return RetentionResult(deleted_count=deleted, retained_count=retained)
