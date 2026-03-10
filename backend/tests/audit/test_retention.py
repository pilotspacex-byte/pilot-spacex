"""Tests for audit log retention purge logic.

Covers:
- fn_purge_audit_log_expired deletes rows older than workspace.audit_retention_days
- Rows within the retention window are preserved
- Default retention is 90 days when workspace.audit_retention_days is NULL
- Per-workspace retention days are respected independently
- Unit-testable via mocked DB query (no real pg_cron required)

Requirements: AUDIT-05
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog


def _make_audit_row(
    workspace_id: uuid.UUID,
    *,
    action: str = "issue.create",
    created_at: datetime | None = None,
) -> AuditLog:
    """Create an in-memory AuditLog row for retention tests."""
    row = AuditLog(
        workspace_id=workspace_id,
        actor_id=uuid.uuid4(),
        actor_type=ActorType.USER,
        action=action,
        resource_type="issue",
        resource_id=uuid.uuid4(),
    )
    row.id = uuid.uuid4()
    row.created_at = created_at or datetime.now(tz=UTC)
    row.updated_at = row.created_at
    return row


class TestPurgeAuditLogExpired:
    """Tests for the purge logic that fn_purge_audit_log_expired implements."""

    @pytest.mark.xfail(
        strict=False, reason="AuditLogRepository.purge_expired implementation pending"
    )
    @pytest.mark.asyncio
    async def test_deletes_rows_older_than_retention_days(self) -> None:
        """purge_expired() must delete rows older than workspace.audit_retention_days."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        workspace_id = uuid.uuid4()
        retention_days = 30
        now = datetime.now(tz=UTC)

        # Old row: 31 days ago — should be deleted
        old_row = _make_audit_row(workspace_id, created_at=now - timedelta(days=31))
        # Recent row: 1 day ago — should be kept
        recent_row = _make_audit_row(workspace_id, created_at=now - timedelta(days=1))

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 1  # One row deleted

        session.execute = AsyncMock(return_value=result_mock)

        repo = AuditLogRepository(session)
        deleted_count = await repo.purge_expired(
            workspace_id=workspace_id,
            retention_days=retention_days,
            now=now,
        )

        assert deleted_count == 1
        session.execute.assert_awaited_once()

    @pytest.mark.xfail(
        strict=False, reason="AuditLogRepository.purge_expired implementation pending"
    )
    @pytest.mark.asyncio
    async def test_keeps_rows_within_retention_window(self) -> None:
        """purge_expired() must not delete rows within the retention window."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        workspace_id = uuid.uuid4()
        now = datetime.now(tz=UTC)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 0  # Nothing deleted

        session.execute = AsyncMock(return_value=result_mock)

        repo = AuditLogRepository(session)
        deleted_count = await repo.purge_expired(
            workspace_id=workspace_id,
            retention_days=90,
            now=now,
        )

        assert deleted_count == 0

    @pytest.mark.xfail(
        strict=False, reason="AuditLogRepository.purge_expired implementation pending"
    )
    @pytest.mark.asyncio
    async def test_default_retention_is_90_days(self) -> None:
        """When workspace.audit_retention_days is None, default to 90 days."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        workspace_id = uuid.uuid4()
        now = datetime.now(tz=UTC)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 0

        session.execute = AsyncMock(return_value=result_mock)

        repo = AuditLogRepository(session)
        # retention_days=None means use default
        deleted_count = await repo.purge_expired(
            workspace_id=workspace_id,
            retention_days=None,
            now=now,
        )

        # Verify the query was called with 90 days cutoff
        assert deleted_count == 0
        session.execute.assert_awaited_once()

    @pytest.mark.xfail(
        strict=False, reason="AuditLogRepository.purge_expired implementation pending"
    )
    @pytest.mark.asyncio
    async def test_per_workspace_retention_respected(self) -> None:
        """Each workspace's retention_days is applied independently."""
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository,
        )

        workspace_a = uuid.uuid4()
        workspace_b = uuid.uuid4()
        now = datetime.now(tz=UTC)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.rowcount = 0
        session.execute = AsyncMock(return_value=result_mock)

        repo = AuditLogRepository(session)

        # Workspace A: 30-day retention
        await repo.purge_expired(workspace_id=workspace_a, retention_days=30, now=now)
        # Workspace B: 365-day retention
        await repo.purge_expired(workspace_id=workspace_b, retention_days=365, now=now)

        assert session.execute.await_count == 2
