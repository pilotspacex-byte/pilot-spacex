"""Service for creating issues from AI extraction results.

Handles multi-step issue creation with NoteIssueLink creation and error handling.
Reusable by both ai_extraction.py and workspace_notes_ai.py routers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import (
    NotFoundError,
    ValidationError as DomainValidationError,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.activity_repository import (
        ActivityRepository,
    )
    from pilot_space.infrastructure.database.repositories.issue_repository import (
        IssueRepository,
    )
    from pilot_space.infrastructure.database.repositories.label_repository import (
        LabelRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_issue_link_repository import (
        NoteIssueLinkRepository,
    )
    from pilot_space.infrastructure.database.repositories.project_repository import (
        ProjectRepository,
    )

logger = get_logger(__name__)


@dataclass
class ExtractedIssueInput:
    """Single issue to create from extraction."""

    title: str
    description: str | None = None
    priority: int = 4
    source_block_id: str | None = None


@dataclass
class CreateExtractedIssuesPayload:
    """Input for creating extracted issues."""

    workspace_id: UUID
    note_id: str | None
    issues: list[ExtractedIssueInput]
    project_id: str | None
    user_id: UUID


@dataclass
class CreatedIssueResult:
    """Single created issue in the result."""

    id: str
    identifier: str
    title: str


@dataclass
class CreateExtractedIssuesResult:
    """Result of creating extracted issues."""

    created_issues: list[CreatedIssueResult] = field(default_factory=list)
    created_count: int = 0
    source_note_id: str | None = None
    message: str = ""


class CreateExtractedIssuesService:
    """Creates issues from AI extraction results.

    Handles:
    - Validation of project and note IDs
    - Issue creation via CreateIssueService
    - NoteIssueLink creation when note_id is provided
    - Error handling per-issue (continues on individual failures)

    Args:
        session: Request-scoped async database session.
        project_repository: Repository for project lookups.
    """

    def __init__(
        self,
        session: AsyncSession,
        project_repository: ProjectRepository,
        issue_repository: IssueRepository,
        activity_repository: ActivityRepository,
        label_repository: LabelRepository,
        note_issue_link_repository: NoteIssueLinkRepository,
    ) -> None:
        self._session = session
        self._project_repo = project_repository
        self._issue_repo = issue_repository
        self._activity_repo = activity_repository
        self._label_repo = label_repository
        self._note_issue_link_repo = note_issue_link_repository

    async def execute(self, payload: CreateExtractedIssuesPayload) -> CreateExtractedIssuesResult:
        """Create extracted issues and link them to the source note.

        Raises:
            DomainValidationError: If no issues provided or invalid IDs.
            NotFoundError: If project not found.
        """
        from pilot_space.application.services.issue import (
            CreateIssuePayload,
            CreateIssueService,
        )
        from pilot_space.infrastructure.database.models.issue import IssuePriority
        from pilot_space.infrastructure.database.models.note_issue_link import (
            NoteIssueLink,
            NoteLinkType,
        )

        if not payload.issues:
            raise DomainValidationError("No issues to create")

        if not payload.project_id:
            raise DomainValidationError("project_id is required to create issues")

        try:
            project_id = UUID(payload.project_id)
        except (ValueError, AttributeError):
            raise DomainValidationError("Invalid project_id format") from None

        # Pre-fetch project identifier for constructing issue identifiers
        project_identifier = await self._project_repo.get_identifier_by_id(
            project_id, payload.workspace_id
        )
        if not project_identifier:
            raise NotFoundError(f"Project not found for id {project_id}")

        note_uuid: UUID | None = None
        if payload.note_id:
            try:
                note_uuid = UUID(payload.note_id)
            except (ValueError, AttributeError):
                raise DomainValidationError("Invalid note_id format") from None

        issue_service = CreateIssueService(
            session=self._session,
            issue_repository=self._issue_repo,
            activity_repository=self._activity_repo,
            label_repository=self._label_repo,
        )
        link_repo = self._note_issue_link_repo if note_uuid else None

        priority_map = {
            0: IssuePriority.URGENT,
            1: IssuePriority.HIGH,
            2: IssuePriority.MEDIUM,
            3: IssuePriority.LOW,
            4: IssuePriority.NONE,
        }

        created_issues_data: list[CreatedIssueResult] = []
        for issue_data in payload.issues:
            issue_payload = CreateIssuePayload(
                workspace_id=payload.workspace_id,
                project_id=project_id,
                reporter_id=payload.user_id,
                name=issue_data.title,
                description=issue_data.description,
                priority=priority_map.get(issue_data.priority, IssuePriority.NONE),
            )
            try:
                async with self._session.begin_nested():
                    result = await issue_service.execute(issue_payload)
                    if result.issue:
                        issue_id = result.issue.id
                        identifier = f"{project_identifier}-{result.issue.sequence_id}"
                        created_issues_data.append(
                            CreatedIssueResult(
                                id=str(issue_id),
                                identifier=identifier,
                                title=result.issue.name,
                            )
                        )

                        # Create NoteIssueLink when note_id is provided
                        if note_uuid and link_repo:
                            try:
                                existing = await link_repo.find_existing(
                                    note_id=note_uuid,
                                    issue_id=issue_id,
                                    link_type=NoteLinkType.EXTRACTED,
                                    workspace_id=payload.workspace_id,
                                )
                                if not existing:
                                    link = NoteIssueLink(
                                        note_id=note_uuid,
                                        issue_id=issue_id,
                                        link_type=NoteLinkType.EXTRACTED,
                                        block_id=issue_data.source_block_id,
                                        workspace_id=payload.workspace_id,
                                    )
                                    await link_repo.create(link)
                            except Exception:
                                logger.warning(
                                    "Failed to create NoteIssueLink, issue was still created",
                                    extra={
                                        "note_id": str(note_uuid),
                                        "issue_id": str(issue_id),
                                    },
                                )
            except Exception:
                logger.warning(
                    "Failed to create issue",
                    extra={"title": issue_data.title},
                    exc_info=True,
                )
                continue

        await self._session.commit()

        return CreateExtractedIssuesResult(
            created_issues=created_issues_data,
            created_count=len(created_issues_data),
            source_note_id=payload.note_id,
            message=f"Successfully created {len(created_issues_data)} issues",
        )
