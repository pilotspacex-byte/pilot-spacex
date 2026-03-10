"""Stream utility functions for PilotSpaceAgent.

Extracted from pilotspace_agent.py for file size compliance.
Contains SSE content capture, structured content building,
effort classification, skill detection, token estimation,
MCP server factory, concurrent SDK+queue stream merging,
and dynamic system prompt assembly.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpServerConfig
from claude_agent_sdk._internal import message_parser as _sdk_parser

from pilot_space.ai.mcp.comment_server import (
    SERVER_NAME as COMMENT_SERVER_NAME,
    create_comment_tools_server,
)
from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.mcp.interaction_server import (
    SERVER_NAME as INTERACTION_SERVER_NAME,
    create_interaction_server,
)
from pilot_space.ai.mcp.issue_relation_server import (
    SERVER_NAME as ISSUE_REL_SERVER_NAME,
    create_issue_relation_tools_server,
)
from pilot_space.ai.mcp.issue_server import (
    SERVER_NAME as ISSUE_SERVER_NAME,
    create_issue_tools_server,
)
from pilot_space.ai.mcp.note_content_server import (
    SERVER_NAME as NOTE_CONTENT_SERVER_NAME,
    create_note_content_server,
)
from pilot_space.ai.mcp.note_query_server import (
    SERVER_NAME as NOTE_QUERY_SERVER_NAME,
    create_note_query_server,
)
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME as NOTE_SERVER_NAME,
    create_note_tools_server,
)
from pilot_space.ai.mcp.project_server import (
    SERVER_NAME as PROJECT_SERVER_NAME,
    create_project_tools_server,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.agents.pilotspace_agent import ChatInput
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap
    from pilot_space.ai.tools.mcp_server import ToolContext

logger = get_logger(__name__)

_original_parse_message = _sdk_parser.parse_message


def _patched_parse_message(data: dict[str, Any]) -> Any:
    """Wrap SDK parse_message to tolerate missing 'signature' in thinking blocks."""
    if data.get("type") == "assistant":
        for block in data.get("message", {}).get("content", []):
            if block.get("type") == "thinking" and "signature" not in block:
                block["signature"] = ""
    return _original_parse_message(data)


_sdk_parser.parse_message = _patched_parse_message  # type: ignore[assignment]


def build_mcp_servers(
    tool_event_queue: asyncio.Queue[str],
    tool_context: ToolContext,
    input_data: ChatInput,
) -> tuple[dict[str, McpServerConfig], BlockRefMap | None]:
    """Build the MCP server dict and block-reference map for an SDK session.

    Constructs a ¶N block reference map from the note context (if present)
    and instantiates all 8 MCP tool servers (7 domain + 1 interaction).

    Returns:
        Tuple of (mcp_servers dict keyed by server name, block_ref_map or None).
    """
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap

    _note_obj = input_data.context.get("note")
    _note_raw = getattr(_note_obj, "content", {}) if _note_obj else {}
    ref_map: BlockRefMap | None = BlockRefMap.from_tiptap(_note_raw) if _note_raw else None
    if ref_map is not None and ref_map.is_empty:
        ref_map = None

    context_note_id = input_data.context.get("note_id")

    publisher = EventPublisher(tool_event_queue)

    servers: dict[str, McpServerConfig] = {
        NOTE_SERVER_NAME: create_note_tools_server(
            publisher,
            context_note_id=str(context_note_id) if context_note_id else None,
            tool_context=tool_context,
            block_ref_map=ref_map,
        ),
        NOTE_QUERY_SERVER_NAME: create_note_query_server(
            tool_context=tool_context,
        ),
        NOTE_CONTENT_SERVER_NAME: create_note_content_server(
            publisher,
            tool_context=tool_context,
            block_ref_map=ref_map,
        ),
        ISSUE_SERVER_NAME: create_issue_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        ISSUE_REL_SERVER_NAME: create_issue_relation_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        PROJECT_SERVER_NAME: create_project_tools_server(
            publisher=publisher,
            tool_context=tool_context,
        ),
        COMMENT_SERVER_NAME: create_comment_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        INTERACTION_SERVER_NAME: create_interaction_server(
            publisher,
            user_id=input_data.user_id,
        ),
    }

    return servers, ref_map


_SIMPLE_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay)\b"),
    re.compile(r"^what (can you|do you) do"),
    re.compile(r"^help\b"),
    re.compile(r"^(yes|no|sure|yep|nope)\b"),
]
_COMPLEX_PATTERNS = [
    re.compile(r"\b(analy[sz]e|audit|review|refactor|architect)\b"),
    re.compile(r"\b(compare|contrast|evaluate|assess)\b"),
    re.compile(r"\b(explain.{0,20}(in detail|thoroughly|step by step))\b"),
    re.compile(r"\b(design|implement|migrate|optimize)\b"),
    re.compile(r"\b(security|vulnerability|performance)\s+(review|audit|check)\b"),
]


def classify_effort(message: str) -> str | None:
    """Return 'low' for greetings, 'high' for complex queries, None for default."""
    msg_lower = message.strip().lower()
    if len(msg_lower) < 50:
        for p in _SIMPLE_PATTERNS:
            if p.match(msg_lower):
                return "low"
    if len(msg_lower) > 200:
        return "high"
    for p in _COMPLEX_PATTERNS:
        if p.search(msg_lower):
            return "high"
    return None


def detect_skill_from_message(message: str) -> str | None:
    """Detect slash-command skill invocation, returning skill name or None."""
    msg_stripped = message.strip()
    if msg_stripped.startswith("/"):
        parts = msg_stripped[1:].split(None, 1)
        return parts[0] if parts else None
    return None


def estimate_tokens(input_data: ChatInput) -> int:
    """Rough token estimate (~4 chars/token) for context size detection (T62)."""
    total_chars = len(input_data.message)
    total_chars += sum(len(str(v)) for v in input_data.context.values())
    return total_chars // 4


def capture_content_from_sse(
    sse_event: str,
    content_blocks: dict[str, dict[str, Any]],
    *,
    max_blocks: int = 500,
) -> None:
    """Capture structured content from SSE events for session persistence.

    Extracts text_delta, thinking_delta, tool_use, and tool_result events
    and accumulates them into content_blocks dictionary.

    Args:
        sse_event: SSE-formatted event string (may contain multiple events)
        content_blocks: Mutable dict to accumulate content by block key
        max_blocks: Safety cap to prevent unbounded memory growth.
    """
    for event_line in sse_event.split("\n\n"):
        if len(content_blocks) >= max_blocks:
            return
        if not event_line.strip():
            continue

        lines = event_line.split("\n")
        event_type = ""
        data_str = ""

        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]

        if not event_type or not data_str:
            continue

        try:
            data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            continue

        block_idx = data.get("blockIndex", 0)

        if event_type == "text_delta":
            key = f"text_{block_idx}"
            if key not in content_blocks:
                content_blocks[key] = {"type": "text", "text": "", "index": block_idx}
            content_blocks[key]["text"] += data.get("delta", "")

        elif event_type == "thinking_delta":
            key = f"thinking_{block_idx}"
            if key not in content_blocks:
                content_blocks[key] = {"type": "thinking", "thinking": "", "index": block_idx}
            content_blocks[key]["thinking"] += data.get("delta", "")
            if "signature" in data:
                content_blocks[key]["signature"] = data["signature"]

        elif event_type == "tool_use":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_use_{tool_id}"
                content_blocks[key] = {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": data.get("toolName", ""),
                    "input": data.get("toolInput", {}),
                    "index": len(content_blocks),
                }
                logger.debug(
                    "content_capture_tool_use",
                    tool_name=data.get("toolName", ""),
                    tool_id=tool_id,
                    total_blocks=len(content_blocks),
                )

        elif event_type == "tool_result":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_result_{tool_id}"
                is_error = data.get("status") == "failed"
                content_blocks[key] = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": data.get("output", data.get("errorMessage", "")),
                    "is_error": is_error,
                    "index": len(content_blocks),
                }
                logger.debug(
                    "content_capture_tool_result",
                    tool_id=tool_id,
                    is_error=is_error,
                    total_blocks=len(content_blocks),
                )


def build_structured_content(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | str:
    """Build structured content list from captured blocks.

    Sorts blocks by their index and returns as a list of content blocks
    in Claude message format. Falls back to plain text if only text content.

    Args:
        content_blocks: Dict of captured content blocks

    Returns:
        List of content block dicts, or plain text string if only text
    """
    if not content_blocks:
        return ""

    sorted_blocks = sorted(
        content_blocks.values(),
        key=lambda b: b.get("index", 0),
    )

    has_non_text = any(b["type"] in ("thinking", "tool_use", "tool_result") for b in sorted_blocks)

    if not has_non_text:
        text_parts = [b.get("text", "") for b in sorted_blocks if b["type"] == "text"]
        return "".join(text_parts)

    result: list[dict[str, Any]] = []
    for block in sorted_blocks:
        clean_block = {k: v for k, v in block.items() if k != "index"}
        # Drop thinking blocks without signatures — they cause
        # "Missing required field: 'signature'" on session resume
        if clean_block.get("type") == "thinking" and "signature" not in clean_block:
            continue
        result.append(clean_block)

    return result


def extract_question_data_from_blocks(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Extract question_data from content_blocks if ask_user questions are pending.

    Scans tool_result blocks for ask_user pending_answer results, extracts
    the questionIds, and looks up the full question data from QuestionAdapter.
    Supports multiple ask_user calls in a single turn.

    Args:
        content_blocks: Dict of captured content blocks from the stream.

    Returns:
        List of question_data dicts [{questionId, questions}, ...] if found, None otherwise.
    """
    from uuid import UUID

    from pilot_space.ai.sdk.question_adapter import get_question_adapter

    results: list[dict[str, Any]] = []

    for block in content_blocks.values():
        if block.get("type") != "tool_result":
            continue

        content = block.get("content", "")

        # Content may be a dict (from SSE capture) or a JSON string
        parsed: dict[str, Any] | None = None
        if isinstance(content, dict):
            parsed = content
        elif isinstance(content, str) and "pending_answer" in content:
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            continue

        if not parsed or parsed.get("status") != "pending_answer":
            continue
        question_id_str = parsed.get("questionId")
        if not question_id_str:
            continue

        try:
            question_id = UUID(question_id_str)
        except ValueError:
            continue

        adapter = get_question_adapter()
        pending = adapter.get_question(question_id)
        if pending is None:
            continue

        results.append(
            {
                "questionId": str(question_id),
                "questions": [q.model_dump() for q in pending.questions],
            }
        )

    return results if results else None


