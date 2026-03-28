"""Unified LLM entry point with direct Anthropic/OpenAI SDK calls.

LLMGateway is the single entry point for all LLM completions in Pilot Space.
It uses the native Anthropic and OpenAI SDKs directly (no LiteLLM dependency),
wraps calls with ResilientExecutor, auto-tracks costs via CostTracker, and
emits Langfuse traces.

Supports two provider APIs:
- Anthropic Messages API (primary — used by Claude Agent SDK)
- OpenAI Chat Completions / Embeddings API (for embeddings + OpenAI-compatible providers)

Replaces 8+ scattered direct AsyncAnthropic() instantiations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

import anthropic
import openai

from pilot_space.ai.exceptions import AINotConfiguredError
from pilot_space.ai.proxy.cost_hooks import track_llm_cost
from pilot_space.ai.proxy.provider_config import (
    extract_model_name,
    extract_provider,
    resolve_model,
)
from pilot_space.ai.proxy.tracing import observe  # pyright: ignore[reportAttributeAccessIssue]
from pilot_space.config import get_settings
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import TaskType

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Provider-agnostic LLM completion response."""

    text: str
    input_tokens: int
    output_tokens: int
    model: str
    raw: Any


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Provider-agnostic embedding response."""

    embeddings: list[list[float]]
    model: str
    input_tokens: int


class LLMGateway:
    """Unified gateway for LLM completions and embeddings.

    Uses native Anthropic and OpenAI SDKs with:
    - BYOK key resolution from SecureKeyStorage
    - ResilientExecutor for retry + circuit breaking
    - Automatic cost tracking via CostTracker
    - Langfuse @observe tracing
    - Per-API-key client pooling (avoids TCP pool churn)

    Usage:
        gateway = LLMGateway(executor, cost_tracker, key_storage)
        response = await gateway.complete(
            workspace_id=ws_id,
            user_id=user_id,
            task_type=TaskType.PR_REVIEW,
            messages=[{"role": "user", "content": "Review this code"}],
        )
    """

    def __init__(
        self,
        executor: ResilientExecutor,
        cost_tracker: CostTracker,
        key_storage: SecureKeyStorage,
    ) -> None:
        self._executor = executor
        self._cost_tracker = cost_tracker
        self._key_storage = key_storage
        # Per-API-key client pools keyed by (key, url, headers) tuple.
        self._anthropic_clients: dict[tuple[str, str, str], anthropic.AsyncAnthropic] = {}
        self._openai_clients: dict[tuple[str, str, str], openai.AsyncOpenAI] = {}

    def _get_anthropic_client(
        self,
        api_key: str,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> anthropic.AsyncAnthropic:
        """Get or create a cached AsyncAnthropic client for this API key.

        Args:
            api_key: Workspace-specific Anthropic API key.
            base_url: Optional custom base URL (for proxies / Ollama).
            default_headers: Optional headers sent with every request (e.g. proxy tenant headers).
        """
        headers_part = str(sorted(default_headers.items())) if default_headers else ""
        cache_key = (api_key, base_url or "", headers_part)
        if cache_key not in self._anthropic_clients:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            if default_headers:
                kwargs["default_headers"] = default_headers
            self._anthropic_clients[cache_key] = anthropic.AsyncAnthropic(**kwargs)
        return self._anthropic_clients[cache_key]

    def _get_openai_client(
        self,
        api_key: str,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> openai.AsyncOpenAI:
        """Get or create a cached AsyncOpenAI client for this API key.

        Args:
            api_key: Workspace-specific OpenAI API key.
            base_url: Optional custom base URL (for proxies / Ollama).
            default_headers: Optional headers sent with every request (e.g. proxy tenant headers).
        """
        headers_part = str(sorted(default_headers.items())) if default_headers else ""
        cache_key = (api_key, base_url or "", headers_part)
        if cache_key not in self._openai_clients:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            if default_headers:
                kwargs["default_headers"] = default_headers
            self._openai_clients[cache_key] = openai.AsyncOpenAI(**kwargs)
        return self._openai_clients[cache_key]

    @observe(name="llm_gateway.complete")  # type: ignore[misc]
    async def complete(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        task_type: TaskType,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
        agent_name: str = "llm_gateway",
    ) -> LLMResponse:
        """Execute an LLM completion via native provider SDK.

        Routes to Anthropic Messages API or OpenAI Chat Completions API
        based on the provider prefix in the resolved model string.

        Args:
            workspace_id: Workspace UUID for BYOK key lookup.
            user_id: User UUID who initiated the call.
            task_type: AI task type for model routing.
            messages: Chat messages in OpenAI format [{"role": ..., "content": ...}].
            model: Optional model override ("provider/model-name" format).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            system: Optional system message.
            agent_name: Agent/service name for cost tracking.

        Returns:
            LLMResponse with completion text and usage data.

        Raises:
            AINotConfiguredError: If no BYOK API key is configured.
        """
        resolved = resolve_model(task_type, model)
        provider = extract_provider(resolved)
        bare_model = extract_model_name(resolved)

        api_key = await self._key_storage.get_api_key(workspace_id, provider, "llm")
        if api_key is None:
            raise AINotConfiguredError(workspace_id=workspace_id)

        key_info = await self._key_storage.get_key_info(workspace_id, provider, "llm")
        base_url = key_info.base_url if key_info else None

        # Proxy routing: when ai_proxy_enabled, override base_url to route
        # through the built-in proxy for centralized cost tracking.
        # workspace_id is encoded in the URL path (no custom headers needed).
        settings = get_settings()
        _is_proxied = False
        if settings.ai_proxy_enabled:
            base_url = f"{settings.ai_proxy_base_url}/{workspace_id}/"
            _is_proxied = True

        if provider == "anthropic":
            return await self._complete_anthropic(
                api_key=api_key,
                base_url=base_url,
                provider=provider,
                model=bare_model,
                resolved_model=resolved,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                workspace_id=workspace_id,
                user_id=user_id,
                agent_name=agent_name,
                _is_proxied=_is_proxied,
            )
        return await self._complete_openai(
            api_key=api_key,
            base_url=base_url,
            provider=provider,
            model=bare_model,
            resolved_model=resolved,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=agent_name,
            _is_proxied=_is_proxied,
        )

    async def _complete_anthropic(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
        provider: str,
        model: str,
        resolved_model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: str | None,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        _is_proxied: bool = False,
    ) -> LLMResponse:
        """Call Anthropic Messages API directly."""
        client = self._get_anthropic_client(
            api_key, base_url=base_url, default_headers=default_headers
        )

        # Anthropic uses a separate `system` param, not a system message in the list
        anthropic_messages: list[dict[str, str]] = []
        effective_system = system
        for msg in messages:
            if msg["role"] == "system":
                # Merge system messages (first one wins, or concatenate)
                if effective_system is None:
                    effective_system = msg["content"]
                else:
                    effective_system = f"{effective_system}\n\n{msg['content']}"
            else:
                anthropic_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if effective_system is not None:
            kwargs["system"] = effective_system

        response = await self._executor.execute(
            provider=provider,
            operation=lambda: client.messages.create(**kwargs),
        )

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        if not _is_proxied:
            await track_llm_cost(
                self._cost_tracker,
                workspace_id=workspace_id,
                user_id=user_id,
                model=resolved_model,
                agent_name=agent_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=resolved_model,
            raw=response,
        )

    async def _complete_openai(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
        provider: str,
        model: str,
        resolved_model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: str | None,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        _is_proxied: bool = False,
    ) -> LLMResponse:
        """Call OpenAI Chat Completions API (also works for OpenAI-compatible providers)."""
        client = self._get_openai_client(
            api_key, base_url=base_url, default_headers=default_headers
        )

        # Filter system messages from list to avoid duplicates when system param is set
        final_messages = [m for m in messages if m["role"] != "system"]
        if system is not None:
            final_messages = [{"role": "system", "content": system}, *final_messages]
        else:
            # Preserve any system messages from the original list
            system_msgs = [m for m in messages if m["role"] == "system"]
            if system_msgs:
                final_messages = [*system_msgs, *final_messages]

        response = await self._executor.execute(
            provider=provider,
            operation=lambda: client.chat.completions.create(
                model=model,
                messages=final_messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        text = ""
        if response.choices:
            text = response.choices[0].message.content or ""

        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0

        if not _is_proxied:
            await track_llm_cost(
                self._cost_tracker,
                workspace_id=workspace_id,
                user_id=user_id,
                model=resolved_model,
                agent_name=agent_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=resolved_model,
            raw=response,
        )

    @observe(name="llm_gateway.embed")  # type: ignore[misc]
    async def embed(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        texts: list[str],
        model: str = "openai/text-embedding-3-large",
        dimensions: int | None = None,
        agent_name: str = "llm_gateway",
    ) -> EmbeddingResponse:
        """Generate embeddings via OpenAI Embeddings API.

        Args:
            workspace_id: Workspace UUID for BYOK key lookup.
            user_id: User UUID who initiated the call.
            texts: List of texts to embed.
            model: Model string ("provider/model-name" format).
            dimensions: Output embedding dimensions (e.g. 768 for pgvector).
            agent_name: Agent/service name for cost tracking.

        Returns:
            EmbeddingResponse with embedding vectors.

        Raises:
            AINotConfiguredError: If no BYOK API key is configured.
        """
        provider = extract_provider(model)
        bare_model = extract_model_name(model)

        api_key = await self._key_storage.get_api_key(workspace_id, provider, "llm")
        if api_key is None:
            raise AINotConfiguredError(workspace_id=workspace_id)

        key_info = await self._key_storage.get_key_info(workspace_id, provider, "llm")
        base_url = key_info.base_url if key_info else None

        # Proxy routing for embeddings: when ai_proxy_enabled, route through
        # the built-in proxy for centralized cost tracking.
        # workspace_id is encoded in the URL path (no custom headers needed).
        settings = get_settings()
        _is_proxied = False
        if settings.ai_proxy_enabled:
            base_url = f"{settings.ai_proxy_base_url}/{workspace_id}/"
            _is_proxied = True

        client = self._get_openai_client(api_key, base_url=base_url)

        embed_kwargs: dict[str, Any] = {
            "model": bare_model,
            "input": texts,
        }
        if dimensions is not None:
            embed_kwargs["dimensions"] = dimensions

        response = await self._executor.execute(
            provider=provider,
            operation=lambda: client.embeddings.create(**embed_kwargs),
        )

        embeddings = [item.embedding for item in response.data]
        input_tokens = response.usage.total_tokens if response.usage else 0

        if not _is_proxied:
            await track_llm_cost(
                self._cost_tracker,
                workspace_id=workspace_id,
                user_id=user_id,
                model=model,
                agent_name=agent_name,
                input_tokens=input_tokens,
                output_tokens=0,
            )

        return EmbeddingResponse(
            embeddings=embeddings,
            model=model,
            input_tokens=input_tokens,
        )


__all__ = ["EmbeddingResponse", "LLMGateway", "LLMResponse"]
