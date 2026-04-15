"""Implement context API schemas.

Response models for GET /api/v1/issues/{issue_id}/implement-context.
Provides all context needed by PilotSpaceAgent to implement an issue.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.infrastructure.database.models import IssuePriority, StateGroup

# ============================================================================
# Nested Schemas
# ============================================================================


class IssueStateDetail(BaseSchema):
    """State information for the issue."""

    id: UUID
    name: str
    color: str
    group: StateGroup


class IssueLabelDetail(BaseSchema):
    """Label information for the issue."""

    id: UUID
    name: str
    color: str


class IssueDetail(BaseSchema):
    """Full issue detail for implement context.

    Contains all fields required for an agent to understand the issue
    and start implementation.
    """

    id: UUID
    identifier: str
    title: str
    description: str | None
    description_html: str | None
    acceptance_criteria: list[str]
    status: str
    priority: IssuePriority
    labels: list[IssueLabelDetail]
    state: IssueStateDetail
    project_id: UUID
    assignee_id: UUID | None
    cycle_id: UUID | None = None

    @classmethod
    def from_issue(cls, issue: Any) -> IssueDetail:
        """Build IssueDetail from an Issue ORM model.

        Args:
            issue: Issue model instance with relations loaded.

        Returns:
            IssueDetail schema instance.
        """
        # Extract acceptance criteria from AI metadata if available
        ai_metadata: dict[str, Any] = issue.ai_metadata or {}
        acceptance_criteria: list[str] = ai_metadata.get("acceptance_criteria", [])

        return cls(
            id=issue.id,
            identifier=issue.identifier,
            title=issue.name,
            description=issue.description,
            description_html=issue.description_html,
            acceptance_criteria=acceptance_criteria,
            status=issue.state.group.value if issue.state else "unstarted",
            priority=issue.priority,
            labels=[IssueLabelDetail.model_validate(label) for label in (issue.labels or [])],
            state=IssueStateDetail.model_validate(issue.state) if issue.state else None,  # type: ignore[arg-type]
            project_id=issue.project_id,
            assignee_id=issue.assignee_id,
            cycle_id=getattr(issue, "cycle_id", None),
        )


class LinkedNoteBlock(BaseSchema):
    """Note context relevant to an issue via NoteIssueLink.

    Attributes:
        note_title: Title of the linked note.
        relevant_blocks: Up to 3 text block excerpts near the link origin.
    """

    note_title: str
    relevant_blocks: list[str] = Field(
        default_factory=list,
        description="Text content of note blocks near the NoteIssueLink origin",
        max_length=3,
    )


class RepositoryContext(BaseSchema):
    """GitHub repository context for the workspace.

    Attributes:
        clone_url: HTTPS clone URL (e.g., https://github.com/org/repo).
        default_branch: Default branch name (e.g., main).
        provider: VCS provider type.
    """

    clone_url: str
    default_branch: str
    provider: Literal["github", "gitlab"]


class WorkspaceContext(BaseSchema):
    """Workspace metadata.

    Attributes:
        slug: URL slug for the workspace.
        name: Display name.
    """

    slug: str
    name: str


class ProjectContext(BaseSchema):
    """Project metadata and tech stack summary.

    Attributes:
        name: Display name of the project.
        tech_stack_summary: First 300 chars of project description, or default.
    """

    name: str
    tech_stack_summary: str


# ============================================================================
# Enrichment Schemas (Phase 74 — Rich Context Engine)
# ============================================================================


class KGDecision(BaseSchema):
    """Knowledge graph decision or pattern relevant to the issue.

    Note: source_type covers both DECISION and PATTERN KG node types —
    CTX-01 "code patterns" are stored as PATTERN nodes in the KG and
    surfaced through the same recall pipeline as DECISION nodes.
    """

    node_id: str
    snippet: str
    score: float
    source_type: str  # "DECISION" or "PATTERN" (both are KG node types)


class RelatedPR(BaseSchema):
    """PR from a related closed issue."""

    issue_identifier: str
    issue_title: str
    pr_url: str
    pr_state: str | None = None  # "merged" | "closed" | "open"


class SprintPeer(BaseSchema):
    """Another issue in the same active sprint."""

    identifier: str
    title: str
    state: str
    assignee_name: str | None = None
    acceptance_criteria_summary: str | None = None  # first 200 chars


# ============================================================================
# Top-Level Response
# ============================================================================


class ImplementContextResponse(BaseSchema):
    """Full implement-context response for an issue.

    Returned by GET /api/v1/issues/{issue_id}/implement-context.
    Provides an AI agent with everything needed to start implementation:
    issue details, linked note context, repository info, workspace and project
    metadata, and the suggested feature branch name.

    Attributes:
        issue: Detailed issue information including acceptance criteria.
        linked_notes: Notes linked to this issue with relevant block excerpts.
        repository: GitHub repository to work against.
        workspace: Workspace slug and name.
        project: Project name and tech stack summary.
        suggested_branch: Computed branch name capped at 60 characters.
    """

    issue: IssueDetail
    linked_notes: list[LinkedNoteBlock] = Field(default_factory=list)
    repository: RepositoryContext
    workspace: WorkspaceContext
    project: ProjectContext
    suggested_branch: str = Field(
        description="Suggested git branch name: feat/ps-{sequence_id}-{title_slug}",
        max_length=60,
    )
    kg_decisions: list[KGDecision] = Field(default_factory=list)
    related_prs: list[RelatedPR] = Field(default_factory=list)
    sprint_peers: list[SprintPeer] = Field(default_factory=list)
    context_budget_used_pct: float | None = None


__all__ = [
    "ImplementContextResponse",
    "IssueDetail",
    "IssueLabelDetail",
    "IssueStateDetail",
    "KGDecision",
    "LinkedNoteBlock",
    "ProjectContext",
    "RelatedPR",
    "RepositoryContext",
    "SprintPeer",
    "WorkspaceContext",
]
