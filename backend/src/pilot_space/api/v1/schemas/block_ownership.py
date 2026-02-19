"""Block ownership schemas for Feature 016 (M6b — Ownership Engine).

Provides request/response schemas for:
- POST /notes/{noteId}/blocks/{blockId}/approve
- POST /notes/{noteId}/blocks/{blockId}/reject
- GET  /notes/{noteId}/blocks/{blockId}/owner

T-113: Block approve/reject API
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class BlockOwnerResponse(BaseSchema):
    """Response for block owner query."""

    block_id: str = Field(description="Block UUID")
    owner: str = Field(description="Current owner: 'human', 'shared', or 'ai:{skill-name}'")
    note_id: str = Field(description="Note UUID containing this block")


class BlockApproveRequest(BaseSchema):
    """Request to approve an AI block (human accepts content, keeps AI ownership label)."""

    convert_to_shared: bool = Field(
        default=False,
        description=(
            "If true, changes ownership to 'shared' after approval, "
            "allowing human editing. If false, keeps 'ai:{skill}' ownership."
        ),
    )


class BlockApproveResponse(BaseSchema):
    """Response after approving an AI block."""

    block_id: str = Field(description="Block UUID")
    note_id: str = Field(description="Note UUID")
    action: Literal["approved"] = Field(default="approved")
    owner: str = Field(description="Resulting owner after approval")


class BlockRejectResponse(BaseSchema):
    """Response after rejecting an AI block."""

    block_id: str = Field(description="Block UUID")
    note_id: str = Field(description="Note UUID")
    action: Literal["rejected"] = Field(default="rejected")
    removed: bool = Field(description="Whether the block was removed from the note")
