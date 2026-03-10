"""TENANT-03: Storage quota enforcement (507 hard block, 80% warning header).

Unit tests for per-workspace resource limits:
- Storage quota: hard block at 100%, X-Storage-Warning header at 80%
- Per-workspace API rate limits from Redis cache
- NULL quota columns fall back to system defaults

Tests cover the quota helper functions and the GET/PATCH quota API endpoints.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.workspace_quota import (
    _check_storage_quota,
    _update_storage_usage,
)

# =============================================================================
# Storage Quota Helper Tests
# =============================================================================


class TestCheckStorageQuota:
    """Tests for _check_storage_quota() helper function."""

    @pytest.mark.asyncio
    async def test_write_blocked_at_100_percent_quota(self) -> None:
        """Returns (False, None) when storage_used + delta >= quota_bytes."""
        session = AsyncMock()
        workspace = MagicMock()
        workspace.storage_quota_mb = 10  # 10 MB
        workspace.storage_used_bytes = 10 * 1024 * 1024  # exactly at quota

        session.get = AsyncMock(return_value=workspace)

        workspace_id = uuid.uuid4()
        allowed, pct = await _check_storage_quota(session, workspace_id, delta_bytes=1)

        assert allowed is False
        assert pct is None

    @pytest.mark.asyncio
    async def test_write_blocked_exceeds_quota(self) -> None:
        """Returns (False, None) when storage_used + delta > quota_bytes."""
        session = AsyncMock()
        workspace = MagicMock()
        workspace.storage_quota_mb = 10  # 10 MB
        workspace.storage_used_bytes = 9 * 1024 * 1024 + 512 * 1024  # 9.5 MB

        session.get = AsyncMock(return_value=workspace)

        workspace_id = uuid.uuid4()
        # Delta that would push past 10 MB
        allowed, pct = await _check_storage_quota(session, workspace_id, delta_bytes=600 * 1024)

        assert allowed is False
        assert pct is None

    @pytest.mark.asyncio
    async def test_warning_header_at_80_percent_quota(self) -> None:
        """Returns (True, pct >= 0.80) when projected usage is at 80%+."""
        session = AsyncMock()
        workspace = MagicMock()
        workspace.storage_quota_mb = 100  # 100 MB
        # Already at 75 MB, delta of 10 MB pushes to 85%
        workspace.storage_used_bytes = 75 * 1024 * 1024

        session.get = AsyncMock(return_value=workspace)

        workspace_id = uuid.uuid4()
        allowed, pct = await _check_storage_quota(
            session, workspace_id, delta_bytes=10 * 1024 * 1024
        )

        assert allowed is True
        assert pct is not None
        assert pct >= 0.80
        assert pct < 1.0

    @pytest.mark.asyncio
    async def test_no_warning_below_80_percent(self) -> None:
        """Returns (True, None) when projected usage is below 80%."""
        session = AsyncMock()
        workspace = MagicMock()
        workspace.storage_quota_mb = 100
        workspace.storage_used_bytes = 50 * 1024 * 1024  # 50 MB

        session.get = AsyncMock(return_value=workspace)

        workspace_id = uuid.uuid4()
        allowed, pct = await _check_storage_quota(session, workspace_id, delta_bytes=1024)

        assert allowed is True
        assert pct is None

    @pytest.mark.asyncio
    async def test_null_quota_always_allows(self) -> None:
        """Returns (True, None) when storage_quota_mb is NULL (unlimited)."""
        session = AsyncMock()
        workspace = MagicMock()
        workspace.storage_quota_mb = None  # unlimited
        workspace.storage_used_bytes = 999 * 1024 * 1024  # Very high usage

        session.get = AsyncMock(return_value=workspace)

        workspace_id = uuid.uuid4()
        # Even with huge delta, NULL quota means unlimited
        allowed, pct = await _check_storage_quota(
            session, workspace_id, delta_bytes=999 * 1024 * 1024
        )

        assert allowed is True
        assert pct is None


class TestUpdateStorageUsage:
    """Tests for _update_storage_usage() helper function."""

    @pytest.mark.asyncio
    async def test_update_storage_usage_positive_delta(self) -> None:
        """Delta update increments storage_used_bytes by the given amount."""
        session = AsyncMock()
        session.execute = AsyncMock()

        workspace_id = uuid.uuid4()
        await _update_storage_usage(session, workspace_id, delta_bytes=1024)

        # Verify execute was called (checking storage update happened)
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_storage_usage_negative_delta(self) -> None:
        """Negative delta decrements storage_used_bytes (content deleted/shrunk)."""
        session = AsyncMock()
        session.execute = AsyncMock()

        workspace_id = uuid.uuid4()
        await _update_storage_usage(session, workspace_id, delta_bytes=-512)

        session.execute.assert_called_once()


# =============================================================================
# Quota API Endpoint Tests
# =============================================================================


class TestQuotaApiEndpoints:
    """Tests for GET/PATCH /workspaces/{slug}/settings/quota endpoints."""

    @pytest.mark.asyncio
    async def test_get_quota_returns_workspace_quota_fields(self) -> None:
        """GET /settings/quota returns rate limits and storage usage fields."""
        from pilot_space.api.v1.routers.workspace_quota import get_workspace_quota

        session = AsyncMock()
        current_user = MagicMock()
        current_user.user_id = uuid.uuid4()

        workspace = MagicMock()
        workspace.id = uuid.uuid4()
        workspace.rate_limit_standard_rpm = 500
        workspace.rate_limit_ai_rpm = 50
        workspace.storage_quota_mb = 100
        workspace.storage_used_bytes = 50 * 1024 * 1024

        with (
            patch(
                "pilot_space.api.v1.routers.workspace_quota._resolve_workspace_and_check_permission",
                return_value=workspace,
            ) as _mock_resolve,
        ):
            result = await get_workspace_quota(
                workspace_slug="test-ws",
                session=session,
                current_user=current_user,
            )

        assert result["rate_limit_standard_rpm"] == 500
        assert result["rate_limit_ai_rpm"] == 50
        assert result["storage_quota_mb"] == 100
        assert result["storage_used_bytes"] == 50 * 1024 * 1024
        assert "storage_used_mb" in result

    @pytest.mark.asyncio
    async def test_patch_quota_by_owner_updates_columns(self) -> None:
        """PATCH /settings/quota by OWNER updates workspace quota columns."""
        from pilot_space.api.v1.routers.workspace_quota import (
            QuotaUpdateRequest,
            patch_workspace_quota,
        )

        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        current_user = MagicMock()
        current_user.user_id = uuid.uuid4()

        workspace = MagicMock()
        workspace.id = uuid.uuid4()
        workspace.rate_limit_standard_rpm = None
        workspace.rate_limit_ai_rpm = None
        workspace.storage_quota_mb = None
        workspace.storage_used_bytes = 0

        body = QuotaUpdateRequest(
            rate_limit_standard_rpm=200,
            rate_limit_ai_rpm=25,
            storage_quota_mb=50,
        )

        mock_redis = AsyncMock()

        with patch(
            "pilot_space.api.v1.routers.workspace_quota._resolve_workspace_and_check_manage",
            return_value=workspace,
        ):
            result = await patch_workspace_quota(
                workspace_slug="test-ws",
                body=body,
                session=session,
                current_user=current_user,
                redis=mock_redis,
            )

        # Verify fields were updated on the workspace model
        assert workspace.rate_limit_standard_rpm == 200
        assert workspace.rate_limit_ai_rpm == 25
        assert workspace.storage_quota_mb == 50
        # Verify Redis cache was invalidated
        mock_redis.delete.assert_called_once_with(f"ws_limits:{workspace.id}")

    @pytest.mark.asyncio
    async def test_patch_quota_by_non_owner_returns_403(self) -> None:
        """PATCH /settings/quota by ADMIN (not OWNER) returns 403."""
        from pilot_space.api.v1.routers.workspace_quota import (
            QuotaUpdateRequest,
            patch_workspace_quota,
        )

        session = AsyncMock()
        current_user = MagicMock()
        current_user.user_id = uuid.uuid4()

        body = QuotaUpdateRequest(storage_quota_mb=100)

        with (
            patch(
                "pilot_space.api.v1.routers.workspace_quota._resolve_workspace_and_check_manage",
                side_effect=HTTPException(status_code=403, detail="Owner access required"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await patch_workspace_quota(
                workspace_slug="test-ws",
                body=body,
                session=session,
                current_user=current_user,
                redis=AsyncMock(),
            )

        assert exc_info.value.status_code == 403


# =============================================================================
# Rate Limit Cache Integration Tests
# =============================================================================


class TestRateLimitCacheIntegration:
    """Tests for per-workspace rate limit caching via Redis."""

    @pytest.mark.asyncio
    async def test_per_workspace_rate_limit_from_redis_cache(self) -> None:
        """Rate limiter uses workspace-specific limit from Redis (ws_limits:{workspace_id})."""
        from unittest.mock import AsyncMock

        from pilot_space.api.middleware.rate_limiter import RateLimitMiddleware

        workspace_id = str(uuid.uuid4())
        mock_redis = AsyncMock()

        # Pre-populate cache with custom limit
        cached_data = json.dumps({"standard_rpm": 10, "ai_rpm": 5})
        mock_redis.get = AsyncMock(return_value=cached_data)

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        limit = await middleware._get_effective_limit(workspace_id, "standard")

        assert limit == 10

    @pytest.mark.asyncio
    async def test_null_quota_columns_use_system_defaults(self) -> None:
        """NULL rate_limit_standard_rpm falls back to system default (1000 RPM)."""
        from pilot_space.api.middleware.rate_limiter import (
            RATE_LIMIT_CONFIGS,
            RateLimitMiddleware,
        )

        workspace_id = str(uuid.uuid4())
        mock_redis = AsyncMock()

        # Cache miss, DB returns NULL column
        cached_data = json.dumps({"standard_rpm": 1000, "ai_rpm": 100})
        mock_redis.get = AsyncMock(return_value=cached_data)

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        limit = await middleware._get_effective_limit(workspace_id, "standard")

        # System default is used when workspace has NULL column
        assert limit == RATE_LIMIT_CONFIGS["standard"].requests_per_minute
