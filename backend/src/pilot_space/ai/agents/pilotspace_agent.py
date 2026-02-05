"""PilotSpace Agent - Centralized orchestrator routing to skills, subagents, or direct responses."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, Message

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.agents.note_space_sync import NoteSpaceSync
from pilot_space.ai.agents.pilotspace_agent_helpers import (
    build_contextual_message,
    build_subagent_definitions,
    transform_sdk_message as transform_sdk_message_helper,
)
from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME as NOTE_SERVER_NAME,
    TOOL_NAMES as NOTE_TOOL_NAMES,
    create_note_tools_server,
)
from pilot_space.ai.sdk.sandbox_config import ModelTier, configure_sdk_for_space
from pilot_space.spaces.manager import SpaceManager

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk.permission_handler import PermissionHandler
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.ai.sdk.skill_registry import SkillRegistry
    from pilot_space.ai.tools.mcp_server import ToolRegistry


logger = logging.getLogger(__name__)


@dataclass
class ChatInput:
    """Input for PilotSpace conversational agent."""

    message: str
    session_id: UUID | None = None
    resume_session_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    workspace_id: UUID | None = None


@dataclass
class ChatOutput:
    """Output from PilotSpace conversational agent."""

    response: str
    session_id: UUID
    tasks: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PilotSpaceAgent(StreamingSDKBaseAgent[ChatInput, ChatOutput]):
    """Main orchestrator agent — routes to skills, subagents, or direct responses."""

    AGENT_NAME = "pilotspace_agent"
    DEFAULT_MODEL_TIER: ClassVar[ModelTier] = ModelTier.SONNET

    SYSTEM_PROMPT_BASE: ClassVar[str] = (
        "You are PilotSpace AI, an embedded assistant in a Note-First SDLC platform. "
        "You help teams capture ideas in notes, extract issues, review PRs, and manage workflows.\n\n"
        "## Note writing vs. chat response\n"
        "- <note_context> present + user asks to write/draft/document/add content → "
        "use `write_to_note`, then summarize in chat.\n"
        "- Questions, analysis, or conversation → respond in chat only.\n\n"
        "## MCP note tools\n"
        "- `write_to_note`: Append markdown to end of note (no block_id needed).\n"
        "- `update_note_block`: Replace/append at a specific block (requires block_id).\n"
        "- `enhance_text`: Improve block clarity (requires block_id).\n"
        "- `summarize_note`: Read note (already in <note_context>).\n"
        "- `extract_issues`, `create_issue_from_note`, `link_existing_issues`: Issue tools.\n\n"
        "Subagents: pr-review, ai-context, doc-generator.\n"
        "Return operation payloads; never mutate DB directly. "
        "Destructive actions always require human approval."
    )

    SUBAGENT_MAP: ClassVar[dict[str, str]] = {
        "pr-review": "PRReviewSubagent",
        "ai-context": "AIContextSubagent",
        "doc-gen": "DocGeneratorSubagent",
    }

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        permission_handler: PermissionHandler,
        session_handler: SessionHandler | None,
        skill_registry: SkillRegistry,
        space_manager: SpaceManager | None = None,
        subagents: dict[str, Any] | None = None,
        key_storage: SecureKeyStorage | None = None,
    ) -> None:
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._permission_handler = permission_handler
        self._session_handler = session_handler
        self._skill_registry = skill_registry
        self._space_manager = space_manager
        self._subagents = subagents or {}
        self._key_storage = key_storage
        self._message_id_holder: dict[str, str | None] = {"_current_message_id": None}
        self._active_clients: dict[str, ClaudeSDKClient] = {}

    def _build_subagent_definitions(self) -> dict[str, AgentDefinition]:
        return build_subagent_definitions()

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        """Get API key from Vault (per-workspace BYOK) or ANTHROPIC_API_KEY env var."""
        if workspace_id and self._key_storage:
            try:
                key = await self._key_storage.get_api_key(workspace_id, "anthropic")
                if key:
                    return key
            except Exception as e:
                logger.warning(
                    "Vault lookup failed for workspace %s: %s. Falling back to env var",
                    workspace_id,
                    str(e),
                    exc_info=True,
                )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "Anthropic API key not found. Configure in workspace settings or set ANTHROPIC_API_KEY."
            raise ValueError(msg)
        return api_key

    async def interrupt_session(self, session_id: str) -> bool:
        """Interrupt active SDK client for a given session. Returns True if sent."""
        client = self._active_clients.get(session_id)
        if not client:
            logger.debug("[SDK/Interrupt] No active client for session %s", session_id)
            return False

        try:
            await asyncio.wait_for(client.interrupt(), timeout=3.0)
            logger.info("[SDK/Interrupt] Interrupted session %s", session_id)
            return True
        except (TimeoutError, Exception) as e:
            logger.warning(
                "[SDK/Interrupt] Failed to interrupt session %s: %s",
                session_id,
                e,
            )
            return False

    async def submit_tool_result(
        self,
        session_id: str,
        tool_call_id: str,
        result: str,
    ) -> None:
        """Submit user answer for AskUserQuestion tool call via follow-up query."""
        client = self._active_clients.get(session_id)
        if not client:
            raise ValueError(f"No active client for session {session_id}")

        answer_msg = f"[Answer to question {tool_call_id}]: {result}"
        await client.query(answer_msg, session_id=session_id)
        logger.info("[SDK/Answer] tool_call=%s session=%s", tool_call_id, session_id)

    def transform_sdk_message(
        self,
        message: Message,
        context: AgentContext,
        delta_buffer: DeltaBuffer | None = None,
        session_id: str | None = None,
    ) -> str | None:
        """Transform SDK message to SSE event string, or None to skip."""
        return transform_sdk_message_helper(
            message,
            self._message_id_holder,
            delta_buffer,
            app_session_id=session_id,
        )

    async def _sync_note_if_present(
        self,
        input_data: ChatInput,
        space_path: Path,
    ) -> None:
        """Sync note content from DB to workspace file if note context is present."""
        note = input_data.context.get("note")
        if note is None:
            return

        note_id = getattr(note, "id", None)
        if note_id is None:
            logger.warning("[NoteSync] Note object missing 'id' attribute, skipping sync")
            return

        try:
            from pilot_space.infrastructure.database import get_db_session

            sync_service = NoteSpaceSync()
            async with get_db_session() as session:
                file_path = await sync_service.sync_note_to_space(
                    space_path=space_path,
                    note_id=note_id,
                    session=session,
                )
                logger.info(
                    "[NoteSync] Synced note %s to workspace: %s",
                    note_id,
                    file_path,
                )

        except Exception as e:
            logger.error(
                "[NoteSync] Failed to sync note %s to workspace: %s",
                note_id,
                str(e),
                exc_info=True,
            )

    async def stream(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute agent with streaming via Claude SDK subprocess."""
        try:
            api_key = await self._get_api_key(context.workspace_id)
            subagent_definitions = self._build_subagent_definitions()
            session_id_str = str(input_data.session_id) if input_data.session_id else None

            # Resume when explicit resume_session_id is set by the router
            resume_id: str | None = None
            if input_data.resume_session_id and session_id_str:
                resume_id = session_id_str
                logger.info(
                    "Resuming SDK session: %s (requested: %s)",
                    resume_id,
                    input_data.resume_session_id,
                )

            if not (self._space_manager and context.workspace_id and context.user_id):
                raise ValueError(  # noqa: TRY301
                    "SpaceManager, workspace_id, and user_id are required. "
                    "Legacy mode has been removed."
                )
            async for chunk in self._stream_with_space(
                input_data=input_data,
                context=context,
                api_key=api_key,
                subagent_definitions=subagent_definitions,
                session_id_str=session_id_str,
                resume_id=resume_id,
            ):
                yield chunk

        except Exception as e:
            error_data = {"type": "error", "error_type": "sdk_error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    async def _stream_with_space(
        self,
        input_data: ChatInput,
        context: AgentContext,
        api_key: str,
        subagent_definitions: dict[str, AgentDefinition],
        session_id_str: str | None,
        resume_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream using SpaceManager for sandboxed execution."""
        assert self._space_manager is not None
        assert context.workspace_id is not None
        assert context.user_id is not None

        space = self._space_manager.get_space(context.workspace_id, context.user_id)

        async with space.session() as space_context:
            tool_event_queue: asyncio.Queue[str] = asyncio.Queue()

            file_hook_executor = None
            if space_context.hooks_file.exists():
                from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor

                file_hook_executor = FileBasedHookExecutor(
                    space_context.hooks_file,
                    cwd=space_context.path,
                )
                logger.debug(f"[SDK/Space] Loaded hooks from {space_context.hooks_file}")

            from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

            hook_executor = PermissionAwareHookExecutor(
                permission_handler=self._permission_handler,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                file_hook_executor=file_hook_executor,
                event_queue=tool_event_queue,
            )

            context_note_id = input_data.context.get("note_id")
            note_tools_server = create_note_tools_server(
                tool_event_queue,
                context_note_id=str(context_note_id) if context_note_id else None,
            )

            from pilot_space.ai.sdk.output_schemas import get_skill_output_format

            skill_name = _detect_skill_from_message(input_data.message)
            output_format = get_skill_output_format(skill_name) if skill_name else None
            effort = _classify_effort(input_data.message)
            streaming_input = _estimate_tokens(input_data) > 30_000

            sdk_config = configure_sdk_for_space(
                space_context,
                permission_mode="default",
                model=self.DEFAULT_MODEL_TIER,
                additional_tools=NOTE_TOOL_NAMES,
                additional_env={
                    "ANTHROPIC_API_KEY": api_key,
                },
                hook_executor=hook_executor,
                include_partial_messages=True,
                memory_enabled=True,
                citations_enabled=True,
                system_prompt_base=self.SYSTEM_PROMPT_BASE,
                output_format=output_format,
                enable_file_checkpointing=True,
                effort=effort,
                streaming_input_mode=streaming_input,
            )

            sdk_params = sdk_config.to_sdk_params()
            sdk_env = sdk_params.get("env", {})
            if "PATH" not in sdk_env:
                sdk_env["PATH"] = os.environ.get("PATH", "")

            sdk_options = ClaudeAgentOptions(
                model=sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id),
                cwd=sdk_params.get("cwd"),
                setting_sources=sdk_params.get("setting_sources", ["project"]),
                allowed_tools=sdk_params.get("allowed_tools", []),
                mcp_servers={NOTE_SERVER_NAME: note_tools_server},
                sandbox=sdk_params.get("sandbox"),
                permission_mode=sdk_params.get("permission_mode", "default"),
                env=sdk_env,
                hooks=sdk_params.get("hooks"),
                agents=subagent_definitions,
                resume=resume_id,
                continue_conversation=resume_id is not None,
                include_partial_messages=sdk_params.get(
                    "include_partial_messages",
                    True,
                ),
            )

            set_workspace_context(context.workspace_id, context.user_id)
            logger.info(
                "[SDK/Space] Config: cwd=%s, env_keys=%s, claude_bin=%s",
                sdk_params.get("cwd"),
                list(sdk_env.keys()),
                shutil.which("claude"),
            )

            await self._sync_note_if_present(
                input_data=input_data,
                space_path=space_context.path,
            )

            client = ClaudeSDKClient(sdk_options)
            query_session_id = session_id_str or "default"
            stream_completed = False

            # Structured content accumulation for session persistence
            # Keys: "text_{idx}", "thinking_{idx}", "tool_use_{id}", "tool_result_{id}"
            content_blocks: dict[str, dict[str, Any]] = {}

            # Initialize delta buffer for water pumping (SSE event reduction)
            delta_buffer = DeltaBuffer()

            try:
                await client.connect()

                logger.info(
                    "[SDK/Space] Client connected (session=%s, resume=%s)",
                    query_session_id,
                    resume_id,
                )

                self._active_clients[query_session_id] = client

                enriched_message = build_contextual_message(input_data)
                await client.query(enriched_message, session_id=query_session_id)

                sdk_event_count = 0
                transformed_count = 0
                tool_event_count = 0

                async for message in client.receive_response():
                    sdk_event_count += 1
                    sse_event = self.transform_sdk_message(
                        message,
                        context,
                        delta_buffer,
                        session_id=session_id_str,  # Pass app session_id to frontend
                    )
                    if sse_event:
                        transformed_count += 1
                        yield sse_event
                        _capture_content_from_sse(sse_event, content_blocks)

                    # Time-based flush check for buffered deltas
                    if delta_buffer.should_flush():
                        flush_event = delta_buffer.flush()
                        if flush_event:
                            transformed_count += 1
                            yield flush_event
                            _capture_content_from_sse(flush_event, content_blocks)

                    try:
                        while True:
                            yield tool_event_queue.get_nowait()
                            tool_event_count += 1
                    except asyncio.QueueEmpty:
                        pass

                # Final flush of any remaining buffered deltas
                final_flush = delta_buffer.flush()
                if final_flush:
                    transformed_count += 1
                    yield final_flush
                    _capture_content_from_sse(final_flush, content_blocks)

                try:
                    while True:
                        yield tool_event_queue.get_nowait()
                        tool_event_count += 1
                except asyncio.QueueEmpty:
                    pass

                stream_completed = True
                logger.info(
                    "[SDK/Space] Query finished: %d sdk_events, %d transformed, %d tool_events",
                    sdk_event_count,
                    transformed_count,
                    tool_event_count,
                )

            finally:
                self._active_clients.pop(query_session_id, None)

                if not stream_completed:
                    try:
                        await asyncio.wait_for(client.interrupt(), timeout=2.0)
                        logger.info(
                            "[SDK/Space] Sent interrupt to Claude process (session=%s)",
                            query_session_id,
                        )
                    except (TimeoutError, Exception) as e:
                        logger.debug("[SDK/Space] Interrupt during cleanup failed: %s", e)

                if stream_completed and self._session_handler and input_data.session_id:
                    try:
                        await self._session_handler.add_message(
                            session_id=input_data.session_id,
                            role="user",
                            content=input_data.message,
                        )
                        # Build structured content from captured blocks
                        structured_content = _build_structured_content(content_blocks)
                        if structured_content:
                            await self._session_handler.add_message(
                                session_id=input_data.session_id,
                                role="assistant",
                                content=structured_content,
                            )
                        logger.debug(
                            "[SDK/Space] Persisted messages to session %s (%d blocks)",
                            input_data.session_id,
                            len(content_blocks),
                        )
                    except Exception as e:
                        logger.warning(
                            "[SDK/Space] Failed to persist session messages: %s",
                            e,
                        )

                await client.disconnect()
                clear_context()

    async def create_client(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> tuple[ClaudeSDKClient, str]:
        """Create unconnected ClaudeSDKClient. Caller manages connect()/disconnect()."""
        api_key = await self._get_api_key(context.workspace_id)
        subagent_definitions = self._build_subagent_definitions()

        session_id_str = "default"
        if input_data.session_id and self._session_handler:
            existing = await self._session_handler.get_session(input_data.session_id)
            if existing:
                session_id_str = str(existing.session_id)

        if not (self._space_manager and context.workspace_id and context.user_id):
            msg = (
                "SpaceManager, workspace_id, and user_id are required. "
                "Legacy mode has been removed."
            )
            raise ValueError(msg)

        space = self._space_manager.get_space(context.workspace_id, context.user_id)
        async with space.session() as space_context:
            sdk_config = configure_sdk_for_space(
                space_context,
                permission_mode="default",
                additional_env={"ANTHROPIC_API_KEY": api_key},
            )
            sdk_params = sdk_config.to_sdk_params()

            sdk_env = sdk_params.get("env", {})
            if "PATH" not in sdk_env:
                sdk_env["PATH"] = os.environ.get("PATH", "")

            sdk_options = ClaudeAgentOptions(
                model=sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id),
                cwd=sdk_params.get("cwd"),
                setting_sources=sdk_params.get("setting_sources", ["project"]),
                allowed_tools=sdk_params.get("allowed_tools", []),
                sandbox=sdk_params.get("sandbox"),
                permission_mode=sdk_params.get("permission_mode", "default"),
                env=sdk_env,
                hooks=sdk_params.get("hooks"),
                agents=subagent_definitions,
                resume=session_id_str if session_id_str != "default" else None,
            )

            return ClaudeSDKClient(sdk_options), session_id_str

    async def execute(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> ChatOutput:
        """Non-streaming execution that collects all chunks into ChatOutput."""
        chunks: list[str] = []
        async for chunk in self.stream(input_data, context):
            processed_chunk = chunk[6:] if chunk.startswith("data: ") else chunk
            chunks.append(processed_chunk)

        full_response = "".join(chunks)
        return ChatOutput(
            response=full_response,
            session_id=input_data.session_id
            or context.operation_id
            or UUID("00000000-0000-0000-0000-000000000000"),
            tasks=[],
            metadata={
                "agent": self.AGENT_NAME,
                "model": self.DEFAULT_MODEL_TIER.model_id,
            },
        )


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


def _classify_effort(message: str) -> str | None:
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


def _detect_skill_from_message(message: str) -> str | None:
    """Detect slash-command skill invocation, returning skill name or None."""
    msg_stripped = message.strip()
    if msg_stripped.startswith("/"):
        parts = msg_stripped[1:].split(None, 1)
        return parts[0] if parts else None
    return None


def _estimate_tokens(input_data: ChatInput) -> int:
    """Rough token estimate (~4 chars/token) for context size detection (T62)."""
    total_chars = len(input_data.message)
    total_chars += sum(len(str(v)) for v in input_data.context.values())
    return total_chars // 4


def _capture_content_from_sse(
    sse_event: str,
    content_blocks: dict[str, dict[str, Any]],
) -> None:
    """Capture structured content from SSE events for session persistence.

    Extracts text_delta, thinking_delta, tool_use, and tool_result events
    and accumulates them into content_blocks dictionary.

    Args:
        sse_event: SSE-formatted event string (may contain multiple events)
        content_blocks: Mutable dict to accumulate content by block key
    """
    for event_line in sse_event.split("\n\n"):
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
            # Capture signature if present
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
                    "index": len(content_blocks),  # Preserve order
                }

        elif event_type == "tool_result":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_result_{tool_id}"
                content_blocks[key] = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": data.get("output", data.get("errorMessage", "")),
                    "is_error": data.get("status") == "failed",
                    "index": len(content_blocks),
                }


def _build_structured_content(
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

    # Sort by index to preserve order
    sorted_blocks = sorted(
        content_blocks.values(),
        key=lambda b: b.get("index", 0),
    )

    # Check if we have only text content
    has_non_text = any(
        b["type"] in ("thinking", "tool_use", "tool_result")
        for b in sorted_blocks
    )

    if not has_non_text:
        # Return plain text for backward compatibility
        text_parts = [b.get("text", "") for b in sorted_blocks if b["type"] == "text"]
        return "".join(text_parts)

    # Return structured content
    result: list[dict[str, Any]] = []
    for block in sorted_blocks:
        # Remove internal index field used for ordering
        clean_block = {k: v for k, v in block.items() if k != "index"}
        result.append(clean_block)

    return result
