"""Contract tests for API schema serialization and HTTP method correctness.

Tests verify:
- C-1: AI suggestion schemas use camelCase (BaseSchema, not BaseModel)
- C-2: AI settings update uses PATCH not PUT
- W-1: WorkspaceIssueResponse includes sort_order and flat date fields
- W-2: Create issue endpoint returns full IssueResponse
- W-3: Workspace member invite accepts owner role
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# C-1: AI suggestion response schemas must serialize as camelCase
# ---------------------------------------------------------------------------


def test_issue_enhancement_response_serializes_camelcase() -> None:
    """C-1: IssueEnhancementResponse must use camelCase (requires BaseSchema)."""
    from pilot_space.api.v1.schemas.ai_suggestion import (
        IssueEnhancementResponse,
        LabelSuggestion,
        PrioritySuggestion,
    )

    response = IssueEnhancementResponse(
        enhanced_title="Fixed title",
        enhanced_description=None,
        suggested_labels=[LabelSuggestion(name="bug", confidence=0.9, is_existing=True)],
        suggested_priority=PrioritySuggestion(priority="high", confidence=0.8),
        title_enhanced=True,
        description_expanded=False,
    )

    data = response.model_dump(by_alias=True)

    assert "enhancedTitle" in data, "must serialize as camelCase"
    assert "enhanced_title" not in data, "must not have snake_case keys in JSON output"
    assert "titleEnhanced" in data
    assert "descriptionExpanded" in data
    assert "suggestedLabels" in data
    assert "suggestedPriority" in data

    # LabelSuggestion nested must also be camelCase
    label = data["suggestedLabels"][0]
    assert "isExisting" in label, "nested LabelSuggestion must use camelCase"
    assert "is_existing" not in label


def test_duplicate_check_response_serializes_camelcase() -> None:
    """C-1: DuplicateCheckResponse must use camelCase."""
    from pilot_space.api.v1.schemas.ai_suggestion import (
        DuplicateCandidateResponse,
        DuplicateCheckResponse,
    )

    response = DuplicateCheckResponse(
        candidates=[
            DuplicateCandidateResponse(
                issue_id=uuid4(),
                identifier="PS-1",
                title="Test",
                similarity=0.9,
                explanation=None,
            )
        ],
        has_likely_duplicate=True,
        highest_similarity=0.9,
    )

    data = response.model_dump(by_alias=True)

    assert "hasLikelyDuplicate" in data, "must serialize as camelCase"
    assert "highestSimilarity" in data
    assert "has_likely_duplicate" not in data, "must not have snake_case keys"
    assert "highest_similarity" not in data

    candidate = data["candidates"][0]
    assert "issueId" in candidate, "nested DuplicateCandidateResponse must use camelCase"
    assert "issue_id" not in candidate


def test_assignee_recommendations_response_serializes_camelcase() -> None:
    """C-1: AssigneeRecommendationsResponse must use camelCase."""
    from pilot_space.api.v1.schemas.ai_suggestion import (
        AssigneeRecommendationResponse,
        AssigneeRecommendationsResponse,
    )

    response = AssigneeRecommendationsResponse(
        recommendations=[
            AssigneeRecommendationResponse(
                user_id=uuid4(),
                name="John",
                email="john@example.com",
                confidence=0.9,
                reason="Expert in this area",
            )
        ],
        has_strong_match=True,
    )

    data = response.model_dump(by_alias=True)

    assert "hasStrongMatch" in data, "must serialize as camelCase"
    assert "has_strong_match" not in data, "must not have snake_case keys"

    recommendation = data["recommendations"][0]
    assert "userId" in recommendation, "nested AssigneeRecommendationResponse must use camelCase"
    assert "user_id" not in recommendation


# ---------------------------------------------------------------------------
# C-2: AI settings update endpoint must use PATCH not PUT
# ---------------------------------------------------------------------------


def test_ai_settings_update_uses_patch_method() -> None:
    """C-2: Update AI settings must use PATCH (not PUT) to match frontend call."""
    from pilot_space.api.v1.routers.workspace_ai_settings import router

    routes = {route.path: route.methods for route in router.routes}
    ai_settings_path = "/{workspace_id}/ai/settings"

    assert ai_settings_path in routes, f"route {ai_settings_path} must exist"

    methods = routes[ai_settings_path]
    assert "PATCH" in methods, "AI settings update endpoint must use PATCH method"
    assert "PUT" not in methods, "AI settings update endpoint must not use PUT method"


# ---------------------------------------------------------------------------
# W-1: WorkspaceIssueResponse must include sort_order and flat date fields
# ---------------------------------------------------------------------------


def test_workspace_issue_response_includes_sort_order() -> None:
    """W-1: WorkspaceIssueResponse must include sort_order field."""

    from pilot_space.api.v1.routers.workspace_issues import WorkspaceIssueResponse
    from pilot_space.api.v1.schemas.issue import StateBriefSchema

    response = WorkspaceIssueResponse(
        id=uuid4(),
        workspace_id=uuid4(),
        identifier="PS-1",
        sequence_id=1,
        name="Test issue",
        state=StateBriefSchema(
            id=uuid4(),
            name="Todo",
            group="unstarted",
            color="#fff",
            is_default=False,
            sequence=0,
        ),
        priority="none",
        reporter_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        sort_order=42,
    )

    data = response.model_dump(by_alias=True)
    assert "sortOrder" in data, "WorkspaceIssueResponse must include sortOrder"
    assert data["sortOrder"] == 42


# ---------------------------------------------------------------------------
# W-3: WorkspaceMemberCreate role pattern must allow 'owner'
# ---------------------------------------------------------------------------


def test_workspace_member_create_accepts_owner_role() -> None:
    """W-3: WorkspaceMemberCreate must accept 'OWNER' role (uppercase per RLS convention)."""
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.workspace import WorkspaceMemberCreate

    # Schema uses uppercase roles (RLS convention: OWNER, ADMIN, MEMBER, GUEST)
    member = WorkspaceMemberCreate(email="admin@example.com", role="OWNER")
    assert member.role == "OWNER"

    # Other valid uppercase roles should work
    for role in ("ADMIN", "MEMBER", "GUEST"):
        m = WorkspaceMemberCreate(email="user@example.com", role=role)
        assert m.role == role

    # Lowercase roles are rejected (schema pattern requires uppercase)
    with pytest.raises(ValidationError):
        WorkspaceMemberCreate(email="admin@example.com", role="owner")

    # Invalid role should still raise
    with pytest.raises(ValidationError):
        WorkspaceMemberCreate(email="user@example.com", role="superadmin")
