"""Model listing service for aggregating available models across configured providers.

Phase 13 — AI Provider Registry + Model Selection (AIPR-03, AIPR-05):

Provides ModelListingService.list_models_for_workspace() which queries all active
AIConfiguration rows for a workspace and fetches available models from each provider.

Design:
- Per-provider failures are isolated: one unreachable provider returns fallback
  models marked is_selectable=False, others are unaffected.
- Kimi and GLM use AsyncOpenAI with provider-specific base_url (OpenAI-compat API).
- Google Gemini uses the google-generativeai SDK wrapped in asyncio.to_thread to
  avoid blocking and protected by the _google_api_lock from ai_configuration router.
- Anthropic returns a hardcoded fallback (models.list() requires beta header).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
    AIConfigurationRepository,
)
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Module-level lock for genai.configure() calls — genai stores API key in global state
# and concurrent calls can race. This lock is separate from the one in ai_configuration
# router because the router's lock is private and we avoid cross-module lock sharing.
_google_model_listing_lock = asyncio.Lock()

logger = get_logger(__name__)


@dataclass
class ProviderModel:
    """A single model available from a configured provider."""

    provider_config_id: str  # str(AIConfiguration.id)
    provider: str
    model_id: str
    display_name: str
    is_selectable: bool


# Hardcoded fallback model lists for providers that may not expose /models or
# whose API is temporarily unreachable. Used when live fetch fails.
_FALLBACK_MODELS: dict[str, list[tuple[str, str]]] = {
    "kimi": [
        ("moonshot-v1-8k", "Kimi 8K"),
        ("moonshot-v1-32k", "Kimi 32K"),
        ("moonshot-v1-128k", "Kimi 128K"),
    ],
    "glm": [
        ("glm-4", "GLM-4"),
        ("glm-4-air", "GLM-4 Air"),
        ("glm-4-flash", "GLM-4 Flash"),
    ],
    "google": [
        ("gemini-2.0-flash", "Gemini 2.0 Flash"),
        ("gemini-2.0-pro", "Gemini 2.0 Pro"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro"),
    ],
    "anthropic": [
        ("claude-opus-4-5", "Claude Opus 4.5"),
        ("claude-sonnet-4", "Claude Sonnet 4"),
        ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku"),
    ],
    "openai": [
        ("gpt-4o", "GPT-4o"),
        ("gpt-4o-mini", "GPT-4o mini"),
        ("gpt-4-turbo", "GPT-4 Turbo"),
    ],
    "custom": [],  # Custom providers have no universal fallback
}

# Default base URLs for known OpenAI-compatible providers
_DEFAULT_BASE_URLS: dict[str, str] = {
    "kimi": "https://api.moonshot.cn/v1",
    "glm": "https://open.bigmodel.cn/api/paas/v4",
}


class ModelListingService:
    """Aggregates available models from all active configured providers in a workspace.

    Each provider's models are fetched independently. A per-provider failure is
    isolated: that provider returns is_selectable=False fallback models while
    other providers remain unaffected.
    """

    async def list_models_for_workspace(
        self,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> list[ProviderModel]:
        """Return all models available across active provider configurations.

        Args:
            workspace_id: Workspace to fetch configurations for.
            db: Active async database session.

        Returns:
            List of ProviderModel items. Failed providers return fallback models
            with is_selectable=False.
        """
        repo = AIConfigurationRepository(session=db)
        configs = await repo.get_by_workspace(workspace_id, include_inactive=False)

        results: list[ProviderModel] = []
        for config in configs:
            try:
                api_key = decrypt_api_key(config.api_key_encrypted)
                models = await self._fetch_models(config.provider, api_key, config.base_url)
                for model_id, model_display_name in models:
                    results.append(
                        ProviderModel(
                            provider_config_id=str(config.id),
                            provider=config.provider,
                            model_id=model_id,
                            display_name=model_display_name,
                            is_selectable=True,
                        )
                    )
            except Exception as e:
                logger.warning(
                    "model_listing_provider_failed",
                    provider=config.provider,
                    error=str(e),
                )
                # Return fallback list with is_selectable=False so the provider
                # remains visible in the UI but models are marked unavailable.
                fallback = _FALLBACK_MODELS.get(config.provider, [])
                for model_id, model_display_name in fallback:
                    results.append(
                        ProviderModel(
                            provider_config_id=str(config.id),
                            provider=config.provider,
                            model_id=model_id,
                            display_name=model_display_name,
                            is_selectable=False,
                        )
                    )

        return results

    async def _fetch_models(
        self,
        provider: str,
        api_key: str,
        base_url: str | None,
    ) -> list[tuple[str, str]]:
        """Dispatch model fetch to the appropriate provider-specific method.

        Args:
            provider: Provider name (anthropic, openai, google, kimi, glm, custom).
            api_key: Decrypted API key.
            base_url: Optional base URL override (required for custom, default for kimi/glm).

        Returns:
            List of (model_id, display_name) tuples.
        """
        if provider == "anthropic":
            return await self._fetch_anthropic_models(api_key)
        if provider in ("openai", "kimi", "glm", "custom"):
            effective_base_url = base_url or self._default_base_url(provider)
            return await self._fetch_openai_compat_models(api_key, effective_base_url)
        if provider == "google":
            return await self._fetch_google_models(api_key)
        # Unknown provider — return empty to trigger fallback
        logger.warning("model_listing_unknown_provider", provider=provider)
        return []

    def _default_base_url(self, provider: str) -> str | None:
        """Return the default base URL for known OpenAI-compatible providers.

        Returns None for openai (uses default openai.com endpoint) and custom
        (caller must provide base_url explicitly).
        """
        return _DEFAULT_BASE_URLS.get(provider)

    async def _fetch_anthropic_models(self, api_key: str) -> list[tuple[str, str]]:
        """Return hardcoded Anthropic model list.

        Anthropic's models.list() requires a beta header not in the stable SDK.
        The api_key parameter is kept for signature consistency (could be used for
        validation in the future). Returning the hardcoded fallback is intentional.
        """
        _ = api_key  # Reserved for future key validation
        return _FALLBACK_MODELS["anthropic"]

    async def _fetch_openai_compat_models(
        self,
        api_key: str,
        base_url: str | None,
    ) -> list[tuple[str, str]]:
        """Fetch models from an OpenAI-compatible /v1/models endpoint.

        Used for: openai, kimi, glm, custom providers.

        Args:
            api_key: Provider API key.
            base_url: Optional custom base URL (kimi/glm use provider defaults).

        Returns:
            List of (model_id, display_name) from the API, or openai fallback if empty.
        """
        import openai

        if base_url:
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            client = openai.AsyncOpenAI(api_key=api_key)
        response = await client.models.list()
        models = [(m.id, m.id) for m in response.data]
        return models if models else _FALLBACK_MODELS.get("openai", [])

    async def _fetch_google_models(self, api_key: str) -> list[tuple[str, str]]:
        """Fetch chat-capable models from Google Generative AI.

        Protected by _google_api_lock to prevent race conditions from
        genai.configure() global state mutation.

        Args:
            api_key: Google AI Studio API key.

        Returns:
            List of (model_id, display_name) for generateContent-capable models.
        """
        import google.generativeai as genai  # type: ignore[import-untyped]

        # Import the module-level lock from the router to share it with the
        # _test_google_key path which also calls genai.configure().
        async with _google_model_listing_lock:
            genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage,reportUnknownMemberType]
            all_models = await asyncio.to_thread(
                list,
                genai.list_models(),  # pyright: ignore[reportPrivateImportUsage,reportUnknownMemberType,reportUnknownArgumentType]
            )

        chat_models = [
            (m.name.removeprefix("models/"), m.display_name)
            for m in all_models
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]
        return chat_models if chat_models else _FALLBACK_MODELS["google"]


__all__ = ["ModelListingService", "ProviderModel"]
