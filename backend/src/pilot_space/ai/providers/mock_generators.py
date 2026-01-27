"""Core mock response generators for AI agents.

Each generator produces realistic mock responses matching agent output schemas.
Generators are auto-registered via @MockResponseRegistry.register decorator.

This module contains core generators (GhostText, AIContext, PRReview, etc.).
Supporting generators are in mock_generators_supporting.py.

Usage:
    # Import this module to auto-register all generators
    from pilot_space.ai.providers import mock_generators  # noqa: F401

    # MockProvider will automatically use registered generators
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pilot_space.ai.providers.mock import MockResponseRegistry

# =============================================================================
# Ghost Text Agent
# =============================================================================


@MockResponseRegistry.register("GhostTextAgent")
def generate_ghost_text(input_data: dict[str, Any]) -> str:
    """Generate mock ghost text completion.

    Args:
        input_data: Dict with current_text, cursor_position, is_code

    Returns:
        Completion suggestion string.
    """
    current_text = input_data.get("current_text", "")
    is_code = input_data.get("is_code", False)

    # Extract last few words for context
    words = current_text.split()
    last_word = words[-1] if words else ""

    if is_code:
        # Code completions based on patterns
        code_patterns = {
            "def ": "user_id: UUID) -> User:",
            "async def": "user_id: UUID) -> User:",
            "class ": "Service(BaseService):",
            "import ": "asyncio",
            "from ": "typing import Any",
        }
        for pattern, completion in code_patterns.items():
            if pattern in current_text:
                return completion
        return "result = await fetch_data()"

    # Prose completions based on keywords
    text_lower = current_text.lower()
    prose_patterns = {
        "implement": "ation should follow clean architecture principles",
        "test": "ing with high coverage ensures reliability",
        "user": " experience is a critical factor",
    }
    for keyword, completion in prose_patterns.items():
        if keyword in text_lower:
            return completion

    # Default contextual completion
    return f"to enhance {last_word} functionality"


# =============================================================================
# AI Context Agent
# =============================================================================


@MockResponseRegistry.register("AIContextAgent")
def generate_ai_context(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate mock AI context for issue.

    Args:
        input_data: Dict with issue_id, workspace_id

    Returns:
        AI context dict with related items, code references, and Claude prompt.
    """
    issue_id = input_data.get("issue_id", str(uuid4()))

    return {
        "related_items": [
            {
                "id": str(uuid4()),
                "type": "issue",
                "title": "Related authentication bug",
                "relevance_score": 0.85,
                "excerpt": "Similar issue with JWT token validation",
                "identifier": "PILOT-123",
                "state": "in_progress",
            },
            {
                "id": str(uuid4()),
                "type": "note",
                "title": "Architecture decisions for auth",
                "relevance_score": 0.72,
                "excerpt": "Document outlining authentication strategy",
            },
        ],
        "code_references": [
            {
                "file_path": "backend/src/pilot_space/infrastructure/auth/supabase_auth.py",
                "line_range": [45, 78],
                "description": "Token validation logic",
                "relevance": "high",
            },
            {
                "file_path": "backend/src/pilot_space/api/v1/routers/auth.py",
                "line_range": [120, 145],
                "description": "Login endpoint handler",
                "relevance": "medium",
            },
        ],
        "tasks": [
            {
                "description": "Review authentication flow in supabase_auth.py",
                "estimated_effort": "30 minutes",
                "dependencies": [],
            },
            {
                "description": "Add unit tests for token validation",
                "estimated_effort": "1 hour",
                "dependencies": ["Review authentication flow"],
            },
        ],
        "claude_code_prompt": f"""# Fix Authentication Issue (Issue ID: {issue_id})

## Context
This issue is related to JWT token validation in the authentication system.

## Related Code
- backend/src/pilot_space/infrastructure/auth/supabase_auth.py (lines 45-78)
- backend/src/pilot_space/api/v1/routers/auth.py (lines 120-145)

## Similar Issues
- PILOT-123: Related authentication bug (in progress)

## Tasks
1. Review authentication flow in supabase_auth.py (30 min)
2. Add unit tests for token validation (1 hour)

## Instructions
Please analyze the authentication code and fix the token validation issue.
Ensure all edge cases are handled and add comprehensive test coverage.
""",
        "generated_at": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# PR Review Agent
# =============================================================================


@MockResponseRegistry.register("PRReviewAgent")
def generate_pr_review(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate mock PR review output.

    Args:
        input_data: Dict with pr_number, pr_title, diff

    Returns:
        PR review output dict with comments and recommendations.
    """
    pr_number = input_data.get("pr_number", 1)
    pr_title = input_data.get("pr_title", "Feature implementation")

    return {
        "summary": f"Reviewed PR #{pr_number}: {pr_title}. Found 2 critical issues, "
        "3 warnings, and 5 suggestions for improvement.",
        "comments": [
            {
                "file_path": "backend/src/pilot_space/api/v1/routers/users.py",
                "line_number": 45,
                "severity": "critical",
                "category": "security",
                "message": "Missing input validation on user_id parameter. This could lead to SQL injection.",
                "suggestion": "Use Pydantic model for input validation and parameterized queries.",
            },
            {
                "file_path": "backend/src/pilot_space/domain/services/user_service.py",
                "line_number": 78,
                "severity": "warning",
                "category": "performance",
                "message": "N+1 query detected in user.get_projects() loop. Consider using eager loading.",
                "suggestion": "Use SQLAlchemy joinedload() to fetch projects in single query.",
            },
            {
                "file_path": "backend/src/pilot_space/domain/models/user.py",
                "line_number": 23,
                "severity": "suggestion",
                "category": "documentation",
                "message": "Missing docstring for User model. Add class documentation.",
                "suggestion": 'Add: """User domain model representing application users."""',
            },
        ],
        "approval_recommendation": "request_changes",
        "critical_count": 2,
        "warning_count": 3,
        "suggestion_count": 5,
        "info_count": 2,
        "partial_review": False,
        "files_reviewed": 8,
        "files_skipped": 0,
        "categories_summary": {
            "architecture": 1,
            "security": 2,
            "quality": 3,
            "performance": 3,
            "documentation": 3,
        },
    }


# =============================================================================
# Issue Extractor Agent
# =============================================================================


@MockResponseRegistry.register("IssueExtractorAgent")
@MockResponseRegistry.register("IssueExtractorSDKAgent")
def generate_extracted_issues(input_data: Any) -> Any:
    """Generate mock extracted issues from note.

    Args:
        input_data: IssueExtractorInput dataclass or dict with note_id, project_id

    Returns:
        IssueExtractorOutput instance with mock issues.
    """
    from pilot_space.ai.agents.issue_extractor_sdk_agent import (
        ExtractedIssue,
        IssueExtractorOutput,
    )
    from pilot_space.ai.prompts.issue_extraction import ConfidenceTag

    # Handle both dataclass and dict input
    if hasattr(input_data, "note_id"):
        note_id = input_data.note_id
    else:
        note_id = input_data.get("note_id", uuid4())

    issues = [
        ExtractedIssue(
            title="Implement user authentication",
            description="Add JWT-based authentication with refresh tokens",
            labels=["auth", "security"],
            priority=1,
            confidence_tag=ConfidenceTag.RECOMMENDED,
            confidence_score=0.92,
            source_block_ids=["block-1", "block-2"],
            rationale="Clear action item with specific technical requirements",
        ),
        ExtractedIssue(
            title="Add rate limiting to API",
            description="Protect endpoints from abuse with per-user rate limits",
            labels=["api", "security"],
            priority=2,
            confidence_tag=ConfidenceTag.DEFAULT,
            confidence_score=0.78,
            source_block_ids=["block-5"],
            rationale="Mentioned as important but less urgency than auth",
        ),
        ExtractedIssue(
            title="Write unit tests for user service",
            description="Achieve >80% coverage for user service layer",
            labels=["testing", "quality"],
            priority=3,
            confidence_tag=ConfidenceTag.CURRENT,
            confidence_score=0.65,
            source_block_ids=["block-8"],
            rationale="Standard practice but not explicitly prioritized",
        ),
    ]

    return IssueExtractorOutput(
        issues=issues,
        source_note_id=note_id,
        extraction_summary="Extracted 3 actionable issues from note content. "
        "1 recommended, 1 default, 1 current confidence level.",
    )


# =============================================================================
# Margin Annotation Agent
# =============================================================================


@MockResponseRegistry.register("MarginAnnotationAgent")
@MockResponseRegistry.register("MarginAnnotationAgentSDK")
def generate_margin_annotations(input_data: dict[str, Any]) -> Any:
    """Generate mock margin annotations covering all types.

    Args:
        input_data: Dict or dataclass with note_id, block_ids

    Returns:
        MarginAnnotationOutput dataclass with all 5 annotation types.
    """
    from pilot_space.ai.agents.margin_annotation_agent_sdk import (
        Annotation,
        AnnotationType,
        MarginAnnotationOutput,
    )

    # Handle both dict and dataclass input
    if hasattr(input_data, "block_ids"):
        block_ids = input_data.block_ids  # type: ignore[union-attr]
    else:
        block_ids = input_data.get(
            "block_ids", ["block-1", "block-2", "block-3", "block-4", "block-5"]
        )

    # Ensure at least 5 block_ids for testing all types
    while len(block_ids) < 5:
        block_ids.append(f"block-{len(block_ids) + 1}")

    # All 5 annotation types with varying confidence levels
    annotations: list[Annotation] = [
        Annotation(
            block_id=block_ids[0],
            type=AnnotationType.SUGGESTION,
            title="Consider adding error handling",
            content="This section could benefit from try-catch blocks for robust error handling. "
            "Wrap the async operation in a try-catch block to gracefully handle network failures.",
            confidence=0.92,  # Recommended (>0.8)
            action_label="Apply suggestion",
            action_payload={"type": "code_example", "template": "try-catch"},
        ),
        Annotation(
            block_id=block_ids[1],
            type=AnnotationType.WARNING,
            title="Potential security issue",
            content="User input is used directly without sanitization. "
            "Consider validating and sanitizing the input to prevent XSS attacks.",
            confidence=0.88,  # Recommended
            action_label="Show fix",
            action_payload={"type": "security_fix"},
        ),
        Annotation(
            block_id=block_ids[2],
            type=AnnotationType.QUESTION,
            title="Clarification needed",
            content="The acceptance criteria for this feature are ambiguous. "
            "Should the notification also be sent via email, or only in-app?",
            confidence=0.65,  # Default (0.5-0.8)
            action_label=None,
            action_payload=None,
        ),
        Annotation(
            block_id=block_ids[3],
            type=AnnotationType.INSIGHT,
            title="Performance optimization",
            content="This database query runs on every render. "
            "Consider memoizing the result or using React Query for automatic caching.",
            confidence=0.75,  # Default
            action_label="Learn more",
            action_payload={"type": "link", "url": "https://tanstack.com/query"},
        ),
        Annotation(
            block_id=block_ids[4],
            type=AnnotationType.REFERENCE,
            title="Related architecture decision",
            content="See ADR-003 for the authentication architecture decision "
            "that relates to this implementation approach.",
            confidence=0.45,  # Alternative (<0.5)
            action_label="Open ADR",
            action_payload={"type": "link", "doc_id": "adr-003"},
        ),
    ]

    return MarginAnnotationOutput(
        annotations=annotations,
        processed_blocks=len(block_ids),
    )


# =============================================================================
# Conversation Agent
# =============================================================================


@MockResponseRegistry.register("ConversationAgent")
@MockResponseRegistry.register("ConversationAgentSDK")
def generate_conversation_response(input_data: dict[str, Any]) -> str:
    """Generate mock conversational response.

    Args:
        input_data: Dict with message, context

    Returns:
        Response string.
    """
    message = input_data.get("message", "")

    if "how" in message.lower():
        return "To implement this feature, I recommend starting with the repository layer, then adding the service logic, and finally exposing it through the API. This follows the clean architecture pattern used in the codebase."

    if "what" in message.lower():
        return "This feature involves creating a new endpoint in the API router, implementing business logic in a service class, and adding database operations in a repository. You'll also need to add Pydantic schemas for request/response validation."

    if "test" in message.lower():
        return "For testing, you should write unit tests for the service layer with mocked repositories, integration tests for the API endpoints, and ensure coverage is above 80%. Use pytest with async support."

    return "I understand your question. Based on the project context, I recommend reviewing the existing patterns in the codebase and following the established architecture. Would you like me to elaborate on any specific aspect?"


# =============================================================================
# Issue Enhancer Agent
# =============================================================================


@MockResponseRegistry.register("IssueEnhancerAgent")
@MockResponseRegistry.register("IssueEnhancerAgentSDK")
def generate_issue_enhancement(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate mock issue enhancement suggestions.

    Args:
        input_data: Dict with issue_id, current_description

    Returns:
        Enhancement suggestions dict.
    """
    return {
        "title_suggestion": "Add rate limiting to authentication endpoints",
        "description_enhancement": """## Problem
Current authentication endpoints lack rate limiting, making them vulnerable to brute force attacks.

## Proposed Solution
Implement per-IP and per-user rate limiting using Redis:
- 5 login attempts per minute per IP
- 10 login attempts per hour per user

## Acceptance Criteria
- [ ] Rate limiter middleware implemented
- [ ] Redis integration configured
- [ ] Rate limit headers returned (X-RateLimit-*)
- [ ] Unit tests with >80% coverage
- [ ] Integration tests for rate limit enforcement

## Technical Details
- Use `slowapi` library for rate limiting
- Store counters in Redis with TTL
- Add Retry-After header on limit exceeded
""",
        "labels_suggestions": ["security", "api", "rate-limiting"],
        "priority_recommendation": 1,
        "estimated_effort": "4 hours",
        "acceptance_criteria": [
            "Rate limiter middleware implemented",
            "Redis integration configured",
            "Rate limit headers returned",
            "Unit tests with >80% coverage",
        ],
    }


# =============================================================================
# Assignee Recommender Agent
# =============================================================================


@MockResponseRegistry.register("AssigneeRecommenderAgent")
@MockResponseRegistry.register("AssigneeRecommenderAgentSDK")
def generate_assignee_recommendations(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate mock assignee recommendations.

    Args:
        input_data: Dict with issue_id, issue_content

    Returns:
        Assignee recommendations dict.
    """
    return {
        "recommendations": [
            {
                "user_id": str(uuid4()),
                "name": "Alice Chen",
                "confidence": 0.89,
                "rationale": "Has worked on 8 similar authentication issues with 95% completion rate",
                "expertise_match": ["authentication", "security", "FastAPI"],
                "availability": "high",
                "estimated_capacity": 0.7,
            },
            {
                "user_id": str(uuid4()),
                "name": "Bob Kumar",
                "confidence": 0.76,
                "rationale": "Recently completed rate limiting implementation in API gateway",
                "expertise_match": ["api", "rate-limiting"],
                "availability": "medium",
                "estimated_capacity": 0.5,
            },
        ],
        "team_capacity": 0.65,
        "analysis_date": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Duplicate Detector Agent
# =============================================================================


@MockResponseRegistry.register("DuplicateDetectorAgent")
@MockResponseRegistry.register("DuplicateDetectorAgentSDK")
def generate_duplicate_detection(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate mock duplicate detection result.

    Args:
        input_data: Dict with issue_id, issue_content

    Returns:
        Duplicate detection result dict.
    """
    return {
        "is_duplicate": False,
        "similar_issues": [
            {
                "issue_id": str(uuid4()),
                "identifier": "PILOT-145",
                "title": "Add authentication to admin endpoints",
                "similarity_score": 0.68,
                "status": "completed",
                "rationale": "Both involve authentication but different endpoints",
            },
            {
                "issue_id": str(uuid4()),
                "identifier": "PILOT-201",
                "title": "Implement OAuth2 flow",
                "similarity_score": 0.55,
                "status": "in_progress",
                "rationale": "Related to auth but different implementation approach",
            },
        ],
        "duplicate_confidence": 0.15,
        "recommendation": "Not a duplicate, but review PILOT-145 for reusable patterns",
    }


__all__ = [
    "generate_ai_context",
    "generate_assignee_recommendations",
    "generate_conversation_response",
    "generate_duplicate_detection",
    "generate_extracted_issues",
    "generate_ghost_text",
    "generate_issue_enhancement",
    "generate_margin_annotations",
    "generate_pr_review",
]
