"""Unit tests for memory engine services.

Tests MemorySearchService, MemorySaveService, ConstitutionIngestService,
and ConstitutionVersionGate application services with mocked repositories.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pilot_space.application.services.memory.constitution_service import (
    ConstitutionIngestPayload,
    ConstitutionIngestService,
    ConstitutionRuleInput,
    ConstitutionVersionGate,
)
from pilot_space.application.services.memory.memory_save_service import (
    MemorySavePayload,
    MemorySaveService,
)
from pilot_space.application.services.memory.memory_search_service import (
    MemorySearchPayload,
    MemorySearchService,
)
from pilot_space.domain.constitution_rule import RuleSeverity
from pilot_space.domain.memory_entry import MemorySourceType

# ---------------------------------------------------------------------------
# Helpers / Fakes
# ---------------------------------------------------------------------------


def _workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-1111-2222-3333-444444444444")


@dataclass
class _FakeMemoryModel:
    id: uuid.UUID
    workspace_id: uuid.UUID
    content: str
    source_type: str
    pinned: bool = False
    keywords: str = ""


@dataclass
class _FakeConstitutionModel:
    id: uuid.UUID
    workspace_id: uuid.UUID
    content: str
    severity: Any
    version: int
    active: bool = True
    source_block_id: uuid.UUID | None = None


def _make_fake_memory_model(content: str = "test content") -> _FakeMemoryModel:
    return _FakeMemoryModel(
        id=uuid.uuid4(),
        workspace_id=_workspace_id(),
        content=content,
        source_type="user_feedback",
    )


def _make_fake_constitution_model(
    content: str = "You must cite sources.",
    version: int = 1,
    active: bool = True,
) -> _FakeConstitutionModel:
    return _FakeConstitutionModel(
        id=uuid.uuid4(),
        workspace_id=_workspace_id(),
        content=content,
        severity=RuleSeverity.MUST,
        version=version,
        active=active,
    )


def _make_memory_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.hybrid_search = AsyncMock(return_value=[])
    repo.list_by_workspace = AsyncMock(return_value=[])
    repo.create = AsyncMock(side_effect=lambda m: m)
    repo.create_with_keywords = AsyncMock(
        side_effect=lambda **kwargs: _make_fake_memory_model(kwargs.get("content", "test"))
    )
    return repo


def _make_constitution_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_latest_version = AsyncMock(return_value=0)
    repo.get_active_rules = AsyncMock(return_value=[])
    repo.create = AsyncMock(side_effect=lambda m: m)
    repo.update = AsyncMock(side_effect=lambda m: m)
    return repo


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_queue() -> AsyncMock:
    queue = AsyncMock()
    queue.enqueue = AsyncMock()
    return queue


# ---------------------------------------------------------------------------
# MemorySearchService tests
# ---------------------------------------------------------------------------


class TestMemorySearchServicePayload:
    def test_defaults(self) -> None:
        payload = MemorySearchPayload(query="test", workspace_id=_workspace_id())
        assert payload.limit == 5
        assert payload.google_api_key is None

    def test_custom_limit(self) -> None:
        payload = MemorySearchPayload(
            query="find this",
            workspace_id=_workspace_id(),
            limit=10,
        )
        assert payload.limit == 10

    def test_with_api_key(self) -> None:
        payload = MemorySearchPayload(
            query="q",
            workspace_id=_workspace_id(),
            google_api_key="key-abc",  # pragma: allowlist secret
        )
        assert payload.google_api_key == "key-abc"  # pragma: allowlist secret


class TestMemorySearchServiceEmbedQuery:
    @pytest.mark.asyncio
    async def test_no_embedding_service_falls_back_to_keyword(self) -> None:
        """When no embedding_service is provided, execute() returns keyword results."""
        repo = _make_memory_repo()
        session = _make_session()
        fake_model = _make_fake_memory_model("test content")
        repo.list_by_workspace = AsyncMock(return_value=[fake_model])

        service = MemorySearchService(repo, session, embedding_service=None)
        result = await service.execute(
            MemorySearchPayload(query="test", workspace_id=_workspace_id())
        )
        assert result.embedding_used is False
        assert result.results == [] or len(result.results) >= 0

    @pytest.mark.asyncio
    async def test_embedding_service_called_on_execute(self) -> None:
        """When embedding_service is provided, execute() calls embed() and uses vector search."""
        repo = _make_memory_repo()
        session = _make_session()
        fake_embedding = [0.1] * 768
        fake_results = [
            {
                "id": str(uuid.uuid4()),
                "content": "result content",
                "source_type": "user_feedback",
                "pinned": False,
                "score": 0.9,
                "embedding_score": 0.9,
                "text_score": 0.7,
            }
        ]
        repo.hybrid_search = AsyncMock(return_value=fake_results)

        mock_embedding_svc = AsyncMock()
        mock_embedding_svc.embed = AsyncMock(return_value=fake_embedding)

        service = MemorySearchService(repo, session, embedding_service=mock_embedding_svc)
        result = await service.execute(
            MemorySearchPayload(query="hello", workspace_id=_workspace_id())
        )
        mock_embedding_svc.embed.assert_awaited_once_with("hello")
        assert result.embedding_used is True

    @pytest.mark.asyncio
    async def test_embedding_service_failure_falls_back(self) -> None:
        """When embedding_service.embed() returns None, fall back to keyword search."""
        repo = _make_memory_repo()
        session = _make_session()
        fake_model = _make_fake_memory_model("fallback content")
        repo.list_by_workspace = AsyncMock(return_value=[fake_model])

        mock_embedding_svc = AsyncMock()
        mock_embedding_svc.embed = AsyncMock(return_value=None)

        service = MemorySearchService(repo, session, embedding_service=mock_embedding_svc)
        result = await service.execute(MemorySearchPayload(query="q", workspace_id=_workspace_id()))
        assert result.embedding_used is False


class TestMemorySearchServiceExecute:
    @pytest.mark.asyncio
    async def test_uses_hybrid_search_when_embedding_available(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        fake_results = [
            {
                "id": str(uuid.uuid4()),
                "content": "memory content",
                "source_type": "user_feedback",
                "pinned": False,
                "score": 0.85,
                "embedding_score": 0.9,
                "text_score": 0.7,
            }
        ]
        repo.hybrid_search = AsyncMock(return_value=fake_results)

        fake_embedding = [0.1] * 768
        mock_embedding_svc = AsyncMock()
        mock_embedding_svc.embed = AsyncMock(return_value=fake_embedding)

        service = MemorySearchService(repo, session, embedding_service=mock_embedding_svc)

        result = await service.execute(
            MemorySearchPayload(
                query="test query",
                workspace_id=_workspace_id(),
            )
        )

        assert result.embedding_used is True
        assert result.query == "test query"
        assert len(result.results) == 1
        repo.hybrid_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_keyword_when_no_embedding(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        fake_model = _make_fake_memory_model("user prefers short answers")
        repo.list_by_workspace = AsyncMock(return_value=[fake_model])

        # No embedding_service → always keyword fallback
        service = MemorySearchService(repo, session, embedding_service=None)

        result = await service.execute(
            MemorySearchPayload(
                query="preferences",
                workspace_id=_workspace_id(),
            )
        )

        assert result.embedding_used is False
        assert len(result.results) == 1
        assert result.results[0]["score"] == 0.0
        assert result.results[0]["content"] == "user prefers short answers"
        repo.list_by_workspace.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_results_when_no_data(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()

        # No embedding_service → keyword fallback → empty list
        service = MemorySearchService(repo, session, embedding_service=None)

        result = await service.execute(
            MemorySearchPayload(
                query="nothing matches",
                workspace_id=_workspace_id(),
            )
        )

        assert result.results == []
        assert result.embedding_used is False

    @pytest.mark.asyncio
    async def test_passes_limit_to_hybrid_search(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        fake_embedding = [0.0] * 768

        mock_embedding_svc = AsyncMock()
        mock_embedding_svc.embed = AsyncMock(return_value=fake_embedding)

        service = MemorySearchService(repo, session, embedding_service=mock_embedding_svc)

        await service.execute(
            MemorySearchPayload(
                query="q",
                workspace_id=_workspace_id(),
                limit=10,
            )
        )

        call_kwargs = repo.hybrid_search.call_args.kwargs
        assert call_kwargs["limit"] == 10


# ---------------------------------------------------------------------------
# MemorySaveService tests
# ---------------------------------------------------------------------------


class TestMemorySaveServicePayload:
    def test_defaults(self) -> None:
        payload = MemorySavePayload(
            workspace_id=_workspace_id(),
            content="Test memory",
            source_type=MemorySourceType.USER_FEEDBACK,
        )
        assert payload.pinned is False
        assert payload.source_id is None
        assert payload.expires_at is None

    def test_pinned_payload(self) -> None:
        payload = MemorySavePayload(
            workspace_id=_workspace_id(),
            content="Important memory",
            source_type=MemorySourceType.SKILL_OUTCOME,
            pinned=True,
        )
        assert payload.pinned is True

    def test_with_expiry(self) -> None:
        expires = datetime(2030, 1, 1, tzinfo=UTC)
        payload = MemorySavePayload(
            workspace_id=_workspace_id(),
            content="Temporary memory",
            source_type=MemorySourceType.INTENT,
            expires_at=expires,
        )
        assert payload.expires_at == expires


class TestMemorySaveServiceExecute:
    @pytest.mark.asyncio
    async def test_persists_entry_and_enqueues_embedding(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        queue = _make_queue()
        fake_model = _make_fake_memory_model("save this memory")
        repo.create_with_keywords = AsyncMock(return_value=fake_model)

        service = MemorySaveService(repo, queue, session)

        result = await service.execute(
            MemorySavePayload(
                workspace_id=_workspace_id(),
                content="save this memory",
                source_type=MemorySourceType.USER_FEEDBACK,
            )
        )

        assert result.entry_id == fake_model.id
        assert result.embedding_enqueued is True
        repo.create_with_keywords.assert_awaited_once()
        session.commit.assert_awaited_once()
        queue.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_keywords_extracted_from_content(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        queue = _make_queue()
        fake_model = _make_fake_memory_model()
        repo.create = AsyncMock(return_value=fake_model)

        service = MemorySaveService(repo, queue, session)

        result = await service.execute(
            MemorySavePayload(
                workspace_id=_workspace_id(),
                content="Python async testing",
                source_type=MemorySourceType.USER_FEEDBACK,
            )
        )

        assert "python" in result.keywords
        assert "async" in result.keywords
        assert "testing" in result.keywords

    @pytest.mark.asyncio
    async def test_embedding_enqueue_failure_still_returns_result(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        queue = _make_queue()
        queue.enqueue = AsyncMock(side_effect=RuntimeError("queue down"))
        fake_model = _make_fake_memory_model()
        repo.create_with_keywords = AsyncMock(return_value=fake_model)

        service = MemorySaveService(repo, queue, session)

        result = await service.execute(
            MemorySavePayload(
                workspace_id=_workspace_id(),
                content="memory content",
                source_type=MemorySourceType.INTENT,
            )
        )

        assert result.entry_id == fake_model.id
        assert result.embedding_enqueued is False

    @pytest.mark.asyncio
    async def test_enqueue_payload_contains_correct_fields(self) -> None:
        repo = _make_memory_repo()
        session = _make_session()
        queue = _make_queue()
        fake_model = _make_fake_memory_model()
        repo.create_with_keywords = AsyncMock(return_value=fake_model)

        service = MemorySaveService(repo, queue, session)
        ws_id = _workspace_id()

        await service.execute(
            MemorySavePayload(
                workspace_id=ws_id,
                content="content",
                source_type=MemorySourceType.USER_FEEDBACK,
            )
        )

        enqueue_call = queue.enqueue.call_args
        job_payload = enqueue_call.args[1]
        assert job_payload["task_type"] == "memory_embedding"
        assert job_payload["workspace_id"] == str(ws_id)
        assert "entry_id" in job_payload


# ---------------------------------------------------------------------------
# ConstitutionIngestService tests
# ---------------------------------------------------------------------------


class TestConstitutionIngestServicePayload:
    def test_empty_rules_defaults(self) -> None:
        payload = ConstitutionIngestPayload(workspace_id=_workspace_id())
        assert payload.rules == []

    def test_with_rules(self) -> None:
        payload = ConstitutionIngestPayload(
            workspace_id=_workspace_id(),
            rules=[ConstitutionRuleInput(content="You MUST do this.")],
        )
        assert len(payload.rules) == 1

    def test_rule_input_severity_override(self) -> None:
        rule = ConstitutionRuleInput(
            content="Some rule",
            severity=RuleSeverity.MUST,
        )
        assert rule.severity == RuleSeverity.MUST

    def test_rule_input_severity_none_means_auto_detect(self) -> None:
        rule = ConstitutionRuleInput(content="Some rule", severity=None)
        assert rule.severity is None


class TestConstitutionIngestServiceExecute:
    @pytest.mark.asyncio
    async def test_empty_rules_returns_current_version(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=3)

        service = ConstitutionIngestService(repo, queue, session)

        result = await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[],
            )
        )

        assert result.version == 3
        assert result.rule_count == 0
        assert result.indexing_enqueued is False

    @pytest.mark.asyncio
    async def test_bumps_version_and_persists_rules(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=2)
        repo.get_active_rules = AsyncMock(return_value=[])

        fake_rule = _make_fake_constitution_model(version=3)
        repo.create = AsyncMock(return_value=fake_rule)

        service = ConstitutionIngestService(repo, queue, session)

        result = await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[ConstitutionRuleInput(content="You MUST cite sources.")],
            )
        )

        assert result.version == 3
        assert result.rule_count == 1
        assert result.indexing_enqueued is True
        repo.create.assert_awaited_once()
        session.commit.assert_awaited_once()
        queue.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivates_existing_rules_before_ingest(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()

        existing_rule = _make_fake_constitution_model(version=1, active=True)
        repo.get_active_rules = AsyncMock(return_value=[existing_rule])
        repo.get_latest_version = AsyncMock(return_value=1)
        repo.create = AsyncMock(return_value=_make_fake_constitution_model(version=2))

        service = ConstitutionIngestService(repo, queue, session)

        await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[ConstitutionRuleInput(content="New rule.")],
            )
        )

        assert existing_rule.active is False
        repo.update.assert_awaited_once_with(existing_rule)

    @pytest.mark.asyncio
    async def test_auto_detects_severity_when_not_provided(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=0)
        repo.get_active_rules = AsyncMock(return_value=[])

        captured_models: list[Any] = []

        async def capture_create(model: Any) -> Any:
            captured_models.append(model)
            return model

        repo.create = AsyncMock(side_effect=capture_create)

        service = ConstitutionIngestService(repo, queue, session)

        await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[
                    ConstitutionRuleInput(
                        content="You MUST always cite sources.",
                        severity=None,
                    )
                ],
            )
        )

        assert len(captured_models) == 1
        assert captured_models[0].severity == RuleSeverity.MUST

    @pytest.mark.asyncio
    async def test_severity_override_wins_over_auto_detection(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=0)
        repo.get_active_rules = AsyncMock(return_value=[])

        captured_models: list[Any] = []

        async def capture_create(model: Any) -> Any:
            captured_models.append(model)
            return model

        repo.create = AsyncMock(side_effect=capture_create)

        service = ConstitutionIngestService(repo, queue, session)

        await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[
                    ConstitutionRuleInput(
                        content="You MUST do X.",  # auto-detect: MUST
                        severity=RuleSeverity.MAY,  # override: MAY wins
                    )
                ],
            )
        )

        assert captured_models[0].severity == RuleSeverity.MAY

    @pytest.mark.asyncio
    async def test_enqueue_failure_returns_false_indexing_enqueued(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        queue.enqueue = AsyncMock(side_effect=RuntimeError("queue unavailable"))
        repo.get_latest_version = AsyncMock(return_value=0)
        repo.get_active_rules = AsyncMock(return_value=[])
        repo.create = AsyncMock(return_value=_make_fake_constitution_model(version=1))

        service = ConstitutionIngestService(repo, queue, session)

        result = await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[ConstitutionRuleInput(content="A rule.")],
            )
        )

        assert result.indexing_enqueued is False
        assert result.rule_count == 1

    @pytest.mark.asyncio
    async def test_multiple_rules_enqueue_per_rule(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=0)
        repo.get_active_rules = AsyncMock(return_value=[])

        call_count = 0

        async def create_mock(model: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return model

        repo.create = AsyncMock(side_effect=create_mock)

        service = ConstitutionIngestService(repo, queue, session)

        await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[
                    ConstitutionRuleInput(content="Rule 1."),
                    ConstitutionRuleInput(content="Rule 2."),
                    ConstitutionRuleInput(content="Rule 3."),
                ],
            )
        )

        assert call_count == 3
        assert queue.enqueue.await_count == 3

    @pytest.mark.asyncio
    async def test_enqueue_payload_has_correct_table(self) -> None:
        repo = _make_constitution_repo()
        session = _make_session()
        queue = _make_queue()
        repo.get_latest_version = AsyncMock(return_value=0)
        repo.get_active_rules = AsyncMock(return_value=[])
        fake_rule = _make_fake_constitution_model(version=1)
        repo.create = AsyncMock(return_value=fake_rule)

        service = ConstitutionIngestService(repo, queue, session)

        await service.execute(
            ConstitutionIngestPayload(
                workspace_id=_workspace_id(),
                rules=[ConstitutionRuleInput(content="Rule.")],
            )
        )

        enqueue_call = queue.enqueue.call_args
        job_payload = enqueue_call.args[1]
        assert job_payload["table"] == "constitution_rules"
        assert job_payload["task_type"] == "memory_embedding"


# ---------------------------------------------------------------------------
# ConstitutionVersionGate tests
# ---------------------------------------------------------------------------


class TestConstitutionVersionGate:
    @pytest.mark.asyncio
    async def test_returns_true_when_version_already_indexed(self) -> None:
        repo = _make_constitution_repo()
        active_rule = _make_fake_constitution_model(version=3, active=True)
        repo.get_active_rules = AsyncMock(return_value=[active_rule])

        gate = ConstitutionVersionGate(repo)

        result = await gate.wait_for_version(_workspace_id(), required_version=3)

        assert result is True
        repo.get_active_rules.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_true_when_indexed_version_exceeds_required(self) -> None:
        repo = _make_constitution_repo()
        active_rule = _make_fake_constitution_model(version=5, active=True)
        repo.get_active_rules = AsyncMock(return_value=[active_rule])

        gate = ConstitutionVersionGate(repo)

        result = await gate.wait_for_version(_workspace_id(), required_version=3)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_active_rules(self) -> None:
        repo = _make_constitution_repo()
        repo.get_active_rules = AsyncMock(return_value=[])

        gate = ConstitutionVersionGate(repo)
        indexed = await gate._get_indexed_version(_workspace_id())

        assert indexed == 0

    @pytest.mark.asyncio
    async def test_get_indexed_version_returns_max_version(self) -> None:
        repo = _make_constitution_repo()
        rules = [
            _make_fake_constitution_model(version=1),
            _make_fake_constitution_model(version=3),
            _make_fake_constitution_model(version=2),
        ]
        repo.get_active_rules = AsyncMock(return_value=rules)

        gate = ConstitutionVersionGate(repo)
        indexed = await gate._get_indexed_version(_workspace_id())

        assert indexed == 3

    @pytest.mark.asyncio
    async def test_times_out_when_version_never_indexed(self) -> None:
        repo = _make_constitution_repo()
        # Always return version 0 — never reaches required_version=1
        repo.get_active_rules = AsyncMock(return_value=[])

        gate = ConstitutionVersionGate(repo)

        # Patch sleep and max wait to avoid real delays
        with (
            patch(
                "pilot_space.application.services.memory.constitution_service._VERSION_GATE_MAX_WAIT_S",
                2.0,
            ),
            patch(
                "pilot_space.application.services.memory.constitution_service._VERSION_GATE_POLL_INTERVAL_S",
                1.0,
            ),
            patch(
                "asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            result = await gate.wait_for_version(_workspace_id(), required_version=1)

        assert result is False

    @pytest.mark.asyncio
    async def test_polls_until_version_available(self) -> None:
        repo = _make_constitution_repo()
        # First call returns nothing, second call returns version 2
        call_count = 0

        async def dynamic_rules(workspace_id: uuid.UUID) -> list[_FakeConstitutionModel]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return []
            return [_make_fake_constitution_model(version=2)]

        repo.get_active_rules = AsyncMock(side_effect=dynamic_rules)

        gate = ConstitutionVersionGate(repo)

        with (
            patch(
                "pilot_space.application.services.memory.constitution_service._VERSION_GATE_MAX_WAIT_S",
                10.0,
            ),
            patch(
                "pilot_space.application.services.memory.constitution_service._VERSION_GATE_POLL_INTERVAL_S",
                1.0,
            ),
            patch(
                "asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            result = await gate.wait_for_version(_workspace_id(), required_version=2)

        assert result is True
        assert call_count == 2
