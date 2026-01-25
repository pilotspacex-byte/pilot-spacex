"""AI Context API schemas.

T209: Create AIContext Pydantic schemas for API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Nested Schemas
# =============================================================================


class RelatedItemResponse(BaseModel):
    """Related item (issue, note, or page) response."""

    id: str
    type: str  # issue, note, page
    title: str
    relevance_score: float = Field(ge=0, le=1)
    excerpt: str = ""
    identifier: str | None = None  # For issues
    state: str | None = None  # For issues

    model_config = ConfigDict(from_attributes=True)


class CodeReferenceResponse(BaseModel):
    """Code file reference response."""

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    description: str = ""
    relevance: str = "medium"  # high, medium, low
    source: str | None = None  # commit, pull_request, manual
    source_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskItemResponse(BaseModel):
    """Implementation task item response."""

    id: str
    description: str
    completed: bool = False
    dependencies: list[str] = Field(default_factory=list)
    estimated_effort: str = "M"  # S, M, L, XL
    order: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    """Conversation message response."""

    role: str  # user, assistant
    content: str
    timestamp: str | None = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Request Schemas
# =============================================================================


class GenerateContextRequest(BaseModel):
    """Request to generate AI context."""

    force_regenerate: bool = False


class RefineContextRequest(BaseModel):
    """Request to refine AI context via chat."""

    query: str = Field(..., min_length=1, max_length=5000)


class MarkTaskCompletedRequest(BaseModel):
    """Request to mark a task as completed."""

    task_id: str = Field(..., min_length=1, max_length=50)


class ExportContextRequest(BaseModel):
    """Request to export AI context."""

    format: str = Field(default="markdown", pattern="^(markdown|json)$")
    include_conversation: bool = False


# =============================================================================
# Response Schemas
# =============================================================================


class AIContextContentResponse(BaseModel):
    """AI context content section response."""

    summary: str = ""
    analysis: str = ""
    complexity: str = "medium"
    estimated_effort: str = "M"
    key_considerations: list[str] = Field(default_factory=list)
    suggested_approach: str = ""
    potential_blockers: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AIContextResponse(BaseModel):
    """Full AI context response."""

    id: str  # UUID as string
    issue_id: str
    workspace_id: str

    # Content
    content: AIContextContentResponse
    claude_code_prompt: str | None = None

    # Related items
    related_issues: list[RelatedItemResponse] = Field(default_factory=list)
    related_notes: list[RelatedItemResponse] = Field(default_factory=list)
    related_pages: list[RelatedItemResponse] = Field(default_factory=list)
    code_references: list[CodeReferenceResponse] = Field(default_factory=list)

    # Tasks
    tasks_checklist: list[TaskItemResponse] = Field(default_factory=list)
    task_count: int = 0
    completed_task_count: int = 0

    # Conversation
    conversation_count: int = 0
    has_conversation: bool = False

    # Metadata
    generated_at: datetime
    last_refined_at: datetime | None = None
    version: int = 1
    is_stale: bool = False

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, context: Any) -> AIContextResponse:
        """Create from AIContext model."""
        content_data = context.content or {}

        return cls(
            id=str(context.id),
            issue_id=str(context.issue_id),
            workspace_id=str(context.workspace_id),
            content=AIContextContentResponse(
                summary=content_data.get("summary", ""),
                analysis=content_data.get("analysis", ""),
                complexity=content_data.get("complexity", "medium"),
                estimated_effort=content_data.get("estimated_effort", "M"),
                key_considerations=content_data.get("key_considerations", []),
                suggested_approach=content_data.get("suggested_approach", ""),
                potential_blockers=content_data.get("potential_blockers", []),
            ),
            claude_code_prompt=context.claude_code_prompt,
            related_issues=[RelatedItemResponse(**item) for item in (context.related_issues or [])],
            related_notes=[RelatedItemResponse(**item) for item in (context.related_notes or [])],
            related_pages=[RelatedItemResponse(**item) for item in (context.related_pages or [])],
            code_references=[
                CodeReferenceResponse(**ref) for ref in (context.code_references or [])
            ],
            tasks_checklist=[TaskItemResponse(**task) for task in (context.tasks_checklist or [])],
            task_count=context.task_count,
            completed_task_count=context.completed_task_count,
            conversation_count=context.conversation_count,
            has_conversation=context.has_conversation,
            generated_at=context.generated_at,
            last_refined_at=context.last_refined_at,
            version=context.version,
            is_stale=context.is_stale,
            created_at=context.created_at,
            updated_at=context.updated_at,
        )


class AIContextBriefResponse(BaseModel):
    """Brief AI context response for lists."""

    id: str
    issue_id: str
    summary: str = ""
    complexity: str = "medium"
    task_count: int = 0
    completed_task_count: int = 0
    generated_at: datetime
    is_stale: bool = False

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, context: Any) -> AIContextBriefResponse:
        """Create from AIContext model."""
        content_data = context.content or {}

        return cls(
            id=str(context.id),
            issue_id=str(context.issue_id),
            summary=content_data.get("summary", ""),
            complexity=content_data.get("complexity", "medium"),
            task_count=context.task_count,
            completed_task_count=context.completed_task_count,
            generated_at=context.generated_at,
            is_stale=context.is_stale,
        )


class GenerateContextResponse(BaseModel):
    """Response from context generation."""

    context_id: str
    issue_id: str
    summary: str
    complexity: str
    task_count: int
    related_issue_count: int
    claude_code_prompt: str | None
    from_cache: bool
    generated_at: datetime
    version: int

    model_config = ConfigDict(from_attributes=True)


class RefineContextResponse(BaseModel):
    """Response from context refinement."""

    context_id: str
    issue_id: str
    response: str
    conversation_count: int
    last_refined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportContextResponse(BaseModel):
    """Response from context export."""

    content: str
    format: str
    filename: str
    content_type: str

    model_config = ConfigDict(from_attributes=True)


class ConversationHistoryResponse(BaseModel):
    """Conversation history response."""

    messages: list[ChatMessageResponse] = Field(default_factory=list)
    total_count: int = 0

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AIContextBriefResponse",
    "AIContextContentResponse",
    "AIContextResponse",
    "ChatMessageResponse",
    "CodeReferenceResponse",
    "ConversationHistoryResponse",
    "ExportContextRequest",
    "ExportContextResponse",
    "GenerateContextRequest",
    "GenerateContextResponse",
    "MarkTaskCompletedRequest",
    "RefineContextRequest",
    "RefineContextResponse",
    "RelatedItemResponse",
    "TaskItemResponse",
]
