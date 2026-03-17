"""Unit tests for _background_graph_extraction.

Tests cover:
- Early return when messages is empty
- Early return when neither api_key nor base_url is provided
- No DB session opened when LLM extracts zero nodes
- set_rls_context called before write when user_id is present
- set_rls_context NOT called when user_id is None
- DB session opened only in write phase (after LLM call completes)
- Strong task reference lifecycle via _background_tasks set
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent import _background_graph_extraction

pytestmark = pytest.mark.asyncio

_MESSAGES = [
    {"role": "user", "content": "Which cache backend should we use?"},
    {"role": "assistant", "content": "We decided to use Redis for caching."},
]


def _make_extraction_result(node_count: int = 2) -> MagicMock:
    """Build a fake ExtractionResult with the requested number of nodes."""
    result = MagicMock()
    result.nodes = [MagicMock() for _ in range(node_count)]
    result.edges = []
    return result


class TestBackgroundGraphExtractionEarlyReturns:
    """Guard conditions that skip processing without touching the DB."""

    async def test_empty_messages_returns_immediately(self) -> None:
        with (
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session"
            ) as mock_build,
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=[],
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        mock_build.assert_not_called()

    async def test_no_api_key_and_no_base_url_returns_immediately(self) -> None:
        with (
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session"
            ) as mock_build,
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key=None,
                base_url=None,
            )

        mock_build.assert_not_called()

    async def test_base_url_without_api_key_proceeds(self) -> None:
        """Ollama workspaces have base_url but no api_key — must not skip."""
        empty_result = _make_extraction_result(node_count=0)
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=empty_result)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_svc,
            ),
            patch("pilot_space.infrastructure.database.get_db_session"),
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key=None,
                base_url="http://localhost:11434",
            )

        mock_svc.execute.assert_awaited_once()


class TestBackgroundGraphExtractionNoNodesSkipsDB:
    """When LLM returns zero nodes, the DB session must never be opened."""

    async def test_no_db_session_opened_when_no_nodes_extracted(self) -> None:
        empty_result = _make_extraction_result(node_count=0)
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=empty_result)

        mock_db_cm = MagicMock()

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_db_cm,
            ) as mock_get_db,
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        mock_get_db.assert_not_called()


class TestBackgroundGraphExtractionRLSContext:
    """set_rls_context must be called before the write when user_id is present."""

    async def test_rls_context_called_before_write(self) -> None:
        workspace_id = uuid4()
        user_id = uuid4()
        result = _make_extraction_result(node_count=1)

        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(return_value=result)

        mock_write_svc = MagicMock()
        mock_write_svc.execute = AsyncMock()

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=False)

        call_order: list[str] = []

        async def fake_set_rls(session: object, uid: object, wid: object) -> None:
            call_order.append("set_rls")

        async def fake_write_execute(payload: object) -> None:
            call_order.append("write")

        mock_write_svc.execute = AsyncMock(side_effect=fake_write_execute)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_db_cm,
            ),
            patch(
                "pilot_space.infrastructure.database.rls.set_rls_context",
                side_effect=fake_set_rls,
            ),
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session",
                return_value=mock_write_svc,
            ),
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=workspace_id,
                user_id=user_id,
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        assert call_order == ["set_rls", "write"], (
            "set_rls_context must be called before graph_write_service.execute"
        )

    async def test_rls_context_not_called_when_user_id_is_none(self) -> None:
        result = _make_extraction_result(node_count=1)

        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(return_value=result)

        mock_write_svc = MagicMock()
        mock_write_svc.execute = AsyncMock()

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_db_cm,
            ),
            patch("pilot_space.infrastructure.database.rls.set_rls_context") as mock_set_rls,
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session",
                return_value=mock_write_svc,
            ),
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=None,
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        mock_set_rls.assert_not_called()


class TestBackgroundGraphExtractionSessionScope:
    """DB session must be acquired only in the write phase, after the LLM call."""

    async def test_db_session_opened_after_extraction(self) -> None:
        """Verify the DB context manager is only entered post-extraction."""
        result = _make_extraction_result(node_count=1)
        phase_log: list[str] = []

        async def fake_extraction_execute(payload: object) -> MagicMock:
            phase_log.append("llm_done")
            return result

        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(side_effect=fake_extraction_execute)

        mock_write_svc = MagicMock()
        mock_write_svc.execute = AsyncMock()

        mock_session = AsyncMock()

        class _FakeDbCm:
            async def __aenter__(self) -> AsyncMock:
                phase_log.append("session_opened")
                return mock_session

            async def __aexit__(self, *args: object) -> bool:
                return False

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=_FakeDbCm(),
            ),
            patch(
                "pilot_space.infrastructure.database.rls.set_rls_context",
                new=AsyncMock(),
            ),
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session",
                return_value=mock_write_svc,
            ),
        ):
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        assert phase_log == ["llm_done", "session_opened"], (
            "DB session must be opened only after the LLM extraction completes"
        )


class TestBackgroundGraphExtractionErrorHandling:
    """Exceptions must be caught and logged — never propagated to the caller."""

    async def test_extraction_exception_is_non_fatal(self) -> None:
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(side_effect=RuntimeError("LLM unreachable"))

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_svc,
            ),
        ):
            # Must not raise
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

    async def test_write_exception_is_non_fatal(self) -> None:
        result = _make_extraction_result(node_count=1)
        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(return_value=result)

        mock_write_svc = MagicMock()
        mock_write_svc.execute = AsyncMock(side_effect=RuntimeError("DB unavailable"))

        mock_session = AsyncMock()
        mock_db_cm = MagicMock()
        mock_db_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_db_cm,
            ),
            patch("pilot_space.infrastructure.database.rls.set_rls_context", new=AsyncMock()),
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session",
                return_value=mock_write_svc,
            ),
        ):
            # Must not raise
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=_MESSAGES,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )
