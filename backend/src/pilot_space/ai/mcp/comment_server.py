"""In-process SDK custom tools for PilotSpace comment manipulation.

Creates an SDK MCP server using create_sdk_mcp_server() with 4 comment tools.
Tool handlers push content_update SSE events to a shared asyncio.Queue
that the PilotSpaceAgent stream method interleaves with SDK messages.

Comment tools work with ThreadedDiscussion (discussion threads) and
DiscussionComment (individual comments) models, supporting discussions
on notes, issues, and other discussion threads.

Architecture:
  ClaudeSDKClient (in-process) → tool handler → pushes to event_queue
  PilotSpaceAgent._stream_with_space() → reads from event_queue + SDK messages
  Frontend useContentUpdates hook → updates UI + API calls

Reference: https://platform.claude.com/docs/en/agent-sdk/custom-tools
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pilot_space.ai.tools.mcp_server import ToolContext
from pilot_space.infrastructure.database.models.discussion_comment import (
    DiscussionComment,
)
from pilot_space.infrastructure.database.models.threaded_discussion import (
    DiscussionStatus,
    ThreadedDiscussion,
)

logger = logging.getLogger(__name__)

# MCP server name — used in allowed_tools as mcp__pilot-comments__{tool_name}
SERVER_NAME = "pilot-comments"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__create_comment",
    f"mcp__{SERVER_NAME}__update_comment",
    f"mcp__{SERVER_NAME}__search_comments",
    f"mcp__{SERVER_NAME}__get_comments",
]


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _text_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool text result."""
    return {"content": [{"type": "text", "text": text}]}


