"""PR Review Agent using Claude Opus with comprehensive analysis.

T193: Create PRReviewAgent for comprehensive AI-powered code review.

Implements unified PR review covering 5 dimensions:
- Architecture (T200c): SOLID, layer separation, modularity
- Security (T200a): OWASP Top 10, auth, input validation, secrets
- Quality: Readability, naming, error handling
- Performance (T200b): N+1 queries, blocking I/O, complexity
- Documentation (T200d): Docstrings, comments

Handles large PRs (T200e):
- >5000 lines or >50 files triggers prioritized partial review
- Priority files: auth/*, security/*, api/*, models/*
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.prompts.pr_review import (
    build_pr_review_prompt,
    parse_pr_review_response,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

logger = logging.getLogger(__name__)

# Thresholds for large PR handling
MAX_LINES_FULL_REVIEW = 5000
MAX_FILES_FULL_REVIEW = 50

# Priority file patterns for partial reviews
PRIORITY_FILE_PATTERNS = [
    "auth/",
    "security/",
    "api/",
    "models/",
    "routes/",
    "routers/",
    "middleware/",
    "services/",
    "domain/",
]


class ReviewSeverity(StrEnum):
    """Severity levels for review comments.

    Attributes:
        CRITICAL: Must fix before merge - security issues, data loss risks.
        WARNING: Should fix - code quality, potential bugs.
        SUGGESTION: Nice to have - style improvements, minor optimizations.
        INFO: FYI - educational notes, pattern explanations.
    """

    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class ReviewCategory(StrEnum):
    """Categories for review comments.

    Maps to the 5 review dimensions per DD-006.

    Attributes:
        ARCHITECTURE: SOLID principles, layer separation, modularity.
        SECURITY: OWASP Top 10, authentication, authorization, secrets.
        QUALITY: Readability, naming conventions, error handling.
        PERFORMANCE: N+1 queries, blocking I/O, algorithm complexity.
        DOCUMENTATION: Docstrings, inline comments, API documentation.
    """

    ARCHITECTURE = "architecture"
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


@dataclass
class ReviewComment:
    """Single review comment with location and context.

    Attributes:
        file_path: Path to the file relative to repository root.
        line_number: Line number for inline comment (0 for file-level).
        end_line: End line for multi-line comments (optional).
        severity: How critical the issue is.
        category: Which review dimension this falls under.
        message: The review comment message.
        suggestion: Code suggestion to fix the issue (optional).
        code_snippet: Relevant code snippet for context (optional).
    """

    file_path: str
    line_number: int
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    end_line: int | None = None
    suggestion: str | None = None
    code_snippet: str | None = None


@dataclass
class PRReviewInput:
    """Input for PR review analysis.

    Attributes:
        pr_number: Pull request number.
        pr_title: Title of the PR.
        pr_description: PR description/body text.
        diff: Unified diff of changes.
        file_contents: Map of file path to file content.
        changed_files: List of changed file paths.
        project_context: Additional project context (tech stack, patterns).
        base_branch: Target branch for the PR.
        head_branch: Source branch of the PR.
    """

    pr_number: int
    pr_title: str
    pr_description: str
    diff: str
    file_contents: dict[str, str] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    project_context: dict[str, str] = field(default_factory=dict)
    base_branch: str = "main"
    head_branch: str = ""


@dataclass
class PRReviewOutput:
    """Output from PR review analysis.

    Attributes:
        summary: High-level summary of the PR and findings.
        comments: List of review comments.
        approval_recommendation: Recommendation for PR (approve/request_changes/comment).
        critical_count: Number of critical issues found.
        warning_count: Number of warning issues found.
        suggestion_count: Number of suggestions made.
        info_count: Number of info comments.
        partial_review: Whether this was a partial review of large PR.
        files_reviewed: Number of files actually reviewed.
        files_skipped: Number of files skipped (for partial reviews).
        categories_summary: Summary count per category.
    """

    summary: str
    comments: list[ReviewComment]
    approval_recommendation: str  # approve, request_changes, comment
    critical_count: int = 0
    warning_count: int = 0
    suggestion_count: int = 0
    info_count: int = 0
    partial_review: bool = False
    files_reviewed: int = 0
    files_skipped: int = 0
    categories_summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate summary counts from comments."""
        self.critical_count = sum(1 for c in self.comments if c.severity == ReviewSeverity.CRITICAL)
        self.warning_count = sum(1 for c in self.comments if c.severity == ReviewSeverity.WARNING)
        self.suggestion_count = sum(
            1 for c in self.comments if c.severity == ReviewSeverity.SUGGESTION
        )
        self.info_count = sum(1 for c in self.comments if c.severity == ReviewSeverity.INFO)

        # Calculate category counts
        for category in ReviewCategory:
            self.categories_summary[category.value] = sum(
                1 for c in self.comments if c.category == category
            )


def _is_priority_file(file_path: str) -> bool:
    """Check if file matches priority patterns for partial review.

    Args:
        file_path: Path to check.

    Returns:
        True if file is high priority.
    """
    file_lower = file_path.lower()
    return any(pattern in file_lower for pattern in PRIORITY_FILE_PATTERNS)


