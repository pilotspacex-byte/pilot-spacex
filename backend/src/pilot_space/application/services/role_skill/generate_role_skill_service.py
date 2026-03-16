"""GenerateRoleSkillService for AI-powered skill generation.

Generates SKILL.md content using Claude Sonnet one-shot query with
template context and experience description. Falls back to template-based
generation when AI is unavailable.

Source: 011-role-based-skills, T010, FR-003, FR-004
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.exceptions import ProviderUnavailableError
from pilot_space.ai.infrastructure.resilience import ResilientExecutor, RetryConfig
from pilot_space.ai.providers.provider_selector import ProviderSelector, TaskType
from pilot_space.application.services.role_skill.types import VALID_ROLE_TYPES
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# In-memory sliding window rate limiter: max 5 generations/hour/user (FR-003)
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW_SECONDS = 3600
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


class SkillGenerationError(Exception):
    """Raised when AI skill generation fails (422)."""

    def __init__(self, message: str = "Skill generation failed") -> None:
        super().__init__(message)


class SkillGenerationRateLimitError(Exception):
    """Raised when user exceeds generation rate limit."""

    def __init__(self, message: str = "Rate limit exceeded: max 5 generations per hour") -> None:
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


def _build_generation_prompt(
    role_type: str,
    display_name: str,
    template_content: str,
    experience_description: str,
    role_name: str | None,
) -> str:
    """Build the Claude Sonnet prompt for skill content generation."""
    name = role_name or display_name
    return f"""You are an expert technical writer creating a personalized AI skill profile \
for an SDLC platform. Generate a SKILL.md document that configures how an AI assistant \
should interact with and support this team member.

## Input

**Role type**: {role_type}
**Role display name**: {display_name}
**User's name for this role**: {name}
**Experience description**: {experience_description}

## Reference Template

Use this template as structural guidance (do not copy verbatim):

{template_content}

## Output Requirements

Return a JSON object with exactly two keys:
1. "skill_content": The full SKILL.md content in markdown format. Include:
   - A heading with the role name
   - Context section describing the role
   - Experience & Background section with the user's experience
   - Sections covering expertise areas, communication preferences, and focus areas
   - Personalized based on the experience description
   - 200-500 words total
2. "suggested_role_name": A concise, professional role title (2-4 words) \
derived from the experience description. Include seniority level if evident \
(e.g., "Senior Developer", "Lead Architect"). If the user provided a role name, \
use it as-is.

