"""PR Review prompt templates.

T194: Create prompt templates for PRReviewAgent with comprehensive review criteria.

Covers 5 review dimensions:
- Architecture: SOLID, layer separation, modularity
- Security: OWASP Top 10, auth, input validation, secrets
- Quality: Readability, naming, error handling
- Performance: N+1, blocking I/O, complexity
- Documentation: Docstrings, comments
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot_space.ai.agents.pr_review_agent import PRReviewOutput

logger = logging.getLogger(__name__)

PR_REVIEW_SYSTEM_PROMPT = """You are an expert senior software engineer conducting a comprehensive code review.
Your task is to review a pull request across 5 key dimensions, providing actionable feedback.

## Review Dimensions

### 1. Architecture (SOLID Principles)
- Single Responsibility: Each module/class/function has one reason to change
- Open/Closed: Code is open for extension, closed for modification
- Liskov Substitution: Subtypes must be substitutable for base types
- Interface Segregation: No client should depend on methods it doesn't use
- Dependency Inversion: Depend on abstractions, not concretions
- Layer separation (presentation, application, domain, infrastructure)
- Modularity and cohesion

### 2. Security (OWASP Top 10)
- Injection flaws (SQL, NoSQL, OS commands, LDAP)
- Broken authentication and session management
- Sensitive data exposure (secrets, PII, credentials in code)
- XML External Entities (XXE)
- Broken access control
- Security misconfiguration
- Cross-Site Scripting (XSS)
- Insecure deserialization
- Using components with known vulnerabilities
- Insufficient logging and monitoring
- Input validation and sanitization

### 3. Code Quality
- Readability and clarity
- Naming conventions (descriptive, consistent)
- Error handling (proper exceptions, no silent failures)
- Code duplication (DRY principle)
- Function/method length and complexity
- Type hints and type safety
- Magic numbers and hardcoded values

### 4. Performance
- N+1 database queries
- Blocking I/O in async functions
- Algorithm complexity (O(n^2) where O(n) is possible)
- Memory leaks and resource management
- Unnecessary computations
- Caching opportunities
- Connection pooling

### 5. Documentation
- Public API docstrings
- Complex logic explanations
- Type annotations
- README updates for new features
- Inline comments for non-obvious code
- API endpoint documentation

## Severity Levels

- **critical**: MUST fix before merge. Security vulnerabilities, data loss risks, breaking changes.
- **warning**: SHOULD fix. Code quality issues, potential bugs, technical debt.
- **suggestion**: NICE to have. Style improvements, minor optimizations, best practices.
- **info**: FYI only. Educational notes, pattern explanations, alternative approaches.

## Output Format

Output valid JSON with this structure:
```json
{
  "summary": "High-level summary of the PR and key findings",
  "approval_recommendation": "approve|request_changes|comment",
  "comments": [
    {
      "file_path": "path/to/file.py",
      "line_number": 42,
      "end_line": 45,
      "severity": "critical|warning|suggestion|info",
      "category": "architecture|security|quality|performance|documentation",
      "message": "Clear description of the issue",
      "suggestion": "Optional code fix or improvement",
      "code_snippet": "Optional relevant code snippet"
    }
  ]
}
```

## Guidelines

1. Be constructive and educational - explain WHY something is an issue
2. Provide specific, actionable suggestions when possible
3. Acknowledge good patterns and practices you see
4. Consider the context - don't flag test code for missing docs
5. Prioritize critical security and correctness issues
6. Don't nitpick trivial style issues unless there's a clear standard
7. Consider backwards compatibility for API changes
8. Check for proper error handling and edge cases"""

PARTIAL_REVIEW_NOTE = """
## Partial Review Notice

This is a large PR. Only the following priority files are being reviewed:
{files_list}

The following files were skipped due to size constraints:
{skipped_count} files not reviewed

