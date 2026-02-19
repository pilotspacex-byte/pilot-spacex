"""Pydantic v2 schemas for the Memory API.

T-036: POST /api/v1/ai/memory/search
       GET  /api/v1/ai/memory/constitution/version

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.domain.constitution_rule import RuleSeverity


class MemorySearchRequest(BaseSchema):
    """Request for hybrid memory search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language query for memory search",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results to return",
    )


class MemorySearchEntry(BaseSchema):
    """Single result from memory search."""

    id: str = Field(description="Memory entry UUID")
    content: str = Field(description="Memory text content")
    source_type: str = Field(description="Source that generated this memory")
    pinned: bool = Field(description="Whether entry is pinned")
    score: float = Field(description="Fusion score (0.0–1.0)")
    embedding_score: float = Field(description="Vector cosine similarity component")
    text_score: float = Field(description="ts_rank full-text component")


class MemorySearchResponse(BaseSchema):
    """Response from hybrid memory search."""

    results: list[MemorySearchEntry] = Field(description="Ranked memory entries")
    query: str = Field(description="Original query text")
    embedding_used: bool = Field(description="Whether vector embedding was used")
    count: int = Field(description="Number of results returned")


class ConstitutionVersionResponse(BaseSchema):
    """Response for current constitution version."""

    version: int = Field(description="Latest constitution version number")
    workspace_id: UUID = Field(description="Workspace UUID")


class ConstitutionRuleInputSchema(BaseSchema):
    """A single constitution rule to ingest."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Rule text (RFC 2119 severity auto-detected)",
    )
    severity: RuleSeverity | None = Field(
        default=None,
        description="Override severity: must, should, or may",
    )
    source_block_id: UUID | None = Field(
        default=None,
        description="TipTap block UUID that generated this rule",
    )


class ConstitutionIngestRequest(BaseSchema):
    """Request to ingest constitution rules."""

    rules: list[ConstitutionRuleInputSchema] = Field(
        ...,
        min_length=1,
        description="List of rules to ingest as new version",
    )

    @field_validator("rules")
    @classmethod
    def validate_rules_not_empty(
        cls, v: list[ConstitutionRuleInputSchema]
    ) -> list[ConstitutionRuleInputSchema]:
        if not v:
            msg = "rules must not be empty"
            raise ValueError(msg)
        return v


class ConstitutionIngestResponse(BaseSchema):
    """Response from constitution rule ingestion."""

    version: int = Field(description="New version number created")
    rule_count: int = Field(description="Number of rules ingested")
    indexing_enqueued: bool = Field(description="Whether async vector indexing was enqueued")
