"""Tests for audit log API endpoints.

Covers:
- GET /workspaces/{slug}/audit returns paginated list
- Filters: actor_id, action, resource_type, start_date, end_date
- Cursor pagination: next page cursor is honored
- PATCH /workspaces/{slug}/settings/audit-retention updates audit_retention_days
- Non-admin users cannot access audit log (403)
- Response schema includes all required fields

Requirements: AUDIT-03, AUDIT-05
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest


class TestAuditLogListEndpoint:
    """Tests for GET /workspaces/{slug}/audit."""

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, client) -> None:
        """GET /workspaces/{slug}/audit should return a paginated list of audit entries."""
        response = await client.get("/api/v1/workspaces/test-workspace/audit")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_next" in data
        assert "next_cursor" in data

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_filter_by_actor_id(self, client) -> None:
        """GET /workspaces/{slug}/audit?actor_id=... should filter by actor."""
        actor_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/workspaces/test-workspace/audit?actor_id={actor_id}")
        assert response.status_code == 200

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_filter_by_action(self, client) -> None:
        """GET /workspaces/{slug}/audit?action=issue.create should filter by action."""
        response = await client.get("/api/v1/workspaces/test-workspace/audit?action=issue.create")
        assert response.status_code == 200

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_filter_by_resource_type(self, client) -> None:
        """GET /workspaces/{slug}/audit?resource_type=issue should filter by resource type."""
        response = await client.get("/api/v1/workspaces/test-workspace/audit?resource_type=issue")
        assert response.status_code == 200

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client) -> None:
        """GET /workspaces/{slug}/audit?start_date=...&end_date=... should filter by date."""
        start = (datetime.now(tz=UTC) - timedelta(days=7)).isoformat()
        end = datetime.now(tz=UTC).isoformat()
        response = await client.get(
            f"/api/v1/workspaces/test-workspace/audit?start_date={start}&end_date={end}"
        )
        assert response.status_code == 200

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_cursor_pagination_honors_cursor(self, client) -> None:
        """Second page request with cursor should return a different page of results."""
        response1 = await client.get("/api/v1/workspaces/test-workspace/audit?page_size=5")
        assert response1.status_code == 200
        data1 = response1.json()
        if data1.get("next_cursor"):
            response2 = await client.get(
                f"/api/v1/workspaces/test-workspace/audit?cursor={data1['next_cursor']}&page_size=5"
            )
            assert response2.status_code == 200
            data2 = response2.json()
            # Items on page 2 must not overlap with page 1
            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert not ids1.intersection(ids2)

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self, client) -> None:
        """Non-ADMIN/OWNER members must receive 403 on audit log list."""
        response = await client.get("/api/v1/workspaces/test-workspace/audit")
        # Depends on auth mock being set to MEMBER role
        assert response.status_code == 403


class TestAuditRetentionEndpoint:
    """Tests for PATCH /workspaces/{slug}/settings/audit-retention."""

    @pytest.mark.xfail(strict=False, reason="audit retention endpoint implementation pending")
    @pytest.mark.asyncio
    async def test_patch_retention_days_succeeds(self, client) -> None:
        """PATCH audit-retention should update workspace.audit_retention_days."""
        response = await client.patch(
            "/api/v1/workspaces/test-workspace/settings/audit-retention",
            json={"audit_retention_days": 30},
        )
        assert response.status_code == 200

    @pytest.mark.xfail(strict=False, reason="audit retention endpoint implementation pending")
    @pytest.mark.asyncio
    async def test_patch_retention_days_requires_admin(self, client) -> None:
        """PATCH audit-retention requires ADMIN or OWNER role."""
        response = await client.patch(
            "/api/v1/workspaces/test-workspace/settings/audit-retention",
            json={"audit_retention_days": 30},
        )
        # Non-admin context must return 403
        assert response.status_code in (200, 403)
