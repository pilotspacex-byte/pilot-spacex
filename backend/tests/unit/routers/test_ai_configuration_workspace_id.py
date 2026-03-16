"""Tests for AI Configuration POST endpoint workspace_id as query parameter.

Verifies that the create_ai_configuration endpoint function signature
expects workspace_id as a non-body query parameter (not in request body).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_ai_configuration_workspace_id_is_query_param() -> None:
    """workspace_id must be a standalone function param (query), not in request body.

    FastAPI resolves bare UUID params as query params.
    AIConfigurationCreate schema must NOT contain workspace_id field.
    """
    from pilot_space.api.v1.routers.ai_configuration import create_ai_configuration
    from pilot_space.api.v1.schemas.ai_configuration import AIConfigurationCreate

    # The endpoint must have workspace_id as a direct parameter (query param in FastAPI)
    sig = inspect.signature(create_ai_configuration)
    assert "workspace_id" in sig.parameters, (
        "create_ai_configuration must accept workspace_id as a parameter"
    )

    # workspace_id must NOT be a field in the request body schema
    schema_fields = AIConfigurationCreate.model_fields
    assert "workspace_id" not in schema_fields, (
        "AIConfigurationCreate must NOT contain workspace_id — "
        "it's a query param, not in the body. "
        "Frontend must send: POST /ai/configurations?workspace_id=<id>"
    )


async def test_ai_configuration_create_schema_has_required_fields() -> None:
    """AIConfigurationCreate schema has provider and api_key but not workspace_id."""
    from pilot_space.api.v1.schemas.ai_configuration import AIConfigurationCreate, LLMProvider

    # Can construct without workspace_id — it's not in the body
    payload = AIConfigurationCreate(
        provider=LLMProvider.CUSTOM,
        api_key="sk-test-key",  # pragma: allowlist secret
        base_url="https://example.com/v1",
        display_name="Test Provider",
    )
    assert payload.provider == LLMProvider.CUSTOM
    assert "workspace_id" not in payload.model_fields
