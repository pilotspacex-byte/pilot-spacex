"""Database MCP tools for Pilot Space data access.

These tools provide read-only access to issues, notes, projects.
Write tools require approval flow (DD-003).

T018: Implement get_issue_context tool
T019-T021: Implement get_note_content, get_project_context, find_similar_issues
T022-T024: Implement get_workspace_members, get_page_content, get_cycle_context
T030: Implement create_note_annotation tool (AUTO_EXECUTE)
T031: Implement create_issue tool (DEFAULT_REQUIRE_APPROVAL)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pilot_space.ai.tools.mcp_server import ToolContext, register_tool
from pilot_space.infrastructure.database.models import (
    Activity,
    AnnotationStatus,
    AnnotationType,
    Cycle,
    Issue,
    Note,
    NoteAnnotation,
    Project,
    WorkspaceMember,
)


@register_tool("database")
async def get_issue_context(
    issue_id: str,
    ctx: ToolContext,
    include_notes: bool = True,
    include_related: bool = True,
    include_activity: bool = True,
) -> dict[str, Any]:
    """Get comprehensive context for an issue.

    Retrieves issue details along with related notes, linked issues,
    and recent activity. Used by AIContextAgent for issue understanding.

    Args:
        issue_id: UUID of the issue
        ctx: Tool context with db_session
        include_notes: Whether to include linked notes (default True)
        include_related: Whether to include related issues (default True)
        include_activity: Whether to include activity log (default True)

    Returns:
        Dict with issue details and related data
    """
    uuid_id = UUID(issue_id)

    # Build query with eager loading to avoid N+1
    query = select(Issue).where(
        Issue.id == uuid_id,
        Issue.workspace_id == UUID(ctx.workspace_id),
    )

    # Add eager loading options
    query = query.options(
        selectinload(Issue.state),
        selectinload(Issue.labels),
        selectinload(Issue.assignee),
        selectinload(Issue.reporter),
        selectinload(Issue.project),
    )

    if include_notes:
        query = query.options(selectinload(Issue.note_links))

    if include_related:
        query = query.options(
            selectinload(Issue.parent),
            selectinload(Issue.sub_issues),
        )

    result = await ctx.db_session.execute(query)
    issue = result.scalar_one_or_none()

    if not issue:
        return {"error": f"Issue {issue_id} not found", "found": False}

    # Build response
    response: dict[str, Any] = {
        "found": True,
        "issue": {
            "id": str(issue.id),
            "identifier": issue.identifier,
            "title": issue.name,
            "description": issue.description,
            "state": (
                {
                    "name": issue.state.name,
                    "group": issue.state.group.value,
                }
                if issue.state
                else None
            ),
            "priority": issue.priority.value if issue.priority else None,
            "labels": [
                {"name": label.name, "color": label.color} for label in (issue.labels or [])
            ],
            "assignee": (
                {
                    "id": str(issue.assignee.id),
                    "name": issue.assignee.full_name or issue.assignee.email,
                }
                if issue.assignee
                else None
            ),
            "reporter": (
                {
                    "id": str(issue.reporter.id),
                    "name": issue.reporter.full_name or issue.reporter.email,
                }
                if issue.reporter
                else None
            ),
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        },
    }

    # Add linked notes
    if include_notes and issue.note_links:
        response["notes"] = [
            {
                "id": str(link.note_id),
                "link_type": link.link_type.value if link.link_type else None,
            }
            for link in issue.note_links[:10]  # Limit to 10
        ]

    # Add related issues
    if include_related:
        response["related_issues"] = {
            "parent": _issue_summary(issue.parent) if issue.parent else None,
            "children": [_issue_summary(child) for child in (issue.sub_issues or [])[:10]],
        }

    # Add activity
    if include_activity:
        activity_query = (
            select(Activity)
            .where(
                Activity.issue_id == uuid_id,
                Activity.workspace_id == UUID(ctx.workspace_id),
            )
            .order_by(Activity.created_at.desc())
            .limit(20)
        )
        activity_result = await ctx.db_session.execute(activity_query)
        activities = activity_result.scalars().all()

        response["activity"] = [
            {
                "id": str(act.id),
                "type": act.activity_type.value if act.activity_type else None,
                "field": act.field,
                "old_value": act.old_value,
                "new_value": act.new_value,
                "created_at": act.created_at.isoformat() if act.created_at else None,
            }
            for act in activities
        ]

    return response


def _issue_summary(issue: Issue) -> dict[str, Any]:
    """Create minimal issue summary for related issues.

    Args:
        issue: Issue model instance

    Returns:
        Dict with basic issue info
    """
    return {
        "id": str(issue.id),
        "identifier": issue.identifier,
        "title": issue.name,
        "state": issue.state.name if issue.state else None,
    }


@register_tool("database")
async def get_note_content(
    note_id: str,
    ctx: ToolContext,
    include_annotations: bool = True,
) -> dict[str, Any]:
    """Get note content with annotations.

    Retrieves note details for AI analysis including any existing
    AI annotations in the margin.

    Args:
        note_id: UUID of the note
        ctx: Tool context with db_session
        include_annotations: Whether to include AI annotations

    Returns:
        Dict with note content and metadata
    """
    uuid_id = UUID(note_id)

    query = select(Note).where(
        Note.id == uuid_id,
        Note.workspace_id == UUID(ctx.workspace_id),
    )

    if include_annotations:
        query = query.options(selectinload(Note.annotations))

    result = await ctx.db_session.execute(query)
    note = result.scalar_one_or_none()

    if not note:
        return {"error": f"Note {note_id} not found", "found": False}

    response: dict[str, Any] = {
        "found": True,
        "note": {
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
    }

    if include_annotations and note.annotations:
        response["annotations"] = [
            {
                "id": str(ann.id),
                "type": ann.type.value if ann.type else None,
                "content": ann.content,
                "status": ann.status.value if ann.status else None,
                "block_id": str(ann.block_id) if ann.block_id else None,
            }
            for ann in note.annotations[:20]  # Limit to 20
        ]

    return response


@register_tool("database")
async def get_project_context(
    project_id: str,
    ctx: ToolContext,
) -> dict[str, Any]:
    """Get project settings, labels, and states.

    Retrieves project configuration for understanding workflow
    conventions and available categorizations.

    Args:
        project_id: UUID of the project
        ctx: Tool context with db_session

    Returns:
        Dict with project settings and metadata
    """
    uuid_id = UUID(project_id)

    query = (
        select(Project)
        .where(
            Project.id == uuid_id,
            Project.workspace_id == UUID(ctx.workspace_id),
        )
        .options(
            selectinload(Project.labels),
            selectinload(Project.states),
        )
    )

    result = await ctx.db_session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        return {"error": f"Project {project_id} not found", "found": False}

    return {
        "found": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "identifier": project.identifier,
            "description": project.description,
        },
        "labels": [
            {
                "id": str(label.id),
                "name": label.name,
                "color": label.color,
                "description": label.description,
            }
            for label in (project.labels or [])
        ],
        "states": [
            {
                "id": str(state.id),
                "name": state.name,
                "group": state.group.value if state.group else None,
                "sequence": state.sequence,
            }
            for state in sorted(project.states or [], key=lambda s: s.sequence)
        ],
    }


@register_tool("database")
async def find_similar_issues(
    query_text: str,
    ctx: ToolContext,
    project_id: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Find similar issues using embedding similarity.

    Uses vector search to find semantically similar issues.
    Useful for duplicate detection and related issue discovery.

    Args:
        query_text: Text to find similar issues for
        ctx: Tool context with db_session
        project_id: Optional project ID to scope search
        limit: Maximum results (default 5, max 20)

    Returns:
        List of similar issues with similarity scores
    """
    # Limit cap
    limit = min(limit, 20)

    # Get embedding for query text
    # Note: In production, this would call the embedding service
    # For now, search by title/description text similarity as fallback

    # Text-based search fallback (replace with vector search when available)
    search_pattern = f"%{query_text.lower()}%"

    query = (
        select(Issue)
        .where(
            Issue.workspace_id == UUID(ctx.workspace_id),
            Issue.deleted_at.is_(None),
        )
        .where(Issue.name.ilike(search_pattern) | Issue.description.ilike(search_pattern))
        .limit(limit)
    )

    if project_id:
        query = query.where(Issue.project_id == UUID(project_id))

    query = query.options(selectinload(Issue.state))

    result = await ctx.db_session.execute(query)
    issues = result.scalars().all()

    return {
        "similar_issues": [
            {
                "id": str(issue.id),
                "identifier": issue.identifier,
                "title": issue.name,
                "state": issue.state.name if issue.state else None,
                "similarity_score": 0.85,  # Placeholder score
            }
            for issue in issues
        ],
        "search_method": "text_similarity",  # Will be "vector" when embeddings ready
    }