def _filter_priority_files(files: list[str]) -> tuple[list[str], list[str]]:
    """Partition files into priority and non-priority.

    Args:
        files: List of file paths.

    Returns:
        Tuple of (priority_files, other_files).
    """
    priority: list[str] = []
    other: list[str] = []

    for f in files:
        if _is_priority_file(f):
            priority.append(f)
        else:
            other.append(f)

    return priority, other


def _should_partial_review(input_data: PRReviewInput) -> bool:
    """Determine if PR is too large for full review.

    Args:
        input_data: PR review input.

    Returns:
        True if partial review should be used.
    """
    # Count lines in diff
    line_count = input_data.diff.count("\n")
    file_count = len(input_data.changed_files)

    return line_count > MAX_LINES_FULL_REVIEW or file_count > MAX_FILES_FULL_REVIEW


class PRReviewAgent(BaseAgent[PRReviewInput, PRReviewOutput]):
    """Agent for comprehensive PR code review using Claude Opus.

    Provides unified review covering:
    - Architecture: SOLID principles, layer separation, clean architecture
    - Security: OWASP Top 10, auth/authz, input validation
    - Quality: Code readability, naming, error handling
    - Performance: N+1 queries, blocking I/O, complexity
    - Documentation: Docstrings, comments, API docs

    Uses Claude Opus 4.5 for deep code analysis with 5-minute timeout.
    """

    task_type = TaskType.COMPLEX_REASONING  # Use Claude Opus for deep analysis
    operation = AIOperation.PR_REVIEW

    # Longer retry config for large PRs
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay_seconds=2.0,
        max_delay_seconds=30.0,
    )

    def __init__(self) -> None:
        """Initialize with Claude Opus model."""
        super().__init__(model="claude-opus-4-5-20251101")

    async def _execute_impl(
        self,
        input_data: PRReviewInput,
        context: AgentContext,
    ) -> AgentResult[PRReviewOutput]:
        """Execute PR review with Claude Opus.

        Handles large PRs by filtering to priority files.

        Args:
            input_data: PR content to review.
            context: Agent execution context.

        Returns:
            AgentResult with review output and metadata.
        """
        import anthropic
        from anthropic.types import TextBlock

        # Determine if partial review needed
        partial_review = _should_partial_review(input_data)
        files_to_review = input_data.changed_files
        files_skipped: list[str] = []

        if partial_review:
            priority_files, other_files = _filter_priority_files(input_data.changed_files)
            files_to_review = priority_files

            # Add some non-priority files up to reasonable limit
            remaining_capacity = MAX_FILES_FULL_REVIEW - len(priority_files)
            if remaining_capacity > 0:
                files_to_review.extend(other_files[:remaining_capacity])
                files_skipped = other_files[remaining_capacity:]
            else:
                files_skipped = other_files

            logger.info(
                "Large PR detected, performing partial review",
                extra={
                    "pr_number": input_data.pr_number,
                    "total_files": len(input_data.changed_files),
                    "reviewing_files": len(files_to_review),
                    "skipped_files": len(files_skipped),
                },
            )

        # Filter file contents to only reviewed files
        filtered_contents = {
            path: content
            for path, content in input_data.file_contents.items()
            if path in files_to_review
        }

        # Build prompt
        prompt = build_pr_review_prompt(
            pr_number=input_data.pr_number,
            pr_title=input_data.pr_title,
            pr_description=input_data.pr_description,
            diff=input_data.diff,
            file_contents=filtered_contents,
            project_context=input_data.project_context,
            partial_review=partial_review,
            files_reviewed=files_to_review,
        )

        # Get API key
        api_key = context.require_api_key(Provider.CLAUDE)

        # Call Claude Opus API with extended timeout
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=self.model,
            max_tokens=8192,  # Large output for detailed review
            messages=[{"role": "user", "content": prompt}],
            timeout=300.0,  # 5-minute timeout for complex reviews
        )

        # Parse response
        response_text = ""
        if message.content:
            first_block = message.content[0]
            if isinstance(first_block, TextBlock):
                response_text = first_block.text

        output = parse_pr_review_response(
            response_text,
            partial_review=partial_review,
            files_reviewed=len(files_to_review),
            files_skipped=len(files_skipped),
        )

        return AgentResult(
            output=output,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
            provider=self.provider,
            metadata={
                "partial_review": partial_review,
                "files_reviewed": len(files_to_review),
                "files_skipped": len(files_skipped),
            },
        )

    def validate_input(self, input_data: PRReviewInput) -> None:
        """Validate PR review input.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if input_data.pr_number <= 0:
            raise ValueError("PR number must be positive")

        if not input_data.pr_title:
            raise ValueError("PR title is required")

        if not input_data.diff:
            raise ValueError("PR diff is required for review")


__all__ = [
    "MAX_FILES_FULL_REVIEW",
    "MAX_LINES_FULL_REVIEW",
    "PRIORITY_FILE_PATTERNS",
    "PRReviewAgent",
    "PRReviewInput",
    "PRReviewOutput",
    "ReviewCategory",
    "ReviewComment",
    "ReviewSeverity",
]
