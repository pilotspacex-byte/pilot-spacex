"""AI Suggestion API schemas.

T141: Create AI suggestion Pydantic schemas.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from pilot_space.api.v1.schemas.base import BaseSchema

# ============================================================================
# Enhancement Schemas
# ============================================================================


class IssueEnhancementRequest(BaseModel):
    """Request for AI issue enhancement."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID


class LabelSuggestion(BaseSchema):
    """A suggested label with confidence."""

    name: str
    confidence: float = Field(..., ge=0, le=1)
    is_existing: bool = True


class PrioritySuggestion(BaseSchema):
    """A suggested priority with confidence."""

    priority: str
    confidence: float = Field(..., ge=0, le=1)


class IssueEnhancementResponse(BaseSchema):
    """Response with AI enhancement suggestions."""

    enhanced_title: str
    enhanced_description: str | None
    suggested_labels: list[LabelSuggestion]
    suggested_priority: PrioritySuggestion | None
    title_enhanced: bool
    description_expanded: bool


# ============================================================================
# Duplicate Detection Schemas
# ============================================================================


class DuplicateCheckRequest(BaseModel):
    """Request for duplicate detection."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    exclude_issue_id: UUID | None = None
    threshold: float = Field(default=0.75, ge=0, le=1)


class DuplicateCandidateResponse(BaseSchema):
    """A potential duplicate issue."""

    issue_id: UUID
    identifier: str
    title: str
    similarity: float = Field(..., ge=0, le=1)
    explanation: str | None


class DuplicateCheckResponse(BaseSchema):
    """Response with duplicate detection results."""

    candidates: list[DuplicateCandidateResponse]
    has_likely_duplicate: bool
    highest_similarity: float


# ============================================================================
# Assignee Recommendation Schemas
# ============================================================================


class AssigneeRecommendationRequest(BaseModel):
    """Request for assignee recommendation."""

    title: str = Field(..., min_length=1)
    description: str | None = None
    label_names: list[str] | None = None
    project_id: UUID


class AssigneeRecommendationResponse(BaseSchema):
    """A recommended assignee."""

    user_id: UUID
    name: str
    email: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    reason: str


class AssigneeRecommendationsResponse(BaseSchema):
    """Response with assignee recommendations."""

    recommendations: list[AssigneeRecommendationResponse]
    has_strong_match: bool


# ============================================================================
# Suggestion Decision Schemas
# ============================================================================


class SuggestionDecisionRequest(BaseModel):
    """Request to record user decision on AI suggestion."""

    suggestion_type: str = Field(
        ..., pattern="^(label|priority|assignee|title|description|duplicate)$"
    )
    accepted: bool
    suggestion_value: Any = None  # The actual suggestion value


class SuggestionDecisionResponse(BaseModel):
    """Response confirming suggestion decision."""

    recorded: bool
    activity_id: UUID | None = None


# ============================================================================
# AI Confidence Tags
# ============================================================================


class ConfidenceTag(BaseModel):
    """Confidence tag for AI suggestions (per DD-048).

    Tags:
    - recommended: High confidence (green) - confidence >= 0.8
    - default: Medium confidence (blue) - confidence >= 0.6
    - alternative: Lower confidence (gray) - confidence >= 0.4
    - current: User's existing choice (neutral)
    """

    tag: str = Field(..., pattern="^(recommended|default|alternative|current)$")
    confidence: float = Field(..., ge=0, le=1)
    reason: str | None = None

    @classmethod
    def from_confidence(cls, confidence: float, reason: str | None = None) -> ConfidenceTag:
        """Create tag from confidence score.

        Args:
            confidence: Score between 0 and 1.
            reason: Optional explanation.

        Returns:
            ConfidenceTag with appropriate tag level.
        """
        if confidence >= 0.8:
            tag = "recommended"
        elif confidence >= 0.6:
            tag = "default"
        else:
            tag = "alternative"

        return cls(tag=tag, confidence=confidence, reason=reason)


class TaggedSuggestion(BaseModel):
    """A suggestion with confidence tag."""

    value: Any
    tag: ConfidenceTag
    is_current: bool = False


__all__ = [
    "AssigneeRecommendationRequest",
    "AssigneeRecommendationResponse",
    "AssigneeRecommendationsResponse",
    "ConfidenceTag",
    "DuplicateCandidateResponse",
    "DuplicateCheckRequest",
    "DuplicateCheckResponse",
    "IssueEnhancementRequest",
    "IssueEnhancementResponse",
    "LabelSuggestion",
    "PrioritySuggestion",
    "SuggestionDecisionRequest",
    "SuggestionDecisionResponse",
    "TaggedSuggestion",
]