@register_tool("database")
async def get_workspace_members(
    ctx: ToolContext,
    include_skills: bool = False,
) -> dict[str, Any]:
    """Get workspace members with roles.

    Retrieves team members for assignee recommendations
    and workload analysis.

    Args:
        ctx: Tool context with workspace_id
        include_skills: Whether to include member skills/expertise

    Returns:
        List of workspace members with roles
    """
    query = (
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == UUID(ctx.workspace_id),
        )
        .options(selectinload(WorkspaceMember.user))
    )

    result = await ctx.db_session.execute(query)
    members = result.scalars().all()

    return {
        "members": [
            {
                "id": str(m.user.id) if m.user else None,
                "name": m.user.full_name or m.user.email if m.user else None,
                "email": m.user.email if m.user else None,
                "role": m.role.value if m.role else None,
                "skills": getattr(m.user, "skills", []) if include_skills and m.user else [],
            }
            for m in members
            if m.user
        ],
        "count": len(members),
    }


@register_tool("database")
async def get_page_content(
    page_id: str,
    ctx: ToolContext,
) -> dict[str, Any]:
    """Get wiki/documentation page content.

    Retrieves page content for knowledge base context.
    Pages are hierarchical documentation in Pilot Space.

    Args:
        page_id: UUID of the page
        ctx: Tool context with db_session

    Returns:
        Page content and metadata
    """
    # Note: Page model not yet implemented in codebase
    # This is a placeholder for future implementation
    return {
        "error": "Page model not yet implemented",
        "found": False,
        "note": "Wiki pages feature pending implementation",
    }


