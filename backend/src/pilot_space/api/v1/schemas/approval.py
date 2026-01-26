"""Pydantic schemas for AI approval queue.

Request/response models for approval workflow endpoints.

T075: Approval queue Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequestResponse(BaseModel):
    """Approval request in list response.

    Compact representation for listing approvals.
    """

    id: str = Field(description="Approval request ID")
    agent_name: str = Field(description="Name of the requesting agent")
    action_type: str = Field(description="Type of action (e.g., create_issues)")
    status: ApprovalStatus = Field(description="Current status")
    created_at: datetime = Field(description="When request was created")
    expires_at: datetime = Field(description="When request expires")
    requested_by: str = Field(description="User name who triggered action")
    context_preview: str = Field(description="Brief context preview")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_name": "issue_extractor",
                "action_type": "extract_issues",
                "status": "pending",
                "created_at": "2026-01-26T10:30:00Z",
                "expires_at": "2026-01-27T10:30:00Z",
                "requested_by": "John Doe",
                "context_preview": "3 issues to create",
            }
        }
    }


class ApprovalListResponse(BaseModel):
    """Response for approval list endpoint.

    Includes pagination and metadata.
    """

    requests: list[ApprovalRequestResponse] = Field(description="List of approval requests")
    total: int = Field(description="Total number of requests")
    pending_count: int = Field(description="Number of pending requests")

    model_config = {
        "json_schema_extra": {
            "example": {
                "requests": [],
                "total": 5,
                "pending_count": 2,
            }
        }
    }


class ApprovalDetailResponse(BaseModel):
    """Full approval request details.

    Includes complete payload and context for review.
    """

    id: str = Field(description="Approval request ID")
    agent_name: str = Field(description="Name of the requesting agent")
    action_type: str = Field(description="Type of action")
    status: ApprovalStatus = Field(description="Current status")
    payload: dict[str, Any] = Field(description="Full action payload")
    context: dict[str, Any] | None = Field(default=None, description="Optional context")
    created_at: datetime = Field(description="When request was created")
    expires_at: datetime = Field(description="When request expires")
    resolved_at: datetime | None = Field(default=None, description="When resolved")
    resolved_by: str | None = Field(default=None, description="User who resolved")
    resolution_note: str | None = Field(default=None, description="Resolution note")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_name": "issue_extractor",
                "action_type": "extract_issues",
                "status": "pending",
                "payload": {"issues": [{"title": "Fix bug", "description": "Details"}]},
                "context": {"note_id": "123", "project_id": "456"},
                "created_at": "2026-01-26T10:30:00Z",
                "expires_at": "2026-01-27T10:30:00Z",
                "resolved_at": None,
                "resolved_by": None,
                "resolution_note": None,
            }
        }
    }


class ApprovalResolution(BaseModel):
    """Request to resolve an approval.

    User decision to approve or reject.
    """

    approved: bool = Field(description="True to approve, False to reject")
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional note explaining the decision",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"approved": True, "note": "Looks good"},
                {"approved": False, "note": "Not needed, duplicate of existing issue"},
            ]
        }
    }


class ApprovalResolutionResponse(BaseModel):
    """Response for approval resolution.

    Includes execution result if approved.
    """

    approved: bool = Field(description="Whether request was approved")
    action_result: dict[str, Any] | None = Field(
        default=None,
        description="Result of executing the action (if approved)",
    )
    action_error: str | None = Field(
        default=None,
        description="Error message if action execution failed",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "approved": True,
                "action_result": {"created_issues": ["issue-123", "issue-456"]},
                "action_error": None,
            }
        }
    }


__all__ = [
    "ApprovalDetailResponse",
    "ApprovalListResponse",
    "ApprovalRequestResponse",
    "ApprovalResolution",
    "ApprovalResolutionResponse",
    "ApprovalStatus",
]
