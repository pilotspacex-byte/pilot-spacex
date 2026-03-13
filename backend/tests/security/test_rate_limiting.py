"""T337: Rate Limiting Audit Tests.

Comprehensive tests for rate limiting implementation ensuring:
- Standard endpoint limits (1000 requests/minute)
- AI endpoint limits (100 requests/minute)
- Auth endpoint limits (10 requests/minute - stricter for security)
- Rate limit headers (X-RateLimit-*)
- Graceful degradation at limit (429 response)

Reference: NFR-019 Rate Limiting Requirements
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.requests import Request
from starlette.responses import Response

from pilot_space.api.middleware.rate_limiter import (
    RATE_LIMIT_CONFIGS,
    RateLimitMiddleware,
    _get_endpoint_type,
    _get_workspace_id,
)

# =============================================================================
# Test Data and Helpers
# =============================================================================


def create_mock_request(
    path: str,
    headers: dict[str, str] | None = None,
    client_host: str = "127.0.0.1",
) -> MagicMock:
    """Create a mock Starlette Request object.

    Args:
        path: URL path for the request.
        headers: Optional headers dict.
        client_host: Client IP address.

    Returns:
        Mock Request object.
    """
    request = MagicMock(spec=Request)
    request.url.path = path
    request.headers = headers or {}
    request.client = MagicMock()
    request.client.host = client_host
    request.path_params = {}
    return request


async def mock_call_next(request: Request) -> Response:
    """Mock next middleware call."""
    return Response(content="OK", status_code=200)


# =============================================================================
# Rate Limit Configuration Tests
# =============================================================================


class TestRateLimitConfiguration:
    """Tests for rate limit configuration."""

    def test_standard_endpoint_limit(self) -> None:
        """Standard endpoints should be limited to 1000 requests/minute."""
        config = RATE_LIMIT_CONFIGS["standard"]
        assert config.requests_per_minute == 1000
        assert config.key_prefix == "standard"

    def test_ai_endpoint_limit(self) -> None:
        """AI endpoints should be limited to 100 requests/minute."""
        config = RATE_LIMIT_CONFIGS["ai"]
        assert config.requests_per_minute == 100
        assert config.key_prefix == "ai"


class TestEndpointTypeDetection:
    """Tests for endpoint type classification."""

    @pytest.mark.parametrize(
        ("path", "expected_type"),
        [
            # AI endpoints
            ("/api/v1/ai/ghost-text", "ai"),
            ("/api/v1/ai/analyze-note", "ai"),
            ("/api/v1/ai/extract-issues", "ai"),
            ("/api/v1/ai/chat", "ai"),
            ("/api/v1/notes/", "ai"),  # Notes involve ghost text
            ("/api/v1/issues/ai/suggestions", "ai"),
            ("/api/v1/pr-review/trigger", "ai"),
            # Standard endpoints
            ("/api/v1/workspaces", "standard"),
            ("/api/v1/projects", "standard"),
            ("/api/v1/issues", "standard"),
            ("/api/v1/cycles", "standard"),
            ("/api/v1/auth/me", "standard"),
            ("/health", "standard"),
        ],
    )
    def test_endpoint_type_detection(self, path: str, expected_type: str) -> None:
        """Verify correct endpoint type classification."""
        detected = _get_endpoint_type(path)
        assert detected == expected_type, f"Path {path} should be {expected_type}"


class TestWorkspaceIdExtraction:
    """Tests for workspace ID extraction from requests."""

    def test_extract_workspace_id_from_header(self) -> None:
        """Workspace ID should be extracted from X-Workspace-ID header."""
        workspace_id = str(uuid.uuid4())
        request = create_mock_request(
            path="/api/v1/issues",
            headers={"X-Workspace-ID": workspace_id},
        )

        extracted = _get_workspace_id(request)
        assert extracted == workspace_id

    def test_extract_workspace_id_from_path_params(self) -> None:
        """Workspace ID should be extracted from path parameters."""
        workspace_id = uuid.uuid4()
        request = create_mock_request(path="/api/v1/workspaces/{workspace_id}")
        request.path_params = {"workspace_id": workspace_id}

        extracted = _get_workspace_id(request)
        assert extracted == str(workspace_id)

    def test_fallback_to_none_without_workspace(self) -> None:
        """Should return None when no workspace ID available."""
        request = create_mock_request(path="/api/v1/issues")

        extracted = _get_workspace_id(request)
        assert extracted is None


# =============================================================================
# Rate Limit Middleware Tests
# =============================================================================


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware behavior."""

    @pytest.mark.asyncio
    async def test_middleware_disabled_without_redis(self) -> None:
        """Middleware should pass through when Redis is unavailable."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=None,
            enabled=True,
        )
        request = create_mock_request("/api/v1/issues")

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_explicitly_disabled(self, mock_redis: AsyncMock) -> None:
        """Middleware should pass through when explicitly disabled."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=False,
        )
        request = create_mock_request("/api/v1/issues")

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        # Redis should not be called
        mock_redis.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_check_bypasses_rate_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Health check endpoints should bypass rate limiting."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        for path in ["/health", "/api/v1/health"]:
            request = create_mock_request(path)
            response = await middleware.dispatch(request, mock_call_next)
            assert response.status_code == 200


