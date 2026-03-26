"""Pydantic schemas for AI chat endpoints.

Covers ChatContext, ChatRequest, AbortRequest/Response,
SkillListItem/Response, AgentListItem/Response.

T096: AI chat implementation.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.ai_chat_model_routing import ModelOverride
from pilot_space.api.v1.schemas.base import BaseSchema


class ChatContext(BaseSchema):
    """Context for AI chat request."""

    workspace_id: UUID = Field(..., description="Workspace ID for context")
    note_id: UUID | None = Field(None, description="Note ID if chatting within note")
    issue_id: UUID | None = Field(None, description="Issue ID if chatting about issue")
    project_id: UUID | None = Field(None, description="Project ID if chatting about project")
    selected_text: str | None = Field(
        None, max_length=10000, description="Selected text from editor"
    )
    selected_block_ids: list[str] = Field(
        default_factory=list,
        description="Block IDs selected in editor",
    )
    attachment_ids: list[UUID] = Field(
        default_factory=list, description="Attachment IDs to include as file context", max_length=5
    )


class ChatRequest(BaseSchema):
    """Request for AI chat interaction."""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: str | None = Field(None, description="Session ID to resume conversation")
    fork_session_id: str | None = Field(
        None,
        description="Session ID to fork from (creates a branch for what-if exploration)",
    )
    context: ChatContext | None = Field(None, description="Context for AI response")
    model_override: ModelOverride | None = Field(None, description="User-selected model (AIPR-04)")


class AbortRequest(BaseSchema):
    """Request to abort an active chat session."""

    session_id: str = Field(..., description="Session ID to abort")


class AbortResponse(BaseSchema):
    """Response from abort request."""

    status: str = Field(..., description="'interrupted' or 'not_found'")
    session_id: str = Field(..., description="Session ID that was targeted")


class SkillListItem(BaseSchema):
    """Skill metadata for frontend display."""

    name: str = Field(..., description="Skill identifier (e.g., 'extract-issues')")
    description: str = Field(..., description="Brief description of skill purpose")
    when_to_use: str = Field(default="", description="Usage guidance")


class SkillListResponse(BaseSchema):
    """List of available skills."""

    skills: list[SkillListItem] = Field(default_factory=list, description="Available skills")
    total: int = Field(..., ge=0, description="Total skill count")


class AgentListItem(BaseSchema):
    """Agent metadata for frontend display."""

    name: str = Field(..., description="Agent identifier")
    description: str = Field(default="", description="Agent description")


class AgentListResponse(BaseSchema):
    """List of registered agents."""

    agents: list[AgentListItem] = Field(default_factory=list, description="Registered agents")
    total: int = Field(..., ge=0, description="Total agent count")


__all__ = [
    "AbortRequest",
    "AbortResponse",
    "AgentListItem",
    "AgentListResponse",
    "ChatContext",
    "ChatRequest",
    "SkillListItem",
    "SkillListResponse",
]
