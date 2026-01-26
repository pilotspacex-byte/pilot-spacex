"""SDK Orchestrator for Claude Agent SDK.

Central coordinator for all AI agents, integrating infrastructure
services for approval, cost tracking, and session management.

Reference: docs/architect/claude-agent-sdk-architecture.md
Design Decisions: DD-002 (BYOK), DD-003 (Approval Flow)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    AgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.approval import ApprovalService
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.session.session_manager import SessionManager
    from pilot_space.ai.tools.mcp_server import ToolRegistry


class AgentName(StrEnum):
    """Registered agent names.

    Used as keys in the agent registry and for routing.
    """

    # Note-related agents
    GHOST_TEXT = "ghost_text"
    MARGIN_ANNOTATION = "margin_annotation"
    ISSUE_EXTRACTOR = "issue_extractor"

    # Issue-related agents
    AI_CONTEXT = "ai_context"
    CONVERSATION = "conversation"
    ISSUE_ENHANCER = "issue_enhancer"
    ASSIGNEE_RECOMMENDER = "assignee_recommender"
    DUPLICATE_DETECTOR = "duplicate_detector"

    # PR/Code agents
    PR_REVIEW = "pr_review"
    COMMIT_LINKER = "commit_linker"

    # Documentation agents (T079-T090)
    DOC_GENERATOR = "doc_generator"
    TASK_DECOMPOSER = "task_decomposer"
    DIAGRAM_GENERATOR = "diagram_generator"


class ActionClassification(StrEnum):
    """DD-003 action classification for approval flow."""

    AUTO_EXECUTE = "auto_execute"
    DEFAULT_REQUIRE_APPROVAL = "default_require"
    CRITICAL_REQUIRE_APPROVAL = "critical_require"


@dataclass
class ExecutionResult:
    """Result from orchestrator execution.

    Extends AgentResult with approval flow status.
    """

    success: bool
    output: Any
    cost_usd: float = 0.0
    requires_approval: bool = False
    approval_id: UUID | None = None
    error: str | None = None

    @classmethod
    def from_agent_result(
        cls,
        result: AgentResult[Any],
    ) -> ExecutionResult:
        """Convert AgentResult to ExecutionResult."""
        return cls(
            success=result.success,
            output=result.output,
            cost_usd=result.cost_usd,
            error=result.error,
        )

    @classmethod
    def approval_required(
        cls,
        approval_id: UUID,
        message: str = "Approval required",
    ) -> ExecutionResult:
        """Create result indicating approval is needed."""
        return cls(
            success=True,
            output={"message": message},
            requires_approval=True,
            approval_id=approval_id,
        )


class SDKOrchestrator:
    """Main orchestrator for Claude Agent SDK agents.

    Responsibilities:
    - Agent registration and routing
    - Approval flow integration (DD-003)
    - Session management for multi-turn agents
    - Cost tracking aggregation
    - SSE streaming coordination
    - API key validation (DD-002)

    Usage:
        orchestrator = SDKOrchestrator(...)
        orchestrator.register_agents()
        result = await orchestrator.execute("pr_review", input_data, context)
    """

    # DD-003 action classifications
    ACTION_CLASSIFICATIONS: ClassVar[dict[str, ActionClassification]] = {
        # Auto-execute (non-destructive)
        "ghost_text": ActionClassification.AUTO_EXECUTE,
        "margin_annotation": ActionClassification.AUTO_EXECUTE,
        "ai_context": ActionClassification.AUTO_EXECUTE,
        "pr_review": ActionClassification.AUTO_EXECUTE,
        "duplicate_check": ActionClassification.AUTO_EXECUTE,
        "assignee_recommend": ActionClassification.AUTO_EXECUTE,
        "doc_generate": ActionClassification.AUTO_EXECUTE,
        "diagram_generate": ActionClassification.AUTO_EXECUTE,
        # Default require approval (creates/modifies entities)
        "create_issue": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "create_annotation": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_commit": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "update_issue": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Critical require approval (destructive)
        "delete_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "merge_pr": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "close_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
    }

    def __init__(
        self,
        key_storage: SecureKeyStorage,
        approval_service: ApprovalService,
        cost_tracker: CostTracker,
        session_manager: SessionManager,
        provider_selector: ProviderSelector,
        resilient_executor: ResilientExecutor,
        tool_registry: ToolRegistry,
    ) -> None:
        """Initialize orchestrator with infrastructure dependencies.

        Args:
            key_storage: Secure storage for API keys (DD-002)
            approval_service: Approval flow service (DD-003)
            cost_tracker: Cost tracking service
            session_manager: Session management for multi-turn
            provider_selector: Provider/model selection
            resilient_executor: Retry and circuit breaker
            tool_registry: MCP tool registry
        """
        self._key_storage = key_storage
        self._approval_service = approval_service
        self._cost_tracker = cost_tracker
        self._session_manager = session_manager
        self._provider_selector = provider_selector
        self._resilient_executor = resilient_executor
        self._tool_registry = tool_registry

        # Agent registry
        self._agents: dict[str, SDKBaseAgent[Any, Any]] = {}

    def register_agent(self, name: str, agent: SDKBaseAgent[Any, Any]) -> None:
        """Register an agent instance.

        Args:
            name: Agent identifier (use AgentName enum values)
            agent: Configured agent instance
        """
        self._agents[name] = agent

    def get_agent(self, name: str) -> SDKBaseAgent[Any, Any] | None:
        """Get a registered agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    async def ensure_api_key(
        self, workspace_id: UUID, provider: str = "anthropic"
    ) -> bool:
        """Verify workspace has valid API key.

        Args:
            workspace_id: Workspace to check
            provider: Provider to check key for

        Returns:
            True if valid key exists

        Raises:
            ValueError: If no valid key configured
        """
        key = await self._key_storage.get_api_key(workspace_id, provider)
        if not key:
            msg = f"Workspace has no {provider} API key configured"
            raise ValueError(msg)
        return True

    def classify_action(self, action_type: str) -> ActionClassification:
        """Classify action per DD-003.

        Args:
            action_type: Action type string

        Returns:
            Classification for approval flow
        """
        return self.ACTION_CLASSIFICATIONS.get(
            action_type,
            ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        )

    async def execute(
        self,
        agent_name: str,
        input_data: Any,
        context: AgentContext,
    ) -> ExecutionResult:
        """Execute an agent without approval flow.

        Use for actions that don't require human approval.

        Args:
            agent_name: Name of agent to execute
            input_data: Agent-specific input
            context: Execution context

        Returns:
            ExecutionResult with output and cost

        Raises:
            KeyError: If agent_name not registered
            ValueError: If no API key configured
        """
        agent = self._agents.get(agent_name)
        if not agent:
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Agent '{agent_name}' not registered",
            )

        # Verify API key
        await self.ensure_api_key(context.workspace_id)

        # Execute agent
        result = await agent.run(input_data, context)

        return ExecutionResult.from_agent_result(result)

    async def execute_with_approval(
        self,
        agent_name: str,
        action_type: str,
        input_data: Any,
        context: AgentContext,
        *,
        payload: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute an agent with approval flow (DD-003).

        For actions classified as CRITICAL or DEFAULT_REQUIRE,
        creates an approval request and returns without executing.

        Args:
            agent_name: Name of agent to execute
            action_type: Type of action for classification
            input_data: Agent-specific input
            context: Execution context
            payload: Optional approval payload

        Returns:
            ExecutionResult - check requires_approval and approval_id
        """
        from pilot_space.ai.infrastructure.approval import ActionType

        classification = self.classify_action(action_type)

        # Convert action_type string to ActionType enum
        # Map common action names to ActionType values
        action_type_map = {
            "delete_issue": ActionType.DELETE_ISSUE,
            "delete_workspace": ActionType.DELETE_WORKSPACE,
            "delete_project": ActionType.DELETE_PROJECT,
            "delete_note": ActionType.DELETE_NOTE,
            "merge_pr": ActionType.MERGE_PR,
            "bulk_delete": ActionType.BULK_DELETE,
            "create_sub_issues": ActionType.CREATE_SUB_ISSUES,
            "extract_issues": ActionType.EXTRACT_ISSUES,
            "publish_docs": ActionType.PUBLISH_DOCS,
            "post_pr_comments": ActionType.POST_PR_COMMENTS,
        }

        action_enum = action_type_map.get(action_type)

        if classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            # Always create approval request
            if not action_enum:
                # For unknown critical actions, use a default
                action_enum = ActionType.DELETE_ISSUE

            approval_request = await self._approval_service.create_approval_request(
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                action_type=action_enum,
                action_data=payload or {"input": input_data},
                requested_by_agent=agent_name,
            )
            return ExecutionResult.approval_required(
                approval_request,
                f"Critical action '{action_type}' requires approval",
            )

        if classification == ActionClassification.DEFAULT_REQUIRE_APPROVAL:
            # Check workspace settings
            if not action_enum:
                # For unknown default actions, use a default
                action_enum = ActionType.CREATE_SUB_ISSUES

            requires = self._approval_service.check_approval_required(
                action_enum,
            )
            if requires:
                approval_request = (
                    await self._approval_service.create_approval_request(
                        workspace_id=context.workspace_id,
                        user_id=context.user_id,
                        action_type=action_enum,
                        action_data=payload or {"input": input_data},
                        requested_by_agent=agent_name,
                    )
                )
                return ExecutionResult.approval_required(
                    approval_request,
                    f"Action '{action_type}' requires approval",
                )

        # AUTO_EXECUTE: proceed
        return await self.execute(agent_name, input_data, context)

    async def stream(
        self,
        agent_name: str,
        input_data: Any,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream output from a streaming agent.

        Args:
            agent_name: Name of streaming agent
            input_data: Agent-specific input
            context: Execution context

        Yields:
            Output tokens/chunks as strings

        Raises:
            TypeError: If agent doesn't support streaming
            KeyError: If agent not registered
        """
        agent = self._agents.get(agent_name)
        if not agent:
            yield f"ERROR: Agent '{agent_name}' not registered"
            return

        if not isinstance(agent, StreamingSDKBaseAgent):
            yield f"ERROR: Agent '{agent_name}' does not support streaming"
            return

        # Verify API key
        try:
            await self.ensure_api_key(context.workspace_id)
        except ValueError as e:
            yield f"ERROR: {e}"
            return

        # Stream from agent
        async for chunk in agent.run_stream(input_data, context):
            yield chunk

    # Session management helpers
    async def get_session(
        self,
        session_id: UUID,
    ) -> dict[str, Any] | None:
        """Get existing session data."""
        from pilot_space.ai.session.session_manager import SessionNotFoundError

        try:
            session = await self._session_manager.get_session(session_id)
            return session.to_dict()
        except SessionNotFoundError:
            return None

    async def create_session(
        self,
        context: AgentContext,
        agent_name: str,
        initial_data: dict[str, Any] | None = None,
    ) -> UUID:
        """Create new session for multi-turn agent."""
        session = await self._session_manager.create_session(
            user_id=context.user_id,
            workspace_id=context.workspace_id,
            agent_name=agent_name,
            initial_context=initial_data or {},
        )
        return session.id

    async def update_session(
        self,
        session_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Update session data."""
        from pilot_space.ai.session.session_manager import AIMessage

        # Extract message if provided
        message = None
        if "message" in data:
            message_data = data.pop("message")
            message = AIMessage(
                role=message_data.get("role", "user"),
                content=message_data.get("content", ""),
            )

        await self._session_manager.update_session(
            session_id=session_id,
            message=message,
            context_update=data,
        )

    async def end_session(
        self,
        session_id: UUID,
    ) -> None:
        """End and cleanup session."""
        await self._session_manager.end_session(session_id)


__all__ = [
    "ActionClassification",
    "AgentName",
    "ExecutionResult",
    "SDKOrchestrator",
]
