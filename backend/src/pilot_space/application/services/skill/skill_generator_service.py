"""SkillGeneratorService: multi-turn conversational skill creation.

Manages draft state across conversation turns, generates SKILL.md content
via LLMGateway, infers metadata (example prompts, context requirements,
tool declarations), and persists completed skills.

Phase 051: Conversational Skill Generator
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from pilot_space.ai.prompts.skill_generator import (
    get_skill_generation_system_prompt,
    get_skill_refinement_prompt,
)
from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.domain.exceptions import AppError, ForbiddenError, ValidationError
from pilot_space.infrastructure.database.models.skill_graph import SkillGraph
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
from pilot_space.infrastructure.database.models.user_skill import UserSkill
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.proxy.llm_gateway import LLMGateway

logger = get_logger(__name__)


class SkillGeneratorError(AppError):
    """Raised when skill generation fails."""

    http_status = 500
    error_code = "skill_generator_error"

    def __init__(self, message: str = "Skill generation failed") -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SkillGeneratorPayload:
    """Input for a single generation turn."""

    workspace_id: UUID
    user_id: UUID
    session_id: UUID
    message: str
    turn_number: int
    current_draft: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class SkillGeneratorResult:
    """Output of a generation turn."""

    skill_content: str
    name: str
    description: str
    category: str
    icon: str
    example_prompts: list[str]
    context_requirements: list[str]
    tool_declarations: list[str]
    graph_data: dict[str, Any] | None
    is_complete: bool
    refinement_suggestion: str | None
    session_data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SkillSavePayload:
    """Input for persisting a generated skill."""

    workspace_id: UUID
    user_id: UUID
    session_id: UUID
    save_type: str  # "personal" | "workspace"
    name: str
    description: str
    category: str
    icon: str
    skill_content: str
    example_prompts: list[str]
    graph_data: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class SkillSaveResult:
    """Result of persisting a skill."""

    skill_id: UUID
    skill_name: str
    save_type: str


class SkillGeneratorService:
    """Orchestrates multi-turn conversational skill creation.

    Uses LLMGateway for provider-agnostic completion with automatic
    cost tracking, retry + circuit breaking, and Langfuse tracing.

    Args:
        session: SQLAlchemy async session (request-scoped).
        llm_gateway: Unified LLM gateway for completions.
    """

    def __init__(self, session: AsyncSession, llm_gateway: LLMGateway | None = None) -> None:
        self._session = session
        self._llm_gateway = llm_gateway

    async def generate_turn(self, payload: SkillGeneratorPayload) -> SkillGeneratorResult:
        """Execute a single generation turn.

        Args:
            payload: Turn input with message, turn number, and optional current draft.

        Returns:
            SkillGeneratorResult with generated/refined content and session state.

        Raises:
            SkillGeneratorError: If LLM call fails or response is unparsable.
        """
        system_prompt = get_skill_generation_system_prompt(
            turn_number=payload.turn_number,
            current_draft=payload.current_draft,
        )

        if payload.current_draft and payload.turn_number > 1:
            user_message = get_skill_refinement_prompt(
                current_draft=payload.current_draft,
                user_message=payload.message,
            )
        else:
            user_message = payload.message

        llm_data = await self._call_llm(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            system_prompt=system_prompt,
            user_message=user_message,
        )

        # Determine status based on turn number
        if payload.turn_number == 1:
            status = "gathering"
        elif payload.turn_number == 2:
            status = "refining"
        else:
            status = "preview"

        # Build draft for session persistence
        draft = {
            "name": llm_data.get("name", "Untitled Skill"),
            "description": llm_data.get("description", ""),
            "category": llm_data.get("category", "general"),
            "icon": llm_data.get("icon", "Wand2"),
            "skill_content": llm_data.get("skill_content", ""),
            "example_prompts": llm_data.get("example_prompts", []),
            "context_requirements": llm_data.get("context_requirements", []),
            "tool_declarations": llm_data.get("tool_declarations", []),
            "graph_data": llm_data.get("graph_data"),
        }

        # Build iteration history entry
        history_entry = {
            "turn": payload.turn_number,
            "message": payload.message,
            "status": status,
        }

        session_data: dict[str, Any] = {
            "mode": "skill_generation",
            "turn_count": payload.turn_number,
            "draft": draft,
            "iteration_history": [history_entry],
            "status": status,
        }

        return SkillGeneratorResult(
            skill_content=str(draft["skill_content"]),
            name=str(draft["name"]),
            description=str(draft["description"]),
            category=str(draft["category"]),
            icon=str(draft["icon"]),
            example_prompts=list(draft["example_prompts"] or []),
            context_requirements=list(draft["context_requirements"] or []),
            tool_declarations=list(draft["tool_declarations"] or []),
            graph_data=draft["graph_data"],
            is_complete=bool(llm_data.get("is_complete", False)),
            refinement_suggestion=llm_data.get("refinement_suggestion"),
            session_data=session_data,
        )

    async def save_skill(self, payload: SkillSavePayload) -> SkillSaveResult:
        """Persist a generated skill to the database.

        Args:
            payload: Save input with skill data and target type.

        Returns:
            SkillSaveResult with the saved skill ID.

        Raises:
            ValidationError: If save_type is invalid.
            ForbiddenError: If non-admin user attempts workspace save.
        """
        if payload.save_type not in ("personal", "workspace"):
            msg = f"Invalid save_type: {payload.save_type}"
            raise ValidationError(msg)

        if payload.save_type == "workspace":
            await self._verify_admin_role(payload.workspace_id, payload.user_id)

        if payload.save_type == "personal":
            return await self._save_personal(payload)
        return await self._save_workspace(payload)

    async def _verify_admin_role(self, workspace_id: UUID, user_id: UUID) -> None:
        """Verify user has admin or owner role in the workspace.

        Raises:
            ForbiddenError: If user is not a member or lacks admin/owner role.
        """
        stmt = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active.is_(True),
            WorkspaceMember.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        row = result.scalar()
        if row is None:
            raise ForbiddenError("Not a member of this workspace")
        role = row.value if hasattr(row, "value") else str(row)
        if role not in (WorkspaceRole.ADMIN.value, WorkspaceRole.OWNER.value):
            raise ForbiddenError("Admin or owner role required to save workspace skills")

    async def _save_personal(self, payload: SkillSavePayload) -> SkillSaveResult:
        """Create a UserSkill record for personal save."""
        skill = UserSkill(
            id=uuid.uuid4(),
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            skill_name=payload.name,
            skill_content=payload.skill_content,
            is_active=True,
        )
        self._session.add(skill)
        await self._session.flush()

        return SkillSaveResult(
            skill_id=skill.id,
            skill_name=payload.name,
            save_type="personal",
        )

    async def _save_workspace(self, payload: SkillSavePayload) -> SkillSaveResult:
        """Create a SkillTemplate + optional SkillGraph for workspace save."""
        template = SkillTemplate(
            id=uuid.uuid4(),
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description or "",
            skill_content=payload.skill_content,
            icon=payload.icon or "Wand2",
            source="workspace",
            created_by=payload.user_id,
        )
        self._session.add(template)
        await self._session.flush()

        if payload.graph_data:
            nodes = payload.graph_data.get("nodes", [])
            edges = payload.graph_data.get("edges", [])
            graph = SkillGraph(
                id=uuid.uuid4(),
                workspace_id=payload.workspace_id,
                skill_template_id=template.id,
                graph_json=payload.graph_data,
                node_count=len(nodes),
                edge_count=len(edges),
            )
            self._session.add(graph)
            await self._session.flush()

        return SkillSaveResult(
            skill_id=template.id,
            skill_name=payload.name,
            save_type="workspace",
        )

    async def _call_llm(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """Call LLMGateway and parse JSON response.

        Returns:
            Parsed JSON dict from LLM response.

        Raises:
            SkillGeneratorError: If no LLM gateway or parsing fails.
        """
        if self._llm_gateway is None:
            msg = "No LLM gateway configured for skill generation"
            raise SkillGeneratorError(msg)

        try:
            response = await self._llm_gateway.complete(
                workspace_id=workspace_id,
                user_id=user_id,
                task_type=TaskType.ROLE_SKILL_GENERATION,
                messages=[{"role": "user", "content": user_message}],
                system=system_prompt,
                max_tokens=2048,
                temperature=0.7,
                agent_name="skill_generator",
            )
        except Exception as e:
            msg = f"LLM call failed: {e}"
            raise SkillGeneratorError(msg) from e

        return self._parse_response(response.text)

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        """Parse LLM JSON response, stripping markdown fences if present."""
        text = raw.strip()
        if not text:
            msg = "LLM returned empty response"
            raise SkillGeneratorError(msg)

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # Remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text, strict=False)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: extract JSON object from text
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(), strict=False)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        msg = "Failed to parse LLM response as JSON"
        raise SkillGeneratorError(msg)


__all__ = [
    "SkillGeneratorError",
    "SkillGeneratorPayload",
    "SkillGeneratorResult",
    "SkillGeneratorService",
    "SkillSavePayload",
    "SkillSaveResult",
]
