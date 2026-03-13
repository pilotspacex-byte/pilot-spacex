"""Documentation Generator Subagent for interactive doc creation.

Provides conversational documentation generation:
- API documentation from code
- Architecture decision records
- README and setup guides
- Code comments and docstrings

Reference: docs/architect/ai-layer.md
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
from pilot_space.ai.sdk.config import MODEL_SONNET, build_sdk_env

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class DocGeneratorInput:
    """Input for documentation generator.

    Attributes:
        workspace_id: Workspace UUID
        doc_type: Type of documentation (api, adr, readme, comments)
        source_files: List of source file paths
        output_format: Output format (markdown, rst, html)
    """

    workspace_id: UUID
    doc_type: str
    source_files: list[str]
    output_format: str = "markdown"


@dataclass
class DocGeneratorOutput:
    """Output from documentation generator.

    Attributes:
        content: Generated documentation content
        doc_type: Type of documentation generated
        format: Output format
        metadata: Additional metadata (word count, sections, etc.)
    """

    content: str
    doc_type: str
    format: str
    metadata: dict[str, Any]


class DocGeneratorSubagent(StreamingSDKBaseAgent[DocGeneratorInput, DocGeneratorOutput]):
    """Subagent for interactive documentation generation.

    Provides multi-turn doc creation with code analysis,
    style consistency, and technical accuracy.

    Usage:
        subagent = DocGeneratorSubagent(...)
        async for chunk in subagent.execute_stream(input_data, context):
            yield chunk
    """

    AGENT_NAME = "doc_generator_subagent"
    DEFAULT_MODEL = MODEL_SONNET

    def get_system_prompt(self) -> str:
        """Get system prompt for doc generation.

        Returns:
            System prompt string with documentation guidelines
        """
        return """You are a technical documentation expert.

Your role:
1. **Analyze Code**: Understand code structure, patterns, and intent
2. **Write Clear Docs**: Create accurate, readable documentation
3. **Follow Style**: Match project documentation style and conventions
4. **Include Examples**: Provide practical usage examples

Documentation types:
- **API Docs**: Endpoints, parameters, responses, authentication
- **ADRs**: Context, decision, consequences, alternatives
- **README**: Overview, setup, usage, contributing
- **Code Comments**: Docstrings, inline explanations, examples

Guidelines:
- Use active voice and present tense
- Include code examples with syntax highlighting
- Add links to related documentation
- Document error cases and edge conditions
- Keep paragraphs concise (3-4 sentences)

Format with proper Markdown:
- Use headers (##, ###) for structure
- Code blocks with language specifiers
- Tables for parameters/responses
- Lists for steps and options"""

    def get_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for doc generation.

        Returns:
            List of tool definitions for code analysis
        """
        return [
            {
                "name": "read_source_file",
                "description": "Read source code file for documentation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "analyze_api_endpoints",
                "description": "Analyze API endpoints in codebase",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_paths": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["file_paths"],
                },
            },
            {
                "name": "get_existing_docs",
                "description": "Retrieve existing documentation for consistency",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "doc_pattern": {"type": "string"},
                    },
                    "required": ["workspace_id"],
                },
            },
        ]

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        """Get Anthropic API key for this request.

        AIGOV-05 BYOK enforcement:
        - workspace_id provided → BYOK required; raises AINotConfiguredError if missing.
          No env fallback — using the platform key for workspace calls violates BYOK.
        - workspace_id=None → system agent; env key permitted.

        Args:
            workspace_id: Workspace UUID, or None for system-level operations.

        Returns:
            Decrypted API key string.

        Raises:
            AINotConfiguredError: If workspace has no BYOK key or system has no env key.
        """
        from pilot_space.ai.exceptions import AINotConfiguredError

        if workspace_id is not None:
            # Workspace-scoped call: BYOK required, no env fallback (AIGOV-05).
            # TODO Phase 4 (04-07): Wire key_storage via DI; for now raise immediately
            # when workspace_id is provided and there's no env override for tests.
            raise AINotConfiguredError(workspace_id=workspace_id)

        # System-only: env key permitted
        api_key = os.getenv("ANTHROPIC_API_KEY")  # _SYSTEM_ONLY: never for workspace calls
        if not api_key:
            raise AINotConfiguredError(workspace_id=None)
        return api_key

    def _build_prompt(self, input_data: DocGeneratorInput) -> str:
        """Build documentation generation prompt from input data.

        Args:
            input_data: Doc generator input

        Returns:
            Formatted prompt string
        """
        files_list = "\n".join(f"- {file}" for file in input_data.source_files)

        doc_type_guidance = {
            "api": "Document API endpoints with parameters, responses, and authentication",
            "adr": "Create Architecture Decision Record with context, decision, consequences, alternatives",
            "readme": "Generate README with overview, setup instructions, usage examples, contributing guidelines",
            "comments": "Add docstrings and inline comments explaining code intent and usage",
        }.get(input_data.doc_type, "Create comprehensive technical documentation")

        return f"""Generate {input_data.doc_type} documentation in {input_data.output_format} format.

Source files:
{files_list}

Documentation guidance:
{doc_type_guidance}

Requirements:
- Use active voice and present tense
- Include code examples with syntax highlighting
- Add links to related documentation
- Document error cases and edge conditions
- Keep paragraphs concise (3-4 sentences)

Format with proper {input_data.output_format}:
- Use headers (##, ###) for structure
- Code blocks with language specifiers
- Tables for parameters/responses
- Lists for steps and options

Use available tools to:
1. Read source files for analysis
2. Analyze API endpoints if applicable
3. Review existing documentation for consistency
4. Generate comprehensive, accurate documentation"""

    def _create_agent_options(self, context: AgentContext) -> ClaudeAgentOptions:
        """Create Claude SDK options for doc generation.

        Args:
            context: Agent execution context

        Returns:
            ClaudeAgentOptions configured for doc generation
        """
        return ClaudeAgentOptions(  # type: ignore[call-arg]
            model=self.DEFAULT_MODEL,
            allowed_tools=[
                "Read",
                "Glob",
                "Write",
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
        input_data: DocGeneratorInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute doc generation with streaming.

        Args:
            input_data: Doc generator input
            context: Agent execution context

        Yields:
            SSE chunks with generated documentation
        """
        try:
            # Get API key from context
            api_key = await self._get_api_key(context.workspace_id)

            # Build prompt specific to doc generation
            prompt = self._build_prompt(input_data)

            # Create SDK options with env parameter (no os.environ mutation)
            sdk_options = self._create_agent_options(context)
            sdk_options.env = build_sdk_env(api_key)

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
            error_data = {"type": "error", "error_type": "doc_generator_error", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
