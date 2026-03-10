"""Shared fixtures for audit log tests.

Provides:
- audit_log_factory: creates AuditLog instances for testing
- Reuses db_session, workspace fixtures from parent conftest
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog


@pytest.fixture
def audit_log_factory(db_session: AsyncSession):
    """Factory fixture for creating AuditLog rows.

    Returns a callable that creates and adds an AuditLog to the DB session.
    The caller is responsible for committing the session if needed.

    Usage:
        row = await audit_log_factory(workspace_id=workspace.id, action="issue.create")
    """

    async def _factory(
        *,
        workspace_id: uuid.UUID,
        action: str = "issue.create",
        actor_id: uuid.UUID | None = None,
        actor_type: ActorType = ActorType.USER,
        resource_type: str = "issue",
        resource_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        ai_input: dict[str, Any] | None = None,
        ai_output: dict[str, Any] | None = None,
        ai_model: str | None = None,
        ai_token_cost: int | None = None,
        ai_rationale: str | None = None,
        ip_address: str | None = "127.0.0.1",
        created_at: datetime | None = None,
    ) -> AuditLog:
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id or uuid.uuid4(),
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id or uuid.uuid4(),
            payload=payload,
            ai_input=ai_input,
            ai_output=ai_output,
            ai_model=ai_model,
            ai_token_cost=ai_token_cost,
            ai_rationale=ai_rationale,
            ip_address=ip_address,
        )
        if created_at is not None:
            row.created_at = created_at
            row.updated_at = created_at
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)
        return row

    return _factory
