"""Unit tests for PRReviewSubagent and DocGeneratorSubagent proxy routing.

Tests that both subagents route SDK calls through the built-in HTTP proxy
when ai_proxy_enabled=True and preserve direct BYOK routing when disabled.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
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


def _make_pr_review_subagent(key_storage: AsyncMock | None = None) -> PRReviewSubagent:
    ks = key_storage or AsyncMock()
    if key_storage is None:
        key_info = MagicMock()
        key_info.base_url = BYOK_BASE_URL
        key_info.model_name = None
        ks.get_key_info.return_value = key_info
        ks.get_api_key.return_value = TEST_API_KEY
    return PRReviewSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=ks,
    )


def _make_doc_generator_subagent(key_storage: AsyncMock | None = None) -> DocGeneratorSubagent:
    ks = key_storage or AsyncMock()
    if key_storage is None:
        key_info = MagicMock()
        key_info.base_url = BYOK_BASE_URL
        key_info.model_name = None
        ks.get_key_info.return_value = key_info
        ks.get_api_key.return_value = TEST_API_KEY
    return DocGeneratorSubagent(
        provider_selector=MagicMock(),
        cost_tracker=AsyncMock(),
        resilient_executor=MagicMock(),
        key_storage=ks,
    )


# ---------------------------------------------------------------------------
# PRReviewSubagent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pr_review_proxy_enabled_uses_proxy_base_url() -> None:
    """PRReviewSubagent.stream() uses proxy base_url when ai_proxy_enabled=True."""
    subagent = _make_pr_review_subagent()
    context = _make_context()
    input_data = PRReviewInput(repository_id=uuid4(), pr_number=42)

    with (
        patch(
            "pilot_space.ai.agents.subagents.pr_review_subagent.get_settings",
            return_value=_make_settings(proxy_enabled=True),
        ),
        patch("pilot_space.ai.agents.subagents.pr_review_subagent.build_sdk_env") as mock_build,
        patch(
            "pilot_space.ai.agents.subagents.pr_review_subagent.ClaudeSDKClient"
        ) as mock_client_cls,
    ):
        mock_build.return_value = {"ANTHROPIC_API_KEY": TEST_API_KEY, "PATH": "", "HOME": ""}
        mock_client = AsyncMock()
        mock_client.receive_response = AsyncMock(
            return_value=AsyncMock(
                __aiter__=lambda s: s, __anext__=AsyncMock(side_effect=StopAsyncIteration)
            )
        )
        mock_client_cls.return_value = mock_client

        async for _ in subagent.stream(input_data, context):
            pass

        expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
        mock_build.assert_called_once_with(TEST_API_KEY, base_url=expected_proxy_url)


@pytest.mark.asyncio
async def test_pr_review_proxy_disabled_uses_byok_base_url() -> None:
    """PRReviewSubagent.stream() uses BYOK base_url when ai_proxy_enabled=False."""
    subagent = _make_pr_review_subagent()
    context = _make_context()
    input_data = PRReviewInput(repository_id=uuid4(), pr_number=42)

    with (
        patch(
            "pilot_space.ai.agents.subagents.pr_review_subagent.get_settings",
            return_value=_make_settings(proxy_enabled=False),
        ),
        patch("pilot_space.ai.agents.subagents.pr_review_subagent.build_sdk_env") as mock_build,
        patch(
            "pilot_space.ai.agents.subagents.pr_review_subagent.ClaudeSDKClient"
        ) as mock_client_cls,
    ):
        mock_build.return_value = {"ANTHROPIC_API_KEY": TEST_API_KEY, "PATH": "", "HOME": ""}
        mock_client = AsyncMock()
        mock_client.receive_response = AsyncMock(
            return_value=AsyncMock(
                __aiter__=lambda s: s, __anext__=AsyncMock(side_effect=StopAsyncIteration)
            )
        )
        mock_client_cls.return_value = mock_client

        async for _ in subagent.stream(input_data, context):
            pass

        mock_build.assert_called_once_with(TEST_API_KEY, base_url=BYOK_BASE_URL)


# ---------------------------------------------------------------------------
# DocGeneratorSubagent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_doc_generator_proxy_enabled_uses_proxy_base_url() -> None:
    """DocGeneratorSubagent.stream() uses proxy base_url when ai_proxy_enabled=True."""
    subagent = _make_doc_generator_subagent()
    context = _make_context()
    input_data = DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["a.py"])

    with (
        patch(
            "pilot_space.ai.agents.subagents.doc_generator_subagent.get_settings",
            return_value=_make_settings(proxy_enabled=True),
        ),
        patch("pilot_space.ai.agents.subagents.doc_generator_subagent.build_sdk_env") as mock_build,
        patch(
            "pilot_space.ai.agents.subagents.doc_generator_subagent.ClaudeSDKClient"
        ) as mock_client_cls,
    ):
        mock_build.return_value = {"ANTHROPIC_API_KEY": TEST_API_KEY, "PATH": "", "HOME": ""}
        mock_client = AsyncMock()
        mock_client.receive_response = AsyncMock(
            return_value=AsyncMock(
                __aiter__=lambda s: s, __anext__=AsyncMock(side_effect=StopAsyncIteration)
            )
        )
        mock_client_cls.return_value = mock_client

        async for _ in subagent.stream(input_data, context):
            pass

        expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
        mock_build.assert_called_once_with(TEST_API_KEY, base_url=expected_proxy_url)


@pytest.mark.asyncio
async def test_doc_generator_proxy_disabled_uses_byok_base_url() -> None:
    """DocGeneratorSubagent.stream() uses BYOK base_url when ai_proxy_enabled=False."""
    subagent = _make_doc_generator_subagent()
    context = _make_context()
    input_data = DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["a.py"])

    with (
        patch(
            "pilot_space.ai.agents.subagents.doc_generator_subagent.get_settings",
            return_value=_make_settings(proxy_enabled=False),
        ),
        patch("pilot_space.ai.agents.subagents.doc_generator_subagent.build_sdk_env") as mock_build,
        patch(
            "pilot_space.ai.agents.subagents.doc_generator_subagent.ClaudeSDKClient"
        ) as mock_client_cls,
    ):
        mock_build.return_value = {"ANTHROPIC_API_KEY": TEST_API_KEY, "PATH": "", "HOME": ""}
        mock_client = AsyncMock()
        mock_client.receive_response = AsyncMock(
            return_value=AsyncMock(
                __aiter__=lambda s: s, __anext__=AsyncMock(side_effect=StopAsyncIteration)
            )
        )
        mock_client_cls.return_value = mock_client

        async for _ in subagent.stream(input_data, context):
            pass

        mock_build.assert_called_once_with(TEST_API_KEY, base_url=BYOK_BASE_URL)


# ---------------------------------------------------------------------------
# Proxy env: workspace_id is in URL path, NOT in env vars
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_subagents_encode_workspace_in_url_not_env_when_proxied() -> None:
    """Both subagents encode workspace_id in URL path, not X_WORKSPACE_ID env var."""
    user_id = uuid4()
    context = _make_context(user_id=user_id)

    for SubagentCls, input_data, module_path in [
        (
            PRReviewSubagent,
            PRReviewInput(repository_id=uuid4(), pr_number=1),
            "pilot_space.ai.agents.subagents.pr_review_subagent",
        ),
        (
            DocGeneratorSubagent,
            DocGeneratorInput(workspace_id=WORKSPACE_ID, doc_type="api", source_files=["x.py"]),
            "pilot_space.ai.agents.subagents.doc_generator_subagent",
        ),
    ]:
        ks = AsyncMock()
        key_info = MagicMock()
        key_info.base_url = BYOK_BASE_URL
        key_info.model_name = None
        ks.get_key_info.return_value = key_info
        ks.get_api_key.return_value = TEST_API_KEY

        subagent = SubagentCls(
            provider_selector=MagicMock(),
            cost_tracker=AsyncMock(),
            resilient_executor=MagicMock(),
            key_storage=ks,
        )

        captured_env: dict[str, str] = {}

        def capture_build_sdk_env(api_key: str, base_url: str | None = None) -> dict[str, str]:
            env = {"ANTHROPIC_API_KEY": api_key, "PATH": "", "HOME": ""}
            if base_url:
                env["ANTHROPIC_BASE_URL"] = base_url
            return env

        with (
            patch(f"{module_path}.get_settings", return_value=_make_settings(proxy_enabled=True)),
            patch(f"{module_path}.build_sdk_env", side_effect=capture_build_sdk_env) as mock_build,
            patch(f"{module_path}.ClaudeSDKClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.receive_response = AsyncMock(
                return_value=AsyncMock(
                    __aiter__=lambda s: s,
                    __anext__=AsyncMock(side_effect=StopAsyncIteration),
                )
            )
            mock_client_cls.return_value = mock_client

            async for _ in subagent.stream(input_data, context):
                pass

            # build_sdk_env should receive the URL with workspace_id in path
            expected_proxy_url = f"{PROXY_BASE_URL}/{WORKSPACE_ID}/"
            mock_build.assert_called_once_with(TEST_API_KEY, base_url=expected_proxy_url)

            # The SDK env should NOT have X_WORKSPACE_ID or X_USER_ID
            sdk_options = mock_client_cls.call_args[0][0]
            captured_env = sdk_options.env

        assert "X_WORKSPACE_ID" not in captured_env, (
            f"{SubagentCls.__name__} must NOT set X_WORKSPACE_ID (workspace_id is in URL path)"
        )
        assert "X_USER_ID" not in captured_env, (
            f"{SubagentCls.__name__} must NOT set X_USER_ID (no longer needed)"
        )
