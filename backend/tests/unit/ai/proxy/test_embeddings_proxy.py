"""Unit tests for /v1/embeddings proxy endpoint.

Tests the embeddings proxy endpoint in the proxy sub-application.
All OpenAI SDK calls are mocked -- no real API calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pilot_space.ai.proxy.app import proxy_app

WS_ID = uuid4()
USER_ID = uuid4()

# The patch target is the actual module where the functions live.
_PROXY_MOD = "pilot_space.ai.proxy.app"


def _make_mock_app() -> FastAPI:
    """Create a test app by mounting the proxy sub-app with mocked state.

    Uses a wrapper FastAPI app that mounts proxy_app at the expected
    prefix, mimicking the main app's mount configuration.
    """
    app = FastAPI()
    app.mount("/api/v1/ai/proxy", proxy_app)

    # Mock container on the proxy sub-app's state (same as main.py lifespan)
    container = MagicMock()
    executor = AsyncMock()

    async def _pass_through(provider: str, operation: object, **kwargs: object) -> object:
        return await operation()  # type: ignore[misc]

    executor.execute = AsyncMock(side_effect=_pass_through)
    container.resilient_executor.return_value = executor

    cost_tracker = AsyncMock()
    cost_tracker.track = AsyncMock()
    container.cost_tracker.return_value = cost_tracker

    key_storage = AsyncMock()
    key_storage.get_api_key = AsyncMock(return_value="sk-test-openai-key")
    key_storage.get_key_info = AsyncMock(return_value=None)
    container.secure_key_storage.return_value = key_storage

    redis = AsyncMock()
    container.redis_client.return_value = redis

    proxy_app.state.container = container
    return app


def _make_embedding_response(
    embeddings: list[list[float]] | None = None,
    total_tokens: int = 10,
    model: str = "text-embedding-3-large",
) -> SimpleNamespace:
    if embeddings is None:
        embeddings = [[0.1, 0.2, 0.3]]
    return SimpleNamespace(
        data=[
            SimpleNamespace(embedding=e, index=i, object="embedding")
            for i, e in enumerate(embeddings)
        ],
        usage=SimpleNamespace(total_tokens=total_tokens, prompt_tokens=total_tokens),
        model=model,
        object="list",
    )


def _mock_workspace(
    workspace_id: UUID | None = None,
    ai_enabled: bool = True,
    settings: dict[str, Any] | None = None,
) -> SimpleNamespace:
    ws_settings = settings or {}
    if not ai_enabled:
        ws_settings["ai_features"] = {"enabled": False}
    return SimpleNamespace(
        id=workspace_id or WS_ID,
        is_deleted=False,
        settings=ws_settings,
        rate_limit_ai_rpm=None,
    )


# -- Test 1: Valid embeddings request returns 200 with OpenAI format -----------


@patch(f"{_PROXY_MOD}.get_cached_openai_client")
@patch(f"{_PROXY_MOD}.validate_tenant")
@patch(f"{_PROXY_MOD}.get_session")
async def test_embeddings_returns_200_with_valid_request(
    mock_get_session: MagicMock,
    mock_validate: AsyncMock,
    mock_get_client: MagicMock,
) -> None:
    """POST /{workspace_id}/v1/embeddings with valid path param returns 200."""

    # Mock session dependency to yield a dummy session
    async def _fake_session():  # type: ignore[no-untyped-def]
        yield MagicMock()

    mock_get_session.side_effect = _fake_session

    app = _make_mock_app()

    # Mock validate_tenant to return valid tenant
    container = proxy_app.state.container
    mock_validate.return_value = (
        container.resilient_executor(),
        container.cost_tracker(),
        container.secure_key_storage(),
        None,  # base_url
        0,  # capped_max_tokens (not used for embeddings)
        "anthropic",  # provider
    )

    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response([[0.1, 0.2, 0.3]], total_tokens=5)
    )
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/ai/proxy/{WS_ID}/v1/embeddings",
            json={
                "model": "text-embedding-3-large",
                "input": ["hello world"],
            },
            headers={
                "X-User-Id": str(USER_ID),
                "Authorization": "Bearer sk-test-key",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["embedding"] == [0.1, 0.2, 0.3]
    assert data["data"][0]["object"] == "embedding"
    assert "usage" in data


# -- Test 2: Invalid workspace_id in path returns 422 --------------------------


@patch(f"{_PROXY_MOD}.get_session")
async def test_embeddings_returns_422_with_invalid_workspace_id(
    mock_get_session: MagicMock,
) -> None:
    """POST /{workspace_id}/v1/embeddings with invalid UUID returns 422."""

    async def _fake_session():  # type: ignore[no-untyped-def]
        yield MagicMock()

    mock_get_session.side_effect = _fake_session

    app = _make_mock_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/ai/proxy/not-a-uuid/v1/embeddings",
            json={
                "model": "text-embedding-3-large",
                "input": ["hello"],
            },
            headers={
                "Authorization": "Bearer sk-test-key",
            },
        )

    assert response.status_code == 422


# -- Test 3: Tracks cost via CostTracker --------------------------------------


@patch(f"{_PROXY_MOD}.get_cached_openai_client")
@patch(f"{_PROXY_MOD}.validate_tenant")
@patch(f"{_PROXY_MOD}.track_llm_cost")
@patch(f"{_PROXY_MOD}.get_session")
async def test_embeddings_tracks_cost(
    mock_get_session: MagicMock,
    mock_track_cost: AsyncMock,
    mock_validate: AsyncMock,
    mock_get_client: MagicMock,
) -> None:
    """POST /v1/embeddings tracks cost via CostTracker."""

    async def _fake_session():  # type: ignore[no-untyped-def]
        yield MagicMock()

    mock_get_session.side_effect = _fake_session

    app = _make_mock_app()
    container = proxy_app.state.container
    cost_tracker = container.cost_tracker()

    mock_validate.return_value = (
        container.resilient_executor(),
        cost_tracker,
        container.secure_key_storage(),
        None,
        0,
        "anthropic",
    )

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        return_value=_make_embedding_response(total_tokens=15)
    )
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post(
            f"/api/v1/ai/proxy/{WS_ID}/v1/embeddings",
            json={
                "model": "text-embedding-3-large",
                "input": ["hello"],
            },
            headers={
                "X-User-Id": str(USER_ID),
                "Authorization": "Bearer sk-test-key",
            },
        )

    mock_track_cost.assert_called_once()
    call_kwargs = mock_track_cost.call_args.kwargs
    assert call_kwargs["workspace_id"] == WS_ID
    assert call_kwargs["input_tokens"] == 15
    assert call_kwargs["agent_name"] == "ai_proxy"


# -- Test 4: Validates tenant (calls validate_tenant) -------------------------


@patch(f"{_PROXY_MOD}.get_cached_openai_client")
@patch(f"{_PROXY_MOD}.validate_tenant")
@patch(f"{_PROXY_MOD}.get_session")
async def test_embeddings_validates_tenant(
    mock_get_session: MagicMock,
    mock_validate: AsyncMock,
    mock_get_client: MagicMock,
) -> None:
    """POST /v1/embeddings calls validate_tenant for workspace checks."""

    async def _fake_session():  # type: ignore[no-untyped-def]
        yield MagicMock()

    mock_get_session.side_effect = _fake_session

    app = _make_mock_app()
    container = proxy_app.state.container

    mock_validate.return_value = (
        container.resilient_executor(),
        container.cost_tracker(),
        container.secure_key_storage(),
        None,
        0,
        "anthropic",
    )

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response())
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post(
            f"/api/v1/ai/proxy/{WS_ID}/v1/embeddings",
            json={
                "model": "text-embedding-3-large",
                "input": ["validate me"],
            },
            headers={
                "X-User-Id": str(USER_ID),
                "Authorization": "Bearer sk-test-key",
            },
        )

    mock_validate.assert_called_once()
    call_args = mock_validate.call_args
    assert call_args.args[1] == WS_ID  # workspace_id
    assert call_args.args[3] == "text-embedding-3-large"  # model
