"""AIContext repository for database operations.

T206: Create AIContextRepository for context persistence.

Provides:
- CRUD operations for AIContext
- Cache-aware retrieval (1 hour staleness check)
- Conversation history management
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.ai_context import AIContext
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Cache duration for AI context (1 hour)
CACHE_DURATION_HOURS = 1


class AIContextRepository(BaseRepository[AIContext]):
    """Repository for AIContext operations.

    Provides specialized methods for:
    - Issue-based retrieval (one-to-one)
    - Cache-aware freshness checking
    - Conversation history updates
    - Task completion tracking
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, AIContext)

    async def get_by_issue_id(
        self,
        issue_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> AIContext | None:
        """Get AI context by issue ID.

        Args:
            issue_id: Issue UUID.
            include_deleted: Whether to include soft-deleted contexts.

        Returns:
            AIContext if found, None otherwise.
        """
        query = select(AIContext).where(AIContext.issue_id == issue_id)
        if not include_deleted:
            query = query.where(AIContext.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> tuple[AIContext, bool]:
        """Get existing AI context or create a new one.

        Args:
            issue_id: Issue UUID.
            workspace_id: Workspace UUID.

        Returns:
            Tuple of (AIContext, created) where created is True if new.
        """
        existing = await self.get_by_issue_id(issue_id)
        if existing:
            return existing, False

        # Create new context
        context = AIContext(
            workspace_id=workspace_id,
            issue_id=issue_id,
            content={},
            related_issues=[],
            related_notes=[],
            related_pages=[],
            code_references=[],
            tasks_checklist=[],
            conversation_history=[],
            generated_at=datetime.now(tz=UTC),
            version=1,
        )
        context = await self.create(context)
        return context, True

    async def is_fresh(
        self,
        issue_id: UUID,
        max_age_hours: int = CACHE_DURATION_HOURS,
    ) -> bool:
        """Check if cached context is still fresh.

        Args:
            issue_id: Issue UUID.
            max_age_hours: Maximum age in hours.

        Returns:
            True if context exists and is fresh, False otherwise.
        """
        context = await self.get_by_issue_id(issue_id)
        if not context or not context.generated_at:
            return False

        cutoff = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)
        return context.generated_at.replace(tzinfo=UTC) > cutoff

    async def update_content(
        self,
        issue_id: UUID,
        content: dict[str, Any],
        claude_code_prompt: str | None = None,
        tasks_checklist: list[dict[str, Any]] | None = None,
        related_issues: list[dict[str, Any]] | None = None,
        related_notes: list[dict[str, Any]] | None = None,
        related_pages: list[dict[str, Any]] | None = None,
        code_references: list[dict[str, Any]] | None = None,
    ) -> AIContext | None:
        """Update AI context content.

        Args:
            issue_id: Issue UUID.
            content: New content dictionary.
            claude_code_prompt: Generated Claude Code prompt.
            tasks_checklist: Updated tasks checklist.
            related_issues: Updated related issues.
            related_notes: Updated related notes.
            related_pages: Updated related pages.
            code_references: Updated code references.

        Returns:
            Updated AIContext or None if not found.
        """
        context = await self.get_by_issue_id(issue_id)
        if not context:
            return None

        # Update fields
        context.content = content
        context.generated_at = datetime.now(tz=UTC)
        context.version += 1

        if claude_code_prompt is not None:
            context.claude_code_prompt = claude_code_prompt

        if tasks_checklist is not None:
            context.tasks_checklist = tasks_checklist

        if related_issues is not None:
            context.related_issues = related_issues

        if related_notes is not None:
            context.related_notes = related_notes

        if related_pages is not None:
            context.related_pages = related_pages

        if code_references is not None:
            context.code_references = code_references

        return await self.update(context)

    async def add_conversation_message(
        self,
        issue_id: UUID,
        role: str,
        content: str,
    ) -> AIContext | None:
        """Add a message to conversation history.

        Args:
            issue_id: Issue UUID.
            role: Message role ('user' or 'assistant').
            content: Message content.

        Returns:
            Updated AIContext or None if not found.
        """
        context = await self.get_by_issue_id(issue_id)
        if not context:
            return None

        # Add message to history
        context.add_conversation_message(role, content)
        context.last_refined_at = datetime.now(tz=UTC)

        return await self.update(context)

    async def update_conversation_history(
        self,
        issue_id: UUID,
        history: list[dict[str, Any]],
    ) -> AIContext | None:
        """Replace entire conversation history.

        Args:
            issue_id: Issue UUID.
            history: New conversation history.

        Returns:
            Updated AIContext or None if not found.
        """
        context = await self.get_by_issue_id(issue_id)
        if not context:
            return None

        context.conversation_history = history
        context.last_refined_at = datetime.now(tz=UTC)

        return await self.update(context)

    async def clear_conversation_history(
        self,
        issue_id: UUID,
    ) -> AIContext | None:
        """Clear conversation history for a context.

        Args:
            issue_id: Issue UUID.

        Returns:
            Updated AIContext or None if not found.
        """
        return await self.update_conversation_history(issue_id, [])

    async def mark_task_completed(
        self,
        issue_id: UUID,
        task_id: str,
    ) -> AIContext | None:
        """Mark a task as completed.

        Args:
            issue_id: Issue UUID.
            task_id: Task ID to mark completed.

        Returns:
            Updated AIContext or None if not found or task not found.
        """
        context = await self.get_by_issue_id(issue_id)
        if not context:
            return None

        if context.mark_task_completed(task_id):
            return await self.update(context)
        return None

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> int:
        """Count AI contexts in a workspace.

        Args:
            workspace_id: Workspace UUID.
            include_deleted: Whether to include soft-deleted.

        Returns:
            Count of contexts.
        """
        return await self.count(
            include_deleted=include_deleted,
            filters={"workspace_id": workspace_id},
        )

    async def get_recent_by_workspace(
        self,
        workspace_id: UUID,
        limit: int = 10,
    ) -> list[AIContext]:
        """Get recently generated contexts for a workspace.

        Args:
            workspace_id: Workspace UUID.
            limit: Maximum contexts to return.

        Returns:
            List of recent AIContext instances.
        """
        query = (
            select(AIContext)
            .where(
                and_(
                    AIContext.workspace_id == workspace_id,
                    AIContext.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(AIContext.generated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def bulk_regenerate_stale(
        self,
        workspace_id: UUID,
        max_age_hours: int = 24,
    ) -> list[UUID]:
        """Find issue IDs with stale contexts that need regeneration.

        Args:
            workspace_id: Workspace UUID.
            max_age_hours: Maximum age in hours before considered stale.

        Returns:
            List of issue IDs needing regeneration.
        """
        cutoff = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)

        query = select(AIContext.issue_id).where(
            and_(
                AIContext.workspace_id == workspace_id,
                AIContext.is_deleted == False,  # noqa: E712
                AIContext.generated_at < cutoff,
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


__all__ = ["AIContextRepository"]
