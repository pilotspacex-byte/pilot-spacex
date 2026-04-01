"""Anthropic-compatible LLM proxy — standalone FastAPI sub-application (INTERNAL ONLY).

Mounted on the main app at ``/api/v1/ai/proxy`` via ``app.mount()``.
This is a separate ASGI application (FastAPI sub-application pattern)
with its own exception handlers. **Not for public/external access** —
accepts only internal calls from LLMGateway, GhostTextService, Agent SDK,
and subagents running on the same host.

Flow:
    Claude Agent SDK -> ANTHROPIC_BASE_URL=http://localhost:8000/api/v1/ai/proxy/{workspace_id}/
    -> POST /{workspace_id}/v1/messages
    -> tenant validation (workspace active, AI enabled, budget, rate limit)
    -> provider routing (anthropic/ollama/custom via workspace config)
    -> forward to real provider
    -> cost tracking + observability

Tenant Control:
    1. Workspace must exist and not be deleted
    2. AI features must be enabled (workspace.settings.ai_features)
    3. Monthly cost budget check (workspace.settings.ai_cost_limit_usd)
    4. Rate limiting (workspace.rate_limit_ai_rpm or global default)
    5. Model allowlist enforcement (workspace.settings.allowed_models)
    6. Max tokens ceiling (prevent runaway costs)

Provider Routing:
    - Reads workspace.settings.default_llm_provider
    - Resolves BYOK key + base_url from WorkspaceAPIKey table
    - Routes to: Anthropic API, Ollama (local), or custom OpenAI-compatible
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.exceptions import AINotConfiguredError
from pilot_space.ai.proxy.cost_hooks import track_llm_cost
from pilot_space.ai.proxy.tracing import observe  # pyright: ignore[reportAttributeAccessIssue]
from pilot_space.dependencies.auth import get_session
from pilot_space.domain.constants import SYSTEM_USER_ID
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Default max_tokens ceiling to prevent runaway costs
_MAX_TOKENS_CEILING = 16384


def _register_proxy_exception_handlers(app: FastAPI) -> None:
    """Register RFC 7807 exception handlers on the proxy sub-app.

    The sub-application is a separate ASGI app and does not inherit the
    parent app's exception handlers, so we register them independently.
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    from pilot_space.ai.exceptions import AIError
    from pilot_space.api.middleware.error_handler import (
        ai_error_handler,
        app_error_handler,
        generic_exception_handler,
        http_exception_handler,
        validation_exception_handler,
    )
    from pilot_space.domain.exceptions import AppError

    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AIError, ai_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


