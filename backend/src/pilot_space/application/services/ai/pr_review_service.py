"""PR Review application service.

T196: Create PR Review service for triggering and managing reviews.

Provides:
- TriggerPRReviewService: Enqueue PR review job
- GetPRReviewStatusService: Check review progress/results
- Rate limiting: 1 concurrent review per PR
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import IntegrationProvider
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.handlers.pr_review_handler import (
    PR_REVIEW_QUEUE,
    PRReviewJobPayload,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.database.repositories import (
        IntegrationRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

# Cache keys for job tracking
JOB_STATUS_KEY_PREFIX = "pr_review:job:"
PR_ACTIVE_REVIEW_KEY_PREFIX = "pr_review:active:"
JOB_STATUS_TTL = 86400  # 24 hours
ACTIVE_REVIEW_TTL = 1800  # 30 minutes


class ReviewStatus(StrEnum):
    """Status of a PR review request."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class TriggerPRReviewPayload:
    """Payload for triggering a PR review.

    Attributes:
        workspace_id: Workspace requesting the review.
        integration_id: GitHub integration ID.
        repository: Repository in owner/repo format.
        pr_number: Pull request number.
        user_id: User triggering the review.
        correlation_id: Request correlation ID.
        post_comments: Whether to post inline comments.
        post_summary: Whether to post summary comment.
        project_context: Additional project context.
    """

    workspace_id: UUID
    integration_id: UUID
    repository: str
    pr_number: int
    user_id: UUID
    correlation_id: str = ""
    post_comments: bool = True
    post_summary: bool = True
    project_context: dict[str, str] = field(default_factory=dict)


@dataclass
class TriggerPRReviewResult:
    """Result from triggering a PR review.

    Attributes:
        job_id: Unique job identifier.
        status: Current status.
        queued_at: When the job was queued.
        estimated_wait_minutes: Estimated wait time.
        message: Status message.
    """

    job_id: str
    status: ReviewStatus
    queued_at: datetime
    estimated_wait_minutes: int = 2
    message: str = ""


@dataclass
class PRReviewJobInfo:
    """Information about a PR review job.

    Attributes:
        job_id: Job identifier.
        workspace_id: Workspace ID.
        repository: Repository name.
        pr_number: PR number.
        status: Current status.
        queued_at: When queued.
        started_at: When processing started.
        completed_at: When completed.
        result: Review result data (if completed).
        error: Error message (if failed).
    """

    job_id: str
    workspace_id: str
    repository: str
    pr_number: int
    status: ReviewStatus
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class PRReviewStatusResult:
    """Result from checking PR review status.

    Attributes:
        found: Whether the job was found.
        job_info: Job information (if found).
    """

    found: bool
    job_info: PRReviewJobInfo | None = None


class TriggerPRReviewService:
    """Service for triggering PR reviews.

    Enqueues a PR review job with rate limiting:
    - Only one active review per PR at a time
    - Uses high-priority queue for PR reviews

    Example:
        service = TriggerPRReviewService(...)
        result = await service.execute(TriggerPRReviewPayload(
            workspace_id=workspace_id,
            integration_id=integration_id,
            repository="owner/repo",
            pr_number=123,
            user_id=user_id,
        ))
        print(f"Job ID: {result.job_id}")
    """

    def __init__(
        self,
        session: AsyncSession,
        queue_client: SupabaseQueueClient,
        integration_repo: IntegrationRepository,
        cache_client: RedisClient | None = None,
    ) -> None:
        """Initialize service.

        Args:
            session: Database session.
            queue_client: Supabase queue client.
            integration_repo: Integration repository.
            cache_client: Redis client for rate limiting (optional).
        """
        self._session = session
        self._queue = queue_client
        self._integration_repo = integration_repo
        self._cache = cache_client

    async def execute(self, payload: TriggerPRReviewPayload) -> TriggerPRReviewResult:
        """Trigger a PR review.

        Args:
            payload: Review trigger payload.

        Returns:
            TriggerPRReviewResult with job info.

        Raises:
            ValueError: If integration not found or invalid.
        """
        # Validate integration
        integration = await self._integration_repo.get_by_id(payload.integration_id)
        if not integration:
            raise NotFoundError(f"Integration {payload.integration_id} not found")

        if integration.provider != IntegrationProvider.GITHUB:
            raise ValidationError("Integration must be GitHub")

        if not integration.is_active:
            raise ValidationError("Integration is not active")

        if integration.workspace_id != payload.workspace_id:
            raise ForbiddenError("Integration does not belong to workspace")

        # Check rate limit (one active review per PR)
        if self._cache:
            active_key = f"{PR_ACTIVE_REVIEW_KEY_PREFIX}{payload.repository}:{payload.pr_number}"
            existing = await self._cache.get(active_key)
            if existing:
                return TriggerPRReviewResult(
                    job_id=existing,
                    status=ReviewStatus.RATE_LIMITED,
                    queued_at=datetime.now(tz=UTC),
                    message=f"Review already in progress: {existing}",
                )

        # Generate job ID
        job_id = str(uuid4())
        queued_at = datetime.now(tz=UTC)

        # Build job payload
        job_payload = PRReviewJobPayload(
            job_id=job_id,
            workspace_id=str(payload.workspace_id),
            integration_id=str(payload.integration_id),
            repository=payload.repository,
            pr_number=payload.pr_number,
            user_id=str(payload.user_id),
            correlation_id=payload.correlation_id,
            post_comments=payload.post_comments,
            post_summary=payload.post_summary,
            project_context=payload.project_context,
        )

        # Enqueue job
        await self._queue.enqueue(
            PR_REVIEW_QUEUE,
            {
                "task_type": "pr_review",
                **job_payload.to_dict(),
            },
            max_attempts=3,
        )

        # Store job status in cache
        if self._cache:
            job_info = PRReviewJobInfo(
                job_id=job_id,
                workspace_id=str(payload.workspace_id),
                repository=payload.repository,
                pr_number=payload.pr_number,
                status=ReviewStatus.QUEUED,
                queued_at=queued_at,
            )
            await self._cache.set(
                f"{JOB_STATUS_KEY_PREFIX}{job_id}",
                self._serialize_job_info(job_info),
                ttl=JOB_STATUS_TTL,
            )

            # Mark PR as having active review
            active_key = f"{PR_ACTIVE_REVIEW_KEY_PREFIX}{payload.repository}:{payload.pr_number}"
            await self._cache.set(active_key, job_id, ttl=ACTIVE_REVIEW_TTL)

        logger.info(
            "PR review job queued",
            extra={
                "job_id": job_id,
                "repository": payload.repository,
                "pr_number": payload.pr_number,
                "workspace_id": str(payload.workspace_id),
            },
        )

        return TriggerPRReviewResult(
            job_id=job_id,
            status=ReviewStatus.QUEUED,
            queued_at=queued_at,
            estimated_wait_minutes=2,
            message="PR review queued successfully",
        )

    def _serialize_job_info(self, info: PRReviewJobInfo) -> str:
        """Serialize job info for cache storage."""
        import json

        data = {
            "job_id": info.job_id,
            "workspace_id": info.workspace_id,
            "repository": info.repository,
            "pr_number": info.pr_number,
            "status": info.status.value,
            "queued_at": info.queued_at.isoformat(),
            "started_at": info.started_at.isoformat() if info.started_at else None,
            "completed_at": info.completed_at.isoformat() if info.completed_at else None,
            "result": info.result,
            "error": info.error,
        }
        return json.dumps(data)


