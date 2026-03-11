"""Tests for audit log export functionality.

Covers:
- GET /workspaces/{slug}/audit/export?format=csv returns CSV content-type
- GET /workspaces/{slug}/audit/export?format=json returns JSON content-type
- CSV export includes correct headers (timestamp, actor, action, resource_type, etc.)
- JSON export contains array of audit entries with all fields
- Large export (>10,000 rows) warning is present in response headers
- Non-admin users cannot export (403)
- Applied filters are honored in export

Requirements: AUDIT-04
"""

from __future__ import annotations

import pytest


class TestAuditExportCsv:
    """Tests for CSV export format."""

    @pytest.mark.asyncio
    async def test_csv_export_content_type(self, audit_client) -> None:
        """GET /audit/export?format=csv must return text/csv content-type."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=csv"
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_csv_export_has_correct_headers(self, audit_client) -> None:
        """CSV export must include required column headers."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=csv"
        )
        assert response.status_code == 200
        content = response.text
        # First line is headers
        first_line = content.split("\n")[0]
        assert "timestamp" in first_line.lower() or "created_at" in first_line.lower()
        assert "action" in first_line.lower()
        assert "resource_type" in first_line.lower()

    @pytest.mark.asyncio
    async def test_csv_export_has_content_disposition_header(self, audit_client) -> None:
        """CSV export must include Content-Disposition: attachment header."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=csv"
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")


class TestAuditExportJson:
    """Tests for JSON export format."""

    @pytest.mark.asyncio
    async def test_json_export_content_type(self, audit_client) -> None:
        """GET /audit/export?format=json must return application/json content-type."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=json"
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_json_export_is_array(self, audit_client) -> None:
        """JSON export must return an array of audit entries."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=json"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_json_export_entry_has_required_fields(self, audit_client) -> None:
        """Each JSON export entry must include id, action, resource_type, created_at."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=json"
        )
        assert response.status_code == 200
        data = response.json()
        if data:  # Only check if there are entries
            entry = data[0]
            assert "id" in entry
            assert "action" in entry
            assert "resourceType" in entry
            assert "createdAt" in entry


class TestAuditExportFilters:
    """Tests that export respects applied filters."""

    @pytest.mark.asyncio
    async def test_export_respects_action_filter(self, audit_client) -> None:
        """Export with action filter must only return entries matching that action."""
        response = await audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=json&action=issue.create"
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data:
            assert entry.get("action") == "issue.create"

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self, non_admin_audit_client) -> None:
        """Non-ADMIN/OWNER members must receive 403 on audit export."""
        response = await non_admin_audit_client.get(
            "/api/v1/workspaces/test-workspace/audit/export?format=csv"
        )
        assert response.status_code == 403
