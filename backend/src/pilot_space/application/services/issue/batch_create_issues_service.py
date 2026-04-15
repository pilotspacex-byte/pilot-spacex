"""Batch Issue Creation Service.

Creates multiple issues in a single request, calling CreateIssueService for each item.
Handles partial failures gracefully — returns per-issue success/failure results.

Phase 75, Plan 01 — CIP-01, CIP-02, CIP-05.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.application.services.issue.create_issue_service import (
        CreateIssueService,
    )

logger = get_logger(__name__)


@dataclass
class BatchIssueItemPayload:
    """Payload for a single issue in a batch create request."""

    title: str
    description: str | None = None
    acceptance_criteria: list[dict[str, Any]] | None = None
    priority: str = "medium"


@dataclass
class BatchCreateIssuesPayload:
    """Payload for creating a batch of issues."""

    workspace_id: UUID
    project_id: UUID
    reporter_id: UUID
    issues: list[BatchIssueItemPayload]
    source_note_id: UUID | None = None


@dataclass
class BatchCreateIssueItemResult:
    """Result for a single issue in a batch create response."""

    index: int
    success: bool
    issue_id: UUID | None = None
    error: str | None = None


@dataclass
class BatchCreateIssuesResult:
    """Result from batch issue creation."""

    results: list[BatchCreateIssueItemResult] = field(default_factory=list)
    created_count: int = 0
    failed_count: int = 0


class BatchCreateIssuesService:
    """Service for creating multiple issues in a batch.

    Iterates over BatchIssueItemPayload items, calling CreateIssueService.execute()
    for each. Per-item failures are caught and recorded without aborting remaining items.

    Per RESEARCH Pitfall 6 — partial failures must be handled gracefully.
    """

    def __init__(
        self,
        session: AsyncSession,
        create_issue_service: CreateIssueService,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            create_issue_service: Service instance for individual issue creation.
        """
        self._session = session
        self._create_issue_service = create_issue_service

    async def execute(self, payload: BatchCreateIssuesPayload) -> BatchCreateIssuesResult:
        """Create multiple issues in a batch.

        Args:
            payload: Batch creation parameters.

        Returns:
            BatchCreateIssuesResult with per-issue success/failure records.
        """
        from pilot_space.application.services.issue.create_issue_service import (
            CreateIssuePayload,
        )
        from pilot_space.infrastructure.database.models.issue import IssuePriority

        priority_map = {
            "urgent": IssuePriority.URGENT,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
            "none": IssuePriority.NONE,
        }

        results: list[BatchCreateIssueItemResult] = []
        created_count = 0
        failed_count = 0

        logger.info(
            "BatchCreateIssuesService: creating %d issues",
            len(payload.issues),
            extra={
                "workspace_id": str(payload.workspace_id),
                "project_id": str(payload.project_id),
                "source_note_id": str(payload.source_note_id) if payload.source_note_id else None,
            },
        )

        for idx, item in enumerate(payload.issues):
            try:
                priority = priority_map.get(
                    item.priority.lower() if item.priority else "medium",
                    IssuePriority.MEDIUM,
                )
                svc_payload = CreateIssuePayload(
                    workspace_id=payload.workspace_id,
                    project_id=payload.project_id,
                    reporter_id=payload.reporter_id,
                    name=item.title,
                    description=item.description,
                    priority=priority,
                    acceptance_criteria=item.acceptance_criteria,
                    source_note_id=payload.source_note_id,
                    ai_enhanced=True,
                    ai_metadata={"source": "batch_create", "batch_index": idx},
                )

                result = await self._create_issue_service.execute(svc_payload)
                await self._session.commit()

                results.append(
                    BatchCreateIssueItemResult(
                        index=idx,
                        success=True,
                        issue_id=result.issue.id,
                    )
                )
                created_count += 1
                logger.info(
                    "BatchCreateIssuesService: created issue %d/%d: %s",
                    idx + 1,
                    len(payload.issues),
                    str(result.issue.id),
                )

            except Exception as exc:
                logger.warning(
                    "BatchCreateIssuesService: failed to create issue %d/%d: %s",
                    idx + 1,
                    len(payload.issues),
                    exc,
                )
                results.append(
                    BatchCreateIssueItemResult(
                        index=idx,
                        success=False,
                        error=str(exc),
                    )
                )
                failed_count += 1

        logger.info(
            "BatchCreateIssuesService: completed — created=%d failed=%d",
            created_count,
            failed_count,
        )

        return BatchCreateIssuesResult(
            results=results,
            created_count=created_count,
            failed_count=failed_count,
        )


__all__ = [
    "BatchCreateIssueItemResult",
    "BatchCreateIssuesPayload",
    "BatchCreateIssuesResult",
    "BatchCreateIssuesService",
    "BatchIssueItemPayload",
]
