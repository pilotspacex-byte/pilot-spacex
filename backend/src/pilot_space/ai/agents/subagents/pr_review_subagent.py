"""PR Review Subagent for multi-turn code review conversations.

Provides interactive PR review with:
- Architecture analysis
- Security scanning
- Code quality assessment
- Performance analysis
- Documentation review

Reference: docs/architect/ai-layer.md
Design Decision: DD-006 (Unified AI PR Review)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.sdk.config import MODEL_SONNET

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class PRReviewInput:
    """Input for PR review subagent.

    Attributes:
        repository_id: Repository UUID
        pr_number: Pull request number
        include_architecture: Include architecture review
        include_security: Include security scanning
        include_performance: Include performance analysis
    """

    repository_id: UUID
    pr_number: int
    include_architecture: bool = True
    include_security: bool = True
    include_performance: bool = True


@dataclass
class PRReviewOutput:
    """Output from PR review.

    Attributes:
        summary: High-level review summary
        approval_status: APPROVED | CHANGES_REQUESTED | COMMENTED
        architecture_findings: Architecture-level concerns
        security_findings: Security vulnerabilities found
        code_quality_findings: Code quality issues
        performance_findings: Performance concerns
        documentation_findings: Documentation gaps
    """

    summary: str
    approval_status: str
    architecture_findings: list[dict[str, Any]]
    security_findings: list[dict[str, Any]]
    code_quality_findings: list[dict[str, Any]]
    performance_findings: list[dict[str, Any]]
    documentation_findings: list[dict[str, Any]]


class PRReviewSubagent(StreamingSDKBaseAgent[PRReviewInput, PRReviewOutput]):
    """Subagent for interactive PR review conversations.

    Provides multi-turn streaming review with Claude Agent SDK.
    Inherits from StreamingSDKBaseAgent for SSE support.

    Usage:
        subagent = PRReviewSubagent(...)
        async for chunk in subagent.execute_stream(input_data, context):
            yield chunk
    """

    AGENT_NAME = "pr_review_subagent"
    DEFAULT_MODEL = MODEL_SONNET

    def get_system_prompt(self) -> str:
        """Get system prompt for PR review.

        Returns:
            System prompt string with review guidelines
        """
        return """You are a senior software engineer conducting a thorough PR review.

Review the pull request across these dimensions:
1. **Architecture**: Design patterns, separation of concerns, maintainability
2. **Security**: OWASP vulnerabilities, authentication, authorization, data validation
3. **Code Quality**: Readability, naming, complexity, error handling
4. **Performance**: Algorithmic complexity, database queries, caching
5. **Documentation**: Code comments, API docs, README updates

For each finding:
- Severity: 🔴 CRITICAL | 🟡 WARNING | 🔵 SUGGESTION
- Location: File path and line number
- Rationale: Why this is an issue
- Fix: Specific code suggestion