class GetPRReviewStatusService:
    """Service for checking PR review job status.

    Retrieves job status from cache with result data.
    """

    def __init__(
        self,
        cache_client: RedisClient | None = None,
    ) -> None:
        """Initialize service.

        Args:
            cache_client: Redis client for status lookup.
        """
        self._cache = cache_client

    async def execute(self, job_id: str) -> PRReviewStatusResult:
        """Get status of a PR review job.

        Args:
            job_id: Job identifier.

        Returns:
            PRReviewStatusResult with job info.
        """
        if not self._cache:
            return PRReviewStatusResult(found=False)

        cached = await self._cache.get(f"{JOB_STATUS_KEY_PREFIX}{job_id}")
        if not cached:
            return PRReviewStatusResult(found=False)

        job_info = self._deserialize_job_info(cached)
        return PRReviewStatusResult(found=True, job_info=job_info)

    def _deserialize_job_info(self, data: str) -> PRReviewJobInfo:
        """Deserialize job info from cache."""
        import json

        parsed = json.loads(data)

        return PRReviewJobInfo(
            job_id=parsed["job_id"],
            workspace_id=parsed["workspace_id"],
            repository=parsed["repository"],
            pr_number=parsed["pr_number"],
            status=ReviewStatus(parsed["status"]),
            queued_at=datetime.fromisoformat(parsed["queued_at"]),
            started_at=(
                datetime.fromisoformat(parsed["started_at"]) if parsed.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(parsed["completed_at"])
                if parsed.get("completed_at")
                else None
            ),
            result=parsed.get("result"),
            error=parsed.get("error"),
        )


async def update_job_status(
    cache_client: RedisClient,
    job_id: str,
    status: ReviewStatus,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Update job status in cache.

    Args:
        cache_client: Redis client.
        job_id: Job identifier.
        status: New status.
        started_at: When processing started.
        completed_at: When completed.
        result: Review result data.
        error: Error message.
    """
    import json

    key = f"{JOB_STATUS_KEY_PREFIX}{job_id}"
    cached = await cache_client.get(key)

    if not cached:
        logger.warning(f"Job {job_id} not found in cache for status update")
        return

    data = json.loads(cached)
    data["status"] = status.value

    if started_at:
        data["started_at"] = started_at.isoformat()
    if completed_at:
        data["completed_at"] = completed_at.isoformat()
    if result:
        data["result"] = result
    if error:
        data["error"] = error

    await cache_client.set(key, json.dumps(data), ttl=JOB_STATUS_TTL)

    # Clear active review marker on completion
    if status in (ReviewStatus.COMPLETED, ReviewStatus.FAILED):
        repository = data.get("repository", "")
        pr_number = data.get("pr_number", 0)
        if repository and pr_number:
            active_key = f"{PR_ACTIVE_REVIEW_KEY_PREFIX}{repository}:{pr_number}"
            await cache_client.delete(active_key)


__all__ = [
    "ACTIVE_REVIEW_TTL",
    "JOB_STATUS_KEY_PREFIX",
    "JOB_STATUS_TTL",
    "PR_ACTIVE_REVIEW_KEY_PREFIX",
    "GetPRReviewStatusService",
    "PRReviewJobInfo",
    "PRReviewStatusResult",
    "ReviewStatus",
    "TriggerPRReviewPayload",
    "TriggerPRReviewResult",
    "TriggerPRReviewService",
    "update_job_status",
]