def extract_tool_calls_from_blocks(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Extract structured tool call records from content_blocks for session persistence.

    Pairs tool_use and tool_result blocks by tool call ID to build
    a complete list of tool call records with name, input, output, and status.

    Args:
        content_blocks: Dict of captured content blocks from the stream.

    Returns:
        List of tool call dicts [{id, name, input, output, status}, ...] or None.
    """
    # Collect tool_use entries keyed by tool call ID
    tool_uses: dict[str, dict[str, Any]] = {}
    for block in content_blocks.values():
        if block.get("type") == "tool_use":
            tid = block.get("id", "")
            if tid:
                tool_uses[tid] = block

    if not tool_uses:
        return None

    # Build tool call records by pairing with tool_result blocks
    results: list[dict[str, Any]] = []
    for tid, use_block in tool_uses.items():
        result_key = f"tool_result_{tid}"
        result_block = content_blocks.get(result_key)

        record: dict[str, Any] = {
            "id": tid,
            "name": use_block.get("name", ""),
            "input": use_block.get("input", {}),
        }

        if result_block:
            is_error = result_block.get("is_error", False)
            record["status"] = "failed" if is_error else "completed"
            record["output"] = result_block.get("content", "")
            if is_error:
                record["error_message"] = result_block.get("content", "")
        else:
            record["status"] = "pending"

        results.append(record)

    return results if results else None


# ---------------------------------------------------------------------------
# Concurrent SDK + Queue stream merge
# ---------------------------------------------------------------------------

# Sentinel used to signal the SDK iterator is exhausted.
_SDK_DONE = object()


async def _feed_sdk(sdk_iter: AsyncIterator[Any], out: asyncio.Queue[Any]) -> None:
    """Drain *sdk_iter* into *out*, appending _SDK_DONE when finished."""
    try:
        async for msg in sdk_iter:
            await out.put(msg)
    except Exception as exc:
        logger.error("[StreamMerge] SDK feed error: %s", exc, exc_info=True)
    finally:
        await out.put(_SDK_DONE)


async def merge_sdk_and_queue(
    sdk_iter: AsyncIterator[Any],
    tool_queue: asyncio.Queue[str],
) -> AsyncIterator[tuple[str, Any]]:
    """Yield items from both the SDK response stream and tool_event_queue.

    Produces ``("sdk", message)`` for SDK messages and ``("queue", event)``
    for tool-queue events (e.g. ``approval_request`` SSE strings).

    A background task feeds the SDK iterator into an internal queue so both
    sources can be awaited concurrently with ``asyncio.wait``.  This prevents
    the deadlock where a blocking PreToolUse hook (``wait_for_approval``)
    stops the SDK from producing messages, which in turn prevents the main
    stream loop from draining the tool_event_queue.

    The generator finishes when the SDK iterator is exhausted.  Any remaining
    tool_queue items should be drained by the caller after this returns.
    """
    sdk_queue: asyncio.Queue[Any] = asyncio.Queue()
    feeder = asyncio.create_task(_feed_sdk(sdk_iter, sdk_queue))

    sdk_task: asyncio.Task[Any] | None = None
    queue_task: asyncio.Task[str] | None = None

    try:
        while True:
            if sdk_task is None:
                sdk_task = asyncio.create_task(sdk_queue.get())
            if queue_task is None:
                queue_task = asyncio.create_task(tool_queue.get())

            done, _ = await asyncio.wait(
                {sdk_task, queue_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if task is sdk_task:
                    item = task.result()
                    sdk_task = None
                    if item is _SDK_DONE:
                        return  # SDK stream finished
                    yield ("sdk", item)
                elif task is queue_task:
                    yield ("queue", task.result())
                    queue_task = None
    finally:
        # Cancel any pending tasks
        for task in (sdk_task, queue_task):
            if task is not None and not task.done():
                task.cancel()
        feeder.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await feeder


async def save_session_messages(
    *,
    session_handler: Any,
    session_id: Any,
    message: str,
    content_blocks: dict[str, dict[str, Any]],
) -> None:
    """Persist user + assistant messages to session store.

    Extracted from PilotSpaceAgent._stream_with_space finally block (T-016).

    Args:
        session_handler: SessionHandler instance (or None).
        session_id: Session UUID (or None — no-ops if falsy).
        message: Original user message content.
        content_blocks: Accumulated content blocks from the stream.
    """
    if not (session_handler and session_id):
        return

    try:
        await session_handler.add_message(
            session_id=session_id,
            role="user",
            content=message,
        )
        structured_content = build_structured_content(content_blocks)
        if structured_content:
            question_data = extract_question_data_from_blocks(content_blocks)
            tool_calls = extract_tool_calls_from_blocks(content_blocks)
            await session_handler.add_message(
                session_id=session_id,
                role="assistant",
                content=structured_content,
                question_data=question_data,
                tool_calls=tool_calls,
            )
        logger.debug(
            "[SDK/Space] Persisted messages to session %s (%d blocks)",
            session_id,
            len(content_blocks),
        )
    except Exception as exc:
        logger.warning(
            "[SDK/Space] Failed to persist session messages: %s",
            exc,
        )


def build_graph_search_service_for_session(
    db_session: Any, openai_api_key: str | None = None
) -> Any:
    """Build a fresh GraphSearchService bound to the active request DB session.

    Called once per request inside _build_stream_config to avoid the
    session=None singleton-capture bug.

    Args:
        db_session: Active async DB session for the current request.
        openai_api_key: Optional workspace BYOK OpenAI key for embeddings.
    """
    from pilot_space.application.services.embedding_service import EmbeddingConfig, EmbeddingService
    from pilot_space.application.services.memory.graph_search_service import GraphSearchService
    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )

    embedding_service = EmbeddingService(EmbeddingConfig(openai_api_key=openai_api_key))
    return GraphSearchService(
        knowledge_graph_repository=KnowledgeGraphRepository(db_session),
        embedding_service=embedding_service,
    )


def build_graph_write_service_for_session(db_session: Any, queue_client: Any) -> Any:
    """Build a fresh GraphWriteService bound to the active request DB session.

    queue_client may be None; node upsert still occurs, only embedding enqueue is skipped.
    """
    from pilot_space.application.services.memory.graph_write_service import GraphWriteService
    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )

    return GraphWriteService(
        knowledge_graph_repository=KnowledgeGraphRepository(db_session),
        queue=queue_client,
        session=db_session,
    )


async def get_workspace_openai_key(db_session: Any, workspace_id: Any) -> str | None:
    """Look up the workspace BYOK OpenAI API key, returning None on any failure."""
    try:
        from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
        from pilot_space.config import get_settings

        storage = SecureKeyStorage(
            db=db_session,
            master_secret=get_settings().encryption_key.get_secret_value(),
        )
        return await storage.get_api_key(workspace_id, "openai")
    except Exception:
        return None


async def _load_remote_mcp_servers(  # pyright: ignore[reportUnusedFunction]
    workspace_id: UUID | None,
    db_session: AsyncSession | None,
) -> dict[str, McpServerConfig]:
    """Load registered remote MCP servers for workspace (MCP-04).

    Called from PilotSpaceAgent.stream() before build_mcp_servers() to fetch
    workspace-registered remote servers and construct McpSSEServerConfig entries.
    Uses lazy imports to avoid circular dependencies.

    Returns empty dict if workspace_id or db_session is None.
    Silently skips servers with corrupt/undecodable tokens (logs WARNING).

    Args:
        workspace_id: Workspace UUID, or None for non-workspace (CLI/anonymous) requests.
        db_session: Active async DB session, or None if not available.

    Returns:
        Dict keyed by "remote_{server.id}" with McpSSEServerConfig values.
    """
    if workspace_id is None or db_session is None:
        return {}

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    repo = WorkspaceMcpServerRepository(session=db_session)
    registered = await repo.get_active_by_workspace(workspace_id)
    remote: dict[str, McpServerConfig] = {}

    for server in registered:
        token: str | None = None
        if server.auth_token_encrypted:
            try:
                token = decrypt_api_key(server.auth_token_encrypted)
            except Exception:
                logger.warning(
                    "mcp_token_decrypt_failed",
                    server_id=str(server.id),
                    workspace_id=str(workspace_id),
                )
                continue

        if token:
            config: McpServerConfig = {  # type: ignore[typeddict-item]
                "type": "sse",
                "url": server.url,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        else:
            config = {"type": "sse", "url": server.url}  # type: ignore[typeddict-item]

        remote[f"remote_{server.id}"] = config

    return remote