async def _internal_only_middleware(request: Request, call_next: Any) -> Any:
    """Reject requests not originating from localhost.

    The proxy is an internal service — only LLMGateway, GhostTextService,
    Agent SDK, and subagents running on the same host should call it.
    """
    client_host = request.client.host if request.client else None
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    if client_host not in allowed_hosts:
        logger.warning(
            "ai_proxy_external_request_rejected",
            client_host=client_host,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=403,
            content={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "status": 403,
                "detail": "Proxy accepts internal requests only",
            },
            media_type="application/problem+json",
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Create the sub-application
# ---------------------------------------------------------------------------

proxy_app = FastAPI(
    title="Pilot Space AI Proxy (Internal)",
    description="Internal LLM proxy — not for public access.",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_register_proxy_exception_handlers(proxy_app)
proxy_app.middleware("http")(_internal_only_middleware)

# Session dependency — reuses the same ContextVar-based get_session from the
# main app's auth module.  The ContextVar is per-coroutine so it works
# correctly even though this is a separate ASGI application.
ProxyDbSession = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Tenant validation
# ---------------------------------------------------------------------------


async def validate_tenant(
    request: Request,
    workspace_id: UUID,
    user_id: UUID,
    model: str,
    max_tokens: int,
) -> tuple[Any, Any, Any, str | None, int, str]:
    """Validate workspace tenant before proxying an LLM call.

    Returns:
        (executor, cost_tracker, key_storage, base_url, capped_max_tokens, provider)

    Raises:
        ForbiddenError: Workspace not found, AI disabled, budget exceeded,
                        model not allowed, or rate limit exceeded.
        AINotConfiguredError: No BYOK key configured for workspace.
    """
    from pilot_space.ai.alerts.cost_alerts import get_monthly_cost
    from pilot_space.ai.infrastructure.rate_limiter import RateLimiter
    from pilot_space.config import get_settings
    from pilot_space.container.container import Container
    from pilot_space.dependencies.auth import get_current_session

    container: Container = request.app.state.container  # type: ignore[assignment]
    executor = container.resilient_executor()
    cost_tracker = container.cost_tracker()
    key_storage = container.secure_key_storage()
    settings = get_settings()

    # --- 1. Workspace existence ---
    session = get_current_session()
    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.workspace import Workspace

    result = await session.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.is_deleted.is_(False),
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise ForbiddenError(f"Workspace {workspace_id} not found or deleted")

    ws_settings: dict[str, Any] = workspace.settings or {}

    # --- 2. AI features enabled ---
    ai_features = ws_settings.get("ai_features", {})
    # If ai_features dict exists and has an explicit "enabled" key, check it.
    # Otherwise, AI is enabled by default.
    if ai_features.get("enabled") is False:
        raise ForbiddenError("AI features are disabled for this workspace")

    # --- 3. Cost budget check ---
    cost_limit_usd = ws_settings.get("ai_cost_limit_usd")
    monthly_cost = Decimal(0)
    if cost_limit_usd is not None:
        monthly_cost = await get_monthly_cost(session, workspace_id)
        if monthly_cost >= Decimal(str(cost_limit_usd)):
            raise ForbiddenError(
                f"Monthly AI budget exceeded: ${monthly_cost:.2f} / ${cost_limit_usd:.2f}"
            )

    # --- 4. Rate limiting ---
    ai_rpm = workspace.rate_limit_ai_rpm or settings.rate_limit_ai_per_minute
    rate_limit_exceeded = False
    try:
        redis = container.redis_client()
        limiter = RateLimiter(redis, requests_per_minute=ai_rpm)  # type: ignore[arg-type]
        rate_limit_exceeded = not await limiter.acquire(f"ai_proxy:{workspace_id}")
    except Exception:
        # Redis unavailable -- fail open (allow request, log warning)
        logger.warning("ai_proxy_rate_limit_check_failed", exc_info=True)
    if rate_limit_exceeded:
        raise ForbiddenError(f"AI rate limit exceeded ({ai_rpm} requests/minute)")

    # --- 5. Model allowlist ---
    allowed_models: list[str] | None = ws_settings.get("allowed_models")
    if allowed_models and model not in allowed_models:
        raise ForbiddenError(f"Model '{model}' not in workspace allowlist: {allowed_models}")

    # --- 6. Max tokens ceiling ---
    workspace_max_tokens: int | None = ws_settings.get("ai_max_tokens")
    ceiling = workspace_max_tokens or _MAX_TOKENS_CEILING
    capped_max_tokens = min(max_tokens, ceiling)

    # --- 7. Resolve workspace provider and base_url ---
    provider: str = ws_settings.get("default_llm_provider", "anthropic")
    base_url: str | None = None
    try:
        # Try the configured provider first, then fall back to "anthropic"
        key_info = await key_storage.get_key_info(workspace_id, provider, "llm")
        if not key_info and provider != "anthropic":
            key_info = await key_storage.get_key_info(workspace_id, "anthropic", "llm")
        if key_info:
            base_url = key_info.base_url
    except Exception:
        logger.debug("ai_proxy_key_info_lookup_failed", exc_info=True)

    # Guard against self-referencing base_url — if the workspace's stored
    # base_url points back to this proxy, ignore it to prevent infinite loops.
    if base_url:
        proxy_prefix = settings.ai_proxy_base_url
        if base_url.rstrip("/").startswith(proxy_prefix.rstrip("/")):
            logger.warning(
                "ai_proxy_self_referencing_base_url",
                workspace_id=str(workspace_id),
                base_url=base_url,
                proxy_prefix=proxy_prefix,
            )
            base_url = None

    logger.info(
        "ai_proxy_tenant_validated",
        workspace_id=str(workspace_id),
        user_id=str(user_id),
        model=model,
        max_tokens=capped_max_tokens,
        has_base_url=bool(base_url),
        provider=provider,
        budget_remaining=f"${Decimal(str(cost_limit_usd or 0)) - (monthly_cost if cost_limit_usd else Decimal(0)):.2f}"
        if cost_limit_usd
        else "unlimited",
    )

    return executor, cost_tracker, key_storage, base_url, capped_max_tokens, provider


# ---------------------------------------------------------------------------
# Client pooling
# ---------------------------------------------------------------------------


def _get_cached_sdk_client(
    request: Request,
    api_key: str,
    base_url: str | None,
    *,
    state_attr: str,
    factory: type,
) -> Any:
    """Get or create a cached SDK client from app state.

    Uses a plain tuple as dict key — the dict lives in-memory only,
    so there is no need for cryptographic hashing.
    """
    cache_key = (api_key, base_url or "")

    if not hasattr(request.app.state, state_attr):
        setattr(request.app.state, state_attr, {})

    clients: dict[tuple[str, str], Any] = getattr(request.app.state, state_attr)
    if cache_key not in clients:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        clients[cache_key] = factory(**kwargs)
    return clients[cache_key]


def get_cached_client(request: Request, api_key: str, base_url: str | None) -> Any:
    """Get or create a cached AsyncAnthropic client from app state."""
    import anthropic

    return _get_cached_sdk_client(
        request,
        api_key,
        base_url,
        state_attr="proxy_anthropic_clients",
        factory=anthropic.AsyncAnthropic,
    )


def get_cached_openai_client(request: Request, api_key: str, base_url: str | None) -> Any:
    """Get or create a cached AsyncOpenAI client from app state."""
    import openai

    return _get_cached_sdk_client(
        request,
        api_key,
        base_url,
        state_attr="proxy_openai_clients",
        factory=openai.AsyncOpenAI,
    )


# ---------------------------------------------------------------------------
# Anthropic → OpenAI translation (for Ollama / OpenAI-compatible providers)
# ---------------------------------------------------------------------------


def _anthropic_messages_to_openai(
    messages: list[dict[str, Any]],
    system_msg: str | list[Any] | None,
) -> list[dict[str, Any]]:
    """Translate Anthropic Messages format to OpenAI Chat Completions format."""
    oai_messages: list[dict[str, Any]] = []

    # System message
    if system_msg:
        if isinstance(system_msg, str):
            oai_messages.append({"role": "system", "content": system_msg})
        else:
            # Anthropic system can be a list of content blocks
            text_parts = [b.get("text", "") for b in system_msg if b.get("type") == "text"]
            if text_parts:
                oai_messages.append({"role": "system", "content": "\n".join(text_parts)})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            oai_messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Anthropic content blocks → extract text
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        text_parts.append(str(block.get("content", "")))
            oai_messages.append({"role": role, "content": "\n".join(text_parts) or ""})
        else:
            oai_messages.append({"role": role, "content": str(content)})

    return oai_messages


def _openai_response_to_anthropic(oai_response: Any, model: str) -> dict[str, Any]:
    """Translate OpenAI Chat Completion response to Anthropic Messages format."""
    choice = oai_response.choices[0] if oai_response.choices else None
    text = choice.message.content if choice and choice.message else ""
    usage = oai_response.usage

    return {
        "id": f"msg_{oai_response.id}" if oai_response.id else "msg_proxy",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text or ""}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        },
    }


