"""MCP tools for note content manipulation and issue extraction.

These tools are called by the Claude SDK during AI agent conversations
to manipulate note content and create/link issues. They return structured
dicts that the SSE transform layer will use to execute actual operations.

The tools don't directly modify the database - they return operation payloads
that the transform layer (Task 5) will execute using NoteAIUpdateService.

Reference: Task 4 - Register 6 MCP Tools for Note/Issue Operations
"""

from __future__ import annotations

from typing import Any

from pilot_space.ai.tools.mcp_server import register_tool


@register_tool("note")
async def update_note_block(
    note_id: str,
    block_id: str,
    new_content_markdown: str,
    operation: str = "replace",
) -> dict[str, Any]:
    """Update a specific block in a note with new markdown content.

    The markdown is converted to TipTap JSON and applied to the note.
    Returns the affected block IDs and operation status.

    This tool is called by the AI agent when it needs to modify note content
    during a conversation. The actual DB update happens in the transform layer.

    Args:
        note_id: UUID of the note to update.
        block_id: ID of the block to update.
        new_content_markdown: New content as markdown.
        operation: Operation type - "replace" or "append" (default: "replace").

    Returns:
        Dict with operation details for the transform layer.
    """
    if operation not in {"replace", "append"}:
        return {
            "error": f"Invalid operation: {operation}. Must be 'replace' or 'append'.",
            "status": "error",
        }

    # Map operation to AIUpdateOperation enum values
    ai_operation = "replace_block" if operation == "replace" else "append_blocks"

    return {
        "tool": "update_note_block",
        "note_id": note_id,
        "operation": ai_operation,
        "block_id": block_id,
        "markdown": new_content_markdown,
        "status": "pending_apply",
    }


@register_tool("note")
async def enhance_text(
    note_id: str,
    block_id: str,
    enhanced_markdown: str,
) -> dict[str, Any]:
    """Replace a block's content with an enhanced/improved version.

    Use this when the user asks to improve, rewrite, or enhance text.
    This is a specialized version of update_note_block for clarity.

    Args:
        note_id: UUID of the note to update.
        block_id: ID of the block to enhance.
        enhanced_markdown: Enhanced content as markdown.

    Returns:
        Dict with operation details for the transform layer.
    """
    return {
        "tool": "enhance_text",
        "note_id": note_id,
        "operation": "replace_block",
        "block_id": block_id,
        "markdown": enhanced_markdown,
        "status": "pending_apply",
    }


@register_tool("note")
async def extract_issues(
    note_id: str,
    block_ids: list[str],
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    """Create issues from note content and link them to the note.

    Each issue is created with a NoteIssueLink of type EXTRACTED.
    Returns created issue data for inline node insertion.

    The actual issue creation and linking happens in the transform layer.

    Args:
        note_id: UUID of the note to extract issues from.
        block_ids: List of block IDs where issues were identified.
        issues: List of issue data dicts with title, description, priority, type.

    Returns:
        Dict with issue extraction operation details.
    """
    # Apply defaults to issues that don't have all fields
    normalized_issues = []
    for issue in issues:
        normalized = {
            "title": issue.get("title", "Untitled Issue"),
            "description": issue.get("description", ""),
            "priority": issue.get("priority", "medium"),
            "type": issue.get("type", "task"),
        }
        normalized_issues.append(normalized)

    return {
        "tool": "extract_issues",
        "note_id": note_id,
        "operation": "create_issues",
        "block_ids": block_ids,
        "issues": normalized_issues,
        "link_type": "extracted",
        "status": "pending_apply",
    }


@register_tool("issue")
async def create_issue_from_note(
    note_id: str,
    block_id: str,
    title: str,
    description: str,
    priority: str = "medium",
    issue_type: str = "task",
) -> dict[str, Any]:
    """Create a single issue linked to a specific note block.

    Creates the issue, creates a NoteIssueLink, and returns
    issue data for inline node insertion.

    The actual creation happens in the transform layer.

    Args:
        note_id: UUID of the note.
        block_id: ID of the block to link.
        title: Issue title.
        description: Issue description.
        priority: Priority level (default: "medium").
        issue_type: Issue type (default: "task").

    Returns:
        Dict with issue creation operation details.
    """
    return {
        "tool": "create_issue_from_note",
        "note_id": note_id,
        "operation": "create_single_issue",
        "block_id": block_id,
        "issue": {
            "title": title,
            "description": description,
            "priority": priority,
            "type": issue_type,
        },
        "link_type": "extracted",
        "status": "pending_apply",
    }


@register_tool("note")
async def link_existing_issues(
    note_id: str,
    search_query: str,
    workspace_id: str,
) -> dict[str, Any]:
    """Search for existing issues and link them to the note.

    Searches workspace issues by query, returns matches
    with relevance info for the user to review.

    The actual search and linking happens in the transform layer.

    Args:
        note_id: UUID of the note.
        search_query: Search query to find relevant issues.
        workspace_id: UUID of the workspace to search within.

    Returns:
        Dict with issue search operation details.
    """
    return {
        "tool": "link_existing_issues",
        "note_id": note_id,
        "operation": "search_issues",
        "search_query": search_query,
        "workspace_id": workspace_id,
        "status": "pending_apply",
    }