Return ONLY valid JSON, no markdown code fences, no extra text."""


class GenerateRoleSkillService:
    """Service for generating role skill content via AI.

    Uses Claude Sonnet one-shot query with ResilientExecutor for retries
    and CircuitBreaker for provider health. Falls back to template-based
    generation when AI is unavailable (no API key, provider down, etc.).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: GenerateRoleSkillPayload) -> GenerateRoleSkillResult:
        """Generate role skill content.

        Attempts AI generation via Claude Sonnet. Falls back to template
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
            raise ValueError(msg)

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
        )

        if ai_result is not None:
            skill_content, suggested_name, model = ai_result
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return GenerateRoleSkillResult(
                skill_content=skill_content,
                suggested_role_name=suggested_name,
                word_count=len(skill_content.split()),
                generation_model=model,
                generation_time_ms=elapsed_ms,
            )

        # Only reach here if no LLM provider configured — use template
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
        )

    async def _try_generate_via_ai(
        self,
        role_type: str,
        display_name: str,
        template_content: str,
        experience_description: str,
        role_name: str | None,
        workspace_id: UUID | None,
    ) -> tuple[str, str, str] | None:
        """Attempt AI-powered generation using the workspace's configured LLM provider.

        Supports Anthropic (direct) and Ollama (OpenAI-compatible).

        Returns:
            Tuple of (skill_content, suggested_role_name, model_name) or None.
        """
        provider_info = await self._resolve_llm_provider(workspace_id)
        if provider_info is None:
            logger.info("No LLM provider configured, using template fallback")
            return None

        provider, api_key, base_url, model_name = provider_info

        prompt = _build_generation_prompt(
            role_type=role_type,
            display_name=display_name,
            template_content=template_content,
            experience_description=experience_description,
            role_name=role_name,
        )

        # Use workspace model if configured, otherwise fall back to provider defaults
        if model_name:
            model = model_name
        elif provider == "anthropic":
            selector = ProviderSelector()
            config = selector.select_with_config(TaskType.TEMPLATE_FILLING)
            model = config.model
        else:
            model = "llama3.2"  # Ollama default

        executor = ResilientExecutor()
        retry_config = RetryConfig(max_retries=2, base_delay_seconds=1.0)

        raw_response: str | None = None
        try:
            if provider == "ollama":
                raw_response = await self._call_ollama(
                    base_url=base_url or "http://localhost:11434",
                    model=model,
                    prompt=prompt,
                    api_key=api_key,
                    executor=executor,
                    retry_config=retry_config,
                )
            else:
                raw_response = await self._call_anthropic(
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    executor=executor,
                    retry_config=retry_config,
                )
        except ProviderUnavailableError as e:
            msg = f"{provider} provider unavailable: {e}"
            raise SkillGenerationError(msg) from e
        except Exception as e:
            msg = f"AI skill generation failed ({provider}): {e}"
            raise SkillGenerationError(msg) from e

        result = self._parse_ai_response(raw_response or "", display_name, role_name, model)
        if result is None:
            msg = "AI returned invalid or insufficient content"
            raise SkillGenerationError(msg)
        return result

    async def _call_anthropic(
        self,
        api_key: str,
        model: str,
        prompt: str,
        executor: ResilientExecutor,
        retry_config: RetryConfig,
    ) -> str:
        """Call Anthropic API for skill generation."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=api_key)

        async def _call_api() -> str:
            response = await client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""

        return await executor.execute(
            provider="anthropic",
            operation=_call_api,
            timeout_sec=30.0,
            retry_config=retry_config,
        )

    async def _call_ollama(
        self,
        base_url: str,
        model: str,
        prompt: str,
        api_key: str | None,
        executor: ResilientExecutor,
        retry_config: RetryConfig,
    ) -> str:
        """Call Ollama via OpenAI-compatible API for skill generation."""
        import httpx

        url = f"{base_url.rstrip('/')}/api/chat"

        async def _call_api() -> str:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")

        return await executor.execute(
            provider="ollama",
            operation=_call_api,
            timeout_sec=60.0,
            retry_config=retry_config,
        )

    def _parse_ai_response(
        self,
        raw_response: str,
        display_name: str,
        role_name: str | None,
        model: str,
    ) -> tuple[str, str, str] | None:
        """Parse AI response JSON into (skill_content, suggested_name, model).

        Returns None if parsing fails.
        """
        try:
            # Strip markdown fences if present
            text = raw_response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]  # Remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)

            data = json.loads(text)
            skill_content = data.get("skill_content", "")
            suggested_name = data.get("suggested_role_name", role_name or display_name)

            if not skill_content or len(skill_content.strip()) < 50:
                logger.warning("AI returned insufficient skill content, using fallback")
                return None

            return (skill_content, suggested_name, model)

        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Failed to parse AI response as JSON, using fallback")
            return None

    async def _resolve_llm_provider(
        self, workspace_id: UUID | None
    ) -> tuple[str, str, str | None, str | None] | None:
        """Resolve the workspace's configured LLM provider.

        Returns:
            Tuple of (provider, api_key, base_url, model_name) or None.
        """
        if workspace_id is not None:
            try:
                from sqlalchemy import select as sa_select

                from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
                from pilot_space.config import get_settings
                from pilot_space.infrastructure.database.models.workspace import Workspace

                settings = get_settings()
                encryption_key = settings.encryption_key.get_secret_value()
                if not encryption_key:
                    return None

                # Determine which LLM provider the workspace has selected
                stmt = sa_select(Workspace.settings).where(Workspace.id == workspace_id)
                result = await self._session.execute(stmt)
                ws_settings = result.scalar_one_or_none() or {}
                default_llm = ws_settings.get("default_llm_provider", "anthropic")

                storage = SecureKeyStorage(self._session, encryption_key)
                key_info = await storage.get_key_info(workspace_id, default_llm, "llm")

                if key_info is not None:
                    api_key = await storage.get_api_key(workspace_id, default_llm, "llm")
                    return (
                        default_llm,
                        api_key or "",
                        key_info.base_url,
                        key_info.model_name,
                    )

                # If default provider has no key, try any configured LLM provider
                all_keys = await storage.get_all_key_infos(workspace_id)
                for ki in all_keys:
                    if ki.service_type == "llm":
                        api_key = await storage.get_api_key(workspace_id, ki.provider, "llm")
                        return (ki.provider, api_key or "", ki.base_url, ki.model_name)

            except Exception:
                logger.debug("Could not retrieve workspace LLM provider", exc_info=True)

        # Fall back to app-level Anthropic key
        try:
            from pilot_space.config import get_settings

            settings = get_settings()
            if settings.anthropic_api_key:
                return (
                    "anthropic",
                    settings.anthropic_api_key.get_secret_value(),
                    None,
                    None,
                )
        except Exception:
            logger.debug("Could not retrieve app-level API key", exc_info=True)

        return None

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
