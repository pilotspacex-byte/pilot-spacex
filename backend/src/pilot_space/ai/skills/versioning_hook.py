"""VersioningSkillHook — wire ai_before/ai_after snapshots into skill execution.

Creates NoteVersion snapshots before and after AI skill operations that
mutate note content. Called by the skill dispatch layer, not the executor directly.

Feature 017: Note Versioning — Sprint 1 (T-213)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.application.services.version.snapshot_service import (
    SnapshotPayload,
    VersionSnapshotService,
)
from pilot_space.domain.note_version import VersionTrigger
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.note_repository import NoteRepository
    from pilot_space.infrastructure.database.repositories.note_version_repository import (
        NoteVersionRepository,
    )

logger = get_logger(__name__)

# Skills that mutate note content and require ai_before/ai_after snapshots
_NOTE_MUTATING_SKILLS: frozenset[str] = frozenset(
    {
        "improve-writing",
        "generate-diagram",
        "summarize",
        "extract-issues",
        "enhance-issue",
        "decompose-tasks",
        "generate-code",
    }
)


class VersioningSkillHook:
    """Manages ai_before/ai_after version snapshots around skill execution.

    Usage (in skill dispatch layer):
        async with hook.around_skill(skill_name, note_id, workspace_id, user_id):
            result = await executor.execute(request, output_payload)
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repo: NoteRepository,
        version_repo: NoteVersionRepository,
    ) -> None:
        self._snapshot_svc = VersionSnapshotService(session, note_repo, version_repo)

    def should_version(self, skill_name: str) -> bool:
        """Check if a skill requires before/after versioning.

        Args:
            skill_name: Skill name (e.g. 'improve-writing').

        Returns:
            True if ai_before/ai_after snapshots should be created.
        """
        return skill_name in _NOTE_MUTATING_SKILLS

    @asynccontextmanager
    async def around_skill(
        self,
        skill_name: str,
        note_id: UUID | None,
        workspace_id: UUID,
        user_id: UUID | None,
    ) -> AsyncIterator[None]:
        """Context manager that creates ai_before and ai_after snapshots.

        If the skill doesn't mutate notes, or no note_id provided, yields without
        creating snapshots (transparent pass-through).

        Args:
            skill_name: Skill being executed.
            note_id: Note being mutated (None for non-note skills).
            workspace_id: Workspace UUID.
            user_id: User triggering the skill.

        Yields:
            None — caller executes the skill body here.
        """
        if not note_id or not self.should_version(skill_name):
            yield
            return

        # ai_before snapshot
        try:
            await self._snapshot_svc.execute(
                SnapshotPayload(
                    note_id=note_id,
                    workspace_id=workspace_id,
                    trigger=VersionTrigger.AI_BEFORE,
                    created_by=user_id,
                    label=f"Before: {skill_name}",
                )
            )
            logger.debug(
                "[VersioningHook] ai_before snapshot note_id=%s skill=%s",
                note_id,
                skill_name,
            )
        except Exception as exc:
            # Non-fatal: log and continue; don't block skill execution
            logger.warning(
                "[VersioningHook] ai_before snapshot failed note_id=%s skill=%s err=%s",
                note_id,
                skill_name,
                exc,
            )

        try:
            yield
        finally:
            # ai_after snapshot (always attempt, even if skill failed)
            try:
                await self._snapshot_svc.execute(
                    SnapshotPayload(
                        note_id=note_id,
                        workspace_id=workspace_id,
                        trigger=VersionTrigger.AI_AFTER,
                        created_by=user_id,
                        label=f"After: {skill_name}",
                    )
                )
                logger.debug(
                    "[VersioningHook] ai_after snapshot note_id=%s skill=%s",
                    note_id,
                    skill_name,
                )
            except Exception as exc:
                logger.warning(
                    "[VersioningHook] ai_after snapshot failed note_id=%s skill=%s err=%s",
                    note_id,
                    skill_name,
                    exc,
                )


__all__ = ["VersioningSkillHook"]
