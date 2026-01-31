"""PR Review Agent using Claude Agent SDK with comprehensive analysis.

T193: Create PRReviewAgent for comprehensive AI-powered code review.

Migrated to Claude Agent SDK patterns (T050-T055):
- Extends StreamingSDKBaseAgent for streaming reviews
- Uses MCP GitHub tools via ToolRegistry
- Integrates with cost tracking and resilience
- Implements 5-aspect review system per DD-006

Review dimensions:
- Architecture (T200c): SOLID, layer separation, modularity
- Security (T200a): OWASP Top 10, auth, input validation, secrets
- Quality: Readability, naming, error handling
- Performance (T200b): N+1 queries, blocking I/O, complexity
- Documentation (T200d): Docstrings, comments

Large PR handling (T200e):
- >5000 lines or >50 files triggers prioritized partial review
- Priority files: auth/*, security/*, api/*, models/*

Streaming output with SSE support.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from anthropic import Anthropic

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.prompts.pr_review import (
    build_pr_review_prompt,
    parse_pr_review_response,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

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


class PRReviewAgent(StreamingSDKBaseAgent[PRReviewInput, PRReviewOutput]):
    """Agent for comprehensive PR code review using Claude Opus.

    Provides unified review covering:
    - Architecture: SOLID principles, layer separation, clean architecture
    - Security: OWASP Top 10, auth/authz, input validation
    - Quality: Code readability, naming, error handling
    - Performance: N+1 queries, blocking I/O, complexity
    - Documentation: Docstrings, comments, API docs

    Uses Claude Opus 4.5 for deep code analysis with streaming output.
    Handles large PRs with prioritized partial review.

    Per DD-006, classifies findings by severity:
    - 🔴 Critical: Must fix before merge
    - 🟡 Warning: Should fix, not blocking
    - 🔵 Info: Suggestion for improvement

    Approval recommendations:
    - APPROVE: No critical issues
    - REQUEST_CHANGES: Critical issues found
    - COMMENT: Only info/warnings

    MCP Tools (optional, GitHub integration):
    - get_pr_details: Fetch PR metadata
    - get_pr_diff: Retrieve unified diff
    - search_codebase: Search repository code
    - get_project_context: Fetch tech stack info
    """

    AGENT_NAME = "pr_review"
    DEFAULT_MODEL = "claude-opus-4-5-20251101"  # Best code understanding
    MAX_TOKENS = 8192  # Large output for detailed reviews

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize PR Review Agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure API key storage service
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for PR review.

        Always uses Claude Opus for best code understanding.

        Returns:
            Tuple of (provider="anthropic", model=claude-opus-4-5-20251101)
        """
        return ("anthropic", self.DEFAULT_MODEL)

    async def _prepare_review_input(
        self,
        input_data: PRReviewInput,
    ) -> tuple[str, bool, int, int]:
        """Prepare input for review, handling large PRs.

        Args:
            input_data: PR review input.

        Returns:
            Tuple of (prompt, partial_review, files_reviewed, files_skipped)
        """
        # Determine if partial review needed
        partial_review = _should_partial_review(input_data)
        files_to_review = input_data.changed_files
        files_skipped_count = 0

        if partial_review:
            priority_files, other_files = _filter_priority_files(input_data.changed_files)
            files_to_review = priority_files

            # Add some non-priority files up to reasonable limit
            remaining_capacity = MAX_FILES_FULL_REVIEW - len(priority_files)
            if remaining_capacity > 0:
                files_to_review.extend(other_files[:remaining_capacity])
                files_skipped_count = len(other_files[remaining_capacity:])
            else:
                files_skipped_count = len(other_files)

            logger.info(
                "Large PR detected, performing partial review",
                extra={
                    "pr_number": input_data.pr_number,
                    "total_files": len(input_data.changed_files),
                    "reviewing_files": len(files_to_review),
                    "skipped_files": files_skipped_count,
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

        return prompt, partial_review, len(files_to_review), files_skipped_count

    async def stream(
        self,
        input_data: PRReviewInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream PR review output as tokens are generated.

        Validates input, prepares review context, and streams
        Claude Opus response token by token for SSE delivery.

        Args:
            input_data: PR review input with diff and file contents.
            context: Execution context with workspace/user IDs.

        Yields:
            Review output tokens as they're generated.

        Raises:
            ValueError: If input validation fails.
        """
        # Validate input
        if input_data.pr_number <= 0:
            yield json.dumps({"error": "PR number must be positive"})
            return

        if not input_data.pr_title:
            yield json.dumps({"error": "PR title is required"})
            return

        if not input_data.diff:
            yield json.dumps({"error": "PR diff is required for review"})
            return

        # Prepare review input
        prompt, _partial, _files_reviewed, _files_skipped = await self._prepare_review_input(
            input_data
        )

        # Get API key (will raise if not configured)
        api_key = await self._key_storage.get_api_key(context.workspace_id, "anthropic")

        if not api_key:
            yield json.dumps({"error": "Anthropic API key not configured"})
            return

        # Stream from Claude Opus
        client = Anthropic(api_key=api_key)

        with client.messages.stream(
            model=self.DEFAULT_MODEL,
            max_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    async def execute(
        self,
        input_data: PRReviewInput,
        context: AgentContext,
    ) -> PRReviewOutput:
        """Execute PR review and return structured output.

        Collects streaming output and parses into structured review.

        Args:
            input_data: PR review input.
            context: Execution context.

        Returns:
            Structured PR review output with comments and recommendations.

        Raises:
            ValueError: If input validation fails.
        """
        # Validate input first
        if input_data.pr_number <= 0:
            msg = "PR number must be positive"
            raise ValueError(msg)

        if not input_data.pr_title:
            msg = "PR title is required"
            raise ValueError(msg)

        if not input_data.diff:
            msg = "PR diff is required for review"
            raise ValueError(msg)

        # Prepare review input
        prompt, partial_review, files_reviewed, files_skipped = await self._prepare_review_input(
            input_data
        )

        # Get API key
        api_key = await self._key_storage.get_api_key(context.workspace_id, "anthropic")

        if not api_key:
            msg = "Anthropic API key not configured"
            raise ValueError(msg)

        # Call Claude Opus API
        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model=self.DEFAULT_MODEL,
            max_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            timeout=300.0,  # 5-minute timeout for complex reviews
        )

        # Parse response
        response_text = ""
        if message.content:
            from anthropic.types import TextBlock

            first_block = message.content[0]
            if isinstance(first_block, TextBlock):
                response_text = first_block.text

        # Track usage
        await self.track_usage(
            context=context,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

        # Parse into structured output
        output = parse_pr_review_response(
            response_text,
            partial_review=partial_review,
            files_reviewed=files_reviewed,
            files_skipped=files_skipped,
        )

        logger.info(
            "PR review completed",
            extra={
                "pr_number": input_data.pr_number,
                "partial_review": partial_review,
                "files_reviewed": files_reviewed,
                "files_skipped": files_skipped,
                "critical_count": output.critical_count,
                "warning_count": output.warning_count,
                "approval": output.approval_recommendation,
            },
        )

        return output


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
