"""Unit tests for CostTracker.

T013: Test cost calculation, tracking, and summary queries.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from pilot_space.ai.infrastructure.cost_tracker import (
    PRICING_TABLE,
    CostTracker,
)
from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def cost_tracker_mock() -> CostTracker:
    """Create CostTracker instance with mock session for sync tests."""
    return CostTracker(MagicMock())


@pytest.fixture
def cost_tracker(db_session: AsyncSession) -> CostTracker:
    """Create CostTracker instance with real session for async tests."""
    return CostTracker(db_session)


@pytest.fixture
def workspace_id() -> uuid.UUID:
    """Test workspace UUID."""
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    """Test user UUID."""
    return uuid.uuid4()


class TestCostCalculation:
    """Test cost calculation logic."""

    def test_calculate_cost_anthropic_claude_sonnet(self, cost_tracker_mock: CostTracker) -> None:
        """Verify cost calculation for Claude Sonnet."""
        # Arrange
        provider = "anthropic"
        model = "claude-sonnet-4-20250514"
        input_tokens = 1000
        output_tokens = 500

        # Expected: (1000/1M * 3) + (500/1M * 15) = 0.003 + 0.0075 = 0.0105
        expected_cost = 0.0105

        # Act
        cost = cost_tracker_mock.calculate_cost(provider, model, input_tokens, output_tokens)

        # Assert
        assert cost == pytest.approx(expected_cost, abs=1e-6)

    def test_calculate_cost_openai_gpt4o(self, cost_tracker_mock: CostTracker) -> None:
        """Verify cost calculation for GPT-4o."""
        # Arrange
        provider = "openai"
        model = "gpt-4o"
        input_tokens = 2000
        output_tokens = 1000

        # Expected: (2000/1M * 5) + (1000/1M * 15) = 0.01 + 0.015 = 0.025
        expected_cost = 0.025

        # Act
        cost = cost_tracker_mock.calculate_cost(provider, model, input_tokens, output_tokens)

        # Assert
        assert cost == pytest.approx(expected_cost, abs=1e-6)

    def test_calculate_cost_google_gemini_flash(self, cost_tracker_mock: CostTracker) -> None:
        """Verify cost calculation for Gemini Flash."""
        # Arrange
        provider = "google"
        model = "gemini-2.0-flash"
        input_tokens = 10000
        output_tokens = 5000

        # Expected: (10000/1M * 0.075) + (5000/1M * 0.30) = 0.00075 + 0.0015 = 0.00225
        expected_cost = 0.00225

        # Act
        cost = cost_tracker_mock.calculate_cost(provider, model, input_tokens, output_tokens)

        # Assert
        assert cost == pytest.approx(expected_cost, abs=1e-6)

    def test_calculate_cost_unknown_provider(self, cost_tracker_mock: CostTracker) -> None:
        """Verify error for unknown provider."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown provider"):
            cost_tracker_mock.calculate_cost("unknown", "model", 100, 50)

    def test_calculate_cost_unknown_model(self, cost_tracker_mock: CostTracker) -> None:
        """Verify error for unknown model."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown model"):
            cost_tracker_mock.calculate_cost("anthropic", "unknown-model", 100, 50)

    def test_calculate_cost_embedding_model(self, cost_tracker_mock: CostTracker) -> None:
        """Verify cost calculation for embedding model (no output tokens)."""
        # Arrange
        provider = "openai"
        model = "text-embedding-3-large"
        input_tokens = 5000
        output_tokens = 0

        # Expected: (5000/1M * 0.13) + (0/1M * 0) = 0.00065
        expected_cost = 0.00065

        # Act
        cost = cost_tracker_mock.calculate_cost(provider, model, input_tokens, output_tokens)

        # Assert
        assert cost == pytest.approx(expected_cost, abs=1e-6)


@pytest.mark.skip(reason="Fixture scope mismatch with session-scoped test_engine")
class TestCostTracking:
    """Test cost tracking to database."""

    @pytest.mark.asyncio
    async def test_track_cost_creates_record(
        self,
        cost_tracker: CostTracker,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify tracking creates database record."""
        # Arrange
        agent_name = "note_enhancer"
        provider = "anthropic"
        model = "claude-sonnet-4-20250514"
        input_tokens = 1000
        output_tokens = 500

        # Act
        record = await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=agent_name,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Assert
        assert record.id is not None
        assert record.workspace_id == workspace_id
        assert record.user_id == user_id
        assert record.agent_name == agent_name
        assert record.provider == provider
        assert record.model == model
        assert record.input_tokens == input_tokens
        assert record.output_tokens == output_tokens
        assert record.cost_usd == pytest.approx(0.0105, abs=1e-6)

        # Verify in database
        db_record = await db_session.get(AICostRecord, record.id)
        assert db_record is not None
        assert float(db_record.cost_usd) == pytest.approx(0.0105, abs=1e-6)


