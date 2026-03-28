"""Unit tests for PRReviewSubagent and DocGeneratorSubagent proxy routing.

Tests that both subagents route SDK calls through the built-in HTTP proxy
when ai_proxy_enabled=True and preserve direct BYOK routing when disabled.

Strategy: patch ``build_sdk_env`` so it captures args *and* returns a valid
env dict, then assert on what was passed.  We also patch ``_create_agent_options``
and the ``ClaudeSDKClient`` to avoid hitting real SDK / MCP imports.

NOTE: We import the subagent *modules* and patch attributes directly on them
(rather than using string-based ``patch()``) to avoid import-caching issues
where CI resolves the name to the real function instead of the mock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.subagents import (
    doc_generator_subagent as doc_mod,
    pr_review_subagent as pr_mod,
)
from pilot_space.ai.agents.subagents.doc_generator_subagent import (
    DocGeneratorInput,
    DocGeneratorSubagent,
)
from pilot_space.ai.agents.subagents.pr_review_subagent import (
    PRReviewInput,
    PRReviewSubagent,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID = UUID("12345678-1234-5678-1234-567812345678")
USER_ID = uuid4()
TEST_API_KEY = "sk-ant-test-key"  # pragma: allowlist secret
BYOK_BASE_URL = "https://custom-proxy.example.com/v1"
PROXY_BASE_URL = "http://localhost:8000/api/v1/ai/proxy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(proxy_enabled: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.ai_proxy_enabled = proxy_enabled
    settings.ai_proxy_base_url = PROXY_BASE_URL
    settings.anthropic_base_url = None
    return settings


def _make_context(
    workspace_id: UUID = WORKSPACE_ID,
    user_id: UUID | None = None,
) -> AgentContext:
    return AgentContext(
        workspace_id=workspace_id,
        user_id=user_id or USER_ID,
        metadata={"db_session": MagicMock()},
    )


def _make_mock_sdk_options() -> MagicMock:
    opts = MagicMock()
    opts.model = "claude-sonnet-4-20250514"
    opts.env = {}
    opts.mcp_servers = {}
    return opts


def _make_mock_client() -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.receive_response = AsyncMock(
        return_value=AsyncMock(
            __aiter__=lambda s: s,
            __anext__=AsyncMock(side_effect=StopAsyncIteration),
        )
    )
    return mock_client


def _make_key_storage() -> AsyncMock:
    ks = AsyncMock()
    key_info = MagicMock()
    key_info.base_url = BYOK_BASE_URL
    key_info.model_name = None
    ks.get_key_info.return_value = key_info
    ks.get_api_key.return_value = TEST_API_KEY
    return ks


def _build_sdk_env_spy(calls: list[dict[str, str | None]]):
    """Return a replacement for ``build_sdk_env`` that records calls."""

    def _spy(api_key: str, base_url: str | None = None) -> dict[str, str]:
        calls.append({"api_key": api_key, "base_url": base_url})
        env: dict[str, str] = {"ANTHROPIC_API_KEY": api_key, "PATH": "", "HOME": ""}
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url
        return env

    return _spy


def _patch_subagent_module(mod, calls: list[dict[str, str | None]]):  # type: ignore[no-untyped-def]
    """Return a stack of patches for a subagent module using direct object refs."""
    return [
        patch.object(mod, "get_settings", return_value=None),  # overridden per test
        patch.object(mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
        patch.object(mod, "ClaudeSDKClient", return_value=_make_mock_client()),
        patch.object(mod, "set_workspace_context"),
        patch.object(mod, "clear_context"),
    ]


# ---------------------------------------------------------------------------
# PRReviewSubagent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pr_review_proxy_enabled_uses_proxy_base_url() -> None:
    """PRReviewSubagent.stream() uses proxy base_url when ai_proxy_enabled=True."""
    calls: list[dict[str, str | None]] = []
    subagent = PRReviewSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=_make_key_storage(),
    )
    context = _make_context()
    input_data = PRReviewInput(repository_id=uuid4(), pr_number=42)

    with (
        patch.object(pr_mod, "get_settings", return_value=_make_settings(proxy_enabled=True)),
        patch.object(pr_mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
        patch.object(pr_mod, "ClaudeSDKClient", return_value=_make_mock_client()),
        patch.object(subagent, "_create_agent_options", return_value=_make_mock_sdk_options()),
        patch.object(pr_mod, "set_workspace_context"),
        patch.object(pr_mod, "clear_context"),
    ):
        async for _ in subagent.stream(input_data, context):
            pass

    assert len(calls) == 1, f"build_sdk_env should be called once, got {len(calls)}"
    expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
    assert calls[0]["base_url"] == expected_proxy_url


@pytest.mark.asyncio
async def test_pr_review_proxy_disabled_uses_byok_base_url() -> None:
    """PRReviewSubagent.stream() uses BYOK base_url when ai_proxy_enabled=False."""
    calls: list[dict[str, str | None]] = []
    subagent = PRReviewSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=_make_key_storage(),
    )
    context = _make_context()
    input_data = PRReviewInput(repository_id=uuid4(), pr_number=42)

    with (
        patch.object(pr_mod, "get_settings", return_value=_make_settings(proxy_enabled=False)),
        patch.object(pr_mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
        patch.object(pr_mod, "ClaudeSDKClient", return_value=_make_mock_client()),
        patch.object(subagent, "_create_agent_options", return_value=_make_mock_sdk_options()),
        patch.object(pr_mod, "set_workspace_context"),
        patch.object(pr_mod, "clear_context"),
    ):
        async for _ in subagent.stream(input_data, context):
            pass

    assert len(calls) == 1, f"build_sdk_env should be called once, got {len(calls)}"
    assert calls[0]["base_url"] == BYOK_BASE_URL


# ---------------------------------------------------------------------------
# DocGeneratorSubagent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_doc_generator_proxy_enabled_uses_proxy_base_url() -> None:
    """DocGeneratorSubagent.stream() uses proxy base_url when ai_proxy_enabled=True."""
    calls: list[dict[str, str | None]] = []
    subagent = DocGeneratorSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=_make_key_storage(),
    )
    context = _make_context()
    input_data = DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["a.py"])

    with (
        patch.object(doc_mod, "get_settings", return_value=_make_settings(proxy_enabled=True)),
        patch.object(doc_mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
        patch.object(doc_mod, "ClaudeSDKClient", return_value=_make_mock_client()),
        patch.object(subagent, "_create_agent_options", return_value=_make_mock_sdk_options()),
        patch.object(doc_mod, "set_workspace_context"),
        patch.object(doc_mod, "clear_context"),
    ):
        async for _ in subagent.stream(input_data, context):
            pass

    assert len(calls) == 1, f"build_sdk_env should be called once, got {len(calls)}"
    expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
    assert calls[0]["base_url"] == expected_proxy_url


@pytest.mark.asyncio
async def test_doc_generator_proxy_disabled_uses_byok_base_url() -> None:
    """DocGeneratorSubagent.stream() uses BYOK base_url when ai_proxy_enabled=False."""
    calls: list[dict[str, str | None]] = []
    subagent = DocGeneratorSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=_make_key_storage(),
    )
    context = _make_context()
    input_data = DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["a.py"])

    with (
        patch.object(doc_mod, "get_settings", return_value=_make_settings(proxy_enabled=False)),
        patch.object(doc_mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
        patch.object(doc_mod, "ClaudeSDKClient", return_value=_make_mock_client()),
        patch.object(subagent, "_create_agent_options", return_value=_make_mock_sdk_options()),
        patch.object(doc_mod, "set_workspace_context"),
        patch.object(doc_mod, "clear_context"),
    ):
        async for _ in subagent.stream(input_data, context):
            pass

    assert len(calls) == 1, f"build_sdk_env should be called once, got {len(calls)}"
    assert calls[0]["base_url"] == BYOK_BASE_URL


# ---------------------------------------------------------------------------
# Proxy env: workspace_id is in URL path, NOT in env vars
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_subagents_encode_workspace_in_url_not_env_when_proxied() -> None:
    """Both subagents encode workspace_id in URL path, not X_WORKSPACE_ID env var."""
    user_id = uuid4()
    context = _make_context(user_id=user_id)

    for SubagentCls, input_data, mod in [
        (
            PRReviewSubagent,
            PRReviewInput(repository_id=uuid4(), pr_number=1),
            pr_mod,
        ),
        (
            DocGeneratorSubagent,
            DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["x.py"]),
            doc_mod,
        ),
    ]:
        calls: list[dict[str, str | None]] = []
        subagent = SubagentCls(
            provider_selector=MagicMock(),
            cost_tracker=AsyncMock(),
            resilient_executor=MagicMock(),
            key_storage=_make_key_storage(),
        )

        with (
            patch.object(mod, "get_settings", return_value=_make_settings(proxy_enabled=True)),
            patch.object(mod, "build_sdk_env", side_effect=_build_sdk_env_spy(calls)),
            patch.object(mod, "ClaudeSDKClient") as mock_client_cls,
            patch.object(subagent, "_create_agent_options", return_value=_make_mock_sdk_options()),
            patch.object(mod, "set_workspace_context"),
            patch.object(mod, "clear_context"),
        ):
            mock_client_cls.return_value = _make_mock_client()

            async for _ in subagent.stream(input_data, context):
                pass

            assert len(calls) == 1, (
                f"{SubagentCls.__name__}: build_sdk_env should be called once, got {len(calls)}"
            )
            expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
            assert calls[0]["base_url"] == expected_proxy_url

            # The SDK env should NOT have X_WORKSPACE_ID or X_USER_ID
            sdk_options = mock_client_cls.call_args[0][0]
            captured_env = sdk_options.env

        assert "X_WORKSPACE_ID" not in captured_env, (
            f"{SubagentCls.__name__} must NOT set X_WORKSPACE_ID (workspace_id is in URL path)"
        )
        assert "X_USER_ID" not in captured_env, (
            f"{SubagentCls.__name__} must NOT set X_USER_ID (no longer needed)"
        )
