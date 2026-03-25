"""Tests for _background_graph_extraction LLMGateway wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent import _background_graph_extraction


@asynccontextmanager
async def _mock_db_session():
    """Yield a mock async session for get_db_session."""
    session = AsyncMock()
    yield session


@pytest.mark.asyncio
async def test_background_graph_extraction_constructs_llm_gateway():
    """When resilient_executor and encryption_key are provided, LLMGateway is constructed."""
    mock_graph_queue = MagicMock()
    mock_executor = MagicMock()
    workspace_id = uuid4()
    user_id = uuid4()

    mock_gateway_instance = MagicMock()

    with (
        patch(
            "pilot_space.infrastructure.database.get_db_session",
            side_effect=_mock_db_session,
        ),
        patch(
            "pilot_space.infrastructure.database.rls.set_rls_context",
            new_callable=AsyncMock,
        ),
        patch(
            "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
        ) as mock_ks_cls,
        patch(
            "pilot_space.ai.infrastructure.cost_tracker.CostTracker",
        ) as mock_ct_cls,
        patch(
            "pilot_space.ai.proxy.llm_gateway.LLMGateway",
        ) as mock_gw_cls,
        patch(
            "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
        ) as mock_extract_cls,
    ):
        mock_gw_cls.return_value = mock_gateway_instance

        mock_extract_svc = AsyncMock()
        mock_extract_svc.execute = AsyncMock(return_value=MagicMock(nodes=[], edges=[]))
        mock_extract_cls.return_value = mock_extract_svc

        await _background_graph_extraction(
            graph_queue_client=mock_graph_queue,
            workspace_id=workspace_id,
            user_id=user_id,
            messages=[{"role": "user", "content": "test"}],
            anthropic_api_key="sk-test-key",
            resilient_executor=mock_executor,
            encryption_key="test-secret-key",
        )

        # Verify LLMGateway was constructed with the executor
        mock_gw_cls.assert_called_once()
        call_kwargs = mock_gw_cls.call_args
        assert call_kwargs.kwargs.get("executor") == mock_executor

        # Verify SecureKeyStorage was constructed with encryption_key
        mock_ks_cls.assert_called_once()
        ks_kwargs = mock_ks_cls.call_args
        assert ks_kwargs.kwargs.get("master_secret") == "test-secret-key"

        # Verify GraphExtractionService received the gateway
        mock_extract_cls.assert_called_once()
        gw_arg = mock_extract_cls.call_args.kwargs.get("llm_gateway")
        assert gw_arg is mock_gateway_instance, (
            "GraphExtractionService must receive the constructed LLMGateway instance"
        )


@pytest.mark.asyncio
async def test_background_graph_extraction_no_executor_skips_gateway():
    """When resilient_executor is None, llm_gateway remains None (graceful fallback)."""
    mock_graph_queue = MagicMock()

    with patch(
        "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
    ) as mock_extract_cls:
        mock_extract_svc = AsyncMock()
        mock_extract_svc.execute = AsyncMock(return_value=MagicMock(nodes=[], edges=[]))
        mock_extract_cls.return_value = mock_extract_svc

        await _background_graph_extraction(
            graph_queue_client=mock_graph_queue,
            workspace_id=uuid4(),
            user_id=uuid4(),
            messages=[{"role": "user", "content": "test"}],
            anthropic_api_key="sk-test-key",
            # resilient_executor NOT provided -- defaults to None
        )

        # GraphExtractionService should receive llm_gateway=None
        gw_arg = mock_extract_cls.call_args.kwargs.get("llm_gateway")
        assert gw_arg is None
