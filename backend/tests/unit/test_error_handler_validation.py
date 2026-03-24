"""Unit tests for the error handler middleware — validation error serialization.

Specifically verifies that Pydantic v2 validation errors containing non-serializable
``ctx["error"]`` values (raw ValueError objects) are sanitized to strings before
being included in the 422 response body, preventing 500 errors due to JSON
serialization failure.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, field_validator

from pilot_space.api.middleware.error_handler import register_exception_handlers


class _Body(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_bad(cls, v: str) -> str:
        if v == "bad":
            raise ValueError("This is a raw ValueError in ctx")
        return v


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with error handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/test-validation")
    async def _endpoint(body: _Body) -> dict:
        return {"value": body.value}

    return app


@pytest.mark.asyncio
async def test_pydantic_value_error_in_ctx_returns_422_not_500() -> None:
    """Pydantic validator raising ValueError must produce 422, not 500.

    Pydantic v2 stores the raw exception object in ``ctx["error"]``.
    If not sanitized to a string, JSONResponse raises a TypeError during
    serialization → unhandled → 500.

    This test verifies the ``_sanitize_pydantic_errors`` fix in error_handler.py.
    """
    app = _make_test_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/test-validation", json={"value": "bad"})

    assert response.status_code == 422, (
        f"Expected 422 for validation error, got {response.status_code}: {response.text}"
    )
    assert response.headers.get("content-type", "").startswith("application/problem+json"), (
        f"Expected application/problem+json, got {response.headers.get('content-type')}"
    )


@pytest.mark.asyncio
async def test_pydantic_value_error_in_ctx_body_is_json_serializable() -> None:
    """The 422 body must be fully JSON-parseable (no raw exception objects)."""
    app = _make_test_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/test-validation", json={"value": "bad"})

    # If this call raises a JSON decode error, the body contains non-serializable data
    body = response.json()
    assert body["status"] == 422
    assert "errors" in body
    # ctx.error should be a string, not an exception object representation that breaks JSON
    for error in body["errors"]:
        ctx = error.get("ctx", {})
        if "error" in ctx:
            assert isinstance(ctx["error"], str), (
                f"ctx.error should be a string after sanitization, got {type(ctx['error'])}"
            )


@pytest.mark.asyncio
async def test_valid_input_returns_200() -> None:
    """Sanity check: valid input still returns 200."""
    app = _make_test_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/test-validation", json={"value": "good"})

    assert response.status_code == 200
