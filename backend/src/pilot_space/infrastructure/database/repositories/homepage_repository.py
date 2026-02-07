"""Homepage repository for activity feed data access.

Provides efficient queries for the Homepage Hub activity feed:
- Recent notes with latest annotation preview
- Recent issues with state, priority, assignee, and last activity

References:
- specs/012-homepage-note/spec.md API Endpoints section
- US-19: Homepage Hub feature
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, select, text

from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.note_annotation import NoteAnnotation

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class NoteActivityRow:
    """Lightweight note data for activity feed rendering.

    Avoids loading full TipTap content — only the fields needed
    for the activity card are included.
    """

    id: UUID
    title: str
    word_count: int
    is_pinned: bool
    updated_at: datetime
    project_id: UUID | None
    project_name: str | None
    project_identifier: str | None
    annotation_type: str | None
    annotation_content: str | None
    annotation_confidence: float | None


@dataclass
class IssueActivityRow:
    """Lightweight issue data for activity feed rendering."""

    id: UUID
    sequence_id: int
    name: str
    priority: str
    updated_at: datetime
    project_id: UUID | None
    project_name: str | None
    project_identifier: str | None
    state_name: str | None
    state_color: str | None
    state_group: str | None
    assignee_id: UUID | None
    assignee_name: str | None
    assignee_avatar_url: str | None
    last_activity: str | None


class HomepageRepository:
    """Repository for homepage activity feed queries.

    Uses optimised queries with lateral joins / subqueries to fetch
    recent notes and issues with their latest annotation or activity
    in a single round-trip per entity type.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize HomepageRepository.

        Args:
            session: The async database session.
        """
        self.session = session

    async def get_recent_notes_with_annotations(
        self,
        workspace_id: UUID,
        *,
        limit: int = 20,
        cursor_updated_at: datetime | None = None,
    ) -> Sequence[NoteActivityRow]:
        """Fetch recent notes with their latest annotation preview.

        Returns notes ordered by updated_at desc, with the most recent
        annotation (by created_at) attached via a correlated subquery.

        Args:
            workspace_id: Workspace to query.
            limit: Max notes to return.
            cursor_updated_at: Pagination cursor (exclude notes updated
                at or after this timestamp).

        Returns:
            Sequence of NoteActivityRow dataclass instances.
        """
        from pilot_space.infrastructure.database.models.project import Project

        # Correlated subquery: latest annotation per note
        latest_ann = (
            select(
                NoteAnnotation.type.label("annotation_type"),
                NoteAnnotation.content,
                NoteAnnotation.confidence,
            )
            .where(
                NoteAnnotation.note_id == Note.id,
                NoteAnnotation.is_deleted == False,  # noqa: E712
            )
            .order_by(NoteAnnotation.created_at.desc())
            .limit(1)
            .correlate(Note)
            .lateral("latest_ann")
        )

        query = (
            select(
                Note.id,
                Note.title,
                Note.word_count,
                Note.is_pinned,
                Note.updated_at,
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                Project.identifier.label("project_identifier"),
                latest_ann.c.annotation_type,
                latest_ann.c.content.label("annotation_content"),
                latest_ann.c.confidence.label("annotation_confidence"),
            )
            .outerjoin(Project, Note.project_id == Project.id)
            .outerjoin(latest_ann, text("true"))
            .where(
                Note.workspace_id == workspace_id,
                Note.is_deleted == False,  # noqa: E712
            )
        )

        if cursor_updated_at is not None:
            query = query.where(Note.updated_at < cursor_updated_at)

        query = query.order_by(desc(Note.updated_at)).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            NoteActivityRow(
                id=r.id,
                title=r.title,
                word_count=r.word_count,
                is_pinned=r.is_pinned,
                updated_at=r.updated_at,
                project_id=r.project_id,
                project_name=r.project_name,
                project_identifier=r.project_identifier,
                annotation_type=r.annotation_type,
                annotation_content=r.annotation_content,
                annotation_confidence=r.annotation_confidence,
            )
            for r in rows
        ]

    async def get_recent_issues_with_activity(
        self,
        workspace_id: UUID,
        *,
        limit: int = 20,
        cursor_updated_at: datetime | None = None,
    ) -> Sequence[IssueActivityRow]:
        """Fetch recent issues with state, priority, assignee, and last activity.

        Returns issues ordered by updated_at desc, with the most recent
        activity description attached via a correlated subquery.

        Args:
            workspace_id: Workspace to query.
            limit: Max issues to return.
            cursor_updated_at: Pagination cursor (exclude issues updated
                at or after this timestamp).

        Returns:
            Sequence of IssueActivityRow dataclass instances.
        """
        from pilot_space.infrastructure.database.models.activity import Activity
        from pilot_space.infrastructure.database.models.project import Project
        from pilot_space.infrastructure.database.models.state import State
        from pilot_space.infrastructure.database.models.user import User

        # Correlated subquery: latest activity per issue
        # Activity has no single description column; use comment for
        # comment activities, or activity_type as fallback summary.
        latest_act = (
            select(Activity.comment.label("description"))
            .where(Activity.issue_id == Issue.id)
            .order_by(Activity.created_at.desc())
            .limit(1)
            .correlate(Issue)
            .lateral("latest_act")
        )

        query = (
            select(
                Issue.id,
                Issue.sequence_id,
                Issue.name,
                Issue.priority,
                Issue.updated_at,
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                Project.identifier.label("project_identifier"),
                State.name.label("state_name"),
                State.color.label("state_color"),
                State.group.label("state_group"),
                User.id.label("assignee_id"),
                User.full_name.label("assignee_name"),
                User.avatar_url.label("assignee_avatar_url"),
                latest_act.c.description.label("last_activity"),
            )
            .outerjoin(Project, Issue.project_id == Project.id)
            .outerjoin(State, Issue.state_id == State.id)
            .outerjoin(User, Issue.assignee_id == User.id)
            .outerjoin(latest_act, text("true"))
            .where(
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )

        if cursor_updated_at is not None:
            query = query.where(Issue.updated_at < cursor_updated_at)

        query = query.order_by(desc(Issue.updated_at)).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            IssueActivityRow(
                id=r.id,
                sequence_id=r.sequence_id,
                name=r.name,
                priority=r.priority,
                updated_at=r.updated_at,
                project_id=r.project_id,
                project_name=r.project_name,
                project_identifier=r.project_identifier,
                state_name=r.state_name,
                state_color=r.state_color,
                state_group=r.state_group,
                assignee_id=r.assignee_id,
                assignee_name=r.assignee_name,
                assignee_avatar_url=r.assignee_avatar_url,
                last_activity=r.last_activity,
            )
            for r in rows
        ]