@pytest.mark.skip(reason="Fixture scope mismatch with session-scoped test_engine")
class TestWorkspaceSummary:
    """Test workspace cost summary queries."""

    @pytest.mark.asyncio
    async def test_workspace_summary_empty(
        self,
        cost_tracker: CostTracker,
        workspace_id: uuid.UUID,
    ) -> None:
        """Verify summary for workspace with no records."""
        # Act
        summary = await cost_tracker.get_workspace_summary(workspace_id, days=30)

        # Assert
        assert summary.total_cost == 0.0
        assert summary.total_requests == 0
        assert summary.total_input_tokens == 0
        assert summary.total_output_tokens == 0
        assert summary.by_provider == {}
        assert summary.by_agent == {}
        assert summary.by_model == {}

    @pytest.mark.asyncio
    async def test_workspace_summary_single_record(
        self,
        cost_tracker: CostTracker,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify summary with single record."""
        # Arrange
        await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="test_agent",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )

        # Act
        summary = await cost_tracker.get_workspace_summary(workspace_id, days=30)

        # Assert
        assert summary.total_cost == pytest.approx(0.0105, abs=1e-6)
        assert summary.total_requests == 1
        assert summary.total_input_tokens == 1000
        assert summary.total_output_tokens == 500
        assert summary.by_provider["anthropic"] == pytest.approx(0.0105, abs=1e-6)
        assert summary.by_agent["test_agent"] == pytest.approx(0.0105, abs=1e-6)
        assert summary.by_model["claude-sonnet-4-20250514"] == pytest.approx(0.0105, abs=1e-6)

    @pytest.mark.asyncio
    async def test_workspace_summary_multiple_providers(
        self,
        cost_tracker: CostTracker,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify summary aggregates multiple providers correctly."""
        # Arrange - Create records with different providers
        await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="agent1",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="agent2",
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )

        # Act
        summary = await cost_tracker.get_workspace_summary(workspace_id, days=30)

        # Assert
        assert summary.total_requests == 2
        assert summary.total_cost == pytest.approx(0.0105 + 0.025, abs=1e-6)
        assert summary.by_provider["anthropic"] == pytest.approx(0.0105, abs=1e-6)
        assert summary.by_provider["openai"] == pytest.approx(0.025, abs=1e-6)


