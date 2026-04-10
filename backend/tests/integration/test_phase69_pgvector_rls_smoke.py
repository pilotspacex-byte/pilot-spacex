"""Phase 69 Wave 0 — pgvector + RLS smoke tests.

Guarantees two preconditions for Wave 1+ memory work:

1. pgvector cosine-similarity queries against ``graph_nodes`` return the
   expected row with score >= 0.99 when the query vector is identical to
   the stored embedding.
2. RLS workspace isolation on ``graph_nodes`` works end-to-end when
   ``set_rls_context()`` is called: a user in workspace A sees only A's
   rows even though both A and B rows are physically present.

Both tests are marked ``integration`` and SKIP cleanly
when ``TEST_DATABASE_URL`` is unset (see ``conftest.py``). They MUST NOT
run under the default SQLite engine — RLS no-ops there and pgvector is
unavailable, producing false greens.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.rls import set_rls_context

EMBEDDING_DIM = 768


def _vec_literal(values: list[float]) -> str:
    """Render a pgvector literal e.g. ``[0.1,0.1,...]``."""
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pgvector_recall_returns_results(pg_session: AsyncSession) -> None:
    """Insert a graph_node with a 768-dim embedding, cosine-query, assert recall.

    Uses raw SQL to stay decoupled from the ORM model — Phase 69 may add
    columns to ``graph_nodes`` and we do not want this smoke test to
    break for unrelated reasons.
    """
    workspace_id = uuid4()
    node_id = uuid4()
    embedding = [0.1] * EMBEDDING_DIM
    embedding_literal = _vec_literal(embedding)

    await pg_session.execute(
        text(
            """
            INSERT INTO graph_nodes
                (id, workspace_id, node_type, label, content, properties, embedding,
                 created_at, updated_at)
            VALUES
                (:id, :wsid, 'note_chunk', :label, :content, '{}'::jsonb,
                 CAST(:embedding AS vector),
                 now(), now())
            """,
        ),
        {
            "id": str(node_id),
            "wsid": str(workspace_id),
            "label": "phase69-smoke",
            "content": "phase69 pgvector smoke test content",
            "embedding": embedding_literal,
        },
    )

    rows = (
        await pg_session.execute(
            text(
                """
                SELECT id,
                       1 - (embedding <=> CAST(:q AS vector)) AS cosine_score
                FROM graph_nodes
                WHERE workspace_id = :wsid
                ORDER BY embedding <=> CAST(:q AS vector)
                LIMIT 5
                """,
            ),
            {"q": embedding_literal, "wsid": str(workspace_id)},
        )
    ).all()

    assert rows, "pgvector recall returned no rows"
    top = rows[0]
    assert str(top.id) == str(node_id)
    assert top.cosine_score >= 0.99, f"cosine_score {top.cosine_score} < 0.99"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rls_isolation_between_workspaces(pg_session: AsyncSession) -> None:
    """RLS must prevent workspace A user from reading workspace B rows.

    Seeds one user + one graph_node in each of two workspaces via
    service_role (RLS bypass), then sets the RLS context to user A and
    asserts SELECT only returns workspace A's node.
    """
    workspace_a = uuid4()
    workspace_b = uuid4()
    user_a = uuid4()
    user_b = uuid4()
    node_a = uuid4()
    node_b = uuid4()

    # Seed workspace_members rows so the RLS policy (which joins on
    # workspace_members) admits user_a into workspace_a only.
    for ws, user in ((workspace_a, user_a), (workspace_b, user_b)):
        await pg_session.execute(
            text(
                """
                INSERT INTO workspaces (id, name, slug, created_at, updated_at)
                VALUES (:id, :name, :slug, now(), now())
                ON CONFLICT (id) DO NOTHING
                """,
            ),
            {"id": str(ws), "name": f"ws-{ws}", "slug": f"ws-{ws}"},
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

    for ws, nid in ((workspace_a, node_a), (workspace_b, node_b)):
        await pg_session.execute(
            text(
                """
                INSERT INTO graph_nodes
                    (id, workspace_id, node_type, label, content, properties,
                     created_at, updated_at)
                VALUES (:id, :wsid, 'note_chunk', :label, :content, '{}'::jsonb,
                        now(), now())
                """,
            ),
            {
                "id": str(nid),
                "wsid": str(ws),
                "label": f"rls-{ws}",
                "content": f"rls smoke {ws}",
            },
        )

    # Activate RLS as user A; should only see workspace_a's node.
    await set_rls_context(pg_session, user_id=user_a, workspace_id=workspace_a)
    visible_ids = {
        str(row.id)
        for row in (
            await pg_session.execute(
                text("SELECT id FROM graph_nodes WHERE label LIKE 'rls-%'"),
            )
        ).all()
    }

    assert str(node_a) in visible_ids, "user A cannot see own workspace row"
    assert str(node_b) not in visible_ids, (
        "RLS leak: user A sees workspace B row — isolation broken"
    )
