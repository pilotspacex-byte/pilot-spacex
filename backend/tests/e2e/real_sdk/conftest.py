"""Real SDK test fixtures for integration testing with actual Claude API.

This module provides fixtures for tests that use the real Anthropic API instead of mocks.
Tests marked with @pytest.mark.real_sdk require a valid ANTHROPIC_API_KEY environment variable.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m real_sdk

Note:
    These tests are not run in CI by default. Use them for manual validation or nightly runs.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure(config: pytest.Config) -> None:
    """Register real_sdk marker."""
    config.addinivalue_line(
        "markers",
        "real_sdk: marks tests as requiring real Anthropic API (deselect with '-m \"not real_sdk\"')",
    )


@pytest.fixture
def real_api_key() -> str:
    """Provide real Anthropic API key for SDK tests.

    Raises:
        pytest.skip: If ANTHROPIC_API_KEY is not configured or is a test key.

    Returns:
        str: Valid Anthropic API key
    """
    key = os.environ.get("ANTHROPIC_API_KEY")

    if not key:
        pytest.skip("Real ANTHROPIC_API_KEY not configured")

    if key.startswith("sk-ant-test"):
        pytest.skip("Test API key detected, real API key required")

    return key


@pytest.fixture
async def real_sdk_client(real_api_key: str) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for real SDK testing.

    This fixture uses the real application without mocking Redis or other services.
    It sets the ANTHROPIC_API_KEY environment variable for the duration of the test.

    Args:
        real_api_key: Valid Anthropic API key from real_api_key fixture

    Yields:
        AsyncClient: HTTP client configured for real SDK testing
    """
    from pilot_space.main import app

    # Store original API key
    original_api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Set real API key
    os.environ["ANTHROPIC_API_KEY"] = real_api_key

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Restore original API key
        if original_api_key:
            os.environ["ANTHROPIC_API_KEY"] = original_api_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
