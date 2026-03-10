"""TENANT-01: Cross-workspace data isolation integration tests.

REQUIRES PostgreSQL — SQLite does not enforce RLS.
Run with: TEST_DATABASE_URL=postgresql+asyncpg://... pytest tests/security/test_isolation.py -x

These tests provision two isolated workspaces and verify that a JWT-authenticated
user from workspace A cannot access workspace B data through any endpoint.

Fixture dependency: populated_two_workspace_db (defined in conftest.py as populated_db
already provides two workspaces — workspace_a and workspace_b with cross-membership).
Tests marked xfail until RLS migration 066 is verified applied and test infrastructure
for the two-workspace pattern is finalized in Phase 3 plan 03-02.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import State
from tests.security.conftest import SecurityTestContext, set_test_rls_context

_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite")

pytestmark = pytest.mark.skipif(
    "sqlite" in _DB_URL,
    reason="RLS isolation tests require PostgreSQL. Set TEST_DATABASE_URL.",
)


async def test_cross_workspace_issue_access(
    populated_db: SecurityTestContext,
    db_session: AsyncSession,
) -> None:
    """User A cannot read workspace B issues via RLS.

    Setup: issue created in workspace B by outsider (workspace B owner).
    Action: set RLS context as user A (workspace A member), query all issues.
    Assert: result is empty — RLS blocks cross-workspace access.
    """
    ctx = populated_db

    # Create a project in workspace B (owned by outsider)
    project = Project(
        id=uuid.uuid4(),
        workspace_id=ctx.workspace_b.id,
        name="B Project",
        identifier="BPROJ",
    )
    db_session.add(project)
    await db_session.flush()

    # Create a state in workspace B for the project
    state = State(
        id=uuid.uuid4(),
        workspace_id=ctx.workspace_b.id,
        name="Backlog",
        project_id=project.id,
    )
    db_session.add(state)
    await db_session.flush()

    # Create an issue in workspace B
    issue = Issue(
        id=uuid.uuid4(),
        sequence_id=1,
        workspace_id=ctx.workspace_b.id,
        state_id=state.id,
        project_id=project.id,
        reporter_id=ctx.outsider.id,
        name="WS-B Issue",
    )
    db_session.add(issue)
    await db_session.flush()

    # Set RLS context to workspace A owner — they have no access to workspace B
    await set_test_rls_context(db_session, ctx.owner.id, ctx.workspace_a.id)

    # Query workspace B issues — RLS must filter them all out
    result = await db_session.execute(select(Issue).where(Issue.workspace_id == ctx.workspace_b.id))
    issues = result.scalars().all()

    assert len(issues) == 0, (
        "RLS must block workspace B issues from a user who is only a member of workspace A. "
        f"Found {len(issues)} issue(s) — isolation policy is not enforced."
    )


async def test_cross_workspace_note_access(
    populated_db: SecurityTestContext,
    db_session: AsyncSession,
) -> None:
    """User A cannot read workspace B notes via RLS.

    Setup: note created in workspace B by outsider (workspace B owner).
    Action: set RLS context as user A (workspace A member), query all notes.
    Assert: result is empty — RLS blocks cross-workspace access.
    """
    ctx = populated_db

    # Create a note in workspace B (owned by outsider)
    note = Note(
        id=uuid.uuid4(),
        workspace_id=ctx.workspace_b.id,
        owner_id=ctx.outsider.id,
        title="WS-B Note",
        content={},
    )
    db_session.add(note)
    await db_session.flush()

    # Set RLS context to workspace A owner — they have no access to workspace B
    await set_test_rls_context(db_session, ctx.owner.id, ctx.workspace_a.id)

    # Query workspace B notes — RLS must filter them all out
    result = await db_session.execute(select(Note).where(Note.workspace_id == ctx.workspace_b.id))
    notes = result.scalars().all()

    assert len(notes) == 0, (
        "RLS must block workspace B notes from a user who is only a member of workspace A. "
        f"Found {len(notes)} note(s) — isolation policy is not enforced."
    )


async def test_cross_workspace_audit_log_access(
    populated_db: SecurityTestContext,
    db_session: AsyncSession,
) -> None:
    """User A cannot read workspace B audit log entries via RLS.

    Setup: audit_log entry created in workspace B.
    Action: set RLS context as user A (OWNER of workspace A), query audit_log.
    Assert: result is empty — workspace B entries not visible to workspace A OWNER.
    """
    ctx = populated_db

    # Create an audit log entry in workspace B
    log_entry = AuditLog(
        id=uuid.uuid4(),
        workspace_id=ctx.workspace_b.id,
        actor_id=ctx.outsider.id,
        actor_type=ActorType.USER,
        action="issue.create",
        resource_type="issue",
    )
    db_session.add(log_entry)
    await db_session.flush()

    # Set RLS context to workspace A owner — they have no access to workspace B
    await set_test_rls_context(db_session, ctx.owner.id, ctx.workspace_a.id)

    # Query workspace B audit log — RLS must filter all entries out
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.workspace_id == ctx.workspace_b.id)
    )
    entries = result.scalars().all()

    assert len(entries) == 0, (
        "RLS must block workspace B audit log entries from a workspace A OWNER. "
        f"Found {len(entries)} entry/entries — isolation policy is not enforced."
    )


@pytest.mark.xfail(strict=False, reason="TENANT-01: MCP tool RLS session sharing not yet verified")
async def test_mcp_tool_rls_context_isolation(populated_db: object, db_session: object) -> None:
    """MCP tool handlers use injected session with RLS context, not fresh sessions.

    MCP tools that open a fresh DB session bypass RLS context set by the router.
    This test verifies tool_context.db_session is passed through, not a new session.
    Reference: backend/src/pilot_space/ai/mcp/ tool handlers.
    """
    raise NotImplementedError("Verify tool_context.db_session usage in ai/mcp/ tool handlers")


@pytest.mark.xfail(strict=False, reason="TENANT-01: API router RLS coverage not yet audited")
async def test_all_workspace_routers_call_set_rls_context() -> None:
    """All routers accessing workspace data call set_rls_context() before SELECT.

    Static audit: grep router files for workspace-scoped queries that do not
    call set_rls_context() first. Any router returning workspace data without
    setting RLS context is a potential data leak.

    Implementation approach: parse AST of router files, detect query patterns
    (db_session.execute, session.get, repository methods) and verify
    set_rls_context() precedes them in the same route handler.
    """
    raise NotImplementedError(
        "Implement static audit: grep routers for workspace queries missing set_rls_context"
    )
