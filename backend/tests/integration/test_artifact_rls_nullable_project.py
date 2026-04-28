"""Phase 87.1 Plan 01 — RLS isolation for nullable project_id artifacts.

Asserts that the workspace_isolation policy on ``artifacts`` (migration 092)
continues to enforce cross-workspace isolation when ``project_id IS NULL``.

Default test engine is SQLite, where RLS policies silently no-op and produce
false greens. The ``pg_session`` fixture (see ``conftest.py``) skips cleanly
when ``TEST_DATABASE_URL`` is unset, so this test never runs under SQLite.

Threat scope: T-87.1-01-01 (Information Disclosure across workspaces).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.rls import set_rls_context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_isolation_holds_for_null_project_id(
    pg_session: AsyncSession,
) -> None:
    """A workspace member sees BOTH project-scoped and AI-generated artifacts.

    AI-generated artifacts have ``project_id IS NULL``. The
    ``artifacts_workspace_isolation`` policy filters on ``workspace_id``
    only, so NULL project_id rows must remain visible to workspace members.
    """
    workspace_a = uuid4()
    user_a = uuid4()
    project_a = uuid4()
    project_artifact = uuid4()
    ai_artifact = uuid4()

    await pg_session.execute(
        text(
            """
            INSERT INTO workspaces (id, name, slug, created_at, updated_at)
            VALUES (:id, :name, :slug, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        {"id": str(workspace_a), "name": "ws-a", "slug": "ws-a-87-1"},
    )
    await pg_session.execute(
        text(
            """
            INSERT INTO workspace_members
                (workspace_id, user_id, role, is_deleted, created_at, updated_at)
            VALUES (:wsid, :uid, 'OWNER', false, now(), now())
            ON CONFLICT DO NOTHING
            """,
        ),
        {"wsid": str(workspace_a), "uid": str(user_a)},
    )
    await pg_session.execute(
        text(
            """
            INSERT INTO users (id, email, created_at, updated_at)
            VALUES (:id, :email, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        {"id": str(user_a), "email": f"u-{user_a}@example.com"},
    )
    await pg_session.execute(
        text(
            """
            INSERT INTO projects (id, workspace_id, name, slug, created_at, updated_at)
            VALUES (:id, :wsid, :name, :slug, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        {
            "id": str(project_a),
            "wsid": str(workspace_a),
            "name": "p-a",
            "slug": f"p-a-{project_a}",
        },
    )

    # Project-scoped artifact
    await pg_session.execute(
        text(
            """
            INSERT INTO artifacts
                (id, workspace_id, project_id, user_id, filename, mime_type,
                 size_bytes, storage_key, status, is_deleted, created_at, updated_at)
            VALUES (:id, :wsid, :pid, :uid, :fn, :mt, :sz, :sk, 'ready',
                    false, now(), now())
            """,
        ),
        {
            "id": str(project_artifact),
            "wsid": str(workspace_a),
            "pid": str(project_a),
            "uid": str(user_a),
            "fn": "scope.md",
            "mt": "text/markdown",
            "sz": 12,
            "sk": f"{workspace_a}/{project_a}/{project_artifact}/scope.md",
        },
    )
    # AI-generated artifact (project_id NULL)
    await pg_session.execute(
        text(
            """
            INSERT INTO artifacts
                (id, workspace_id, project_id, user_id, filename, mime_type,
                 size_bytes, storage_key, status, is_deleted, created_at, updated_at)
            VALUES (:id, :wsid, NULL, :uid, :fn, :mt, :sz, :sk, 'ready',
                    false, now(), now())
            """,
        ),
        {
            "id": str(ai_artifact),
            "wsid": str(workspace_a),
            "uid": str(user_a),
            "fn": "ai.md",
            "mt": "text/markdown",
            "sz": 16,
            "sk": f"{workspace_a}/ai-generated/{ai_artifact}/ai.md",
        },
    )

    await set_rls_context(pg_session, user_id=user_a, workspace_id=workspace_a)
    visible_ids = {
        str(row.id)
        for row in (
            await pg_session.execute(
                text("SELECT id FROM artifacts WHERE workspace_id = :wsid"),
                {"wsid": str(workspace_a)},
            )
        ).all()
    }

    assert str(project_artifact) in visible_ids, (
        "workspace member cannot see project-scoped artifact"
    )
    assert str(ai_artifact) in visible_ids, (
        "workspace member cannot see AI-generated artifact (project_id IS NULL)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cross_workspace_isolation_holds_for_null_project_id(
    pg_session: AsyncSession,
) -> None:
    """A user in workspace B MUST NOT see workspace A's NULL-project artifact.

    Regression for T-87.1-01-01 — making project_id nullable must not weaken
    cross-workspace isolation.
    """
    workspace_a = uuid4()
    workspace_b = uuid4()
    user_a = uuid4()
    user_b = uuid4()
    ai_artifact_a = uuid4()

    for ws, user in ((workspace_a, user_a), (workspace_b, user_b)):
        await pg_session.execute(
            text(
                """
                INSERT INTO workspaces (id, name, slug, created_at, updated_at)
                VALUES (:id, :name, :slug, now(), now())
                ON CONFLICT (id) DO NOTHING
                """,
            ),
            {"id": str(ws), "name": f"ws-{ws}", "slug": f"ws-iso-{ws}"},
        )
        await pg_session.execute(
            text(
                """
                INSERT INTO workspace_members
                    (workspace_id, user_id, role, is_deleted, created_at, updated_at)
                VALUES (:wsid, :uid, 'OWNER', false, now(), now())
                ON CONFLICT DO NOTHING
                """,
            ),
            {"wsid": str(ws), "uid": str(user)},
        )
        await pg_session.execute(
            text(
                """
                INSERT INTO users (id, email, created_at, updated_at)
                VALUES (:id, :email, now(), now())
                ON CONFLICT (id) DO NOTHING
                """,
            ),
            {"id": str(user), "email": f"iso-{user}@example.com"},
        )

    # Seed an AI-generated (NULL project_id) artifact in workspace A
    await pg_session.execute(
        text(
            """
            INSERT INTO artifacts
                (id, workspace_id, project_id, user_id, filename, mime_type,
                 size_bytes, storage_key, status, is_deleted, created_at, updated_at)
            VALUES (:id, :wsid, NULL, :uid, :fn, :mt, :sz, :sk, 'ready',
                    false, now(), now())
            """,
        ),
        {
            "id": str(ai_artifact_a),
            "wsid": str(workspace_a),
            "uid": str(user_a),
            "fn": "secret.md",
            "mt": "text/markdown",
            "sz": 8,
            "sk": f"{workspace_a}/ai-generated/{ai_artifact_a}/secret.md",
        },
    )

    # Activate RLS as user B; must NOT see workspace A's NULL-project artifact
    await set_rls_context(pg_session, user_id=user_b, workspace_id=workspace_b)
    visible_ids = {
        str(row.id)
        for row in (
            await pg_session.execute(
                text("SELECT id FROM artifacts"),
            )
        ).all()
    }

    assert str(ai_artifact_a) not in visible_ids, (
        "RLS leak: user B sees workspace A's NULL-project artifact — "
        "cross-workspace isolation broken for AI-generated artifacts"
    )
