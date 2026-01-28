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

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

# Import Claude Agent SDK (required dependency)
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

from pilot_space.ai.agents.sdk_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.context import (
    clear_context,
    get_api_key_lock,
    set_api_key,
    set_workspace_context,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk.permission_handler import PermissionHandler
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.ai.tools.mcp_server import ToolRegistry


# Removed IntentType, ParsedIntent - SDK handles intent parsing via .claude/ directory


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


# Removed TaskEntry - SDK handles task tracking natively


class SkillRegistry:
    """Registry for loading and managing skill definitions.

    Skills are defined in `.claude/skills/{skill-name}/SKILL.md` files.
    Uses progressive loading: metadata at startup, instructions on demand.
    """

    def __init__(self, skills_dir: Path):
        """Initialize registry with skills directory.

        Args:
            skills_dir: Path to .claude/skills directory
        """
        self._skills_dir = skills_dir
        self._metadata_cache: dict[str, dict[str, str]] = {}
        self._loaded_skills: dict[str, str] = {}

    def load_metadata(self) -> dict[str, dict[str, str]]:
        """Load metadata for all skills.

        Parses YAML frontmatter from SKILL.md files.

        Returns:
            Dict mapping skill name to metadata (name, description)
        """
        if self._metadata_cache:
            return self._metadata_cache

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            # Parse YAML frontmatter
            content = skill_file.read_text()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    metadata = {}
                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()

                    self._metadata_cache[skill_dir.name] = metadata

        return self._metadata_cache

    def get_skill_instructions(self, skill_name: str) -> str | None:
        """Load full skill instructions on demand.

        Args:
            skill_name: Name of skill to load

        Returns:
            Full SKILL.md content or None if not found
        """
        if skill_name in self._loaded_skills:
            return self._loaded_skills[skill_name]

        skill_file = self._skills_dir / skill_name / "SKILL.md"
        if not skill_file.exists():
            return None

        content = skill_file.read_text()
        self._loaded_skills[skill_name] = content
        return content

    def get_available_skills(self) -> list[str]:
        """Get list of available skill names.

        Returns:
            List of skill names
        """
        return list(self.load_metadata().keys())


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
        self._subagents = subagents or {}

    # Removed old routing methods (_parse_intent, _execute_skill, _spawn_subagent,
    # _plan_tasks, _handle_natural_language) - SDK handles all routing via .claude/

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

    def _transform_sdk_message(  # noqa: PLR0911  # Many returns needed for message types
        self, message: Any, context: AgentContext
    ) -> str | None:
        """Transform Claude SDK message to frontend SSE event.

        SDK Message Types (from claude-agent-sdk):
        - StreamEvent with type: "text_delta", "tool_use", "tool_result"
        - SystemMessage with subtype: "init"
        - AssistantMessage, UserMessage, ResultMessage

        Args:
            message: SDK message object (StreamEvent, AssistantMessage, etc.)
            context: Agent execution context

        Returns:
            SSE-formatted string or None if message should be ignored
        """
        # Handle StreamEvent messages
        if hasattr(message, "type"):
            msg_type = getattr(message, "type", None)

            # Session initialization
            if msg_type == "system" and hasattr(message, "subtype"):
                if message.subtype == "init" and hasattr(message, "session_id"):
                    session_id = message.session_id
                    return f"data: {{'type': 'message_start', 'session_id': '{session_id}'}}\n\n"

            # Text streaming
            elif msg_type == "text_delta" and hasattr(message, "delta"):
                content = message.delta
                # Escape single quotes for JSON
                content_escaped = content.replace("'", "\\'").replace("\n", "\\n")
                return f"data: {{'type': 'text_delta', 'content': '{content_escaped}'}}\n\n"

            # Tool use
            elif msg_type == "tool_use" and hasattr(message, "id"):
                tool_call_id = message.id
                tool_name = getattr(message, "name", "")
                return (
                    f"data: {{'type': 'tool_use', 'tool_call_id': '{tool_call_id}', "
                    f"'tool_name': '{tool_name}'}}\n\n"
                )

            # Tool result
            elif msg_type == "tool_result" and hasattr(message, "tool_use_id"):
                tool_call_id = message.tool_use_id
                is_error = getattr(message, "is_error", False)
                status = "failed" if is_error else "completed"
                return (
                    f"data: {{'type': 'tool_result', 'tool_call_id': '{tool_call_id}', "
                    f"'status': '{status}'}}\n\n"
                )

            # Message stop
            elif msg_type == "stop":
                session_id = str(context.operation_id) if context.operation_id else "unknown"
                return f"data: {{'type': 'message_stop', 'session_id': '{session_id}'}}\n\n"

        # Handle AssistantMessage (final response)
        if hasattr(message, "content") and hasattr(message, "role"):
            if message.role == "assistant":
                # This is a complete assistant message
                content = message.content
                if isinstance(content, list):
                    # Join text blocks
                    text_content = " ".join(
                        block.get("text", "") for block in content if isinstance(block, dict)
                    )
                else:
                    text_content = str(content)

                text_escaped = text_content.replace("'", "\\'").replace("\n", "\\n")
                return f"data: {{'type': 'text_delta', 'content': '{text_escaped}'}}\n\n"

        # Unknown message type - ignore
        return None

    async def stream(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute conversational agent with streaming output using Claude SDK.

        Uses Claude Agent SDK's query() function to handle:
        - Skill execution (via .claude/skills/ filesystem discovery)
        - Subagent spawning (via Task tool)
        - Natural language responses (via Claude's reasoning)
        - Permission handling (via hooks)

        Args:
            input_data: Chat input with message and context
            context: Agent execution context

        Yields:
            SSE chunks with response content
        """
        # Build SDK options
        try:
            # Get API key from workspace settings
            api_key = await self._get_api_key(context.workspace_id)

            # Build subagent definitions for SDK
            subagent_definitions = {
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

            # Handle session resumption
            session_id_str = None
            if input_data.session_id and self._session_handler:
                # Try to get existing session (only if session handler available)
                existing_session = await self._session_handler.get_session(input_data.session_id)
                if existing_session:
                    session_id_str = str(existing_session.session_id)

            # SDK options configuration
            sdk_options = ClaudeAgentOptions(  # type: ignore[call-arg]
                model=self.DEFAULT_MODEL,
                # Enable built-in tools (use allowed_tools parameter)
                allowed_tools=[
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Glob",
                    "Grep",
                    "Skill",  # For skill execution
                    "Task",  # For subagent spawning
                    "AskUserQuestion",  # For clarifications
                    "WebFetch",
                    "WebSearch",
                ],
                # Load .claude/ directory for project context
                setting_sources=["project"],  # type: ignore[call-arg]
                # Register subagents
                agents=subagent_definitions,  # type: ignore[call-arg]
                # Permission handling
                permission_mode="default",  # type: ignore[call-arg]
                # Session resumption
                resume=session_id_str,  # type: ignore[call-arg]
            )

            # Set context for observability and debugging
            set_api_key(api_key)
            set_workspace_context(context.workspace_id, context.user_id)

            # CRITICAL: Acquire lock before setting os.environ to prevent race conditions
            # Multiple concurrent requests from different workspaces must not clobber each other's API keys
            async with get_api_key_lock():
                original_api_key = os.getenv("ANTHROPIC_API_KEY")
                os.environ["ANTHROPIC_API_KEY"] = api_key

                try:
                    # Stream from Claude SDK (SDK reads API key from os.environ)
                    async for message in query(prompt=input_data.message, options=sdk_options):
                        # Transform SDK message to SSE event
                        sse_event = self._transform_sdk_message(message, context)
                        if sse_event:
                            yield sse_event
                finally:
                    # Restore original API key
                    if original_api_key:
                        os.environ["ANTHROPIC_API_KEY"] = original_api_key
                    elif "ANTHROPIC_API_KEY" in os.environ:
                        del os.environ["ANTHROPIC_API_KEY"]
                    # Clear context variables
                    clear_context()

        except Exception as e:
            # Error handling
            error_msg = str(e).replace("'", "\\'")
            yield f"data: {{'type': 'error', 'error_type': 'sdk_error', 'message': '{error_msg}'}}\n\n"

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
                "model": self.DEFAULT_MODEL,
            },
        )


__all__ = [
    "ChatInput",
    "ChatOutput",
    "PilotSpaceAgent",
    "SkillRegistry",
]
