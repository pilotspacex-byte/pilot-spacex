"""Integration tests for cost tracking endpoints.

T094: Integration tests for cost tracking API.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.infrastructure.cost_tracker import CostTracker
from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord
from pilot_space.infrastructure.database.models.user import User

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    "sqlite" in os.getenv("DATABASE_URL", "sqlite"),
    reason="Requires PostgreSQL (JSONB columns)",
)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def second_user(db_session: AsyncSession) -> User:
    """Create second test user."""
    user = User(
        id=uuid4(),
        email="user2@example.com",
        full_name="Second User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def cost_tracker(db_session: AsyncSession) -> CostTracker:
    """Create cost tracker instance."""
    return CostTracker(session=db_session)


@pytest.fixture
async def workspace_with_costs(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
) -> UUID:
    """Create workspace with sample cost records."""
    workspace_id = uuid4()

    # Create cost records for different agents, users, and days
    today = datetime.now(UTC)

    # Records from 3 days ago
    three_days_ago = today - timedelta(days=3)
    db_session.add(
        AICostRecord(
            workspace_id=workspace_id,
            user_id=test_user.id,
            agent_name="ghost_text",
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.00175,  # (1000*0.25 + 500*1.25)/1M = 0.00175
            created_at=three_days_ago,
        )
    )

    # Records from 2 days ago
    two_days_ago = today - timedelta(days=2)
    db_session.add(
        AICostRecord(
            workspace_id=workspace_id,
            user_id=test_user.id,
            agent_name="pr_review",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=5000,
            output_tokens=2000,
            cost_usd=0.045,  # (5000*3 + 2000*15)/1M = 0.045
            created_at=two_days_ago,
        )
    )
    db_session.add(
        AICostRecord(
            workspace_id=workspace_id,
            user_id=second_user.id,
            agent_name="ghost_text",
            provider="google",
            model="gemini-2.0-flash",
            input_tokens=10000,
            output_tokens=3000,
            cost_usd=0.00165,  # (10000*0.075 + 3000*0.30)/1M = 0.00165
            created_at=two_days_ago,
        )
    )

    # Records from yesterday
    yesterday = today - timedelta(days=1)
    db_session.add(
        AICostRecord(
            workspace_id=workspace_id,
            user_id=test_user.id,
            agent_name="issue_extractor",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=3000,
            output_tokens=1500,
            cost_usd=0.0315,  # (3000*3 + 1500*15)/1M = 0.0315
            created_at=yesterday,
        )
    )

    await db_session.commit()
    return workspace_id


class TestCostSummaryEndpoint:
    """Test GET /ai/costs/summary endpoint."""

    @pytest.mark.asyncio
    async def test_returns_cost_summary(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify endpoint returns complete cost summary."""
        # Arrange
        headers = {
            "X-Workspace-Id": str(workspace_with_costs),
        }

        # Act
        response = await client.get("/api/v1/ai/costs/summary", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "workspace_id" in data
        assert "total_cost_usd" in data
        assert "total_requests" in data
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "by_agent" in data
        assert "by_user" in data
        assert "by_day" in data

        # Verify data structure
        assert isinstance(data["by_agent"], list)
        assert isinstance(data["by_user"], list)
        assert isinstance(data["by_day"], list)

        # Verify we have 4 total records
        assert data["total_requests"] == 4

    @pytest.mark.asyncio
    async def test_filters_by_date_range(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify date range filtering."""
        # Arrange - Query only last 2 days
        start = (datetime.now(UTC).date() - timedelta(days=2)).isoformat()
        end = datetime.now(UTC).date().isoformat()

        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            f"/api/v1/ai/costs/summary?start_date={start}&end_date={end}",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == start
        assert data["period_end"] == end

        # Should have 3 records (excluding 3-day-old record)
        assert data["total_requests"] == 3

    @pytest.mark.asyncio
    async def test_aggregates_by_agent(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify agent aggregation."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get("/api/v1/ai/costs/summary", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        by_agent = {item["agent_name"]: item for item in data["by_agent"]}

        # Verify ghost_text aggregation (2 records)
        assert "ghost_text" in by_agent
        assert by_agent["ghost_text"]["request_count"] == 2

        # Verify pr_review (1 record)
        assert "pr_review" in by_agent
        assert by_agent["pr_review"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_aggregates_by_user(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
        test_user: User,
        second_user: User,
    ) -> None:
        """Verify user aggregation with names."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get("/api/v1/ai/costs/summary", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        by_user = {item["user_id"]: item for item in data["by_user"]}

        # Verify test_user (3 records)
        assert str(test_user.id) in by_user
        assert by_user[str(test_user.id)]["request_count"] == 3
        assert by_user[str(test_user.id)]["user_name"] == "Test User"

        # Verify second_user (1 record)
        assert str(second_user.id) in by_user
        assert by_user[str(second_user.id)]["request_count"] == 1
        assert by_user[str(second_user.id)]["user_name"] == "Second User"

    @pytest.mark.asyncio
    async def test_aggregates_by_day(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify daily aggregation."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get("/api/v1/ai/costs/summary", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert len(data["by_day"]) > 0
        # Each day should have date, total_cost_usd, request_count
        for day_item in data["by_day"]:
            assert "date" in day_item
            assert "total_cost_usd" in day_item
            assert "request_count" in day_item

    @pytest.mark.asyncio
    async def test_validates_date_range(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify date validation."""
        # Arrange - Invalid: start after end
        start = datetime.now(UTC).date().isoformat()
        end = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            f"/api/v1/ai/costs/summary?start_date={start}&end_date={end}",
            headers=headers,
        )

        # Assert
        assert response.status_code == 400
        assert "start_date" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_requires_workspace_header(
        self,
        client: AsyncClient,
    ) -> None:
        """Verify workspace header required."""
        # Act
        response = await client.get("/api/v1/ai/costs/summary")

        # Assert
        assert response.status_code == 400
        assert "workspace" in response.json()["detail"].lower()


class TestCostByUserEndpoint:
    """Test GET /ai/costs/by-user endpoint."""

    @pytest.mark.asyncio
    async def test_returns_user_breakdown(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify endpoint returns user cost breakdown."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get("/api/v1/ai/costs/by-user", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "workspace_id" in data
        assert "users" in data
        assert "total_cost_usd" in data
        assert isinstance(data["users"], list)

    @pytest.mark.asyncio
    async def test_filters_by_date_range(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify date filtering works."""
        # Arrange
        start = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        end = datetime.now(UTC).date().isoformat()

        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            f"/api/v1/ai/costs/by-user?start_date={start}&end_date={end}",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == start
        assert data["period_end"] == end


class TestCostTrendsEndpoint:
    """Test GET /ai/costs/trends endpoint."""

    @pytest.mark.asyncio
    async def test_returns_daily_trends(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify daily trend data."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            "/api/v1/ai/costs/trends?granularity=daily",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "workspace_id" in data
        assert "granularity" in data
        assert data["granularity"] == "daily"
        assert "trends" in data
        assert isinstance(data["trends"], list)

        # Each trend should have required fields
        if data["trends"]:
            trend = data["trends"][0]
            assert "period" in trend
            assert "total_cost_usd" in trend
            assert "request_count" in trend
            assert "avg_cost_per_request" in trend

    @pytest.mark.asyncio
    async def test_returns_weekly_trends(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify weekly trend data."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            "/api/v1/ai/costs/trends?granularity=weekly",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "weekly"

    @pytest.mark.asyncio
    async def test_validates_granularity(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify granularity validation."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act
        response = await client.get(
            "/api/v1/ai/costs/trends?granularity=monthly",
            headers=headers,
        )

        # Assert
        assert response.status_code == 400
        assert "granularity" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_uses_correct_default_period(
        self,
        client: AsyncClient,
        workspace_with_costs: UUID,
    ) -> None:
        """Verify default periods differ by granularity."""
        # Arrange
        headers = {"X-Workspace-Id": str(workspace_with_costs)}

        # Act - Daily (should default to 30 days)
        daily_response = await client.get(
            "/api/v1/ai/costs/trends?granularity=daily",
            headers=headers,
        )

        # Act - Weekly (should default to 90 days)
        weekly_response = await client.get(
            "/api/v1/ai/costs/trends?granularity=weekly",
            headers=headers,
        )

        # Assert
        assert daily_response.status_code == 200
        assert weekly_response.status_code == 200

        daily_data = daily_response.json()
        weekly_data = weekly_response.json()

        # Verify different default periods
        assert daily_data["period_start"] != weekly_data["period_start"]