Be constructive and specific. Focus on significant issues that impact
production reliability, security, or maintainability."""

    def get_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for PR review.

        Returns:
            List of tool definitions for GitHub and code analysis
        """
        return [
            {
                "name": "get_pr_diff",
                "description": "Get full diff for pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["repository_id", "pr_number"],
                },
            },
            {
                "name": "get_pr_files",
                "description": "Get list of changed files in PR",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["repository_id", "pr_number"],
                },
            },
            {
                "name": "add_review_comment",
                "description": "Add inline comment to specific line in PR",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                        "file_path": {"type": "string"},
                        "line_number": {"type": "integer"},
                        "severity": {"enum": ["critical", "warning", "suggestion"]},
                        "comment": {"type": "string"},
                        "fix_suggestion": {"type": "string"},
                    },
                    "required": [
                        "repository_id",
                        "pr_number",
                        "file_path",
                        "line_number",
                        "severity",
                        "comment",
                    ],
                },
            },
        ]

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
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                msg = "No workspace_id provided and ANTHROPIC_API_KEY not set"
                raise ValueError(msg)
            return api_key

        # BYOK: Falls back to env var. Per-workspace vault lookup pending DD-060.
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = (
                f"Anthropic API key not found for workspace {workspace_id}. "
                "Please set ANTHROPIC_API_KEY environment variable or "
                "configure in workspace settings."
            )
            raise ValueError(msg)
        return api_key

    def _build_prompt(self, input_data: PRReviewInput) -> str:
        """Build PR review prompt from input data.

        Args:
            input_data: PR review input

        Returns:
            Formatted prompt string
        """
        review_dimensions = []
        if input_data.include_architecture:
            review_dimensions.append("architecture analysis")
        if input_data.include_security:
            review_dimensions.append("security scanning")
        if input_data.include_performance:
            review_dimensions.append("performance analysis")

        dimensions_str = (
            ", ".join(review_dimensions) if review_dimensions else "comprehensive review"
        )

        return f"""Review Pull Request #{input_data.pr_number} in repository {input_data.repository_id}.

Focus on: {dimensions_str}

Provide detailed findings with:
- Severity level (🔴 CRITICAL | 🟡 WARNING | 🔵 SUGGESTION)
- File path and line number
- Clear rationale
- Specific fix recommendations

Use available tools to:
1. Get PR diff and changed files
2. Analyze code for issues
3. Add inline review comments where appropriate

Be constructive and focus on production reliability, security, and maintainability."""

    def _create_agent_options(self, context: AgentContext) -> ClaudeAgentOptions:
        """Create Claude SDK options for PR review.

        Args:
            context: Agent execution context

        Returns:
            ClaudeAgentOptions configured for PR review
        """
        return ClaudeAgentOptions(  # type: ignore[call-arg]
            model=self.DEFAULT_MODEL,
            allowed_tools=[
                "Read",
                "Glob",
                "Grep",
                "WebFetch",
            ],
            setting_sources=["project"],  # type: ignore[call-arg]
        )

    def _transform_sdk_message(self, message: Any, context: AgentContext) -> str | None:
        """Transform Claude SDK message to SSE event.

        Handles real Claude Agent SDK message types:
        - SystemMessage: skip (init event)
        - AssistantMessage: content is list[TextBlock]
        - ResultMessage: completion signal

        Args:
            message: SDK message object (SystemMessage | AssistantMessage | ResultMessage)
            context: Agent execution context

        Returns:
            SSE-formatted string or None if message should be ignored
        """
        msg_type = type(message).__name__

        # SystemMessage: skip (init event)
        if msg_type == "SystemMessage":
            return None

        # AssistantMessage: content is list[TextBlock]
        if msg_type == "AssistantMessage":
            content = getattr(message, "content", None)
            if content is None:
                return None
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
                    elif hasattr(block, "text"):
                        parts.append(block.text)
                text_content = " ".join(parts)
            else:
                text_content = str(content)
            if not text_content.strip():
                return None
            return f"event: text_delta\ndata: {json.dumps({'messageId': str(uuid4()), 'delta': text_content})}\n\n"

        # ResultMessage: completion
        if msg_type == "ResultMessage":
            return f"event: message_stop\ndata: {json.dumps({'messageId': str(uuid4()), 'stopReason': 'end_turn'})}\n\n"

        return None

    async def stream(
        self,
        input_data: PRReviewInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute PR review with streaming.

        Args:
            input_data: PR review input
            context: Agent execution context

        Yields:
            SSE chunks with review findings
        """
        try:
            # Get API key from context
            api_key = await self._get_api_key(context.workspace_id)

            # Build prompt specific to PR review
            prompt = self._build_prompt(input_data)

            # Create SDK options with env parameter (no os.environ mutation)
            sdk_options = self._create_agent_options(context)
            sdk_env: dict[str, str] = {"ANTHROPIC_API_KEY": api_key}
            if "PATH" not in sdk_env:
                sdk_env["PATH"] = os.environ.get("PATH", "")
            sdk_options.env = sdk_env

            # Set context for observability
            set_workspace_context(context.workspace_id, context.user_id)

            client = ClaudeSDKClient(sdk_options)
            try:
                await client.connect()
                await client.query(prompt)
                async for message in client.receive_response():
                    sse_event = self._transform_sdk_message(message, context)
                    if sse_event:
                        yield sse_event
            finally:
                await client.disconnect()
                clear_context()

        except Exception as e:
            error_msg = str(e).replace("'", "\\'")
            yield f"data: {{'type': 'error', 'error_type': 'pr_review_error', 'message': '{error_msg}'}}\n\n"
