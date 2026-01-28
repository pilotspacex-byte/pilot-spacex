"""AIContext SQLAlchemy model.

AIContext stores AI-aggregated context for issues including:
- Related issues, notes, and pages
- Code references from linked commits/PRs
- Tasks checklist with implementation guidance
- Claude Code prompt for developers
- Conversation history for refinement

T201: Create AIContext model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue


class AIContext(WorkspaceScopedModel):
    """AI-aggregated context for issues.

    Provides comprehensive context for developers including:
    - Summary and analysis of the issue
    - Related issues, notes, and pages for reference
    - Code references from linked commits/PRs
    - Implementation tasks checklist
    - Claude Code prompt for AI-assisted development
    - Conversation history for multi-turn refinement

    Per US-12: AI Context feature provides aggregated context
    for issues using Claude Opus 4.5 with multi-turn conversation.

    Attributes:
        issue_id: FK to the issue this context belongs to (one-to-one).
        content: JSONBCompat containing the structured context data.
        claude_code_prompt: Generated prompt for Claude Code.
        related_issues: List of related issue references with relevance scores.
        related_notes: List of related note references with excerpts.
        related_pages: List of related page references.
        code_references: List of code file references with line ranges.
        tasks_checklist: List of implementation tasks with dependencies.
        conversation_history: Multi-turn conversation for refinement.
        generated_at: When the context was first generated.
        last_refined_at: When the context was last refined via chat.
        version: Version number for optimistic locking.
    """

    __tablename__ = "ai_contexts"  # type: ignore[assignment]

    # One-to-one relationship with issue
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Structured content (primary context data)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=dict,
    )
    # content structure:
    # {
    #   "summary": "AI-generated summary of the issue",
    #   "analysis": "Detailed analysis and recommendations",
    #   "complexity": "low|medium|high",
    #   "estimated_effort": "S|M|L|XL",
    #   "key_considerations": ["list", "of", "points"],
    #   "suggested_approach": "Implementation approach",
    #   "potential_blockers": ["list of potential blockers"],
    #   "model_used": "claude-opus-4-5-20251101",
    #   "generation_timestamp": "2026-01-24T10:00:00Z"
    # }

    # Claude Code prompt for developers
    claude_code_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Related items (denormalized for performance)
    related_issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # related_issues structure:
    # [
    #   {
    #     "id": "uuid",
    #     "identifier": "PILOT-123",
    #     "title": "Issue title",
    #     "relevance_score": 0.85,
    #     "excerpt": "Why it's related...",
    #     "state": "In Progress"
    #   }
    # ]

    related_notes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # related_notes structure:
    # [
    #   {
    #     "id": "uuid",
    #     "title": "Note title",
    #     "relevance_score": 0.78,
    #     "excerpt": "Relevant content excerpt..."
    #   }
    # ]

    related_pages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # related_pages structure:
    # [
    #   {
    #     "id": "uuid",
    #     "title": "Page title",
    #     "relevance_score": 0.72,
    #     "excerpt": "Relevant content excerpt..."
    #   }
    # ]

    # Code references from linked commits/PRs
    code_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # code_references structure:
    # [
    #   {
    #     "file_path": "src/services/auth.py",
    #     "line_start": 45,
    #     "line_end": 78,
    #     "description": "Authentication service method",
    #     "relevance": "high|medium|low",
    #     "source": "commit|pull_request|manual",
    #     "source_id": "external_id"
    #   }
    # ]

    # Implementation tasks checklist
    tasks_checklist: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # tasks_checklist structure:
    # [
    #   {
    #     "id": "task-1",
    #     "description": "Implement the service method",
    #     "completed": false,
    #     "dependencies": ["task-0"],
    #     "estimated_effort": "M",
    #     "order": 1
    #   }
    # ]

    # Conversation history for multi-turn refinement
    conversation_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )
    # conversation_history structure:
    # [
    #   {
    #     "role": "user|assistant",
    #     "content": "Message content",
    #     "timestamp": "2026-01-24T10:00:00Z"
    #   }
    # ]

    # Generation timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_refined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Version for optimistic locking
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Relationship to issue
    issue: Mapped[Issue] = relationship(
        "Issue",
        back_populates="ai_context",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("issue_id", name="uq_ai_contexts_issue_id"),
        Index("ix_ai_contexts_workspace_id", "workspace_id"),
        Index("ix_ai_contexts_issue_id", "issue_id"),
        Index("ix_ai_contexts_generated_at", "generated_at"),
        Index("ix_ai_contexts_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AIContext(id={self.id}, issue_id={self.issue_id}, version={self.version})>"

    @property
    def summary(self) -> str | None:
        """Get the summary from content."""
        if not self.content:
            return None
        return self.content.get("summary")

    @property
    def has_conversation(self) -> bool:
        """Check if there's conversation history."""
        return bool(self.conversation_history)

    @property
    def conversation_count(self) -> int:
        """Get number of conversation messages."""
        return len(self.conversation_history) if self.conversation_history else 0

    @property
    def task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks_checklist) if self.tasks_checklist else 0

    @property
    def completed_task_count(self) -> int:
        """Get number of completed tasks."""
        if not self.tasks_checklist:
            return 0
        return sum(1 for task in self.tasks_checklist if task.get("completed", False))

    @property
    def is_stale(self) -> bool:
        """Check if context might be stale (more than 24 hours old).

        Actual staleness detection should also consider if the issue
        has been updated since generation.
        """
        from datetime import UTC, timedelta

        if not self.generated_at:
            return True
        now = datetime.now(tz=UTC)
        age = now - self.generated_at.replace(tzinfo=UTC)
        return age > timedelta(hours=24)

    def add_conversation_message(
        self,
        role: str,
        content: str,
    ) -> None:
        """Add a message to conversation history.

        Args:
            role: Message role ('user' or 'assistant').
            content: Message content.
        """
        from datetime import UTC

        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
        )

    def mark_task_completed(self, task_id: str) -> bool:
        """Mark a task as completed.

        Args:
            task_id: The task ID to mark as completed.

        Returns:
            True if task was found and updated, False otherwise.
        """
        if not self.tasks_checklist:
            return False

        for task in self.tasks_checklist:
            if task.get("id") == task_id:
                task["completed"] = True
                return True
        return False


__all__ = ["AIContext"]