async def _handle_openai_compatible(
    *,
    request: Request,
    api_key: str,
    base_url: str,
    body: dict[str, Any],
    model: str,
    messages: list[dict[str, Any]],
    system_msg: str | list[Any] | None,
    max_tokens: int,
    temperature: float,
    stream: bool,
    executor: Any,
    cost_tracker: Any,
    workspace_id: UUID,
    user_id: UUID,
) -> StreamingResponse | JSONResponse:
    """Handle requests for OpenAI-compatible providers (Ollama, custom).

    Translates Anthropic Messages format → OpenAI Chat Completions,
    forwards to the provider, then translates the response back.
    """
    # Normalize base_url for OpenAI SDK — must end with /v1 or /v1/
    # Ollama stores base_url as "http://localhost:11434/" but OpenAI SDK needs /v1
    _oai_base_url = base_url.rstrip("/")
    if not _oai_base_url.endswith("/v1"):
        _oai_base_url += "/v1"

    oai_client = get_cached_openai_client(request, api_key, _oai_base_url)
    oai_messages = _anthropic_messages_to_openai(messages, system_msg)

    logger.info(
        "ai_proxy_openai_request",
        model=model,
        stream=stream,
        base_url=base_url,
        workspace_id=str(workspace_id),
        message_count=len(oai_messages),
        max_tokens=max_tokens,
    )

    create_kwargs: dict[str, Any] = {
        "model": model,
        "messages": oai_messages,
        "max_tokens": max_tokens,
    }
    if temperature != 1.0:
        create_kwargs["temperature"] = temperature

    # Pass through common params
    for param in ("top_p", "stop"):
        if param in body:
            create_kwargs[param] = body[param]

    if stream:
        return await _handle_openai_streaming(
            client=oai_client,
            create_kwargs=create_kwargs,
            executor=executor,
            cost_tracker=cost_tracker,
            workspace_id=workspace_id,
            user_id=user_id,
            model=model,
        )

    response = await executor.execute(
        provider="openai",
        operation=lambda: oai_client.chat.completions.create(**create_kwargs),
    )

    anthropic_response = _openai_response_to_anthropic(response, model)

    usage = response.usage
    if workspace_id and cost_tracker and usage:
        await track_llm_cost(
            cost_tracker,
            workspace_id=workspace_id,
            user_id=user_id,
            model=f"openai/{model}",
            agent_name="ai_proxy",
            input_tokens=usage.prompt_tokens or 0,
            output_tokens=usage.completion_tokens or 0,
        )

    return JSONResponse(content=anthropic_response, media_type="application/json")


