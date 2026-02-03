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
    transform_sdk_message as transform_sdk_message_helper,
)
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME as NOTE_SERVER_NAME,
    TOOL_NAMES as NOTE_TOOL_NAMES,
    create_note_tools_server,
)
from pilot_space.ai.sdk.sandbox_config import configure_sdk_for_space
from pilot_space.spaces.manager import SpaceManager

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
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
    """Input for PilotSpace conversational agent.

    Attributes:
        message: User message content
        session_id: Optional session ID for multi-turn conversation
        context: Current working context (note, issue, project)
        user_id: User UUID for RLS
        workspace_id: Workspace UUID for RLS
    """

    message: str
    session_id: UUID | None = None
    resume_session_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    workspace_id: UUID | None = None


@dataclass
class ChatOutput:
    """Output from PilotSpace conversational agent.

    Attributes:
        response: Agent response text
        session_id: Session ID for continuation
        tasks: Created tasks if any
        approvals: Approval requests if any
        metadata: Additional metadata (cost, tokens, etc.)
    """

    response: str
    session_id: UUID
    tasks: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PilotSpaceAgent(StreamingSDKBaseAgent[ChatInput, ChatOutput]):
    r"""Main orchestrator agent for PilotSpace.

    Replaces 13 siloed agents with unified conversational interface.
    Routes requests to skills, subagents, or direct responses based on intent.

    Intent patterns:
    - `\skill-name` → Skill execution
    - `@agent-name` → Subagent delegation
    - Natural language → Direct response with context

    Architecture:
    - Skills: Lightweight one-shot tasks (8 skills in backend/.claude/skills/)
    - Subagents: Complex multi-turn tasks (3 subagents: PR review, AI context, doc gen)
    - Direct: Natural language responses with context awareness

    Usage:
        agent = PilotSpaceAgent(...)
        async for chunk in agent.stream(ChatInput(...), context):
            yield chunk
    """

    AGENT_NAME = "pilotspace_agent"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

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
        self._message_id_holder: dict[str, str | None] = {"_current_message_id": None}
        # Track active SDK clients by session ID for interrupt support
        self._active_clients: dict[str, ClaudeSDKClient] = {}

    # Removed old routing methods (_parse_intent, _execute_skill, _spawn_subagent,
    # _plan_tasks, _handle_natural_language) - SDK handles all routing via .claude/

    def _build_subagent_definitions(self) -> dict[str, AgentDefinition]:
        """Build subagent definitions for SDK agent spawning.

        Returns:
            Dict of agent name to AgentDefinition for SDK's Task tool.
        """
        return {
            "pr-review": AgentDefinition(
                description="Expert code reviewer for GitHub PRs",
                prompt="Analyze pull requests for architecture, security, and performance",
                tools=["Read", "Glob", "Grep", "WebFetch"],
            ),
            "ai-context": AgentDefinition(
                description="Aggregates context for issues from notes, code, and tasks",
                prompt="Find related notes, code snippets, and similar issues",
                tools=["Read", "Glob", "Grep"],
            ),
            "doc-generator": AgentDefinition(
                description="Generates technical documentation from code",
                prompt="Create comprehensive documentation with examples",
                tools=["Read", "Glob", "Write"],
            ),
        }

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        """Get Anthropic API key from workspace settings.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Decrypted API key

        Raises:
            ValueError: If API key not found
        """
        if not workspace_id:
            # Use environment variable as fallback
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                msg = "No workspace_id provided and ANTHROPIC_API_KEY not set"
                raise ValueError(msg)
            return api_key

        # TODO: Integrate with SecureKeyStorage when available
        # For now, use environment variable
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = (
                f"Anthropic API key not found for workspace {workspace_id}. "
                "Please set ANTHROPIC_API_KEY environment variable or "
                "configure in workspace settings."
            )
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
        """Execute conversational agent with streaming output using Claude SDK.

        Uses ClaudeSDKClient for persistent subprocess to handle:
        - Skill execution (via .claude/skills/ filesystem discovery)
        - Subagent spawning (via Task tool)
        - Natural language responses (via Claude's reasoning)
        - Permission handling (via hooks)

        Architecture:
        - If SpaceManager is configured, uses isolated space with sandbox settings
        - API key is injected via SDK's env parameter, not os.environ mutation
        - Enables multi-tenant concurrent requests without race conditions

        Args:
            input_data: Chat input with message and context
            context: Agent execution context

        Yields:
            SSE chunks with response content
        """
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
        """Stream using SpaceManager for isolated execution.

        Creates an isolated space for the workspace/user pair with:
        - Sandboxed filesystem access
        - API key injection via env parameter
        - Proper cleanup on completion
        """
        assert self._space_manager is not None
        assert context.workspace_id is not None
        assert context.user_id is not None

        # Get space for this workspace/user
        space = self._space_manager.get_space(context.workspace_id, context.user_id)

        async with space.session() as space_context:
            # Load file-based hooks if hooks.json exists
            hook_executor = None
            if space_context.hooks_file.exists():
                from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor

                hook_executor = FileBasedHookExecutor(
                    space_context.hooks_file,
                    cwd=space_context.path,
                )
                logger.debug(f"[SDK/Space] Loaded hooks from {space_context.hooks_file}")

            # Create event queue for tool-generated SSE events
            tool_event_queue: asyncio.Queue[str] = asyncio.Queue()

            # Create in-process MCP server with note tools
            # Pass context_note_id to prevent LLM UUID corruption
            context_note_id = input_data.context.get("note_id")
            note_tools_server = create_note_tools_server(
                tool_event_queue,
                context_note_id=str(context_note_id) if context_note_id else None,
            )

            # Configure SDK for this space (with hooks if available)
            sdk_config = configure_sdk_for_space(
                space_context,
                permission_mode="default",
                additional_tools=NOTE_TOOL_NAMES,
                additional_env={"ANTHROPIC_API_KEY": api_key},
                hook_executor=hook_executor,
            )

            # Build SDK options from space config
            sdk_params = sdk_config.to_sdk_params()

            # Ensure PATH is inherited so subprocess can find claude binary
            sdk_env = sdk_params.get("env", {})
            if "PATH" not in sdk_env:
                sdk_env["PATH"] = os.environ.get("PATH", "")

            sdk_options = ClaudeAgentOptions(
                model=sdk_params.get("model", self.DEFAULT_MODEL),
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
            response_chunks: list[str] = []
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
                        # Accumulate text content for session persistence
                        if sse_event.startswith("data: "):
                            response_chunks.append(sse_event[6:])

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

                # Persist conversation messages to session storage
                if stream_completed and self._session_handler and input_data.session_id:
                    try:
                        await self._session_handler.add_message(
                            session_id=input_data.session_id,
                            role="user",
                            content=input_data.message,
                        )
                        full_response = "".join(response_chunks)
                        if full_response:
                            await self._session_handler.add_message(
                                session_id=input_data.session_id,
                                role="assistant",
                                content=full_response,
                            )
                        logger.debug(
                            "[SDK/Space] Persisted messages to session %s",
                            input_data.session_id,
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
            model=sdk_params.get("model", self.DEFAULT_MODEL),
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
        Persists user and assistant messages to session storage.

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

        full_response = "".join(chunks)

        # Session persistence is handled in _stream_with_space finally block.
        # For execute(), stream() already persisted messages, so no duplicate needed.

        return ChatOutput(
            response=full_response,
            session_id=input_data.session_id
            or context.operation_id
            or UUID("00000000-0000-0000-0000-000000000000"),
            tasks=[],  # SDK handles task tracking internally
            metadata={
                "agent": self.AGENT_NAME,
                "model": self.DEFAULT_MODEL,
            },
        )


__all__ = [
    "ChatInput",
    "ChatOutput",
    "PilotSpaceAgent",
]
