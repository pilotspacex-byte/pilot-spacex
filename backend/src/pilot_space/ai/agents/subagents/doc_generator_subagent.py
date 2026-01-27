"""Documentation Generator Subagent for interactive doc creation.

Provides conversational documentation generation:
- API documentation from code
- Architecture decision records
- README and setup guides
- Code comments and docstrings

Reference: docs/architect/ai-layer.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, StreamingSDKBaseAgent

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
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

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

    async def stream(
        self,
        input_data: DocGeneratorInput,
        context: AgentContext,  # noqa: ARG002
    ) -> AsyncIterator[str]:
        """Execute doc generation with streaming.

        Args:
            input_data: Doc generator input
            context: Agent execution context

        Yields:
            SSE chunks with generated documentation
        """
        # Implementation will use ClaudeSDKClient for streaming
        yield "Generating documentation...\n"
        yield f"Type: {input_data.doc_type}\n"
        yield f"Format: {input_data.output_format}\n"
        yield f"Analyzing {len(input_data.source_files)} files...\n"