async def _handle_openai_streaming(
    *,
    client: Any,
    create_kwargs: dict[str, Any],
    executor: Any,
    cost_tracker: Any,
    workspace_id: UUID,
    user_id: UUID,
    model: str,
) -> StreamingResponse:
    """Stream OpenAI Chat Completions and translate to Anthropic SSE format."""

    async def generate() -> AsyncIterator[bytes]:
        create_kwargs["stream"] = True
        collected_text = ""
        input_tokens = 0
        output_tokens = 0

        # Emit Anthropic-style message_start event
        msg_start = {
            "type": "message_start",
            "message": {
                "id": "msg_proxy_stream",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }
        yield f"event: message_start\ndata: {json.dumps(msg_start)}\n\n".encode()

        # Emit content_block_start
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n".encode()

        try:
            stream_response = await executor.execute(
                provider="openai",
                operation=lambda: client.chat.completions.create(**create_kwargs),
            )
            async for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta_text = chunk.choices[0].delta.content
                    collected_text += delta_text
                    output_tokens += 1  # Approximate

                    delta_event = {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": delta_text},
                    }
                    yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n".encode()

                # Check for usage in the final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens or 0
                    output_tokens = chunk.usage.completion_tokens or output_tokens
        except Exception:
            logger.exception("ai_proxy_openai_stream_error")

        # Emit content_block_stop
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n".encode()

        # Emit message_delta (stop reason)
        msg_delta = {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        }
        yield f"event: message_delta\ndata: {json.dumps(msg_delta)}\n\n".encode()

        # Emit message_stop
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n".encode()

        # Track cost
        if workspace_id and cost_tracker:
            await track_llm_cost(
                cost_tracker,
                workspace_id=workspace_id,
                user_id=user_id,
                model=f"openai/{model}",
                agent_name="ai_proxy",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Main proxy endpoint
# ---------------------------------------------------------------------------


@proxy_app.post("/{workspace_id}/v1/messages", response_model=None, tags=["ai-proxy"])
@observe(name="ai_proxy.messages")  # type: ignore[misc]
async def proxy_messages(
    request: Request,
    workspace_id: UUID,
    session: ProxyDbSession,  # populates ContextVar for DI-injected services
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> StreamingResponse | JSONResponse:
    """Anthropic Messages API proxy with tenant validation.

    Validates workspace permissions, enforces budget/rate limits,
    resolves provider config, then forwards to the real LLM provider.

    Path params:
        workspace_id: Workspace UUID for tenant validation + cost attribution
    Headers:
        x-api-key: Anthropic API key (sent by SDK automatically)
        X-User-Id: User UUID for cost attribution (optional, defaults to SYSTEM)
    """

    api_key = request.headers.get("x-api-key") or ""
    if not api_key:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            api_key = auth[7:]

    if not api_key:
        raise AINotConfiguredError(workspace_id=workspace_id)

    body = await request.json()
    model: str = body.get("model", "claude-sonnet-4-20250514")
    messages: list[dict[str, Any]] = body.get("messages", [])
    max_tokens: int = body.get("max_tokens", 1024)
    temperature: float = body.get("temperature", 1.0)
    system_msg: str | list[Any] | None = body.get("system")
    stream: bool = body.get("stream", False)

    user_id = UUID(x_user_id) if x_user_id else SYSTEM_USER_ID

    executor, cost_tracker, _key_storage, base_url, max_tokens, provider = await validate_tenant(
        request, workspace_id, user_id, model, max_tokens
    )

    # Route to OpenAI-compatible path for providers that don't speak Anthropic API.
    # Ollama natively supports Anthropic Messages API, so it uses the Anthropic path.
    _use_openai = provider in ("openai", "custom") and base_url is not None
    if _use_openai:
        assert base_url is not None  # narrowing for pyright
        return await _handle_openai_compatible(
            request=request,
            api_key=api_key,
            base_url=base_url,
            body=body,
            model=model,
            messages=messages,
            system_msg=system_msg,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            executor=executor,
            cost_tracker=cost_tracker,
            workspace_id=workspace_id,
            user_id=user_id,
        )

    client = get_cached_client(request, api_key, base_url)

    create_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature != 1.0:
        create_kwargs["temperature"] = temperature
    if system_msg is not None:
        create_kwargs["system"] = system_msg
    if stream:
        create_kwargs["stream"] = True

    # Pass through Anthropic-specific params
    for param in (
        "top_p",
        "top_k",
        "stop_sequences",
        "metadata",
        "tools",
        "tool_choice",
        "thinking",
    ):
        if param in body:
            create_kwargs[param] = body[param]

    logger.info(
        "ai_proxy_request",
        model=model,
        stream=stream,
        workspace_id=str(workspace_id) if workspace_id else None,
        has_base_url=bool(base_url),
        message_count=len(messages),
        max_tokens=max_tokens,
    )

    if stream:
        return await _handle_streaming(
            client=client,
            create_kwargs=create_kwargs,
            executor=executor,
            cost_tracker=cost_tracker,
            workspace_id=workspace_id,
            user_id=user_id,
            model=model,
        )

    response = await executor.execute(
        provider="anthropic",
        operation=lambda: client.messages.create(**create_kwargs),
    )

    if workspace_id and cost_tracker:
        await track_llm_cost(
            cost_tracker,
            workspace_id=workspace_id,
            user_id=user_id,
            model=f"anthropic/{model}",
            agent_name="ai_proxy",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    logger.info(
        "ai_proxy_response",
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    return JSONResponse(
        content=response.model_dump(),
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Embeddings proxy endpoint
# ---------------------------------------------------------------------------


@proxy_app.post("/{workspace_id}/v1/embeddings", response_model=None, tags=["ai-proxy"])
@observe(name="ai_proxy.embeddings")  # type: ignore[misc]
async def proxy_embeddings(
    request: Request,
    workspace_id: UUID,
    session: ProxyDbSession,  # populates ContextVar for DI-injected services
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> JSONResponse:
    """OpenAI Embeddings API proxy with tenant validation.

    Validates workspace permissions, enforces budget/rate limits,
    resolves provider config, then forwards to the real OpenAI Embeddings API.

    Path params:
        workspace_id: Workspace UUID for tenant validation + cost attribution
    Headers:
        Authorization: Bearer <api-key> (OpenAI API key)
        X-User-Id: User UUID for cost attribution (optional, defaults to SYSTEM)
    """
    user_id = UUID(x_user_id) if x_user_id else SYSTEM_USER_ID

    api_key = ""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        api_key = auth[7:]
    if not api_key:
        api_key = request.headers.get("x-api-key") or ""

    body = await request.json()
    model: str = body.get("model", "text-embedding-3-large")
    input_texts: str | list[str] = body.get("input", [])
    dimensions: int | None = body.get("dimensions")

    executor, cost_tracker, key_storage, base_url, _capped, _provider = await validate_tenant(
        request, workspace_id, user_id, model, 0
    )

    openai_key = await key_storage.get_api_key(workspace_id, "openai", "llm")
    if openai_key is None:
        from pilot_space.config import get_settings

        settings = get_settings()
        openai_key = getattr(settings, "openai_api_key", "") or api_key
    if not openai_key:
        openai_key = api_key

    client = get_cached_openai_client(request, openai_key, base_url)

    embed_kwargs: dict[str, Any] = {
        "model": model,
        "input": input_texts,
    }
    if dimensions is not None:
        embed_kwargs["dimensions"] = dimensions

    logger.info(
        "ai_proxy_embeddings_request",
        model=model,
        workspace_id=str(workspace_id),
        input_count=len(input_texts) if isinstance(input_texts, list) else 1,
    )

    response = await executor.execute(
        provider="openai",
        operation=lambda: client.embeddings.create(**embed_kwargs),
    )

    total_tokens = response.usage.total_tokens if response.usage else 0
    await track_llm_cost(
        cost_tracker,
        workspace_id=workspace_id,
        user_id=user_id,
        model=f"openai/{model}",
        agent_name="ai_proxy",
        input_tokens=total_tokens,
        output_tokens=0,
    )

    logger.info(
        "ai_proxy_embeddings_response",
        model=model,
        total_tokens=total_tokens,
    )

    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": i,
                    "embedding": item.embedding,
                }
                for i, item in enumerate(response.data)
            ],
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "total_tokens": total_tokens,
            },
        },
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Streaming handler
# ---------------------------------------------------------------------------


async def _handle_streaming(
    *,
    client: Any,
    create_kwargs: dict[str, Any],
    executor: Any,
    cost_tracker: Any,
    workspace_id: UUID | None,
    user_id: UUID,
    model: str,
) -> StreamingResponse:
    """Forward streaming Messages API response with cost tracking."""

    async def _stream_generator() -> AsyncIterator[str]:
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            stream = await executor.execute(
                provider="anthropic",
                operation=lambda: client.messages.create(**create_kwargs),
            )

            async for event in stream:
                event_data = event.model_dump() if hasattr(event, "model_dump") else {}
                event_type = getattr(event, "type", "")

                if event_type == "message_start":
                    usage = event_data.get("message", {}).get("usage", {})
                    total_input_tokens = usage.get("input_tokens", 0)

                if event_type == "message_delta":
                    usage = event_data.get("usage", {})
                    total_output_tokens = usage.get("output_tokens", 0)

                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

        except Exception:
            logger.exception("ai_proxy_stream_error")
            # Return a generic message to avoid leaking internal details.
            error_data = {
                "type": "error",
                "error": {"type": "api_error", "message": "An internal error occurred."},
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        finally:
            if workspace_id and cost_tracker and (total_input_tokens or total_output_tokens):
                try:
                    await track_llm_cost(
                        cost_tracker,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model=f"anthropic/{model}",
                        agent_name="ai_proxy",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                except Exception:
                    logger.debug("ai_proxy_stream_cost_tracking_failed", exc_info=True)

            logger.info(
                "ai_proxy_stream_complete",
                model=model,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )

    return StreamingResponse(
        _stream_generator(),
        media_type="text/event-stream",
        headers={
            "content-type": "text/event-stream",
            "cache-control": "no-cache",
            "connection": "keep-alive",
        },
    )
