"""GenerateRoleSkillService for AI-powered skill generation.

Generates SKILL.md content using LLMGateway one-shot query with
template context and experience description. Falls back to template-based
generation when AI is unavailable.

Source: 011-role-based-skills, T010, FR-003, FR-004
"""

from __future__ import annotations

import dataclasses
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.prompts.skill_generation import build_skill_generation_prompt
from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.application.services.role_skill.types import VALID_ROLE_TYPES
from pilot_space.domain.exceptions import AppError, ValidationError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.proxy.llm_gateway import LLMGateway

logger = get_logger(__name__)

# Sentinel user ID for system-initiated generation (no real user context)
_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# In-memory sliding window rate limiter: max 30 generations/hour/user (FR-003)
_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW_SECONDS = 3600
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


class SkillGenerationError(AppError):
    """Raised when AI skill generation fails (500)."""

    http_status = 500
    error_code = "skill_generation_error"

    def __init__(self, message: str = "Skill generation failed") -> None:
        super().__init__(message)


class SkillGenerationRateLimitError(AppError):
    """Raised when user exceeds generation rate limit."""

    http_status = 429
    error_code = "skill_generation_rate_limit"

    def __init__(
        self,
        message: str = f"Rate limit exceeded: max {_RATE_LIMIT_MAX} generations per hour",
    ) -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class GenerateRoleSkillPayload:
    """Payload for generating a role skill."""

    role_type: str
    experience_description: str
    role_name: str | None = None
    workspace_id: UUID | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GenerateRoleSkillResult:
    """Result from AI skill generation."""

    skill_content: str
    suggested_role_name: str
    word_count: int
    generation_model: str
    generation_time_ms: int
    suggested_tags: list[str] = dataclasses.field(default_factory=list)
    suggested_usage: str | None = None


def _check_rate_limit(user_id: UUID) -> None:
    """Check in-memory sliding window rate limit for skill generation.

    Raises:
        SkillGenerationRateLimitError: If limit exceeded.
    """
    now = time.monotonic()
    key = str(user_id)
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS

    # Prune expired entries
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > window_start]

    if len(_rate_limit_store[key]) >= _RATE_LIMIT_MAX:
        raise SkillGenerationRateLimitError

    _rate_limit_store[key].append(now)