@pytest.mark.skip(reason="Fixture scope mismatch with session-scoped test_engine")
class TestUserSummary:
    """Test user cost summary queries."""

    @pytest.mark.asyncio
    async def test_user_summary_single_user(
        self,
        cost_tracker: CostTracker,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Verify user summary aggregates correctly."""
        # Arrange
        await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="agent1",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        await cost_tracker.track(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="agent2",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=2000,
            output_tokens=1000,
        )

        # Act
        summary = await cost_tracker.get_user_summary(user_id, days=30)

        # Assert
        assert summary.total_requests == 2
        assert summary.total_cost == pytest.approx(0.0105 + 0.021, abs=1e-6)
        assert summary.total_input_tokens == 3000
        assert summary.total_output_tokens == 1500


class TestGetCostTrends:
    """Test get_cost_trends query construction."""

    @pytest.mark.asyncio
    async def test_get_cost_trends_daily_empty(self) -> None:
        """Verify daily trends returns empty list when no records exist."""
        from datetime import date
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(session)
        ws_id = uuid.uuid4()

        result = await tracker.get_cost_trends(
            workspace_id=ws_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            granularity="daily",
        )

        assert result == []
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_trends_weekly_empty(self) -> None:
        """Verify weekly trends returns empty list when no records exist."""
        from datetime import date
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(session)
        ws_id = uuid.uuid4()

        result = await tracker.get_cost_trends(
            workspace_id=ws_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            granularity="weekly",
        )

        assert result == []
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_trends_daily_with_data(self) -> None:
        """Verify daily trends correctly formats results."""
        from datetime import date
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        row = MagicMock()
        row.period = date(2026, 1, 15)
        row.total_cost_usd = Decimal("0.025")
        row.request_count = 5
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row]))
        session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(session)
        ws_id = uuid.uuid4()

        result = await tracker.get_cost_trends(
            workspace_id=ws_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            granularity="daily",
        )

        assert len(result) == 1
        assert result[0]["period"] == "2026-01-15"
        assert result[0]["total_cost_usd"] == pytest.approx(0.025, abs=1e-6)
        assert result[0]["request_count"] == 5
        assert result[0]["avg_cost_per_request"] == pytest.approx(0.005, abs=1e-6)

    @pytest.mark.asyncio
    async def test_get_cost_trends_weekly_with_data(self) -> None:
        """Verify weekly trends correctly formats string period."""
        from datetime import date
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        row = MagicMock()
        row.period = "2026-03"  # ISO week format
        row.total_cost_usd = Decimal("1.50")
        row.request_count = 10
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row]))
        session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(session)
        ws_id = uuid.uuid4()

        result = await tracker.get_cost_trends(
            workspace_id=ws_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            granularity="weekly",
        )

        assert len(result) == 1
        assert result[0]["period"] == "2026-03"
        assert result[0]["total_cost_usd"] == pytest.approx(1.50, abs=1e-6)
        assert result[0]["request_count"] == 10


class TestPricingTable:
    """Test pricing table completeness."""

    def test_pricing_table_has_all_providers(self) -> None:
        """Verify pricing table includes all required providers."""
        assert "anthropic" in PRICING_TABLE
        assert "google" in PRICING_TABLE
        assert "openai" in PRICING_TABLE

    def test_pricing_table_has_anthropic_models(self) -> None:
        """Verify Anthropic models are in pricing table."""
        assert "claude-opus-4-5-20251101" in PRICING_TABLE["anthropic"]
        assert "claude-sonnet-4-20250514" in PRICING_TABLE["anthropic"]
        assert "claude-3-5-haiku-20241022" in PRICING_TABLE["anthropic"]

    def test_pricing_table_has_google_models(self) -> None:
        """Verify Google models are in pricing table."""
        assert "gemini-2.0-pro" in PRICING_TABLE["google"]
        assert "gemini-2.0-flash" in PRICING_TABLE["google"]

    def test_pricing_table_has_openai_models(self) -> None:
        """Verify OpenAI models are in pricing table."""
        assert "gpt-4o" in PRICING_TABLE["openai"]
        assert "gpt-4o-mini" in PRICING_TABLE["openai"]
        assert "text-embedding-3-large" in PRICING_TABLE["openai"]

    def test_pricing_format_is_decimal_tuple(self) -> None:
        """Verify pricing is stored as (Decimal, Decimal) tuples."""
        for models in PRICING_TABLE.values():
            for pricing in models.values():
                assert isinstance(pricing, tuple)
                assert len(pricing) == 2
                assert isinstance(pricing[0], Decimal)
                assert isinstance(pricing[1], Decimal)


# ============================================================================
# Phase 4 AIGOV-06 — operation_type tests (implemented in plan 04-02)
# ============================================================================


@pytest.mark.asyncio
async def test_track_persists_operation_type() -> None:
    """CostTracker.track(operation_type='ghost_text') saves operation_type to DB.

    When operation_type is provided, the saved AICostRecord.operation_type
    must equal the passed value.
    """
    from unittest.mock import AsyncMock, MagicMock

    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Set up mock session
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    captured_record: list[AICostRecord] = []

    def capture_add(record: AICostRecord) -> None:
        captured_record.append(record)

    session.add.side_effect = capture_add

    async def mock_refresh(record: AICostRecord) -> None:
        # Simulate DB assigning id and created_at after flush
        record.id = uuid.uuid4()
        from datetime import UTC, datetime

        record.created_at = datetime.now(UTC)

    session.refresh = mock_refresh

    tracker = CostTracker(session)

    result = await tracker.track(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_name="ghost_text_agent",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=500,
        output_tokens=100,
        operation_type="ghost_text",
    )

    assert len(captured_record) == 1
    saved = captured_record[0]
    assert saved.operation_type == "ghost_text"


@pytest.mark.asyncio
async def test_track_operation_type_nullable() -> None:
    """track() with no operation_type saves NULL to DB.

    When operation_type is omitted, AICostRecord.operation_type must be None.
    Ensures backward compatibility with existing callers that don't pass operation_type.
    """
    from unittest.mock import AsyncMock, MagicMock

    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    captured_record: list[AICostRecord] = []

    def capture_add(record: AICostRecord) -> None:
        captured_record.append(record)

    session.add.side_effect = capture_add

    async def mock_refresh(record: AICostRecord) -> None:
        record.id = uuid.uuid4()
        from datetime import UTC, datetime

        record.created_at = datetime.now(UTC)

    session.refresh = mock_refresh

    tracker = CostTracker(session)

    await tracker.track(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_name="some_agent",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=50,
        # operation_type not passed — should default to None
    )

    assert len(captured_record) == 1
    saved = captured_record[0]
    assert saved.operation_type is None
