"""Unit tests for request context middleware."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from pilot_space.api.middleware.request_context import (
    CorrelationId,
    RequestContextMiddleware,
    WorkspaceId,
    get_correlation_id,
    get_workspace_id,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the middleware."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/test-workspace")
    async def test_workspace_endpoint(workspace_id: WorkspaceId) -> dict[str, str]:
        return {"workspace_id": str(workspace_id)}

    @app.get("/test-correlation")
    async def test_correlation_endpoint(correlation_id: CorrelationId) -> dict[str, str]:
        return {"correlation_id": correlation_id}

    @app.get("/test-both")
    async def test_both_endpoint(
        workspace_id: WorkspaceId,
        correlation_id: CorrelationId,
    ) -> dict[str, str]:
        return {
            "workspace_id": str(workspace_id),
            "correlation_id": correlation_id,
        }

    @app.get("/test-manual")
    async def test_manual_endpoint(request: Request) -> dict[str, str]:
        workspace_id = get_workspace_id(request)
        correlation_id = get_correlation_id(request)
        return {
            "workspace_id": str(workspace_id),
            "correlation_id": correlation_id,
        }

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_workspace_id_uuid(client: TestClient) -> None:
    """Test workspace ID extraction with valid UUID."""
    test_workspace_id = uuid.uuid4()
    response = client.get(
        "/test-workspace",
        headers={"X-Workspace-ID": str(test_workspace_id)},
    )
    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(test_workspace_id)


def test_workspace_id_invalid_slug(client: TestClient) -> None:
    """Test workspace ID extraction with non-UUID string."""
    response = client.get(
        "/test-workspace",
        headers={"X-Workspace-ID": "pilot-space-demo"},
    )
    assert response.status_code == 400


def test_workspace_id_missing(client: TestClient) -> None:
    """Test missing workspace ID header."""
    response = client.get("/test-workspace")
    assert response.status_code == 400
    assert "X-Workspace-ID header required" in response.json()["detail"]


def test_workspace_id_invalid_uuid(client: TestClient) -> None:
    """Test invalid UUID format."""
    response = client.get(
        "/test-workspace",
        headers={"X-Workspace-ID": "invalid-uuid"},
    )
    assert response.status_code == 400


def test_workspace_id_case_insensitive_header(client: TestClient) -> None:
    """Test case-insensitive header name."""
    test_workspace_id = uuid.uuid4()
    response = client.get(
        "/test-workspace",
        headers={"x-workspace-id": str(test_workspace_id)},
    )
    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(test_workspace_id)


def test_correlation_id_provided(client: TestClient) -> None:
    """Test correlation ID when provided in header."""
    test_correlation_id = str(uuid.uuid4())
    response = client.get(
        "/test-correlation",
        headers={
            "X-Correlation-ID": test_correlation_id,
            "X-Workspace-ID": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 200
    assert response.json()["correlation_id"] == test_correlation_id
    assert response.headers["X-Correlation-ID"] == test_correlation_id


def test_correlation_id_generated(client: TestClient) -> None:
    """Test correlation ID auto-generation when not provided."""
    response = client.get(
        "/test-correlation",
        headers={"X-Workspace-ID": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    correlation_id = response.json()["correlation_id"]
    assert uuid.UUID(correlation_id)  # Validate it's a valid UUID
    assert response.headers["X-Correlation-ID"] == correlation_id


def test_both_dependencies(client: TestClient) -> None:
    """Test both workspace_id and correlation_id dependencies."""
    test_workspace_id = uuid.uuid4()
    test_correlation_id = str(uuid.uuid4())

    response = client.get(
        "/test-both",
        headers={
            "X-Workspace-ID": str(test_workspace_id),
            "X-Correlation-ID": test_correlation_id,
        },
    )
    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(test_workspace_id)
    assert response.json()["correlation_id"] == test_correlation_id


def test_manual_dependency_extraction(client: TestClient) -> None:
    """Test manual dependency extraction using get_* functions."""
    test_workspace_id = uuid.uuid4()
    test_correlation_id = str(uuid.uuid4())

    response = client.get(
        "/test-manual",
        headers={
            "X-Workspace-ID": str(test_workspace_id),
            "X-Correlation-ID": test_correlation_id,
        },
    )
    assert response.status_code == 200
    assert response.json()["workspace_id"] == str(test_workspace_id)
    assert response.json()["correlation_id"] == test_correlation_id


def test_correlation_id_in_response_header(client: TestClient) -> None:
    """Test that correlation ID is added to response headers."""
    test_workspace_id = uuid.uuid4()
    response = client.get(
        "/test-workspace",
        headers={"X-Workspace-ID": str(test_workspace_id)},
    )
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    # Validate it's a valid UUID
    uuid.UUID(response.headers["X-Correlation-ID"])
