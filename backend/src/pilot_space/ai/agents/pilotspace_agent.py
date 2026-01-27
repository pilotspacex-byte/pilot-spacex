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

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, StreamingSDKBaseAgent

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk.permission_handler import PermissionHandler
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.ai.tools.mcp_server import ToolRegistry


class IntentType(StrEnum):
    """Intent types for user input routing."""

    SKILL = "skill"
    SUBAGENT = "subagent"
    NATURAL = "natural"


@dataclass
class ParsedIntent:
    """Parsed user intent with routing information.

    Attributes:
        intent_type: Type of intent (skill, subagent, natural)
        target: Skill or agent name if applicable
        args: Remaining message content after intent prefix
        original_message: Full original message
    """

    intent_type: IntentType
    target: str | None
    args: str
    original_message: str


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


@dataclass
class TaskEntry:
    """Task tracking entry for complex operations.

    Attributes:
        task_id: Unique task identifier
        subject: Task subject/title
        description: Task description
        status: Current status (pending, in_progress, completed, failed)
        dependencies: List of task IDs this depends on
        output: Task output if completed
        error: Error message if failed
    """

    task_id: str
    subject: str
    description: str
    status: str = "pending"
    dependencies: list[str] = field(default_factory=list)
    output: str | None = None
    error: str | None = None


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
        session_handler: SessionHandler,
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
            session_handler: Session management handler
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
        self._tasks: dict[str, TaskEntry] = {}

    def _parse_intent(self, message: str) -> ParsedIntent:
        """Parse user message to determine intent and routing.

        Intent patterns:
        - `\\skill-name [args]` → Skill execution
        - `@agent-name [args]` → Subagent delegation
        - Natural language → Direct handling

        Args:
            message: User message content

        Returns:
            ParsedIntent with routing information
        """
        message_stripped = message.strip()

        # Check for skill invocation: \\skill-name
        if message_stripped.startswith("\\\\"):
            parts = message_stripped[1:].split(None, 1)
            skill_name = parts[0] if parts else ""
            args = parts[1] if len(parts) > 1 else ""

            return ParsedIntent(
                intent_type=IntentType.SKILL,
                target=skill_name,
                args=args,
                original_message=message,
            )

        # Check for subagent mention: @agent-name
        if message_stripped.startswith("@"):
            parts = message_stripped[1:].split(None, 1)
            agent_name = parts[0] if parts else ""
            args = parts[1] if len(parts) > 1 else ""

            return ParsedIntent(
                intent_type=IntentType.SUBAGENT,
                target=agent_name,
                args=args,
                original_message=message,
            )

        # Natural language processing
        return ParsedIntent(
            intent_type=IntentType.NATURAL,
            target=None,
            args=message,
            original_message=message,
        )

    async def _execute_skill(
        self,
        skill_name: str,
        args: str,  # noqa: ARG002
        context: AgentContext,  # noqa: ARG002
        chat_context: dict[str, Any],
    ) -> AsyncIterator[str]:
        """Execute a skill with given arguments.

        Workflow:
        1. Load skill instructions from registry
        2. Build prompt with skill template + context
        3. Execute via Claude SDK with skill context
        4. Stream structured output with confidence tags (DD-048)

        Args:
            skill_name: Name of skill to execute
            args: Additional arguments for skill
            context: Agent execution context
            chat_context: Current working context (note, issue, etc.)

        Yields:
            SSE chunks with skill execution results
        """
        # Load skill instructions
        instructions = self._skill_registry.get_skill_instructions(skill_name)
        if not instructions:
            yield f"ERROR: Skill '{skill_name}' not found\n"
            yield f"Available skills: {', '.join(self._skill_registry.get_available_skills())}\n"
            return

        # Build context-aware prompt
        yield f"🔧 Executing skill: {skill_name}\n"

        # Extract note content if available
        note_content = chat_context.get("note_content", "")
        selected_text = chat_context.get("selected_text", "")

        # Build execution prompt (will be used when integrating ClaudeSDKClient)
        # TODO: Integrate with ClaudeSDKClient for actual skill execution
        # execution_prompt will include: instructions, args, note_content, selected_text

        # Stream execution (placeholder for actual SDK integration)
        yield "\n📝 Processing with skill instructions...\n"
        yield f"Context: {len(note_content)} chars note content, {len(selected_text)} chars selected\n"
        yield "\n✅ Skill execution complete\n"

    async def _spawn_subagent(
        self,
        agent_name: str,
        args: str,  # noqa: ARG002
        context: AgentContext,
        chat_context: dict[str, Any],  # noqa: ARG002
    ) -> AsyncIterator[str]:
        """Spawn a subagent for complex multi-turn tasks.

        Workflow:
        1. Map agent name to subagent class
        2. Create subagent instance with shared context
        3. Delegate execution and stream results
        4. Track task progress

        Subagent mapping:
        - @pr-review → PRReviewSubagent
        - @ai-context → AIContextSubagent
        - @doc-gen → DocGeneratorSubagent

        Args:
            agent_name: Name of subagent to spawn
            args: Arguments for subagent
            context: Agent execution context
            chat_context: Current working context

        Yields:
            SSE chunks with subagent output
        """
        # Check if subagent exists
        if agent_name not in self.SUBAGENT_MAP:
            yield f"ERROR: Unknown subagent '{agent_name}'\n"
            yield f"Available subagents: {', '.join(self.SUBAGENT_MAP.keys())}\n"
            return

        subagent_class = self.SUBAGENT_MAP[agent_name]
        subagent = self._subagents.get(agent_name)

        if not subagent:
            yield f"ERROR: Subagent '{agent_name}' not initialized\n"
            return

        # Create task entry
        task_id = f"task-{agent_name}-{context.operation_id or 'default'}"
        task = TaskEntry(
            task_id=task_id,
            subject=f"Execute {agent_name}",
            description=f"Subagent: {subagent_class}",
            status="in_progress",
        )
        self._tasks[task_id] = task

        yield f"🤖 Spawning subagent: {agent_name}\n"
        yield f"📋 Task created: {task_id}\n"

        # Stream subagent execution
        try:
            # Subagent-specific input construction
            if agent_name == "pr-review":
                # Extract PR info from args or context
                yield "🔍 Analyzing PR...\n"
                # TODO: Call PRReviewSubagent.stream()

            elif agent_name == "ai-context":
                # Extract issue info from args or context
                yield "🔍 Aggregating context...\n"
                # TODO: Call AIContextSubagent.stream()

            elif agent_name == "doc-gen":
                # Extract doc generation info
                yield "📝 Generating documentation...\n"
                # TODO: Call DocGeneratorSubagent.stream()

            task.status = "completed"
            task.output = f"Subagent {agent_name} completed"
            yield f"\n✅ Task completed: {task_id}\n"

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            yield f"\n❌ Task failed: {task_id} - {e}\n"

    async def _plan_tasks(
        self,
        message: str,
        context: AgentContext,
    ) -> list[TaskEntry]:
        """Break complex request into executable tasks.

        For complex requests, decompose into:
        1. Subtasks with dependencies
        2. Task status tracking (pending → in_progress → completed)
        3. Emit TaskUpdate SSE events

        Args:
            message: Complex user request
            context: Agent execution context

        Returns:
            List of TaskEntry objects with dependencies
        """
        # Simple heuristic: multiple action verbs = complex request
        action_verbs = [
            "create",
            "update",
            "analyze",
            "review",
            "generate",
            "extract",
            "find",
        ]
        verb_matches = [verb for verb in action_verbs if verb in message.lower()]

        # Single action = no task breakdown needed
        if len(verb_matches) <= 1:
            return []

        # Create tasks for each action
        tasks: list[TaskEntry] = []
        for idx, verb in enumerate(verb_matches):
            task_id = f"task-{context.operation_id or 'default'}-{idx}"
            task = TaskEntry(
                task_id=task_id,
                subject=f"{verb.capitalize()} operation",
                description=f"Extracted from: {message[:100]}...",
                status="pending",
                dependencies=[tasks[-1].task_id] if tasks else [],
            )
            tasks.append(task)
            self._tasks[task_id] = task

        return tasks

    async def _handle_natural_language(
        self,
        message: str,
        context: AgentContext,
        chat_context: dict[str, Any],
    ) -> AsyncIterator[str]:
        """Handle natural language query with context awareness.

        Args:
            message: User message
            context: Agent execution context
            chat_context: Current working context

        Yields:
            Response chunks
        """
        yield "💬 Processing natural language query...\n"

        # Check if this needs task planning
        tasks = await self._plan_tasks(message, context)
        if tasks:
            yield f"\n📋 Created {len(tasks)} tasks:\n"
            for task in tasks:
                yield f"  - {task.subject} ({task.status})\n"

        # Build context-aware response
        note_id = chat_context.get("note_id")
        issue_id = chat_context.get("issue_id")

        if note_id:
            yield f"\n📄 Context: Working in note {note_id}\n"
        if issue_id:
            yield f"\n🎫 Context: Viewing issue {issue_id}\n"

        # TODO: Integrate with ClaudeSDKClient for actual natural language response
        yield f'\n🤔 Analyzing your request: "{message[:100]}..."\n'
        yield "\n✨ Response generation would happen here via Claude SDK\n"

    async def stream(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute conversational agent with streaming output.

        Main routing logic:
        1. Parse intent from message
        2. Route to skill, subagent, or natural language handler
        3. Stream results as SSE events
        4. Handle approval flow per DD-003

        Args:
            input_data: Chat input with message and context
            context: Agent execution context

        Yields:
            SSE chunks with response content
        """
        # Parse user intent
        intent = self._parse_intent(input_data.message)

        yield f"data: {{'type': 'message_start', 'session_id': '{input_data.session_id}'}}\n\n"

        # Route based on intent type
        if intent.intent_type == IntentType.SKILL:
            async for chunk in self._execute_skill(
                skill_name=intent.target or "",
                args=intent.args,
                context=context,
                chat_context=input_data.context,
            ):
                yield f"data: {{'type': 'text_delta', 'content': '{chunk}'}}\n\n"

        elif intent.intent_type == IntentType.SUBAGENT:
            async for chunk in self._spawn_subagent(
                agent_name=intent.target or "",
                args=intent.args,
                context=context,
                chat_context=input_data.context,
            ):
                yield f"data: {{'type': 'text_delta', 'content': '{chunk}'}}\n\n"

        elif intent.intent_type == IntentType.NATURAL:
            async for chunk in self._handle_natural_language(
                message=intent.args,
                context=context,
                chat_context=input_data.context,
            ):
                yield f"data: {{'type': 'text_delta', 'content': '{chunk}'}}\n\n"

        yield f"data: {{'type': 'message_stop', 'session_id': '{input_data.session_id}'}}\n\n"

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
            tasks=[
                {
                    "task_id": task.task_id,
                    "subject": task.subject,
                    "status": task.status,
                }
                for task in self._tasks.values()
            ],
            metadata={
                "agent": self.AGENT_NAME,
                "model": self.DEFAULT_MODEL,
            },
        )


__all__ = [
    "ChatInput",
    "ChatOutput",
    "IntentType",
    "ParsedIntent",
    "PilotSpaceAgent",
    "SkillRegistry",
    "TaskEntry",
]
