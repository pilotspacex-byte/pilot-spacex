"""PR Review API schemas.

T197: Create Pydantic schemas for PR review API.

Provides request/response schemas for:
- TriggerReviewRequest
- ReviewStatusResponse
- ReviewCommentResponse
- ReviewSummaryResponse
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReviewSeverity(StrEnum):
    """Severity levels for review findings."""

    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class ReviewCategory(StrEnum):
    """Review aspect categories."""

    ARCHITECTURE = "architecture"
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


@dataclass
class ReviewComment:
    """Single review comment from findings."""

    file_path: str
    line_number: int
    end_line: int | None
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    suggestion: str | None = None
    code_snippet: str | None = None


class TriggerReviewRequest(BaseModel):
    """Request to trigger a PR review.

    Attributes:
        repository: Repository in owner/repo format.
        pr_number: Pull request number.
        post_comments: Whether to post inline comments.
        post_summary: Whether to post summary comment.
        project_context: Additional project context.
    """

    repository: str = Field(
        ...,
        pattern=r"^[^/]+/[^/]+$",
        description="Repository in owner/repo format",
        examples=["owner/repo"],
    )
    pr_number: int = Field(
        ...,
        ge=1,
        description="Pull request number",
    )
    post_comments: bool = Field(
        default=True,
        description="Whether to post inline comments to GitHub",
    )
    post_summary: bool = Field(
        default=True,
        description="Whether to post summary comment to GitHub",
    )
    project_context: dict[str, str] = Field(
        default_factory=dict,
        description="Additional project context (tech stack, patterns)",
    )


class TriggerReviewResponse(BaseModel):
    """Response from triggering a PR review.

    Attributes:
        job_id: Unique job identifier.
        status: Current status (queued, rate_limited).
        queued_at: When the job was queued.
        estimated_wait_minutes: Estimated wait time.
        message: Status message.
    """

    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Current status")
    queued_at: datetime = Field(description="When queued")
    estimated_wait_minutes: int = Field(
        default=2,
        description="Estimated wait time in minutes",
    )
    message: str = Field(default="", description="Status message")


class ReviewCommentResponse(BaseModel):
    """Single review comment.

    Attributes:
        file_path: Path to the file.
        line_number: Line number for the comment.
        end_line: End line for multi-line comments.
        severity: Severity level.
        category: Review category.
        message: Comment message.
        suggestion: Code suggestion (optional).
        code_snippet: Related code snippet (optional).
    """

    file_path: str = Field(description="File path")
    line_number: int = Field(description="Line number")
    end_line: int | None = Field(default=None, description="End line")
    severity: str = Field(description="Severity level")
    category: str = Field(description="Review category")
    message: str = Field(description="Comment message")
    suggestion: str | None = Field(default=None, description="Code suggestion")
    code_snippet: str | None = Field(default=None, description="Code snippet")

    model_config = ConfigDict(from_attributes=True)


class ReviewSummaryResponse(BaseModel):
    """Summary of PR review findings.

    Attributes:
        summary: High-level summary.
        approval_recommendation: Recommendation (approve/request_changes/comment).
        critical_count: Number of critical issues.
        warning_count: Number of warnings.
        suggestion_count: Number of suggestions.
        info_count: Number of info comments.
        partial_review: Whether this was a partial review.
        files_reviewed: Number of files reviewed.
        files_skipped: Number of files skipped.
        categories_summary: Count per category.
    """

    summary: str = Field(description="High-level summary")
    approval_recommendation: str = Field(
        description="Approval recommendation",
        examples=["approve", "request_changes", "comment"],
    )
    critical_count: int = Field(default=0, description="Critical issues count")
    warning_count: int = Field(default=0, description="Warnings count")
    suggestion_count: int = Field(default=0, description="Suggestions count")
    info_count: int = Field(default=0, description="Info comments count")
    partial_review: bool = Field(
        default=False,
        description="Whether this was a partial review",
    )
    files_reviewed: int = Field(default=0, description="Files reviewed")
    files_skipped: int = Field(default=0, description="Files skipped")
    categories_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count per category",
    )


class ReviewStatusResponse(BaseModel):
    """Response for PR review job status.

    Attributes:
        job_id: Job identifier.
        status: Current status.
        repository: Repository name.
        pr_number: PR number.
        queued_at: When queued.
        started_at: When processing started.
        completed_at: When completed.
        progress_percent: Estimated progress (0-100).
        summary: Review summary (if completed).
        comments: Review comments (if completed).
        error: Error message (if failed).
    """

    job_id: str = Field(description="Job identifier")
    status: str = Field(
        description="Current status",
        examples=["queued", "processing", "completed", "failed"],
    )
    repository: str = Field(description="Repository name")
    pr_number: int = Field(description="PR number")
    queued_at: datetime = Field(description="When queued")
    started_at: datetime | None = Field(default=None, description="When started")
    completed_at: datetime | None = Field(default=None, description="When completed")
    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Estimated progress",
    )
    summary: ReviewSummaryResponse | None = Field(
        default=None,
        description="Review summary",
    )
    comments: list[ReviewCommentResponse] | None = Field(
        default=None,
        description="Review comments",
    )
    error: str | None = Field(default=None, description="Error message")


class ReviewHistoryItem(BaseModel):
    """Single item in review history.

    Attributes:
        job_id: Job identifier.
        pr_number: PR number.
        status: Job status.
        queued_at: When queued.
        completed_at: When completed.
        approval_recommendation: Recommendation.
        critical_count: Critical issues found.
        warning_count: Warnings found.
    """

    job_id: str
    pr_number: int
    status: str
    queued_at: datetime
    completed_at: datetime | None = None
    approval_recommendation: str | None = None
    critical_count: int = 0
    warning_count: int = 0


class ReviewHistoryResponse(BaseModel):
    """Response for PR review history.

    Attributes:
        items: List of historical reviews.
        total: Total count.
    """

    items: list[ReviewHistoryItem]
    total: int


class StreamPRReviewRequest(BaseModel):
    """Request body for streaming PR review.

    Attributes:
        include_architecture: Include architecture review aspect.
        include_security: Include security scanning aspect.
        include_performance: Include performance analysis aspect.
        post_comments: Post review comments back to GitHub PR.
        force_refresh: If true, bypass cache and re-review.
    """

    include_architecture: bool = Field(
        default=True,
        description="Include architecture review",
    )
    include_security: bool = Field(
        default=True,
        description="Include security scanning",
    )
    include_performance: bool = Field(
        default=True,
        description="Include performance analysis",
    )
    post_comments: bool = Field(
        default=False,
        description="Post review comments to GitHub PR (MVP: disabled by default)",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh, bypass cache",
    )


__all__ = [
    "ReviewCommentResponse",
    "ReviewHistoryItem",
    "ReviewHistoryResponse",
    "ReviewStatusResponse",
    "ReviewSummaryResponse",
    "StreamPRReviewRequest",
    "TriggerReviewRequest",
    "TriggerReviewResponse",
]