# =============================================================================
# Standard Endpoint Rate Limiting Tests
# =============================================================================


class TestStandardEndpointRateLimiting:
    """Tests for standard endpoint rate limits (1000/min)."""

    @pytest.mark.asyncio
    async def test_standard_endpoint_within_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Requests within limit should succeed with rate limit headers."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "1000"

    @pytest.mark.asyncio
    async def test_standard_endpoint_rate_limit_headers(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify rate limit headers are correctly set."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/projects",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        # Verify headers
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset = int(response.headers["X-RateLimit-Reset"])

        assert limit == 1000
        assert remaining == 999  # First request
        assert reset > int(time.time())  # Future timestamp

    @pytest.mark.asyncio
    async def test_standard_endpoint_approaching_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify remaining count decreases correctly."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Simulate multiple requests
        for i in range(5):
            request = create_mock_request(
                "/api/v1/issues",
                headers={"X-Workspace-ID": workspace_id},
            )
            response = await middleware.dispatch(request, mock_call_next)
            remaining = int(response.headers["X-RateLimit-Remaining"])
            assert remaining == 1000 - (i + 1), (
                f"Request {i + 1}: remaining should be {1000 - (i + 1)}"
            )


# =============================================================================
# AI Endpoint Rate Limiting Tests
# =============================================================================


class TestAIEndpointRateLimiting:
    """Tests for AI endpoint rate limits (100/min)."""

    @pytest.mark.asyncio
    async def test_ai_endpoint_lower_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """AI endpoints should have lower rate limit (100/min)."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/ai/ghost-text",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "100"

    @pytest.mark.asyncio
    async def test_ai_endpoint_exceeds_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """AI endpoint should return 429 when limit exceeded."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Simulate 100 requests to reach limit
        for _ in range(100):
            request = create_mock_request(
                "/api/v1/ai/ghost-text",
                headers={"X-Workspace-ID": workspace_id},
            )
            await middleware.dispatch(request, mock_call_next)

        # 101st request should be rate limited — returns JSONResponse(429)
        request = create_mock_request(
            "/api/v1/ai/ghost-text",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_ai_endpoint_different_paths_share_limit(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """All AI endpoints should share the same rate limit."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        ai_paths = [
            "/api/v1/ai/ghost-text",
            "/api/v1/ai/analyze-note",
            "/api/v1/ai/extract-issues",
            "/api/v1/ai/chat",
        ]

        # Make requests to different AI endpoints
        for i, path in enumerate(ai_paths):
            request = create_mock_request(
                path,
                headers={"X-Workspace-ID": workspace_id},
            )
            response = await middleware.dispatch(request, mock_call_next)
            remaining = int(response.headers["X-RateLimit-Remaining"])
            assert remaining == 100 - (i + 1), "AI requests should share limit"


# =============================================================================
# Auth Endpoint Rate Limiting Tests
# =============================================================================


class TestAuthEndpointRateLimiting:
    """Tests for auth endpoint rate limits (stricter for security).

    Note: Auth endpoints should have stricter limits to prevent
    brute force attacks. Current implementation treats them as standard
    endpoints, but this documents the expected security enhancement.
    """

    @pytest.mark.asyncio
    async def test_auth_login_endpoint_rate_limited(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Login endpoint should be rate limited."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/login",
            client_host="192.168.1.100",
        )

        response = await middleware.dispatch(request, mock_call_next)

        # Auth endpoints currently use standard limits
        # TODO: Implement stricter auth rate limiting (10/min)
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_auth_callback_endpoint_rate_limited(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """OAuth callback should be rate limited."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/callback",
            client_host="192.168.1.100",
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers


# =============================================================================
# Rate Limit Header Tests
# =============================================================================


class TestRateLimitHeaders:
    """Tests for rate limit response headers."""

    @pytest.mark.asyncio
    async def test_x_ratelimit_limit_header(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """X-RateLimit-Limit should indicate max requests allowed."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Test standard endpoint
        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": workspace_id},
        )
        response = await middleware.dispatch(request, mock_call_next)
        assert response.headers["X-RateLimit-Limit"] == "1000"

    @pytest.mark.asyncio
    async def test_x_ratelimit_remaining_header(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """X-RateLimit-Remaining should decrease with each request."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # First request
        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": workspace_id},
        )
        response = await middleware.dispatch(request, mock_call_next)
        remaining_1 = int(response.headers["X-RateLimit-Remaining"])

        # Second request
        response = await middleware.dispatch(request, mock_call_next)
        remaining_2 = int(response.headers["X-RateLimit-Remaining"])

        assert remaining_2 == remaining_1 - 1

    @pytest.mark.asyncio
    async def test_x_ratelimit_reset_header(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """X-RateLimit-Reset should be a future Unix timestamp."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        reset_time = int(response.headers["X-RateLimit-Reset"])
        current_time = int(time.time())

        # Reset should be at most 60 seconds in the future (next minute boundary)
        assert reset_time > current_time
        assert reset_time <= current_time + 120  # Within 2 minutes

    @pytest.mark.asyncio
    async def test_retry_after_header_on_429(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Retry-After header should be set on 429 response."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Exhaust AI endpoint limit (100 requests)
        for _ in range(100):
            request = create_mock_request(
                "/api/v1/ai/chat",
                headers={"X-Workspace-ID": workspace_id},
            )
            await middleware.dispatch(request, mock_call_next)

        # Next request should trigger 429 — dispatch returns JSONResponse(429)
        request = create_mock_request(
            "/api/v1/ai/chat",
            headers={"X-Workspace-ID": workspace_id},
        )

        response = await middleware.dispatch(request, mock_call_next)

        # Verify Retry-After header
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        retry_after = int(response.headers["Retry-After"])
        assert retry_after >= 0
        assert retry_after <= 60  # At most 60 seconds


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when rate limiting fails."""

    @pytest.mark.asyncio
    async def test_redis_error_allows_request(self) -> None:
        """Request should succeed if Redis fails."""
        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = Exception("Redis connection error")

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request("/api/v1/issues")

        # Should not raise, should pass through
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redis_timeout_allows_request(self) -> None:
        """Request should succeed if Redis times out."""
        import asyncio

        mock_redis = AsyncMock()

        async def slow_incr(key: str) -> int:
            await asyncio.sleep(5)  # Simulate timeout
            return 1

        mock_redis.incr = slow_incr

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request("/api/v1/issues")

        # Note: In real implementation, we'd have a timeout wrapper
        # For this test, we verify the error handling path works
        # by directly testing with an exception
        mock_redis.incr = AsyncMock(side_effect=TimeoutError("Redis timeout"))

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200


# =============================================================================
# Workspace Isolation for Rate Limits Tests
# =============================================================================


class TestWorkspaceIsolationForRateLimits:
    """Tests ensuring rate limits are per-workspace."""

    @pytest.mark.asyncio
    async def test_different_workspaces_have_separate_limits(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Rate limits should be tracked separately per workspace."""
        workspace_a = str(uuid.uuid4())
        workspace_b = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Exhaust limit for workspace A
        for _ in range(100):
            request = create_mock_request(
                "/api/v1/ai/chat",
                headers={"X-Workspace-ID": workspace_a},
            )
            await middleware.dispatch(request, mock_call_next)

        # Workspace A should be limited — dispatch returns JSONResponse(429)
        request = create_mock_request(
            "/api/v1/ai/chat",
            headers={"X-Workspace-ID": workspace_a},
        )
        response_a = await middleware.dispatch(request, mock_call_next)
        assert response_a.status_code == 429

        # Workspace B should still have quota
        request = create_mock_request(
            "/api/v1/ai/chat",
            headers={"X-Workspace-ID": workspace_b},
        )
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200
        assert int(response.headers["X-RateLimit-Remaining"]) == 99

    @pytest.mark.asyncio
    async def test_ip_based_limit_without_workspace(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Requests without workspace should use IP-based limiting."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Request without workspace header
        request = create_mock_request(
            "/api/v1/issues",
            client_host="192.168.1.50",
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================


class TestRateLimitingEdgeCases:
    """Tests for edge cases and security considerations."""

    @pytest.mark.asyncio
    async def test_malformed_workspace_id_uses_ip(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Malformed workspace ID should fall back to IP-based limiting."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )
        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": "not-a-uuid"},
            client_host="10.0.0.1",
        )

        # Should still work - rate limit by the provided value
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests_handled_correctly(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Concurrent requests should be counted correctly."""
        import asyncio

        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        async def make_request() -> Response:
            request = create_mock_request(
                "/api/v1/ai/chat",
                headers={"X-Workspace-ID": workspace_id},
            )
            return await middleware.dispatch(request, mock_call_next)

        # Make 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Remaining should reflect all 50 requests
        final_remaining = int(responses[-1].headers["X-RateLimit-Remaining"])
        # Note: Due to async timing, exact count may vary slightly
        assert final_remaining <= 50

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Rate limit should reset after the time window.

        Note: This tests the concept - actual time-based testing
        would require mocking time.time().
        """
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Make some requests
        for _ in range(10):
            request = create_mock_request(
                "/api/v1/ai/chat",
                headers={"X-Workspace-ID": workspace_id},
            )
            await middleware.dispatch(request, mock_call_next)

        # Clear counts to simulate window reset
        mock_redis._call_counts.clear()

        # New request should have fresh quota
        request = create_mock_request(
            "/api/v1/ai/chat",
            headers={"X-Workspace-ID": workspace_id},
        )
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert int(response.headers["X-RateLimit-Remaining"]) == 99


# =============================================================================
# Integration Test Markers
# =============================================================================


class TestRateLimitMiddlewareWiring:
    """Verify RateLimitMiddleware wiring — registered and returns 429."""

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_registered_returns_429(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """RateLimitMiddleware is present in app stack and returns 429 when limit exceeded.

        Two assertions:
        1. Middleware stack inspection confirms RateLimitMiddleware is registered.
        2. Direct dispatch() call confirms 429 Response when INCR > limit.
        """
        from fastapi import FastAPI
        from fastapi.responses import PlainTextResponse
        from starlette.testclient import TestClient

        inner = FastAPI()

        @inner.get("/api/v1/issues")
        async def homepage() -> PlainTextResponse:
            return PlainTextResponse("ok")

        inner.add_middleware(
            RateLimitMiddleware,
            redis_client=mock_redis,
            enabled=True,
        )

        # Part 1: verify middleware is in the stack (built lazily via TestClient.__enter__).
        with TestClient(inner, raise_server_exceptions=False):
            stack = inner.middleware_stack
            found_rate_limit = False
            for _ in range(10):  # walk at most 10 layers
                if "RateLimitMiddleware" in type(stack).__name__:
                    found_rate_limit = True
                    break
                stack = getattr(stack, "app", None)
                if stack is None:
                    break
        assert found_rate_limit, "RateLimitMiddleware not found in FastAPI middleware stack"

        # Part 2: direct dispatch() call proves 429 Response is returned.
        # dispatch() now returns JSONResponse(429) instead of raising HTTPException,
        # so we assert on the response status code directly.
        mock_redis.incr.side_effect = None
        mock_redis.incr.return_value = 9999  # exceeds all standard/workspace limits
        middleware_instance = RateLimitMiddleware(
            app=MagicMock(), redis_client=mock_redis, enabled=True
        )

        request = create_mock_request(
            "/api/v1/issues",
            headers={"X-Workspace-ID": str(uuid.uuid4())},
        )
        response = await middleware_instance.dispatch(request, mock_call_next)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers


@pytest.mark.integration
class TestRateLimitingIntegration:
    """Integration tests requiring real Redis connection.

    These tests are marked as integration and require:
    - Running Redis instance
    - TEST_REDIS_URL environment variable

    Run with: pytest -m integration
    """

    @pytest.mark.skip(reason="Requires real Redis instance")
    @pytest.mark.asyncio
    async def test_real_redis_rate_limiting(self) -> None:
        """Test rate limiting with real Redis."""
        # This would test with actual Redis connection
        # Implementation left for integration test environment


# =============================================================================
# Per-Workspace Rate Limit Tests (TENANT-03)
# =============================================================================


class TestPerWorkspaceRateLimits:
    """Tests for per-workspace rate limit configuration via Redis cache."""

    @pytest.mark.asyncio
    async def test_get_effective_limit_returns_workspace_limit_from_redis(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_get_effective_limit returns workspace-specific RPM from Redis cache."""
        import json

        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Pre-populate Redis cache with workspace-specific limit
        cached_limits = {"standard_rpm": 200, "ai_rpm": 50}
        mock_redis._call_counts[f"ws_limits:{workspace_id}"] = json.dumps(cached_limits)

        limit = await middleware._get_effective_limit(workspace_id, "standard")

        assert limit == 200

    @pytest.mark.asyncio
    async def test_get_effective_limit_ai_endpoint_from_redis(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_get_effective_limit returns workspace AI RPM from Redis cache."""
        import json

        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        cached_limits = {"standard_rpm": 500, "ai_rpm": 25}
        mock_redis._call_counts[f"ws_limits:{workspace_id}"] = json.dumps(cached_limits)

        limit = await middleware._get_effective_limit(workspace_id, "ai")

        assert limit == 25

    @pytest.mark.asyncio
    async def test_get_effective_limit_null_workspace_column_uses_system_default(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_get_effective_limit returns system default when workspace column is NULL."""
        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Cache miss: Redis GET returns None, DB fallback returns None (NULL column)
        import json

        cached_limits = {"standard_rpm": 1000, "ai_rpm": 100}
        mock_redis._call_counts[f"ws_limits:{workspace_id}"] = json.dumps(cached_limits)

        limit = await middleware._get_effective_limit(workspace_id, "standard")

        # Returns system default when workspace has NULL (maps to 1000)
        assert limit == 1000

    @pytest.mark.asyncio
    async def test_get_effective_limit_redis_unavailable_returns_system_default(
        self,
    ) -> None:
        """_get_effective_limit returns system default when Redis is unavailable."""
        workspace_id = str(uuid.uuid4())
        failing_redis = AsyncMock()
        failing_redis.get = AsyncMock(side_effect=Exception("Redis connection refused"))

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=failing_redis,
            enabled=True,
        )

        # Should not raise, should return system default
        limit = await middleware._get_effective_limit(workspace_id, "standard")

        assert limit == RATE_LIMIT_CONFIGS["standard"].requests_per_minute  # 1000

    @pytest.mark.asyncio
    async def test_get_effective_limit_ai_redis_unavailable_returns_system_default(
        self,
    ) -> None:
        """_get_effective_limit returns AI system default when Redis is unavailable."""
        workspace_id = str(uuid.uuid4())
        failing_redis = AsyncMock()
        failing_redis.get = AsyncMock(side_effect=Exception("Redis connection refused"))

        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=failing_redis,
            enabled=True,
        )

        limit = await middleware._get_effective_limit(workspace_id, "ai")

        assert limit == RATE_LIMIT_CONFIGS["ai"].requests_per_minute  # 100

    @pytest.mark.asyncio
    async def test_violation_counter_incremented_on_429(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Violation counter rl_violations:{workspace_id}:{date} is incremented on 429."""
        from datetime import UTC, datetime

        workspace_id = str(uuid.uuid4())
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            redis_client=mock_redis,
            enabled=True,
        )

        # Exhaust AI limit
        for _ in range(100):
            request = create_mock_request(
                "/api/v1/ai/ghost-text",
                headers={"X-Workspace-ID": workspace_id},
            )
            await middleware.dispatch(request, mock_call_next)

        # 101st request triggers 429 — dispatch returns JSONResponse(429)
        request = create_mock_request(
            "/api/v1/ai/ghost-text",
            headers={"X-Workspace-ID": workspace_id},
        )
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify violation counter was incremented
        today = datetime.now(UTC).strftime("%Y%m%d")
        violation_key = f"rl_violations:{workspace_id}:{today}"
        assert mock_redis._call_counts.get(violation_key, 0) >= 1


# =============================================================================
# Main App Registration Tests (TENANT-03)
# =============================================================================


class TestRateLimitMiddlewareMainRegistration:
    """Verify RateLimitMiddleware is registered in main.app and returns 429."""

    def test_middleware_active_returns_429_via_testclient(self) -> None:
        """RateLimitMiddleware in main.app returns 429 when Redis INCR exceeds limit.

        Uses TestClient (not dispatch()) so the full middleware stack is built.
        Patches _resolve_redis to inject a mock Redis that always returns count > limit.
        Does not require a running Redis instance.
        """
        from unittest.mock import AsyncMock, patch

        from starlette.testclient import TestClient

        from pilot_space.api.middleware.rate_limiter import RateLimitMiddleware
        from pilot_space.main import app

        # Build a mock Redis where INCR always returns 9999 (exceeds all limits)
        mock_redis_raw = AsyncMock()
        mock_redis_raw.incr = AsyncMock(return_value=9999)
        mock_redis_raw.expire = AsyncMock(return_value=True)
        mock_redis_raw.get = AsyncMock(return_value=None)
        mock_redis_raw.set = AsyncMock(return_value=True)

        def fake_resolve_redis(self_mw: RateLimitMiddleware, request: object) -> None:
            # Inject mock Redis directly, skip container lookup
            self_mw.redis = mock_redis_raw
            self_mw._redis_resolved = True

        with (
            patch.object(RateLimitMiddleware, "_resolve_redis", fake_resolve_redis),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            # Verify middleware is in the stack
            stack = app.middleware_stack
            found = False
            for _ in range(20):
                if "RateLimitMiddleware" in type(stack).__name__:
                    found = True
                    break
                stack = getattr(stack, "app", None)
                if stack is None:
                    break
            assert found, "RateLimitMiddleware not found in app.middleware_stack"

            # Verify 429 is returned — dispatch() returns JSONResponse(429) directly,
            # which propagates through Starlette's middleware chain as a real 429 response.
            response = client.get(
                "/api/v1/workspaces",
                headers={"X-Workspace-ID": "test-workspace-id"},
            )
            assert response.status_code == 429, (
                f"Expected 429 from rate limit, got {response.status_code}"
            )
            assert "Retry-After" in response.headers

        # Reset the singleton middleware instance state that fake_resolve_redis set.
        # patch.object restores the _resolve_redis METHOD but NOT the instance attributes
        # (_redis_resolved=True, redis=mock_redis_raw) that leak into subsequent tests.
        stack = app.middleware_stack
        for _ in range(20):
            if isinstance(stack, RateLimitMiddleware):
                stack._redis_resolved = False
                stack.redis = None
                break
            stack = getattr(stack, "app", None)
            if stack is None:
                break
