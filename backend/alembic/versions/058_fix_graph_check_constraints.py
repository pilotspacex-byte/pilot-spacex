"""Fix graph_nodes node_type and graph_edges edge_type CHECK constraints.

Revision ID: 058_fix_graph_check_constraints
Revises: 057_resize_graph_embedding
Create Date: 2026-03-04

Migration 055 created CHECK constraints with an obsolete set of node_type
and edge_type values that don't match the current NodeType / EdgeType enums.
This migration drops the stale constraints and recreates them with the
correct values, preventing CheckViolation errors on PostgreSQL.

NodeType values added: pull_request, branch, commit, code_reference, decision,
  skill_outcome, conversation_summary, learned_pattern, constitution_rule,
  work_intent, user_preference
NodeType values removed: concept, agent, workspace, label, comment, document,
  task, sprint, epic

EdgeType values added: caused_by, led_to, decided_in, authored_by, belongs_to,
  references, learned_from, summarizes
EdgeType values removed: blocked_by, child_of, mentions, created_by,
  labeled_with, part_of, links_to, summarises, referenced_by
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "058_fix_graph_check_constraints"
down_revision: str | None = "057_resize_graph_embedding"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Drop stale CHECK constraints and recreate with correct enum values."""

    # ------------------------------------------------------------------
    # graph_nodes — node_type constraint
    # ------------------------------------------------------------------
    op.execute(
        text(
            "ALTER TABLE graph_nodes DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check"
        )
    )
    op.execute(
        text(
            "ALTER TABLE graph_nodes ADD CONSTRAINT graph_nodes_node_type_check "
            "CHECK (node_type IN ("
            "'issue', 'note', 'project', 'cycle', 'user', "
            "'pull_request', 'branch', 'commit', 'code_reference', "
            "'decision', 'skill_outcome', 'conversation_summary', "
            "'learned_pattern', 'constitution_rule', 'work_intent', "
            "'user_preference'"
            "))"
        )
    )

    # ------------------------------------------------------------------
    # graph_edges — edge_type constraint
    # The original constraint was inline (no explicit name), so PostgreSQL
    # auto-names it. Drop by searching pg_constraint.
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        DO $$
        DECLARE
            con_name text;
        BEGIN
            SELECT conname INTO con_name
            FROM pg_constraint
            WHERE conrelid = 'graph_edges'::regclass
              AND contype = 'c'
              AND conname != 'chk_graph_edges_no_self_loop';
            IF con_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE graph_edges DROP CONSTRAINT ' || quote_ident(con_name);
            END IF;
        END
        $$
        """
        )
    )
    op.execute(
        text(
            "ALTER TABLE graph_edges ADD CONSTRAINT chk_graph_edges_edge_type "
            "CHECK (edge_type IN ("
            "'relates_to', 'caused_by', 'led_to', 'decided_in', "
            "'authored_by', 'assigned_to', 'belongs_to', 'references', "
            "'learned_from', 'summarizes', 'blocks', 'duplicates', 'parent_of'"
            "))"
        )
    )


def downgrade() -> None:
    """Restore original (wrong) constraints — only for rollback to 057."""
    op.execute(
        text(
            "ALTER TABLE graph_nodes DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check"
        )
    )
    op.execute(
        text(
            "ALTER TABLE graph_nodes ADD CONSTRAINT graph_nodes_node_type_check "
            "CHECK (node_type IN ("
            "'issue', 'note', 'concept', 'agent', 'user', "
            "'workspace', 'project', 'cycle', 'label', "
            "'comment', 'document', 'task', 'sprint', 'epic'"
            "))"
        )
    )

    op.execute(
        text(
            "ALTER TABLE graph_edges DROP CONSTRAINT IF EXISTS chk_graph_edges_edge_type"
        )
    )
    op.execute(
        text(
            "ALTER TABLE graph_edges ADD CONSTRAINT graph_edges_edge_type_check "
            "CHECK (edge_type IN ("
            "'relates_to', 'blocks', 'blocked_by', 'duplicates', "
            "'parent_of', 'child_of', 'mentions', 'assigned_to', "
            "'created_by', 'labeled_with', 'part_of', 'links_to', "
            "'summarises', 'referenced_by'"
            "))"
        )
    )