@register_tool("database")
async def get_cycle_context(
    cycle_id: str,
    ctx: ToolContext,
    include_issues: bool = False,
) -> dict[str, Any]:
    """Get cycle (sprint) context with progress metrics.

    Retrieves cycle details for sprint planning and
    velocity analysis.

    Args:
        cycle_id: UUID of the cycle
        ctx: Tool context with db_session
        include_issues: Whether to include issues in cycle

    Returns:
        Cycle details with progress metrics
    """
    uuid_id = UUID(cycle_id)

    query = select(Cycle).where(
        Cycle.id == uuid_id,
        Cycle.workspace_id == UUID(ctx.workspace_id),
    )

    if include_issues:
        query = query.options(selectinload(Cycle.issues))

    result = await ctx.db_session.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        return {"error": f"Cycle {cycle_id} not found", "found": False}

    response: dict[str, Any] = {
        "found": True,
        "cycle": {
            "id": str(cycle.id),
            "name": cycle.name,
            "description": cycle.description,
            "start_date": cycle.start_date.isoformat() if cycle.start_date else None,
            "end_date": cycle.end_date.isoformat() if cycle.end_date else None,
            "status": cycle.status.value if cycle.status else None,
        },
    }

    if include_issues:
        issues = cycle.issues or []
        completed_count = sum(
            1 for i in issues if i.state and i.state.group and i.state.group.value == "completed"
        )
        response["metrics"] = {
            "total_issues": len(issues),
            "completed_issues": completed_count,
            "progress_percent": (completed_count / len(issues) * 100) if issues else 0,
        }
        response["issues"] = [
            {
                "id": str(i.id),
                "identifier": i.identifier,
                "title": i.name,
                "state": i.state.name if i.state else None,
            }
            for i in issues[:20]  # Limit to 20
        ]

    return response


