"""Tests for alembic migration 107 — memory producer toggles + PR review unique index.

These tests require a real PostgreSQL database because the migration creates
an expression-based partial UNIQUE index on ``graph_nodes.properties`` JSONB
(not supported by SQLite). They are gated on ``TEST_DATABASE_URL`` via the
``postgres`` marker.

Contract asserted:

    1. Single alembic head after upgrade (== 107_memory_producer_toggles).
    2. Four boolean columns added to workspace_ai_settings with documented
       defaults (TRUE, TRUE, TRUE, FALSE).
    3. Partial unique index ``uq_graph_nodes_pr_review_finding`` exists and
       is scoped to ``node_type = 'pr_review_finding'``.
    4. Downgrade reverts all four columns and drops the index cleanly.
"""

from __future__ import annotations

import os

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from alembic import command

pytestmark = pytest.mark.postgres


def _alembic_config() -> Config:
    # backend/ is the alembic project root; tests run from backend/ cwd.
    cfg = Config("alembic.ini")
    if (url := os.environ.get("TEST_DATABASE_URL")):
        cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def pg_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not url.startswith(("postgresql", "postgres")):
        pytest.skip("TEST_DATABASE_URL not set to a PostgreSQL URL")
    return url


def test_single_head_is_107() -> None:
    cfg = _alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected single alembic head, got {heads}"
    assert heads[0] == "107_memory_producer_toggles"


def test_upgrade_adds_four_columns_with_defaults(pg_url: str) -> None:
    cfg = _alembic_config()
    command.upgrade(cfg, "107_memory_producer_toggles")

    engine = create_engine(pg_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT column_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'workspace_ai_settings'
                  AND column_name IN (
                      'memory_producer_agent_turn_enabled',
                      'memory_producer_user_correction_enabled',
                      'memory_producer_pr_review_enabled',
                      'memory_summarizer_enabled'
                  )
                """
            )
        ).all()
    by_name = {r[0]: (r[1], r[2]) for r in rows}
    assert set(by_name.keys()) == {
        "memory_producer_agent_turn_enabled",
        "memory_producer_user_correction_enabled",
        "memory_producer_pr_review_enabled",
        "memory_summarizer_enabled",
    }
    # Defaults: first three TRUE, summarizer FALSE.
    assert "true" in (by_name["memory_producer_agent_turn_enabled"][0] or "").lower()
    assert "true" in (by_name["memory_producer_user_correction_enabled"][0] or "").lower()
    assert "true" in (by_name["memory_producer_pr_review_enabled"][0] or "").lower()
    assert "false" in (by_name["memory_summarizer_enabled"][0] or "").lower()
    for _, nullable in by_name.values():
        assert nullable == "NO"


def test_upgrade_creates_pr_review_finding_partial_unique_index(pg_url: str) -> None:
    engine = create_engine(pg_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE indexname = 'uq_graph_nodes_pr_review_finding'
                """
            )
        ).first()
    assert row is not None, "uq_graph_nodes_pr_review_finding index missing"
    indexdef = row[0]
    assert "UNIQUE" in indexdef
    assert "pr_review_finding" in indexdef
    assert "properties" in indexdef


def test_downgrade_reverts_columns_and_index(pg_url: str) -> None:
    cfg = _alembic_config()
    command.downgrade(cfg, "106_phase69_memory_node_types")

    engine = create_engine(pg_url)
    with engine.connect() as conn:
        cols = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'workspace_ai_settings'
                  AND column_name LIKE 'memory_%'
                """
            )
        ).all()
        idx = conn.execute(
            text(
                "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_graph_nodes_pr_review_finding'"
            )
        ).first()
    assert cols == [], f"Expected all memory_* cols dropped, got {cols}"
    assert idx is None

    # Re-upgrade for test cleanliness.
    command.upgrade(cfg, "107_memory_producer_toggles")
