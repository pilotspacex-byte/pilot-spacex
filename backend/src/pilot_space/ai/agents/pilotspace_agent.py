"""PilotSpace Agent - Centralized orchestrator routing to skills, subagents, or direct responses."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, Message

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.agents.pilotspace_agent_helpers import (
    build_contextual_message,
    build_subagent_definitions,
    transform_sdk_message as transform_sdk_message_helper,
)
from pilot_space.ai.agents.pilotspace_stream_utils import (
    build_structured_content,
    capture_content_from_sse,
    classify_effort,
    detect_skill_from_message,
    estimate_tokens,
)
from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.mcp.comment_server import (
    SERVER_NAME as COMMENT_SERVER_NAME,
    TOOL_NAMES as COMMENT_TOOL_NAMES,
    create_comment_tools_server,
)
from pilot_space.ai.mcp.issue_relation_server import (
    SERVER_NAME as ISSUE_REL_SERVER_NAME,
    TOOL_NAMES as ISSUE_REL_TOOL_NAMES,
    create_issue_relation_tools_server,
)
from pilot_space.ai.mcp.issue_server import (
    SERVER_NAME as ISSUE_SERVER_NAME,
    TOOL_NAMES as ISSUE_TOOL_NAMES,
    create_issue_tools_server,
)
from pilot_space.ai.mcp.note_content_server import (
    SERVER_NAME as NOTE_CONTENT_SERVER_NAME,
    TOOL_NAMES as NOTE_CONTENT_TOOL_NAMES,
    create_note_content_server,
)
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME as NOTE_SERVER_NAME,
    TOOL_NAMES as NOTE_TOOL_NAMES,
    create_note_tools_server,
)
from pilot_space.ai.mcp.project_server import (
    SERVER_NAME as PROJECT_SERVER_NAME,
    TOOL_NAMES as PROJECT_TOOL_NAMES,
    create_project_tools_server,
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

# Aggregated tool names across all MCP servers (27 tools total)
ALL_TOOL_NAMES: list[str] = [
    *NOTE_TOOL_NAMES,
    *NOTE_CONTENT_TOOL_NAMES,
    *ISSUE_TOOL_NAMES,
    *ISSUE_REL_TOOL_NAMES,
    *PROJECT_TOOL_NAMES,
    *COMMENT_TOOL_NAMES,
]


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
        "## Tool categories\n"
        "**Notes** (9 tools): write_to_note, update_note_block, enhance_text, "
        "extract_issues, create_issue_from_note, link_existing_issues, search_notes, create_note, update_note.\n"
        "**Note content** (5 tools): search_note_content, insert_block, remove_block, remove_content, replace_content.\n"
        "**Issues** (4 CRUD + 6 relations): get_issue, search_issues, create_issue, update_issue, "
        "link_issue_to_note, unlink_issue_from_note, link_issues, unlink_issues, add_sub_issue, transition_issue_state.\n"
        "**Projects** (5 tools): get_project, search_projects, create_project, update_project, update_project_settings.\n"
        "**Comments** (4 tools): create_comment, update_comment, search_comments, get_comments.\n\n"
        "## Entity resolution\n"
        "Issue/project tools accept UUID or human-readable identifiers (e.g., PILOT-123, PILOT).\n\n"
        "## Approval tiers\n"
        "- Auto-execute: search/get tools (read-only).\n"
        "- Require approval: create/update/link tools.\n"
        "- Always require: unlink tools (destructive).\n\n"
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

            # Build ToolContext for MCP servers that need DB access
            from pilot_space.ai.tools.mcp_server import ToolContext
            from pilot_space.infrastructure.database import get_db_session

            tool_context: ToolContext | None = None
            db_session_cm = get_db_session()
            db_session = await db_session_cm.__aenter__()
            try:
                tool_context = ToolContext(
                    db_session=db_session,
                    workspace_id=str(context.workspace_id),
                    user_id=str(context.user_id) if context.user_id else None,
                )
            except Exception:
                await db_session_cm.__aexit__(None, None, None)
                raise

            context_note_id = input_data.context.get("note_id")
            note_tools_server = create_note_tools_server(
                tool_event_queue,
                context_note_id=str(context_note_id) if context_note_id else None,
                tool_context=tool_context,
            )
            note_content_server = create_note_content_server(
                tool_event_queue,
                tool_context=tool_context,
            )
            issue_tools_server = create_issue_tools_server(
                tool_event_queue,
                tool_context=tool_context,
            )
            issue_rel_server = create_issue_relation_tools_server(
                tool_event_queue,
                tool_context=tool_context,
            )
            project_tools_server = create_project_tools_server(
                event_queue=tool_event_queue,
                tool_context=tool_context,
            )
            comment_tools_server = create_comment_tools_server(
                tool_event_queue,
                tool_context=tool_context,
            )

            from pilot_space.ai.sdk.output_schemas import get_skill_output_format

            skill_name = detect_skill_from_message(input_data.message)
            output_format = get_skill_output_format(skill_name) if skill_name else None
            effort = classify_effort(input_data.message)
            streaming_input = estimate_tokens(input_data) > 30_000

            sdk_config = configure_sdk_for_space(
                space_context,
                permission_mode="default",
                model=self.DEFAULT_MODEL_TIER,
                additional_tools=ALL_TOOL_NAMES,
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
                mcp_servers={
                    NOTE_SERVER_NAME: note_tools_server,
                    NOTE_CONTENT_SERVER_NAME: note_content_server,
                    ISSUE_SERVER_NAME: issue_tools_server,
                    ISSUE_REL_SERVER_NAME: issue_rel_server,
                    PROJECT_SERVER_NAME: project_tools_server,
                    COMMENT_SERVER_NAME: comment_tools_server,
                },
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
                        capture_content_from_sse(sse_event, content_blocks)

                    # Time-based flush check for buffered deltas
                    if delta_buffer.should_flush():
                        flush_event = delta_buffer.flush()
                        if flush_event:
                            transformed_count += 1
                            yield flush_event
                            capture_content_from_sse(flush_event, content_blocks)

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
                    capture_content_from_sse(final_flush, content_blocks)

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
                        structured_content = build_structured_content(content_blocks)
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

                # Clean up tool context db session
                await db_session_cm.__aexit__(None, None, None)

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
