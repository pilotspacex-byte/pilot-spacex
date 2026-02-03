"""PilotSpace Agent - Main orchestrator for conversational AI.

Replaces 13 siloed agents with unified conversational interface.
Routes requests to skills, subagents, or direct responses based on intent.

Intent patterns:
- `\\skill-name` → Skill execution
- `@agent-name` → Subagent delegation
- Natural language → Direct response with context

Reference: specs/005-conversational-agent-arch/plan.md (T027-T031)
Design Decisions: DD-003 (Human-in-the-Loop), DD-048 (Confidence Tags)
"""

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

# Import Claude Agent SDK (required dependency)
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, Message

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.agents.note_space_sync import NoteSpaceSync
from pilot_space.ai.agents.pilotspace_agent_helpers import (
    build_contextual_message,
    build_subagent_definitions,
    transform_sdk_message as transform_sdk_message_helper,
)
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


# Removed IntentType, ParsedIntent - SDK handles intent parsing via .claude/ directory

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

    # Base system prompt for SDK-native prompt caching (cache_control: ephemeral).
    # This stable text is cached across requests, saving ~63% on input tokens.
    SYSTEM_PROMPT_BASE: ClassVar[str] = (
        "You are PilotSpace AI, an embedded assistant in a Note-First SDLC platform. "
        "You help software teams capture ideas in notes, extract issues, review PRs, "
        "and manage project workflows. You have access to MCP note tools "
        "(update_note_block, enhance_text, summarize_note, extract_issues, "
        "create_issue_from_note, link_existing_issues) and can delegate to subagents "
        "(pr-review, ai-context, doc-generator). Follow the user's workspace context. "
        "Return operation payloads for mutations; never mutate the database directly. "
        "For destructive actions, always request human approval."
    )

    # Subagent routing map
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
        """Initialize PilotSpace agent with dependencies.

        Args:
            tool_registry: MCP tool registry
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            permission_handler: Permission and approval handler
            session_handler: Session management handler (None if Redis not configured)
            skill_registry: Skill loading registry
            space_manager: Space management service (None for legacy mode)
            subagents: Optional dict of subagent instances
            key_storage: Secure API key storage (None falls back to env var)
        """
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
        # Track active SDK clients by session ID for interrupt support
        self._active_clients: dict[str, ClaudeSDKClient] = {}

    # Removed old routing methods (_parse_intent, _execute_skill, _spawn_subagent,
    # _plan_tasks, _handle_natural_language) - SDK handles all routing via .claude/

    def _build_subagent_definitions(self) -> dict[str, AgentDefinition]:
        """Build subagent definitions for SDK agent spawning."""
        return build_subagent_definitions()

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        """Get Anthropic API key from Vault or environment.

        Lookup order:
        1. SecureKeyStorage (Supabase Vault) if workspace_id and key_storage available
        2. ANTHROPIC_API_KEY environment variable (fallback)

        Args:
            workspace_id: Workspace UUID for per-workspace BYOK lookup

        Returns:
            Decrypted API key

        Raises:
            ValueError: If API key not found in any source
        """
        # Try Vault first for per-workspace BYOK keys
        if workspace_id and self._key_storage:
            try:
                key = await self._key_storage.get_api_key(workspace_id, "anthropic")
                if key:
                    return key
            except Exception:
                logger.warning(
                    "Vault lookup failed for workspace %s, falling back to env var",
                    workspace_id,
                )

        # Fallback to environment variable
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "Anthropic API key not found. Configure in workspace settings or set ANTHROPIC_API_KEY."
            raise ValueError(msg)
        return api_key

    async def interrupt_session(self, session_id: str) -> bool:
        """Interrupt active SDK client for a given session.

        Sends interrupt control request to Claude subprocess, stopping
        the current turn gracefully per Claude Agent SDK guidelines.

        Args:
            session_id: Session identifier to interrupt.

        Returns:
            True if interrupt was sent, False if no active client found.
        """
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
        context: AgentContext,  # noqa: ARG002
    ) -> str | None:
        """Transform Claude SDK message to frontend SSE event.

        Args:
            message: SDK message object
            context: Agent execution context

        Returns:
            SSE-formatted string or None if message should be ignored
        """
        return transform_sdk_message_helper(message, self._message_id_holder)

    async def _sync_note_if_present(
        self,
        input_data: ChatInput,
        space_path: Path,
    ) -> None:
        """Sync note to workspace if note context is present.

        Checks if input_data.context contains a note_id and syncs the latest
        note content from database to the workspace markdown file.

        This ensures the agent always works with fresh note content.

        Args:
            input_data: Chat input with context
            space_path: Path to workspace root

        Raises:
            No exceptions - errors are logged but don't block agent execution
        """
        # Check if note context is present
        note = input_data.context.get("note")
        if note is None:
            return

        # Extract note_id from the note object
        note_id = getattr(note, "id", None)
        if note_id is None:
            logger.warning("[NoteSync] Note object missing 'id' attribute, skipping sync")
            return

        # Sync note to workspace
        try:
            from pilot_space.infrastructure.database import get_db_session

            sync_service = NoteSpaceSync()

            # Create a new database session for sync
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
            # Log error but don't block agent execution (graceful degradation)
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
            # Get API key from workspace settings
            api_key = await self._get_api_key(context.workspace_id)

            # Build subagent definitions for SDK
            subagent_definitions = self._build_subagent_definitions()

            # Session tracking ID (for frontend, always set)
            session_id_str = str(input_data.session_id) if input_data.session_id else None

            # SDK resume ID (only set when continuing an existing conversation)
            resume_id: str | None = None
            if input_data.resume_session_id and self._session_handler:
                existing_session = await self._session_handler.get_session(
                    UUID(input_data.resume_session_id)
                )
                if existing_session:
                    resume_id = str(existing_session.session_id)

            # Require SpaceManager for isolated execution
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

        # Get space for this workspace/user
        space = self._space_manager.get_space(context.workspace_id, context.user_id)

        async with space.session() as space_context:
            # Create event queue for tool-generated SSE events
            tool_event_queue: asyncio.Queue[str] = asyncio.Queue()

            # Load file-based hooks if hooks.json exists
            file_hook_executor = None
            if space_context.hooks_file.exists():
                from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor

                file_hook_executor = FileBasedHookExecutor(
                    space_context.hooks_file,
                    cwd=space_context.path,
                )
                logger.debug(f"[SDK/Space] Loaded hooks from {space_context.hooks_file}")

            # Compose file hooks + DD-003 permission checks into
            # a single SDK-compatible hook executor
            from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

            hook_executor = PermissionAwareHookExecutor(
                permission_handler=self._permission_handler,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                file_hook_executor=file_hook_executor,
                event_queue=tool_event_queue,
            )

            # Create in-process MCP server with note tools
            # Pass context_note_id to prevent LLM UUID corruption
            context_note_id = input_data.context.get("note_id")
            note_tools_server = create_note_tools_server(
                tool_event_queue,
                context_note_id=str(context_note_id) if context_note_id else None,
            )

            # Detect skill invocation for structured output (T3/G-03)
            from pilot_space.ai.sdk.output_schemas import get_skill_output_format

            skill_name = _detect_skill_from_message(input_data.message)
            output_format = get_skill_output_format(skill_name) if skill_name else None

            # Classify effort for latency optimization (T7/G-09)
            effort = _classify_effort(input_data.message)

            # T62: Auto-detect large context for streaming input mode
            streaming_input = _estimate_tokens(input_data) > 30_000

            # Configure SDK for this space (with hooks if available)
            # Model selection per DD-011: DEFAULT_MODEL (Sonnet) for orchestration
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

            # Build SDK options from space config
            sdk_params = sdk_config.to_sdk_params()

            # Ensure PATH is inherited so subprocess can find claude binary
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
                hooks=sdk_params.get("hooks"),  # SDK-native hooks from hooks.json
                agents=subagent_definitions,
                resume=resume_id,
            )

            # Set context for observability
            set_workspace_context(context.workspace_id, context.user_id)

            logger.info(
                "[SDK/Space] Config: cwd=%s, env_keys=%s, claude_bin=%s",
                sdk_params.get("cwd"),
                list(sdk_env.keys()),
                shutil.which("claude"),
            )

            # Sync note to workspace if note_id in context
            await self._sync_note_if_present(
                input_data=input_data,
                space_path=space_context.path,
            )

            client = ClaudeSDKClient(sdk_options)
            query_session_id = session_id_str or "default"
            stream_completed = False
            try:
                await client.connect()

                logger.info(
                    "[SDK/Space] Client connected (session=%s, resume=%s)",
                    query_session_id,
                    resume_id,
                )

                # Track active client for external interrupt support
                self._active_clients[query_session_id] = client

                enriched_message = build_contextual_message(input_data)
                await client.query(enriched_message, session_id=query_session_id)

                sdk_event_count = 0
                transformed_count = 0
                tool_event_count = 0

                async for message in client.receive_response():
                    sdk_event_count += 1
                    sse_event = self.transform_sdk_message(message, context)
                    if sse_event:
                        transformed_count += 1
                        yield sse_event

                    # Drain tool-generated events after each SDK message
                    while not tool_event_queue.empty():
                        tool_event_count += 1
                        yield tool_event_queue.get_nowait()

                # Drain any remaining tool events after SDK stream ends
                while not tool_event_queue.empty():
                    tool_event_count += 1
                    yield tool_event_queue.get_nowait()

                stream_completed = True
                logger.info(
                    "[SDK/Space] Query finished: %d sdk_events, %d transformed, %d tool_events",
                    sdk_event_count,
                    transformed_count,
                    tool_event_count,
                )

            finally:
                # Remove from active clients
                self._active_clients.pop(query_session_id, None)

                # If stream was interrupted (not completed naturally),
                # send interrupt signal to Claude subprocess before disconnect
                if not stream_completed:
                    try:
                        await asyncio.wait_for(client.interrupt(), timeout=2.0)
                        logger.info(
                            "[SDK/Space] Sent interrupt to Claude process (session=%s)",
                            query_session_id,
                        )
                    except (TimeoutError, Exception) as e:
                        logger.debug("[SDK/Space] Interrupt during cleanup failed: %s", e)

                await client.disconnect()
                clear_context()

    async def create_client(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> tuple[ClaudeSDKClient, str]:
        """Create a configured ClaudeSDKClient for the given context.

        Used by ConversationWorker to manage client lifecycle externally.
        Client is NOT connected — caller must call connect()/disconnect().

        Args:
            input_data: Chat input with session context
            context: Agent execution context

        Returns:
            Tuple of (unconnected ClaudeSDKClient, session_id for query())
        """
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
        space_context = await space.session().__aenter__()

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
        """Execute agent and collect full output.

        Non-streaming version that collects all chunks.

        Args:
            input_data: Chat input
            context: Agent execution context

        Returns:
            Complete ChatOutput with response and metadata
        """
        chunks: list[str] = []
        async for chunk in self.stream(input_data, context):
            # Remove SSE formatting for collected output
            processed_chunk = chunk[6:] if chunk.startswith("data: ") else chunk
            chunks.append(processed_chunk)

        return ChatOutput(
            response="".join(chunks),
            session_id=input_data.session_id
            or context.operation_id
            or UUID("00000000-0000-0000-0000-000000000000"),
            tasks=[],  # SDK handles task tracking internally
            metadata={
                "agent": self.AGENT_NAME,
                "model": self.DEFAULT_MODEL_TIER.model_id,
            },
        )


# Module-level helpers (kept outside class to avoid line bloat)

# Patterns for low-effort queries (T7/G-09) — pre-compiled for performance (T69)
_SIMPLE_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay)\b"),
    re.compile(r"^what (can you|do you) do"),
    re.compile(r"^help\b"),
    re.compile(r"^(yes|no|sure|yep|nope)\b"),
]


def _classify_effort(message: str) -> str | None:
    """Classify query effort level for latency optimization.

    Returns 'low' for simple greetings/confirmations, None for default.
    """
    msg_lower = message.strip().lower()
    if len(msg_lower) < 50:
        for pattern in _SIMPLE_PATTERNS:
            if pattern.match(msg_lower):
                return "low"
    return None


def _detect_skill_from_message(message: str) -> str | None:
    """Detect slash-command skill invocation from message content.

    Returns skill name (e.g., 'extract-issues') or None.
    """
    msg_stripped = message.strip()
    if msg_stripped.startswith("/"):
        # Extract first word after slash
        parts = msg_stripped[1:].split(None, 1)
        return parts[0] if parts else None
    return None


def _estimate_tokens(input_data: ChatInput) -> int:
    """Rough token estimate for context size detection (T62).

    Uses ~4 chars per token heuristic. Counts message + context fields.
    """
    total_chars = len(input_data.message)
    for value in input_data.context.values():
        total_chars += len(str(value))
    return total_chars // 4


__all__ = [
    "ChatInput",
    "ChatOutput",
    "PilotSpaceAgent",
]