Focus your review on the security-critical and core logic files provided.
"""


def build_pr_review_prompt(
    *,
    pr_number: int,
    pr_title: str,
    pr_description: str,
    diff: str,
    file_contents: dict[str, str],
    project_context: dict[str, str] | None = None,
    partial_review: bool = False,
    files_reviewed: list[str] | None = None,
) -> str:
    """Build the PR review prompt.

    Args:
        pr_number: PR number.
        pr_title: Title of the PR.
        pr_description: PR description/body.
        diff: Unified diff of changes.
        file_contents: Map of file path to content.
        project_context: Additional context (tech stack, etc).
        partial_review: Whether this is a partial review.
        files_reviewed: List of files being reviewed.

    Returns:
        Formatted prompt string.
    """
    parts = [PR_REVIEW_SYSTEM_PROMPT, "\n---\n"]

    # Add partial review notice if applicable
    if partial_review and files_reviewed:
        files_list = "\n".join(f"- {f}" for f in files_reviewed[:20])
        if len(files_reviewed) > 20:
            files_list += f"\n- ... and {len(files_reviewed) - 20} more priority files"

        skipped_count = len(file_contents) - len(files_reviewed)
        parts.append(
            PARTIAL_REVIEW_NOTE.format(
                files_list=files_list,
                skipped_count=skipped_count,
            )
        )
        parts.append("\n---\n")

    # Add project context
    if project_context:
        parts.append("## Project Context\n")
        for key, value in project_context.items():
            parts.append(f"**{key}**: {value}\n")
        parts.append("\n")

    # Add PR metadata
    parts.append(f"## Pull Request #{pr_number}\n")
    parts.append(f"**Title**: {pr_title}\n")
    if pr_description:
        parts.append(f"**Description**:\n{pr_description}\n")
    parts.append("\n")

    # Add diff (truncate if too long)
    max_diff_chars = 50000
    if len(diff) > max_diff_chars:
        parts.append("## Changes (Diff - Truncated)\n")
        parts.append("```diff\n")
        parts.append(diff[:max_diff_chars])
        parts.append("\n... (diff truncated)\n```\n\n")
    else:
        parts.append("## Changes (Diff)\n")
        parts.append("```diff\n")
        parts.append(diff)
        parts.append("\n```\n\n")

    # Add file contents for context
    if file_contents:
        parts.append("## File Contents\n")
        total_chars = 0
        max_total_chars = 100000

        for file_path, content in file_contents.items():
            if total_chars > max_total_chars:
                parts.append("\n*Additional files truncated for length*\n")
                break

            # Determine file extension for syntax highlighting
            ext = file_path.split(".")[-1] if "." in file_path else ""
            lang_map = {
                "py": "python",
                "ts": "typescript",
                "tsx": "typescript",
                "js": "javascript",
                "jsx": "javascript",
                "go": "go",
                "rs": "rust",
                "java": "java",
                "kt": "kotlin",
                "sql": "sql",
            }
            lang = lang_map.get(ext, ext)

            # Truncate individual files if needed
            max_file_chars = 10000
            display_content = content
            if len(content) > max_file_chars:
                display_content = content[:max_file_chars] + "\n... (file truncated)"

            parts.append(f"### {file_path}\n")
            parts.append(f"```{lang}\n")
            parts.append(display_content)
            parts.append("\n```\n\n")

            total_chars += len(display_content)

    parts.append("\nPlease review this PR and provide your analysis as JSON.")

    return "".join(parts)


def parse_pr_review_response(
    response_text: str,
    partial_review: bool = False,
    files_reviewed: int = 0,
    files_skipped: int = 0,
) -> PRReviewOutput:
    """Parse the AI response into structured output.

    Args:
        response_text: Raw AI response.
        partial_review: Whether this was a partial review.
        files_reviewed: Number of files reviewed.
        files_skipped: Number of files skipped.

    Returns:
        Parsed PRReviewOutput.
    """
    from pilot_space.ai.agents.pr_review_agent import (
        PRReviewOutput,
        ReviewCategory,
        ReviewComment,
        ReviewSeverity,
    )

    # Try to extract JSON from response
    try:
        # Look for JSON block - handle markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response_text)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # Try to find raw JSON object
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("No JSON found in PR review response")
                data = {}
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse PR review JSON: %s", e)
        data = {}

    # Extract and validate fields
    summary = data.get("summary", "Review could not be completed")
    approval = data.get("approval_recommendation", "comment")
    if approval not in ("approve", "request_changes", "comment"):
        approval = "comment"

    # Parse comments
    raw_comments = data.get("comments", [])
    comments: list[ReviewComment] = []

    for raw in raw_comments:
        if not isinstance(raw, dict):
            continue

        # Validate required fields
        file_path = raw.get("file_path", "")
        if not file_path:
            continue

        line_number = raw.get("line_number", 0)
        if not isinstance(line_number, int):
            try:
                line_number = int(line_number)
            except (ValueError, TypeError):
                line_number = 0

        # Parse severity
        severity_str = raw.get("severity", "suggestion").lower()
        try:
            severity = ReviewSeverity(severity_str)
        except ValueError:
            severity = ReviewSeverity.SUGGESTION

        # Parse category
        category_str = raw.get("category", "quality").lower()
        try:
            category = ReviewCategory(category_str)
        except ValueError:
            category = ReviewCategory.QUALITY

        message = raw.get("message", "")
        if not message:
            continue

        comments.append(
            ReviewComment(
                file_path=file_path,
                line_number=line_number,
                end_line=raw.get("end_line"),
                severity=severity,
                category=category,
                message=message,
                suggestion=raw.get("suggestion"),
                code_snippet=raw.get("code_snippet"),
            )
        )

    return PRReviewOutput(
        summary=summary,
        comments=comments,
        approval_recommendation=approval,
        partial_review=partial_review,
        files_reviewed=files_reviewed,
        files_skipped=files_skipped,
    )


def format_review_as_markdown(output: Any) -> str:
    """Format PR review output as markdown for GitHub comment.

    Args:
        output: PRReviewOutput instance.

    Returns:
        Formatted markdown string.
    """
    from pilot_space.ai.agents.pr_review_agent import (
        PRReviewOutput,
        ReviewSeverity,
    )

    if not isinstance(output, PRReviewOutput):
        return "Error: Invalid review output"

    parts: list[str] = []

    # Header with recommendation
    recommendation_emoji = {
        "approve": ":white_check_mark:",
        "request_changes": ":x:",
        "comment": ":speech_balloon:",
    }
    emoji = recommendation_emoji.get(output.approval_recommendation, ":speech_balloon:")
    parts.append(f"## {emoji} AI Code Review\n")

    # Partial review notice
    if output.partial_review:
        parts.append(
            f"> **Note**: This is a partial review. "
            f"Reviewed {output.files_reviewed} priority files, "
            f"skipped {output.files_skipped} files.\n\n"
        )

    # Summary
    parts.append(f"### Summary\n{output.summary}\n\n")

    # Statistics
    parts.append("### Findings Overview\n")
    parts.append("| Severity | Count |\n")
    parts.append("|----------|-------|\n")
    parts.append(f"| :red_circle: Critical | {output.critical_count} |\n")
    parts.append(f"| :orange_circle: Warning | {output.warning_count} |\n")
    parts.append(f"| :large_blue_circle: Suggestion | {output.suggestion_count} |\n")
    parts.append(f"| :white_circle: Info | {output.info_count} |\n\n")

    # Group comments by severity
    severity_order = [
        ReviewSeverity.CRITICAL,
        ReviewSeverity.WARNING,
        ReviewSeverity.SUGGESTION,
        ReviewSeverity.INFO,
    ]

    severity_headers = {
        ReviewSeverity.CRITICAL: "### :red_circle: Critical Issues\n",
        ReviewSeverity.WARNING: "### :orange_circle: Warnings\n",
        ReviewSeverity.SUGGESTION: "### :large_blue_circle: Suggestions\n",
        ReviewSeverity.INFO: "### :white_circle: Information\n",
    }

    for severity in severity_order:
        severity_comments = [c for c in output.comments if c.severity == severity]
        if not severity_comments:
            continue

        parts.append(severity_headers[severity])

        for comment in severity_comments:
            # File and line reference
            line_ref = f"L{comment.line_number}"
            if comment.end_line:
                line_ref = f"L{comment.line_number}-L{comment.end_line}"

            parts.append(f"#### `{comment.file_path}` ({line_ref})\n")
            parts.append(f"**Category**: {comment.category.value}\n\n")
            parts.append(f"{comment.message}\n")

            if comment.suggestion:
                parts.append("\n**Suggested fix**:\n")
                parts.append(f"```\n{comment.suggestion}\n```\n")

            parts.append("\n---\n\n")

    return "".join(parts)


__all__ = [
    "build_pr_review_prompt",
    "format_review_as_markdown",
    "parse_pr_review_response",
]