@register_tool("database")
async def create_note_annotation(
    note_id: str,
    ctx: ToolContext,
    annotation_type: str,
    content: str,
    block_id: str | None = None,
    confidence: float = 0.8,
) -> dict[str, Any]:
    """Create AI annotation for a note.

    Adds an AI-generated suggestion to the note margin.
    This is an AUTO_EXECUTE action (DD-003) - no approval required.

    Args:
        note_id: UUID of the note
        ctx: Tool context with db_session
        annotation_type: Type (suggestion, warning, issue_candidate, info)
        content: Annotation content
        block_id: Optional block ID to attach annotation to
        confidence: Confidence score (0.0-1.0)

    Returns:
        Created annotation details
    """
    # Verify note exists and belongs to workspace
    note_query = select(Note).where(
        Note.id == UUID(note_id),
        Note.workspace_id == UUID(ctx.workspace_id),
    )
    result = await ctx.db_session.execute(note_query)
    note = result.scalar_one_or_none()

    if not note:
        return {"error": f"Note {note_id} not found", "created": False}

    # Validate annotation type
    try:
        ann_type = AnnotationType(annotation_type)
    except ValueError:
        valid_types = [t.value for t in AnnotationType]
        return {
            "error": f"Invalid annotation_type. Valid types: {valid_types}",
            "created": False,
        }

    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        return {
            "error": "Confidence must be between 0.0 and 1.0",
            "created": False,
        }

    annotation = NoteAnnotation(
        note_id=UUID(note_id),
        block_id=block_id if block_id else "",
        type=ann_type,
        content=content,
        status=AnnotationStatus.PENDING,
        confidence=confidence,
        workspace_id=UUID(ctx.workspace_id),
    )

    ctx.db_session.add(annotation)
    await ctx.db_session.commit()
    await ctx.db_session.refresh(annotation)

    return {
        "created": True,
        "annotation": {
            "id": str(annotation.id),
            "type": annotation_type,
            "content": content,
            "confidence": confidence,
            "status": "pending",
            "block_id": block_id,
        },
    }


@register_tool("database")
async def create_issue(
    project_id: str,
    title: str,
    ctx: ToolContext,
    description: str | None = None,
    priority: int = 2,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new issue from AI extraction.

    REQUIRES APPROVAL (DD-003: DEFAULT_REQUIRE_APPROVAL).
    Returns approval_required status. The orchestrator must
    handle the approval flow before actual creation.

    Args:
        project_id: UUID of the project
        title: Issue title
        ctx: Tool context with db_session
        description: Issue description
        priority: Priority level (0=urgent, 4=none, default 2=medium)
        labels: Optional label names to attach

    Returns:
        Approval request details (not the created issue)
    """
    # Verify project exists and belongs to workspace
    project_query = select(Project).where(
        Project.id == UUID(project_id),
        Project.workspace_id == UUID(ctx.workspace_id),
    )
    result = await ctx.db_session.execute(project_query)
    project = result.scalar_one_or_none()

    if not project:
        return {"error": f"Project {project_id} not found", "approval_required": False}

    # Validate priority
    if not 0 <= priority <= 4:
        return {
            "error": "Priority must be between 0 (urgent) and 4 (none)",
            "approval_required": False,
        }

    # This action requires approval - return payload for approval
    # The orchestrator/agent will create the approval request
    return {
        "approval_required": True,
        "action_type": "create_issue",
        "payload": {
            "project_id": project_id,
            "project_name": project.name,
            "title": title,
            "description": description,
            "priority": priority,
            "labels": labels or [],
        },
        "message": "Issue creation requires approval. Submit for review.",
    }
