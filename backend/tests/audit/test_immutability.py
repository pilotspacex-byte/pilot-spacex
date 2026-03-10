"""Tests for audit log immutability enforcement.

Covers:
- Direct UPDATE on audit_log raises database exception (PostgreSQL trigger)
- Direct DELETE on audit_log raises database exception (PostgreSQL trigger)
- No DELETE endpoint exposed in audit router
- No UPDATE endpoint exposed in audit router
- fn_purge_audit_log_expired can delete via session variable bypass

Note: PostgreSQL-specific tests require TEST_DATABASE_URL to be set.
These are marked @pytest.mark.integration and will skip on SQLite.

Requirements: AUDIT-06
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


class TestAuditLogImmutabilityTrigger:
    """Tests for the fn_audit_log_immutable PostgreSQL trigger.

    These tests require a real PostgreSQL instance (TEST_DATABASE_URL).
    They are skipped on SQLite where the trigger is not available.
    """

    @pytest.mark.xfail(
        strict=False, reason="PostgreSQL immutability trigger - requires TEST_DATABASE_URL"
    )
    @pytest.mark.asyncio
    async def test_direct_update_raises_exception(self, db_session_committed) -> None:
        """Direct UPDATE on audit_log must raise an exception from the immutability trigger."""
        from sqlalchemy import text

        from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog

        workspace_id = uuid.uuid4()
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
            actor_type=ActorType.USER,
            action="issue.create",
            resource_type="issue",
            resource_id=uuid.uuid4(),
        )
        db_session_committed.add(row)
        await db_session_committed.flush()
        row_id = row.id

        # Direct UPDATE must raise exception
        async def _do_update() -> None:
            await db_session_committed.execute(
                text("UPDATE audit_log SET action = 'tampered' WHERE id = :id"),
                {"id": str(row_id)},
            )
            await db_session_committed.commit()

        with pytest.raises(Exception, match="immutable"):
            await _do_update()

    @pytest.mark.xfail(
        strict=False, reason="PostgreSQL immutability trigger - requires TEST_DATABASE_URL"
    )
    @pytest.mark.asyncio
    async def test_direct_delete_raises_exception(self, db_session_committed) -> None:
        """Direct DELETE on audit_log must raise an exception from the immutability trigger."""
        from sqlalchemy import text

        from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog

        workspace_id = uuid.uuid4()
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
            actor_type=ActorType.USER,
            action="note.delete",
            resource_type="note",
            resource_id=uuid.uuid4(),
        )
        db_session_committed.add(row)
        await db_session_committed.flush()
        row_id = row.id

        # Direct DELETE must raise exception
        async def _do_delete() -> None:
            await db_session_committed.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": str(row_id)},
            )
            await db_session_committed.commit()

        with pytest.raises(Exception, match="immutable"):
            await _do_delete()

    @pytest.mark.xfail(
        strict=False, reason="PostgreSQL immutability trigger - requires TEST_DATABASE_URL"
    )
    @pytest.mark.asyncio
    async def test_purge_bypass_allows_delete(self, db_session_committed) -> None:
        """fn_purge_audit_log_expired must be able to delete via app.audit_purge bypass."""
        from sqlalchemy import text

        from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog

        workspace_id = uuid.uuid4()
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=None,
            actor_type=ActorType.SYSTEM,
            action="test.purge_candidate",
            resource_type="test",
            resource_id=uuid.uuid4(),
        )
        db_session_committed.add(row)
        await db_session_committed.flush()
        row_id = row.id

        # Set the bypass session variable and delete — must succeed
        await db_session_committed.execute(
            text("SELECT set_config('app.audit_purge', 'true', true)")
        )
        await db_session_committed.execute(
            text("DELETE FROM audit_log WHERE id = :id"),
            {"id": str(row_id)},
        )
        await db_session_committed.commit()

        # Verify row is gone
        result = await db_session_committed.execute(
            text("SELECT id FROM audit_log WHERE id = :id"),
            {"id": str(row_id)},
        )
        assert result.fetchone() is None


class TestAuditRouterNoMutationEndpoints:
    """Tests that audit router exposes no UPDATE or DELETE endpoints."""

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    def test_no_delete_endpoint_in_audit_router(self) -> None:
        """Audit router must not expose any DELETE endpoints for audit entries."""
        from pilot_space.api.v1.routers.audit import router

        delete_routes = [
            route
            for route in router.routes
            if hasattr(route, "methods") and "DELETE" in (route.methods or set())
        ]
        # No DELETE routes allowed on audit entries
        delete_paths = [r.path for r in delete_routes]
        # Allow DELETE on settings (e.g. reset retention) but NOT on audit entries
        audit_entry_deletes = [p for p in delete_paths if "audit" in p and "settings" not in p]
        assert not audit_entry_deletes, f"Found unauthorized DELETE routes: {audit_entry_deletes}"

    @pytest.mark.xfail(strict=False, reason="audit router implementation pending")
    def test_no_put_patch_on_audit_entries(self) -> None:
        """Audit router must not expose PUT/PATCH endpoints on audit entries."""
        from pilot_space.api.v1.routers.audit import router

        mutating_routes = [
            route
            for route in router.routes
            if hasattr(route, "methods")
            and bool((route.methods or set()).intersection({"PUT", "PATCH"}))
            and "audit" in (route.path or "")
            and "settings" not in (route.path or "")
            and "retention" not in (route.path or "")
        ]
        assert not mutating_routes, (
            f"Found unauthorized mutation routes on audit entries: "
            f"{[(r.path, r.methods) for r in mutating_routes]}"
        )