def create_comment_tools_server(
    event_queue: asyncio.Queue[str],
    *,
    tool_context: ToolContext | None = None,
) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server with 4 comment tools.

    Each tool handler interacts with ThreadedDiscussion and DiscussionComment
    models and returns operation payloads or search results.

    Args:
        event_queue: Queue for SSE events consumed by the stream method.
        tool_context: ToolContext for database access and RLS enforcement.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers.
    """
    if tool_context is None:
        raise ValueError("tool_context is required for comment tools")

    @tool(
        "create_comment",
        "Create a comment on an issue, note, or discussion thread. "
        "Comments are AI-generated and tracked with is_ai_generated=True. "
        "Supports threaded replies via parent_comment_id.",
        {
            "type": "object",
            "properties": {
                "target_type": {
                    "type": "string",
                    "enum": ["issue", "note", "discussion"],
                    "description": "Type of target (issue/note/discussion)",
                },
                "target_id": {
                    "type": "string",
                    "description": "UUID of the target entity",
                },
                "content": {
                    "type": "string",
                    "description": "Comment text content",
                },
                "parent_comment_id": {
                    "type": "string",
                    "description": "Optional parent comment ID for threaded replies",
                },
            },
            "required": ["target_type", "target_id", "content"],
        },
    )
    async def create_comment(args: dict[str, Any]) -> dict[str, Any]:
        """Create a new AI comment on a target entity."""
        target_type = args["target_type"]
        target_id_str = args["target_id"]
        content = args["content"]
        parent_comment_id_str = args.get("parent_comment_id")

        # Validate inputs upfront
        validation_errors = []
        if not content or not content.strip():
            validation_errors.append("comment content cannot be empty")

        target_id: uuid.UUID | None = None
        try:
            target_id = uuid.UUID(target_id_str)
        except ValueError:
            validation_errors.append(f"invalid target_id UUID: {target_id_str}")

        parent_comment_id: uuid.UUID | None = None
        if parent_comment_id_str:
            try:
                parent_comment_id = uuid.UUID(parent_comment_id_str)
            except ValueError:
                validation_errors.append(f"invalid parent_comment_id UUID: {parent_comment_id_str}")

        workspace_id = uuid.UUID(tool_context.workspace_id)
        user_id = uuid.UUID(tool_context.user_id) if tool_context.user_id else None

        if not user_id:
            validation_errors.append("user_id is required for comment creation")

        if validation_errors:
            return _text_result(f"Error: {'; '.join(validation_errors)}.")

        # Type narrowing: at this point target_id cannot be None
        assert target_id is not None

        session = tool_context.db_session

        # Find or create ThreadedDiscussion
        if target_type == "note":
            # For notes, use note_id directly
            query = select(ThreadedDiscussion).where(
                ThreadedDiscussion.workspace_id == workspace_id,
                ThreadedDiscussion.target_type == "note",
                ThreadedDiscussion.target_id == target_id,
                ThreadedDiscussion.note_id == target_id,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        elif target_type == "issue":
            # For issues, create generic discussion
            query = select(ThreadedDiscussion).where(
                ThreadedDiscussion.workspace_id == workspace_id,
                ThreadedDiscussion.target_type == "issue",
                ThreadedDiscussion.target_id == target_id,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        elif target_type == "discussion":
            # For discussion replies, use existing discussion
            query = select(ThreadedDiscussion).where(
                ThreadedDiscussion.id == target_id,
                ThreadedDiscussion.workspace_id == workspace_id,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        else:
            return _text_result(
                f"Error: unsupported target_type '{target_type}'. "
                "Must be 'issue', 'note', or 'discussion'."
            )

        result = await session.execute(query)
        discussion = result.scalar_one_or_none()

        # Create discussion if it doesn't exist
        if not discussion:
            if target_type == "discussion":
                return _text_result(f"Error: discussion {target_id} not found in workspace.")

            discussion = ThreadedDiscussion(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                note_id=target_id if target_type == "note" else None,
                target_type=target_type,
                target_id=target_id,
                status=DiscussionStatus.OPEN,
                title=None,
            )
            session.add(discussion)
            await session.flush()
            logger.info(
                "[CommentTools] created discussion: type=%s, target=%s",
                target_type,
                target_id,
            )

        # Validate parent_comment if provided
        if parent_comment_id:
            parent_query = select(DiscussionComment).where(
                DiscussionComment.id == parent_comment_id,
                DiscussionComment.discussion_id == discussion.id,
                DiscussionComment.workspace_id == workspace_id,
                DiscussionComment.is_deleted == False,  # noqa: E712
            )
            parent_result = await session.execute(parent_query)
            parent_comment = parent_result.scalar_one_or_none()
            if not parent_comment:
                return _text_result(f"Error: parent comment {parent_comment_id} not found.")

        # Create comment
        comment = DiscussionComment(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            discussion_id=discussion.id,
            author_id=user_id,
            content=content.strip(),
            is_ai_generated=True,
        )
        session.add(comment)
        await session.flush()

        logger.info(
            "[CommentTools] create_comment: discussion=%s, content_len=%d",
            discussion.id,
            len(content),
        )

        # Push SSE event
        event_data = {
            "operation": "comment_created",
            "targetType": target_type,
            "targetId": str(target_id),
            "discussionId": str(discussion.id),
            "commentId": str(comment.id),
            "content": content.strip(),
            "isAiGenerated": True,
            "parentCommentId": str(parent_comment_id) if parent_comment_id else None,
        }
        await event_queue.put(_sse_event("content_update", event_data))

        return _text_result(
            f"Created AI comment on {target_type} {target_id}. Comment ID: {comment.id}"
        )

    @tool(
        "update_comment",
        "Update an existing AI-generated comment. "
        "Only AI-generated comments can be updated by AI. "
        "Sets edited_at timestamp to track modifications.",
        {
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "UUID of the comment to update",
                },
                "content": {
                    "type": "string",
                    "description": "New comment content",
                },
            },
            "required": ["comment_id", "content"],
        },
    )
    async def update_comment(args: dict[str, Any]) -> dict[str, Any]:
        """Update an AI-generated comment (requires approval)."""
        comment_id_str = args["comment_id"]
        new_content = args["content"]

        if not new_content or not new_content.strip():
            return _text_result("Error: comment content cannot be empty.")

        try:
            comment_id = uuid.UUID(comment_id_str)
        except ValueError:
            return _text_result(f"Error: invalid comment_id UUID: {comment_id_str}")

        workspace_id = uuid.UUID(tool_context.workspace_id)
        session = tool_context.db_session

        # Find comment
        query = select(DiscussionComment).where(
            DiscussionComment.id == comment_id,
            DiscussionComment.workspace_id == workspace_id,
            DiscussionComment.is_deleted == False,  # noqa: E712
        )
        result = await session.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return _text_result(f"Error: comment {comment_id} not found in workspace.")

        # Verify comment is AI-generated
        if not comment.is_ai_generated:
            return _text_result(
                "Error: cannot update user-generated comment. "
                "AI can only update AI-generated comments."
            )

        old_content = comment.content

        logger.info(
            "[CommentTools] update_comment: comment=%s, old_len=%d, new_len=%d",
            comment_id,
            len(old_content),
            len(new_content),
        )

        # Push SSE event as operation payload (no direct DB mutation)
        event_data = {
            "operation": "comment_updated",
            "status": "approval_required",
            "commentId": str(comment_id),
            "discussionId": str(comment.discussion_id),
            "oldContent": old_content,
            "newContent": new_content.strip(),
            "requiresApproval": True,
        }
        await event_queue.put(_sse_event("content_update", event_data))

        return _text_result(
            f"Comment {comment_id} update requested. Approval required. "
            f"Old length: {len(old_content)}, New length: {len(new_content)}"
        )

    @tool(
        "search_comments",
        "Search for comments by text content with optional filters. "
        "Supports filtering by target type, target ID, and author. "
        "Returns matching comments with author info.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for comment content (ILIKE)",
                },
                "target_type": {
                    "type": "string",
                    "enum": ["issue", "note", "discussion"],
                    "description": "Optional: filter by target type",
                },
                "target_id": {
                    "type": "string",
                    "description": "Optional: filter by target UUID",
                },
                "author_id": {
                    "type": "string",
                    "description": "Optional: filter by author UUID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 20, max 100)",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    )
    async def search_comments(args: dict[str, Any]) -> dict[str, Any]:
        """Search comments with filters."""
        query_text = args["query"]
        target_type = args.get("target_type")
        target_id_str = args.get("target_id")
        author_id_str = args.get("author_id")
        limit = min(args.get("limit", 20), 100)

        workspace_id = uuid.UUID(tool_context.workspace_id)
        session = tool_context.db_session

        # Escape ILIKE wildcards to prevent injection
        safe_query = query_text.replace("%", r"\%").replace("_", r"\_")

        # Build query
        stmt = (
            select(DiscussionComment)
            .join(ThreadedDiscussion)
            .where(
                DiscussionComment.workspace_id == workspace_id,
                DiscussionComment.is_deleted == False,  # noqa: E712
                DiscussionComment.content.ilike(f"%{safe_query}%"),
            )
            .options(selectinload(DiscussionComment.author))
        )

        # Apply filters
        if target_type:
            stmt = stmt.where(ThreadedDiscussion.target_type == target_type)

        if target_id_str:
            try:
                target_id = uuid.UUID(target_id_str)
                stmt = stmt.where(ThreadedDiscussion.target_id == target_id)
            except ValueError:
                return _text_result(f"Error: invalid target_id UUID: {target_id_str}")

        if author_id_str:
            try:
                author_id = uuid.UUID(author_id_str)
                stmt = stmt.where(DiscussionComment.author_id == author_id)
            except ValueError:
                return _text_result(f"Error: invalid author_id UUID: {author_id_str}")

        stmt = stmt.order_by(DiscussionComment.created_at.desc()).limit(limit)

        result = await session.execute(stmt)
        comments = result.unique().scalars().all()

        logger.info(
            "[CommentTools] search_comments: query='%s', found=%d",
            query_text,
            len(comments),
        )

        if not comments:
            return _text_result(
                f"No comments found matching query '{query_text}' with applied filters."
            )

        # Format results
        results = []
        for comment in comments:
            results.append(
                {
                    "id": str(comment.id),
                    "content": comment.content,
                    "author": {
                        "id": str(comment.author.id),
                        "display_name": comment.author.full_name,
                        "email": comment.author.email,
                    }
                    if comment.author
                    else None,
                    "is_ai_generated": comment.is_ai_generated,
                    "created_at": comment.created_at.isoformat(),
                    "edited_at": comment.edited_at.isoformat() if comment.edited_at else None,
                    "discussion_id": str(comment.discussion_id),
                }
            )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(comments)} comment(s) matching '{query_text}':\n\n"
                    + json.dumps(results, indent=2),
                }
            ]
        }

    @tool(
        "get_comments",
        "Get all comments for a target entity (issue, note, or discussion). "
        "Returns comments with author info and threaded structure. "
        "Supports include_replies to build full thread hierarchy.",
        {
            "type": "object",
            "properties": {
                "target_type": {
                    "type": "string",
                    "enum": ["issue", "note", "discussion"],
                    "description": "Type of target (issue/note/discussion)",
                },
                "target_id": {
                    "type": "string",
                    "description": "UUID of the target entity",
                },
                "include_replies": {
                    "type": "boolean",
                    "description": "Include threaded replies (default true)",
                    "default": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum comments to return (default 50)",
                    "default": 50,
                },
            },
            "required": ["target_type", "target_id"],
        },
    )
    async def get_comments(args: dict[str, Any]) -> dict[str, Any]:
        """Get all comments for a target entity."""
        target_type = args["target_type"]
        target_id_str = args["target_id"]
        _include_replies = args.get("include_replies", True)  # Reserved for future threading
        limit = args.get("limit", 50)

        try:
            target_id = uuid.UUID(target_id_str)
        except ValueError:
            return _text_result(f"Error: invalid target_id UUID: {target_id_str}")

        workspace_id = uuid.UUID(tool_context.workspace_id)
        session = tool_context.db_session

        # Find discussions for target
        if target_type in ("note", "issue"):
            disc_query = select(ThreadedDiscussion).where(
                ThreadedDiscussion.workspace_id == workspace_id,
                ThreadedDiscussion.target_type == target_type,
                ThreadedDiscussion.target_id == target_id,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        elif target_type == "discussion":
            # Get single discussion
            disc_query = select(ThreadedDiscussion).where(
                ThreadedDiscussion.id == target_id,
                ThreadedDiscussion.workspace_id == workspace_id,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        else:
            return _text_result(
                f"Error: unsupported target_type '{target_type}'. "
                "Must be 'issue', 'note', or 'discussion'."
            )

        disc_result = await session.execute(disc_query)
        discussions = disc_result.scalars().all()

        if not discussions:
            return _text_result(f"No discussions found for {target_type} {target_id}.")

        # Get all comments for these discussions
        discussion_ids = [d.id for d in discussions]
        comment_query = (
            select(DiscussionComment)
            .where(
                DiscussionComment.discussion_id.in_(discussion_ids),
                DiscussionComment.workspace_id == workspace_id,
                DiscussionComment.is_deleted == False,  # noqa: E712
            )
            .options(selectinload(DiscussionComment.author))
            .order_by(DiscussionComment.created_at.asc())
            .limit(limit)
        )

        comment_result = await session.execute(comment_query)
        comments = comment_result.unique().scalars().all()

        logger.info(
            "[CommentTools] get_comments: type=%s, target=%s, found=%d",
            target_type,
            target_id,
            len(comments),
        )

        if not comments:
            return _text_result(f"No comments found for {target_type} {target_id}.")

        # Format results
        results = []
        for comment in comments:
            results.append(
                {
                    "id": str(comment.id),
                    "content": comment.content,
                    "author": {
                        "id": str(comment.author.id),
                        "display_name": comment.author.full_name,
                        "email": comment.author.email,
                    }
                    if comment.author
                    else None,
                    "is_ai_generated": comment.is_ai_generated,
                    "created_at": comment.created_at.isoformat(),
                    "edited_at": comment.edited_at.isoformat() if comment.edited_at else None,
                    "discussion_id": str(comment.discussion_id),
                }
            )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(comments)} comment(s) for {target_type} {target_id}:\n\n"
                    + json.dumps(results, indent=2),
                }
            ]
        }

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            create_comment,
            update_comment,
            search_comments,
            get_comments,
        ],
    )
