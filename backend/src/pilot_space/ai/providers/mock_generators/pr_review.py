"""Mock PR review generator.

Provides deterministic PR review comments based on
diff analysis and common patterns.
"""

from pilot_space.ai.agents.pr_review_agent import (
    PRReviewInput,
    PRReviewOutput,
    ReviewCategory,
    ReviewComment,
    ReviewSeverity,
)
from pilot_space.ai.providers.mock import MockResponseRegistry

# Pattern-based review rules
REVIEW_PATTERNS: list[dict[str, str | ReviewSeverity | ReviewCategory]] = [
    # Security patterns
    {
        "pattern": "password",
        "severity": ReviewSeverity.CRITICAL,
        "category": ReviewCategory.SECURITY,
        "message": "Ensure password is properly hashed before storage",
    },
    {
        "pattern": "api_key",
        "severity": ReviewSeverity.CRITICAL,
        "category": ReviewCategory.SECURITY,
        "message": "Verify API keys are not hardcoded or exposed in logs",
    },
    {
        "pattern": "SELECT * FROM",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.PERFORMANCE,
        "message": "Avoid SELECT * queries - specify columns explicitly",
    },
    # Quality patterns
    {
        "pattern": "# TODO",
        "severity": ReviewSeverity.WARNING,
        "category": ReviewCategory.QUALITY,
        "message": "TODO comment found - create issue to track or resolve now",
    },
    {
        "pattern": "print(",
        "severity": ReviewSeverity.SUGGESTION,
        "category": ReviewCategory.QUALITY,
        "message": "Use logging instead of print statements",
    },
    # Documentation patterns
    {
        "pattern": "def ",
        "severity": ReviewSeverity.SUGGESTION,
        "category": ReviewCategory.DOCUMENTATION,
        "message": "Consider adding docstring to document function purpose",
    },
    {
        "pattern": "class ",
        "severity": ReviewSeverity.SUGGESTION,
        "category": ReviewCategory.DOCUMENTATION,
        "message": "Consider adding class docstring to explain purpose",
    },
    # Performance patterns
    {
        "pattern": "for",
        "severity": ReviewSeverity.INFO,
        "category": ReviewCategory.PERFORMANCE,
        "message": "Review loop complexity - consider optimization if N is large",
    },
]


@MockResponseRegistry.register("PRReviewAgent")
def generate_pr_review(input_data: PRReviewInput) -> PRReviewOutput:
    """Generate mock PR review.

    Analyzes diff for common patterns:
    1. Security issues (passwords, API keys)
    2. Performance concerns (SELECT *, loops)
    3. Quality issues (TODOs, print statements)
    4. Documentation gaps (missing docstrings)

    Args:
        input_data: PR review input.

    Returns:
        PRReviewOutput with review comments.
    """
    comments: list[ReviewComment] = []
    diff = input_data.diff
    changed_files = input_data.changed_files

    # General summary comment
    summary = f"""## PR Review Summary

**PR #{input_data.pr_number}: {input_data.pr_title}**

This PR modifies {len(changed_files)} file(s). Mock review has identified several areas for consideration.

### Changes Overview
"""
    for file in changed_files[:5]:  # Show first 5 files
        summary += f"- `{file}`\n"
    if len(changed_files) > 5:
        summary += f"- ...and {len(changed_files) - 5} more files\n"

    # Analyze diff for patterns
    lines = diff.split("\n")
    for line_num, line in enumerate(lines, start=1):
        line_lower = line.lower()

        for pattern_rule in REVIEW_PATTERNS:
            pattern = str(pattern_rule.get("pattern", ""))
            if pattern.lower() in line_lower:
                severity = pattern_rule.get("severity")
                category = pattern_rule.get("category")
                message = pattern_rule.get("message")

                if not isinstance(severity, ReviewSeverity):
                    severity = ReviewSeverity.INFO
                if not isinstance(category, ReviewCategory):
                    category = ReviewCategory.QUALITY
                if not isinstance(message, str):
                    message = "Review this line"

                # Determine file from diff context
                file_path = "unknown"
                for i in range(line_num - 1, -1, -1):
                    if i >= len(lines):
                        break
                    if lines[i].startswith("+++"):
                        file_path = lines[i][6:].split("\t")[0]
                        break

                comments.append(
                    ReviewComment(
                        file_path=file_path,
                        line_number=line_num,
                        severity=severity,
                        category=category,
                        message=message,
                        code_snippet=line[:100] if len(line) > 100 else line,
                    )
                )

                # Limit comments per pattern
                break

    # Limit total comments
    comments = comments[:15]

    # Determine approval recommendation
    critical_count = sum(1 for c in comments if c.severity == ReviewSeverity.CRITICAL)
    warning_count = sum(1 for c in comments if c.severity == ReviewSeverity.WARNING)

    if critical_count > 0:
        approval_recommendation = "request_changes"
        summary += "\n**Recommendation: Request Changes** - Critical issues found.\n"
    elif warning_count > 3:
        approval_recommendation = "comment"
        summary += "\n**Recommendation: Comment** - Several warnings to address.\n"
    else:
        approval_recommendation = "approve"
        summary += "\n**Recommendation: Approve** - Looks good overall.\n"

    # Determine if partial review
    line_count = diff.count("\n")
    file_count = len(changed_files)
    partial_review = line_count > 5000 or file_count > 50

    return PRReviewOutput(
        summary=summary,
        comments=comments,
        approval_recommendation=approval_recommendation,
        partial_review=partial_review,
        files_reviewed=len(changed_files),
        files_skipped=0,
    )


__all__ = ["generate_pr_review"]
