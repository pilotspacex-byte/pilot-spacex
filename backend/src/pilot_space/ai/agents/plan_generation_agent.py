"""Plan Generation Agent — one-shot Claude query for implementation plan generation.

Uses claude_agent_sdk.query() with ModelTier.SONNET to generate a structured
JSON plan, then converts it to YAML-frontmatter markdown via parse_plan_response().

Services call PlanGenerationAgent.run(input) -> PlanOutput. The agent is a plain
class (not inheriting SDKBaseAgent) following the same pattern as AIContextAgent.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.prompts.implementation_plan import (
    PLAN_SYSTEM_PROMPT,
    build_plan_prompt,
    parse_plan_response,
)
from pilot_space.ai.sdk.config import build_sdk_env
from pilot_space.ai.sdk.sandbox_config import ModelTier
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent

logger = get_logger(__name__)


# =============================================================================
# Data Classes — stable interface for service layer
# =============================================================================


@dataclass
class PlanInput:
    """Input for implementation plan generation.

    Attributes:
        issue_id: Issue UUID string.
        issue_title: Issue name/title.
        issue_description: Issue description text (may be None).
        issue_identifier: Human-readable identifier (e.g. PS-42).
        workspace_id: Workspace UUID string.
        tasks_checklist: Existing task breakdown from AIContext (list of dicts).
        related_issues: Pre-discovered related issues (list of dicts).
        code_references: Pre-extracted code file references (list of dicts).
        complexity: Complexity estimate (low|medium|high).
        suggested_approach: Recommended implementation approach from AIContext.
    """

    issue_id: str
    issue_title: str
    issue_description: str | None
    issue_identifier: str
    workspace_id: str
    tasks_checklist: list[dict[str, Any]] = field(default_factory=list)
    related_issues: list[dict[str, Any]] = field(default_factory=list)
    code_references: list[dict[str, Any]] = field(default_factory=list)
    complexity: str = "medium"
    suggested_approach: str = ""


@dataclass
class PlanOutput:
    """Output from implementation plan generation.

    Attributes:
        plan_markdown: Canonical YAML-frontmatter markdown string.
        subagent_count: Number of subagents in the plan.
    """

    plan_markdown: str
    subagent_count: int


# =============================================================================
# PlanGenerationAgent
# =============================================================================


class PlanGenerationAgent:
    """Implementation plan generation agent.

    Executes a single one-shot claude_agent_sdk.query() call (no tools, no SSE)
    to generate a JSON plan, then converts to canonical YAML-frontmatter markdown.

    Usage from service layer:
        agent = PlanGenerationAgent(pilotspace_agent=agent)
        output = await agent.run(plan_input)
    """

    AGENT_NAME = "plan_generation_agent"

    def __init__(self, pilotspace_agent: PilotSpaceAgent) -> None:
        self._agent = pilotspace_agent

    async def run(self, input_data: PlanInput) -> PlanOutput:
        """Generate implementation plan from issue context.

        Args:
            input_data: Issue details plus existing AIContext data.

        Returns:
            PlanOutput with rendered markdown and subagent count.

        Raises:
            Exception: Propagated from SDK on network/auth failures.
        """
        workspace_uuid = UUID(input_data.workspace_id)

        context_data: dict[str, Any] = {
            "summary": "",
            "analysis": "",
            "complexity": input_data.complexity,
            "estimated_effort": "",
            "suggested_approach": input_data.suggested_approach,
            "tasks_checklist": input_data.tasks_checklist,
        }

        user_prompt = build_plan_prompt(
            issue_title=input_data.issue_title,
            issue_description=input_data.issue_description,
            issue_identifier=input_data.issue_identifier,
            context_data=context_data,
            related_issues=input_data.related_issues,
            code_references=input_data.code_references,
        )

        response_text = await self._execute_query(user_prompt, workspace_uuid)
        plan_markdown = parse_plan_response(
            response_text,
            issue_identifier=input_data.issue_identifier,
            issue_title=input_data.issue_title,
        )

        subagent_count = _count_subagents(plan_markdown)

        logger.info(
            "plan_generation_complete",
            issue_id=input_data.issue_id,
            issue_identifier=input_data.issue_identifier,
            subagent_count=subagent_count,
            plan_len=len(plan_markdown),
        )

        return PlanOutput(plan_markdown=plan_markdown, subagent_count=subagent_count)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _get_api_key(self, workspace_id: UUID) -> str:
        """Get API key from PilotSpaceAgent (BYOK vault + env fallback)."""
        return await self._agent._get_api_key(workspace_id)  # type: ignore[no-any-return]  # noqa: SLF001

    async def _execute_query(
        self,
        user_prompt: str,
        workspace_id: UUID,
    ) -> str:
        """Execute one-shot query via claude_agent_sdk.query().

        Uses SDK query() with no allowed_tools and max_turns=1 to get a clean
        JSON response without tool-calling interference.
        """
        import claude_agent_sdk

        model_tier = ModelTier.SONNET
        api_key = await self._get_api_key(workspace_id)

        stderr_lines: list[str] = []

        def _capture_stderr(line: str) -> None:
            stderr_lines.append(line)
            logger.debug("[PlanGen] CLI stderr: %s", line.rstrip())

        cwd = tempfile.mkdtemp()
        options = claude_agent_sdk.ClaudeAgentOptions(
            model=model_tier.model_id,
            system_prompt=PLAN_SYSTEM_PROMPT,
            allowed_tools=[],
            max_turns=1,
            permission_mode="default",
            cwd=cwd,
            setting_sources=[],
            stderr=_capture_stderr,
            extra_args={"debug-to-stderr": None},
            env=build_sdk_env(api_key),
        )

        text_parts: list[str] = []
        try:
            async with asyncio.timeout(120):
                async for message in claude_agent_sdk.query(
                    prompt=user_prompt,
                    options=options,
                ):
                    if isinstance(message, claude_agent_sdk.AssistantMessage):
                        for block in message.content:
                            if isinstance(block, claude_agent_sdk.TextBlock):
                                text_parts.append(block.text)
                    elif isinstance(message, claude_agent_sdk.ResultMessage):
                        logger.info(
                            "[PlanGen] query() result: cost=$%.4f, turns=%s",
                            message.total_cost_usd,
                            message.num_turns,
                        )
        except Exception:
            logger.exception(
                "[PlanGen] SDK query() failed. stderr=%s",
                "\n".join(stderr_lines),
            )
            raise

        full_response = "".join(text_parts)
        logger.info(
            "[PlanGen] query() finished: response_len=%d, preview=%.200s",
            len(full_response),
            full_response[:200],
        )

        if not full_response:
            msg = "AI model returned an empty response for plan generation"
            logger.error("[PlanGen] %s", msg)
            raise RuntimeError(msg)

        return full_response


# =============================================================================
# Module-level helpers
# =============================================================================


def _count_subagents(plan_markdown: str) -> int:
    """Count subagent sections in rendered markdown.

    Counts lines matching '### sa-' prefix which each represent one subagent heading.
    Falls back to 0 when no subagents are present.
    """
    matches = re.findall(r"^### sa-\w+", plan_markdown, re.MULTILINE)
    return len(matches)


__all__ = [
    "PlanGenerationAgent",
    "PlanInput",
    "PlanOutput",
]
