"""Unit tests for WorkspaceAIPolicy model.

Phase 4 — AI Governance (AIGOV-01) schema verification.

Tests are xfail(strict=False) until migration is applied to the test DB.
The SQLite in-memory default lacks the workspace_ai_policy table;
set TEST_DATABASE_URL to PostgreSQL for full validation.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.workspace_ai_policy import (
    WorkspaceAIPolicy,
)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 schema — xfail until migration applied in test DB (SQLite lacks workspace_ai_policy table)",
)
async def test_workspace_ai_policy_fields(db_session: AsyncSession) -> None:
    """WorkspaceAIPolicy model has required fields: workspace_id, role, action_type, requires_approval."""
    workspace_id = uuid.uuid4()
    policy = WorkspaceAIPolicy(
        workspace_id=workspace_id,
        role="ADMIN",
        action_type="create_issues",
        requires_approval=False,
    )
    db_session.add(policy)
    await db_session.flush()

    assert policy.workspace_id == workspace_id
    assert policy.role == "ADMIN"
    assert policy.action_type == "create_issues"
    assert policy.requires_approval is False
    assert policy.id is not None


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 schema — xfail until migration applied in test DB (SQLite lacks workspace_ai_policy table)",
)
async def test_workspace_ai_policy_unique_constraint(
    db_session_committed: AsyncSession,
) -> None:
    """Inserting two rows with identical (workspace_id, role, action_type) raises IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    workspace_id = uuid.uuid4()
    policy_1 = WorkspaceAIPolicy(
        workspace_id=workspace_id,
        role="MEMBER",
        action_type="extract_issues",
        requires_approval=True,
    )
    policy_2 = WorkspaceAIPolicy(
        workspace_id=workspace_id,
        role="MEMBER",
        action_type="extract_issues",
        requires_approval=False,
    )
    db_session_committed.add(policy_1)
    await db_session_committed.commit()

    db_session_committed.add(policy_2)
    with pytest.raises(IntegrityError):
        await db_session_committed.commit()


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 schema — xfail until migration applied in test DB (SQLite lacks workspace_ai_policy table)",
)
async def test_ai_cost_record_has_operation_type(db_session: AsyncSession) -> None:
    """AICostRecord model has operation_type mapped column (nullable str)."""
    from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord

    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    record = AICostRecord(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_name="test_agent",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        operation_type="ghost_text",
    )
    db_session.add(record)
    await db_session.flush()

    assert record.operation_type == "ghost_text"

    # Also verify nullable — operation_type=None should persist without error
    record_no_op = AICostRecord(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_name="test_agent",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        operation_type=None,
    )
    db_session.add(record_no_op)
    await db_session.flush()

    assert record_no_op.operation_type is None