class GenerateRoleSkillService:
    """Service for generating role skill content via AI.

    Uses LLMGateway for provider-agnostic LLM completion with automatic
    cost tracking, retry + circuit breaking, and Langfuse tracing.
    Falls back to template-based generation when AI is unavailable
    (no LLMGateway, no API key, provider down, etc.).
    """

    def __init__(self, session: AsyncSession, llm_gateway: LLMGateway | None = None) -> None:
        self._session = session
        self._llm_gateway = llm_gateway

    async def execute(self, payload: GenerateRoleSkillPayload) -> GenerateRoleSkillResult:
        """Generate role skill content.

        Attempts AI generation via LLMGateway. Falls back to template
        when AI is unavailable or fails.

        Args:
            payload: Generation parameters.

        Returns:
            GenerateRoleSkillResult with generated content.

        Raises:
            ValueError: If role_type is invalid.
            SkillGenerationRateLimitError: If rate limit exceeded.
        """
        if payload.role_type not in VALID_ROLE_TYPES:
            msg = f"Invalid role type: {payload.role_type}"
            raise ValidationError(msg)

        # Rate limit check (only when user_id is provided)
        if payload.user_id is not None:
            _check_rate_limit(payload.user_id)

        start_time = time.monotonic()

        # Load template content for context
        template_content = await self._get_template_content(payload.role_type)
        display_name = await self._get_template_display_name(payload.role_type)

        # Generate via configured LLM provider (no silent fallback)
        ai_result = await self._try_generate_via_ai(
            role_type=payload.role_type,
            display_name=display_name,
            template_content=template_content,
            experience_description=payload.experience_description,
            role_name=payload.role_name,
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
        )

        if ai_result is not None:
            skill_content, suggested_name, model, suggested_tags, suggested_usage = ai_result
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return GenerateRoleSkillResult(
                skill_content=skill_content,
                suggested_role_name=suggested_name,
                word_count=len(skill_content.split()),
                generation_model=model,
                generation_time_ms=elapsed_ms,
                suggested_tags=suggested_tags,
                suggested_usage=suggested_usage,
            )

        # Only reach here if no LLM gateway configured -- use template
        skill_content = self._generate_content_from_template(
            template_content=template_content,
            display_name=display_name,
            experience_description=payload.experience_description,
            role_name=payload.role_name,
        )
        suggested_name = self._suggest_role_name_heuristic(
            display_name=display_name,
            experience_description=payload.experience_description,
            provided_name=payload.role_name,
        )
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return GenerateRoleSkillResult(
            skill_content=skill_content,
            suggested_role_name=suggested_name,
            word_count=len(skill_content.split()),
            generation_model="template-v1",
            generation_time_ms=elapsed_ms,
            suggested_tags=[],
            suggested_usage=None,
        )

    async def _try_generate_via_ai(
        self,
        role_type: str,
        display_name: str,
        template_content: str,
        experience_description: str,
        role_name: str | None,
        workspace_id: UUID | None,
        user_id: UUID | None = None,
    ) -> tuple[str, str, str, list[str], str | None] | None:
        """Attempt AI-powered generation using LLMGateway.

        Returns:
            Tuple of (skill_content, suggested_role_name, model_name, suggested_tags,
            suggested_usage) or None.
        """
        if self._llm_gateway is None:
            logger.info("No LLM gateway configured, using template fallback")
            return None

        if workspace_id is None:
            logger.info("No workspace_id provided, using template fallback")
            return None

        prompt = build_skill_generation_prompt(
            role_type=role_type,
            display_name=display_name,
            template_content=template_content,
            experience_description=experience_description,
            role_name=role_name,
        )

        try:
            response = await self._llm_gateway.complete(
                workspace_id=workspace_id,
                user_id=user_id or _SYSTEM_USER_ID,
                task_type=TaskType.ROLE_SKILL_GENERATION,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.7,
                agent_name="role_skill_generation",
            )
        except SkillGenerationError:
            raise
        except Exception as e:
            msg = f"AI skill generation failed: {e}"
            raise SkillGenerationError(msg) from e

        result = self._parse_ai_response(response.text, display_name, role_name, response.model)
        if result is None:
            msg = "AI returned invalid or insufficient content"
            raise SkillGenerationError(msg)
        return result

    def _parse_ai_response(
        self,
        raw_response: str,
        display_name: str,
        role_name: str | None,
        model: str,
    ) -> tuple[str, str, str, list[str], str | None] | None:
        """Parse AI response into (skill_content, suggested_name, model, tags, usage).

        Tries JSON first, then treats raw text as markdown skill content.
        Returns None only if content is empty or too short.
        Tags and usage default to [] / None when missing from response.
        """
        text = raw_response.strip()
        if not text:
            logger.warning("AI returned empty response")
            return None

        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # Remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Try JSON parse first (expected format)
        # strict=False allows literal control characters (newlines, tabs) inside
        # JSON string values -- common with Ollama/kimi models that don't escape them.
        try:
            data = json.loads(text, strict=False)
            if isinstance(data, dict):
                skill_content = data.get("skill_content", "")
                suggested_name = data.get("suggested_role_name", role_name or display_name)
                suggested_tags = self._extract_tags(data.get("suggested_tags"))
                suggested_usage = data.get("suggested_usage") or None

                if skill_content and len(skill_content.strip()) >= 50:
                    return (skill_content, suggested_name, model, suggested_tags, suggested_usage)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Second attempt: extract JSON object from surrounding text via regex
        # Handles AI responses like "Here is your skill: {...} Hope this helps!"
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(), strict=False)
                if not isinstance(data, dict):
                    data = {}
                skill_content = data.get("skill_content", "")
                suggested_name = data.get("suggested_role_name", role_name or display_name)
                suggested_tags = self._extract_tags(data.get("suggested_tags"))
                suggested_usage = data.get("suggested_usage") or None

                if skill_content and len(skill_content.strip()) >= 50:
                    logger.info(
                        "AI response parsed via regex JSON extraction",
                        extra={"model": model, "content_length": len(skill_content)},
                    )
                    return (skill_content, suggested_name, model, suggested_tags, suggested_usage)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Third attempt: extract fields via regex for malformed JSON
        # (e.g., kimi returns JSON with unescaped newlines in string values)
        sc_match = re.search(
            r'"skill_content"\s*:\s*"((?:[^"\\]|\\.)*)"|'
            r'"skill_content"\s*:\s*"([\s\S]*?)"(?:\s*,|\s*\})',
            text,
        )
        if sc_match:
            raw_content = sc_match.group(1) or sc_match.group(2) or ""
            # Unescape JSON escape sequences
            skill_content = raw_content.replace("\\n", "\n").replace('\\"', '"')
            if skill_content and len(skill_content.strip()) >= 50:
                name_match = re.search(r'"suggested_role_name"\s*:\s*"([^"]*)"', text)
                suggested_name = name_match.group(1) if name_match else (role_name or display_name)
                logger.info(
                    "AI response parsed via regex field extraction (malformed JSON)",
                    extra={"model": model, "content_length": len(skill_content)},
                )
                return (skill_content, suggested_name, model, [], None)

        # Fallback: treat raw response as markdown skill content directly,
        # but guard against leaking raw JSON as user-visible content.
        stripped = text.strip()
        is_leaked_json = stripped.startswith("{") and '"skill_content"' in stripped
        if not is_leaked_json and len(stripped) >= 50:
            suggested_name = self._suggest_role_name_heuristic(
                display_name=display_name,
                experience_description=text[:200],
                provided_name=role_name,
            )
            logger.info(
                "AI response parsed as raw markdown (non-JSON)",
                extra={"model": model, "content_length": len(text)},
            )
            return (text, suggested_name, model, [], None)

        logger.warning(
            "AI returned invalid or insufficient content",
            extra={"model": model, "response_length": len(text)},
        )
        return None

    @staticmethod
    def _extract_tags(raw: object) -> list[str]:
        """Safely extract a list of string tags from AI JSON response.

        Args:
            raw: The value from JSON at "suggested_tags" key (any type).

        Returns:
            List of string tags, truncated to max 30 chars each, max 20 tags.
            Empty list if input is invalid.
        """
        if not isinstance(raw, list):
            return []
        return [str(tag)[:30] for tag in raw if tag][:20]

    async def _get_template_content(self, role_type: str) -> str:
        """Load template default_skill_content for a role type."""
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleTemplateRepository,
        )

        if role_type == "custom":
            return (
                "# Custom Role\n\n"
                "## Expertise\n\n"
                "Describe your areas of expertise.\n\n"
                "## Communication Style\n\n"
                "Describe your preferred communication approach.\n\n"
                "## Focus Areas\n\n"
                "List your key focus areas and priorities."
            )

        repo = RoleTemplateRepository(self._session)
        template = await repo.get_by_role_type(role_type)
        if template is None:
            return f"# {role_type.replace('_', ' ').title()}\n\nDefault content."
        return template.default_skill_content

    async def _get_template_display_name(self, role_type: str) -> str:
        """Get display name for a role type."""
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleTemplateRepository,
        )

        if role_type == "custom":
            return "Custom Role"

        repo = RoleTemplateRepository(self._session)
        template = await repo.get_by_role_type(role_type)
        if template is None:
            return role_type.replace("_", " ").title()
        return template.display_name

    def _generate_content_from_template(
        self,
        template_content: str,
        display_name: str,
        experience_description: str,
        role_name: str | None,
    ) -> str:
        """Generate personalized skill content from template (fallback).

        Template-based generation: inserts experience context into template.
        """
        name = role_name or display_name

        lines = [
            f"# {name}",
            "",
            "## Context",
            "",
            f"This skill is configured for a **{display_name}** role.",
            "",
            "## Experience & Background",
            "",
            experience_description,
            "",
        ]

        template_lines = template_content.strip().split("\n")
        skip_first_heading = len(template_lines) > 0 and template_lines[0].startswith("# ")
        start_idx = 1 if skip_first_heading else 0

        if skip_first_heading and len(template_lines) > 1:
            for i in range(1, len(template_lines)):
                if template_lines[i].strip():
                    start_idx = i
                    break

        remaining = "\n".join(template_lines[start_idx:]).strip()
        if remaining:
            lines.append(remaining)

        return "\n".join(lines)

    def _suggest_role_name_heuristic(
        self,
        display_name: str,
        experience_description: str,
        provided_name: str | None,
    ) -> str:
        """Suggest a role name via keyword heuristic (fallback)."""
        if provided_name:
            return provided_name

        desc_lower = experience_description.lower()
        seniority = ""
        if any(word in desc_lower for word in ["senior", "10+", "8+"]):
            seniority = "Senior "
        elif any(word in desc_lower for word in ["lead", "principal"]):
            seniority = "Lead "
        elif any(word in desc_lower for word in ["junior", "entry", "new"]):
            seniority = "Junior "

        return f"{seniority}{display_name}"


__all__ = [
    "GenerateRoleSkillPayload",
    "GenerateRoleSkillResult",
    "GenerateRoleSkillService",
    "SkillGenerationError",
    "SkillGenerationRateLimitError",
]
