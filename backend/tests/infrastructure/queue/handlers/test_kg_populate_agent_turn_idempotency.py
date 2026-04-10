"""Phase 70 Wave 2 — GREEN: kg_populate dedupes agent_turn replays.

Contract: replaying the same ``(workspace_id, session_id, turn_index)``
payload twice MUST result in exactly one ``graph_nodes`` row of type
``agent_turn``, via the ``uq_graph_nodes_agent_turn_cache`` partial unique
index (migration 106). The handler swallows the ``IntegrityError`` on
retry and returns ``{"success": True, "duplicate": True}``.

Requires real PostgreSQL — SQLite has no partial unique index semantics.
Gated on ``TEST_DATABASE_URL`` via the ``postgres_session`` fixture.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from pilot_space.application.services.embedding_service import (
    EmbeddingConfig,
    EmbeddingService,
)
from pilot_space.infrastructure.queue.handlers.kg_populate_handler import (
    KgPopulateHandler,
)

pytestmark = [pytest.mark.postgres, pytest.mark.asyncio]


async def test_duplicate_turn_hits_unique_index_no_error(postgres_session) -> None:
    workspace_id = uuid4()
    session_id = uuid4()
    actor_user_id = uuid4()

    payload = {
        "task_type": "kg_populate",
        "memory_type": "agent_turn",
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        "session_id": str(session_id),
        "turn_index": 0,
        "content": "USER: hi\n\nASSISTANT: hello",
        "label": "turn 0",
        "metadata": {
            "session_id": str(session_id),
            "turn_index": 0,
            "tools_used": [],
        },
    }

    # Stub embedding + queue — we only care about the row lifecycle.
    embedding_service = EmbeddingService(EmbeddingConfig(openai_api_key="sk-test"))
    embedding_service.embed_texts = AsyncMock(return_value=[[0.0] * 1536])  # type: ignore[method-assign]
    queue = AsyncMock()

    handler = KgPopulateHandler(
        session=postgres_session,
        embedding_service=embedding_service,
        queue=queue,
    )

    try:
        # First run — writes one row.
        result1 = await handler.handle(payload)
        await postgres_session.commit()
        assert result1["success"] is True
        assert result1.get("duplicate") is not True

        # Replay — must hit the partial unique index and be swallowed.
        result2 = await handler.handle(payload)
        await postgres_session.commit()
        assert result2["success"] is True
        assert result2.get("duplicate") is True

        # Exactly one agent_turn row for this (workspace, session).
        count_stmt = text(
            """
            SELECT COUNT(*) FROM graph_nodes
            WHERE workspace_id = :w
              AND node_type = 'agent_turn'
              AND properties->>'session_id' = :s
            """
        )
        row = await postgres_session.execute(
            count_stmt, {"w": str(workspace_id), "s": str(session_id)}
        )
        assert row.scalar_one() == 1
    finally:
        # Cleanup — this fixture commits, so we must clean our rows.
        await postgres_session.execute(
            text("DELETE FROM graph_nodes WHERE workspace_id = :w"),
            {"w": str(workspace_id)},
        )
        await postgres_session.commit()
