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
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

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
) -> tuple[Any, Any, Any, str | None, int]:
    """Validate workspace tenant before proxying an LLM call.

    Returns:
        (executor, cost_tracker, key_storage, base_url, capped_max_tokens)

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
        redis = container.redis()  # type: ignore[attr-defined]
        limiter = RateLimiter(redis, requests_per_minute=ai_rpm)
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

    # --- 7. Resolve workspace base_url ---
    base_url: str | None = None
    try:
        key_info = await key_storage.get_key_info(workspace_id, "anthropic", "llm")
        if key_info:
            base_url = key_info.base_url
    except Exception:
        logger.debug("ai_proxy_key_info_lookup_failed", exc_info=True)

    logger.info(
        "ai_proxy_tenant_validated",
        workspace_id=str(workspace_id),
        user_id=str(user_id),
        model=model,
        max_tokens=capped_max_tokens,
        has_base_url=bool(base_url),
        budget_remaining=f"${Decimal(str(cost_limit_usd or 0)) - (monthly_cost if cost_limit_usd else Decimal(0)):.2f}"
        if cost_limit_usd
        else "unlimited",
    )

    return executor, cost_tracker, key_storage, base_url, capped_max_tokens


# ---------------------------------------------------------------------------
# Client pooling
# ---------------------------------------------------------------------------


def get_cached_client(
    request: Request,
    api_key: str,
    base_url: str | None,
) -> Any:
    """Get or create a cached AsyncAnthropic client from app state."""
    import hashlib
    import hmac

    import anthropic

    # HMAC-SHA256 with a fixed key — used only for cache-slot deduplication,
    # NOT for password storage.  CodeQL flags bare sha256(api_key) as weak
    # password hashing; using hmac makes the intent explicit.
    key_hash = hmac.new(
        b"proxy-client-pool", f"{api_key}:{base_url or ''}".encode(), hashlib.sha256
    ).hexdigest()[:16]

    proxy_clients_attr = "proxy_anthropic_clients"
    if not hasattr(request.app.state, proxy_clients_attr):
        setattr(request.app.state, proxy_clients_attr, {})

    clients: dict[str, anthropic.AsyncAnthropic] = getattr(request.app.state, proxy_clients_attr)
    if key_hash not in clients:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        clients[key_hash] = anthropic.AsyncAnthropic(**kwargs)
    return clients[key_hash]


def get_cached_openai_client(
    request: Request,
    api_key: str,
    base_url: str | None,
) -> Any:
    """Get or create a cached AsyncOpenAI client from app state."""
    import hashlib
    import hmac

    import openai

    # HMAC-SHA256 for cache-slot deduplication (not password storage).
    key_hash = hmac.new(
        b"proxy-client-pool", f"{api_key}:{base_url or ''}".encode(), hashlib.sha256
    ).hexdigest()[:16]

    proxy_clients_attr = "proxy_openai_clients"
    if not hasattr(request.app.state, proxy_clients_attr):
        setattr(request.app.state, proxy_clients_attr, {})

    clients: dict[str, openai.AsyncOpenAI] = getattr(request.app.state, proxy_clients_attr)
    if key_hash not in clients:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        clients[key_hash] = openai.AsyncOpenAI(**kwargs)
    return clients[key_hash]


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
    # --- Extract API key ---
    api_key = request.headers.get("x-api-key") or ""
    if not api_key:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            api_key = auth[7:]

    if not api_key:
        raise AINotConfiguredError(workspace_id=workspace_id)

    # --- Parse request body ---
    body = await request.json()
    model: str = body.get("model", "claude-sonnet-4-20250514")
    messages: list[dict[str, Any]] = body.get("messages", [])
    max_tokens: int = body.get("max_tokens", 1024)
    temperature: float = body.get("temperature", 1.0)
    system_msg: str | list[Any] | None = body.get("system")
    stream: bool = body.get("stream", False)

    user_id = UUID(x_user_id) if x_user_id else _SYSTEM_USER_ID

    # --- Tenant validation ---
    executor, cost_tracker, _key_storage, base_url, max_tokens = await validate_tenant(
        request, workspace_id, user_id, model, max_tokens
    )

    # --- Get pooled client ---
    client = get_cached_client(request, api_key, base_url)

    # --- Build Anthropic Messages API kwargs ---
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

    # --- Forward request ---
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
        content=json.loads(response.model_dump_json()),
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
    user_id = UUID(x_user_id) if x_user_id else _SYSTEM_USER_ID

    # --- Extract API key ---
    api_key = ""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        api_key = auth[7:]
    if not api_key:
        api_key = request.headers.get("x-api-key") or ""

    # --- Parse request body ---
    body = await request.json()
    model: str = body.get("model", "text-embedding-3-large")
    input_texts: str | list[str] = body.get("input", [])
    dimensions: int | None = body.get("dimensions")

    # --- Tenant validation ---
    executor, cost_tracker, key_storage, base_url, _capped = await validate_tenant(
        request, workspace_id, user_id, model, 0
    )

    # --- Resolve OpenAI API key (BYOK or env fallback) ---
    openai_key = await key_storage.get_api_key(workspace_id, "openai", "llm")
    if openai_key is None:
        from pilot_space.config import get_settings

        settings = get_settings()
        openai_key = getattr(settings, "openai_api_key", "") or api_key
    if not openai_key:
        openai_key = api_key  # Use the key from the request header

    # --- Get pooled OpenAI client ---
    client = get_cached_openai_client(request, openai_key, base_url)

    # --- Build embeddings kwargs ---
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

    # --- Forward to OpenAI ---
    response = await executor.execute(
        provider="openai",
        operation=lambda: client.embeddings.create(**embed_kwargs),
    )

    # --- Track cost ---
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

    # --- Return OpenAI-format response ---
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
