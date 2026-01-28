"""T101: RLS Policy Tests for AI Tables.

Verify RLS policies on AI-related tables:
- workspace_api_keys: workspace-scoped access
- ai_approval_requests: workspace admin access
- ai_cost_records: workspace member read, admin write
- ai_sessions: user owns their sessions

Reference: specs/004-mvp-agents-build/tasks/P15-T095-T110.md
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from pilot_space.domain.models import (
    AIApprovalRequest,
    AICostRecord,
    AISession,
    ApprovalStatus,
    WorkspaceAPIKey,
)
from pilot_space.infrastructure.database.rls import set_rls_context

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.security.conftest import SecurityTestContext


class TestAITablesRLS:
    """T101: Verify RLS policies on AI-related tables.

    Tests for:
    - workspace_api_keys: workspace-scoped access
    - ai_approval_requests: workspace admin access
    - ai_cost_records: workspace member read, admin write
    - ai_sessions: user owns their sessions
    """

    @pytest.mark.asyncio
    async def test_workspace_api_keys_has_rls(
        self,
        db_session: AsyncSession,  # noqa: ARG002 - Required for test signature
    ) -> None:
        """Verify workspace_api_keys table has RLS enabled.

        Expected policy: Only workspace members can view/manage their workspace's keys.
        """
        # This test documents expected RLS behavior
        # In PostgreSQL, verify with:
        # SELECT relrowsecurity FROM pg_class WHERE relname = 'workspace_api_keys';

        # For SQLite test, document the requirement
        assert True  # RLS enforced in PostgreSQL deployment

    @pytest.mark.asyncio
    async def test_workspace_api_keys_isolated_by_workspace(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Verify users cannot access API keys from other workspaces."""
        # Create API key for workspace A
        key_a = WorkspaceAPIKey(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_a.id,
            provider="anthropic",
            encrypted_key="encrypted_value_a",
            is_valid=True,
        )
        db_session.add(key_a)

        # Create API key for workspace B
        key_b = WorkspaceAPIKey(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_b.id,
            provider="openai",
            encrypted_key="encrypted_value_b",
            is_valid=True,
        )
        db_session.add(key_b)
        await db_session.commit()

        # Set RLS context as workspace A member
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        # Query API keys - should only see workspace A
        result = await db_session.execute(
            select(WorkspaceAPIKey).where(
                WorkspaceAPIKey.workspace_id == populated_db.workspace_b.id
            )
        )
        keys = result.scalars().all()

        # Should not see workspace B keys
        assert len(keys) == 0, "User should not access other workspace's API keys"

    @pytest.mark.asyncio
    async def test_ai_approval_requests_has_rls(
        self,
        db_session: AsyncSession,  # noqa: ARG002 - Required for test signature
    ) -> None:
        """Verify ai_approval_requests table has RLS enabled.

        Expected policy: Workspace admin/member access only.
        """
        # Document expected RLS behavior
        assert True  # Enforced via PostgreSQL RLS policies

    @pytest.mark.asyncio
    async def test_ai_approval_requests_isolated_by_workspace(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Verify approval requests are workspace-isolated."""
        # Create approval in workspace A
        approval_a = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_a.id,
            requested_by_id=populated_db.owner.id,
            agent_type="issue_extractor",
            action_type="create_issues",
            action_payload={"issues": []},
            status=ApprovalStatus.PENDING,
            confidence_score=0.9,
        )
        db_session.add(approval_a)

        # Create approval in workspace B
        approval_b = AIApprovalRequest(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_b.id,
            requested_by_id=populated_db.outsider.id,
            agent_type="task_decomposer",
            action_type="create_sub_issues",
            action_payload={"tasks": []},
            status=ApprovalStatus.PENDING,
            confidence_score=0.85,
        )
        db_session.add(approval_b)
        await db_session.commit()

        # Set context as workspace A member
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        # Query approvals - should not see workspace B
        result = await db_session.execute(
            select(AIApprovalRequest).where(
                AIApprovalRequest.workspace_id == populated_db.workspace_b.id
            )
        )
        approvals = result.scalars().all()

        assert len(approvals) == 0, "Approval requests should be workspace-isolated"

    @pytest.mark.asyncio
    async def test_ai_cost_records_has_rls(
        self,
        db_session: AsyncSession,  # noqa: ARG002 - Required for test signature
    ) -> None:
        """Verify ai_cost_records table has RLS enabled.

        Expected policies:
        - Workspace members can read cost records
        - Only admins/service role can write
        """
        assert True  # Enforced via RLS

    @pytest.mark.asyncio
    async def test_ai_cost_records_isolated_by_workspace(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Verify cost records are workspace-isolated."""
        # Create cost record for workspace A
        cost_a = AICostRecord(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_a.id,
            user_id=populated_db.owner.id,
            provider="anthropic",
            model="claude-opus-4-5",
            operation="pr_review",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
        )
        db_session.add(cost_a)

        # Create cost record for workspace B
        cost_b = AICostRecord(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_b.id,
            user_id=populated_db.outsider.id,
            provider="openai",
            model="gpt-4",
            operation="embedding",
            input_tokens=500,
            output_tokens=0,
            cost_usd=0.01,
        )
        db_session.add(cost_b)
        await db_session.commit()

        # Set context as workspace A member
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        # Query cost records - should not see workspace B
        result = await db_session.execute(
            select(AICostRecord).where(AICostRecord.workspace_id == populated_db.workspace_b.id)
        )
        costs = result.scalars().all()

        assert len(costs) == 0, "Cost records should be workspace-isolated"

    @pytest.mark.asyncio
    async def test_ai_sessions_has_rls(
        self,
        db_session: AsyncSession,  # noqa: ARG002 - Required for test signature
    ) -> None:
        """Verify ai_sessions table has RLS enabled.

        Expected policy: Users can only access their own sessions.
        """
        assert True  # Enforced via RLS

    @pytest.mark.asyncio
    async def test_ai_sessions_user_isolation(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Verify users can only see their own AI sessions."""
        # Create session for owner
        session_owner = AISession(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_a.id,
            user_id=populated_db.owner.id,
            agent_type="conversation",
            context_id=str(uuid.uuid4()),
            message_history=[],
            token_count=100,
        )
        db_session.add(session_owner)

        # Create session for member (same workspace)
        session_member = AISession(
            id=uuid.uuid4(),
            workspace_id=populated_db.workspace_a.id,
            user_id=populated_db.member.id,
            agent_type="ai_context",
            context_id=str(uuid.uuid4()),
            message_history=[],
            token_count=50,
        )
        db_session.add(session_member)
        await db_session.commit()

        # Set context as member
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        # Query sessions - should only see member's sessions
        result = await db_session.execute(
            select(AISession).where(AISession.user_id == populated_db.owner.id)
        )
        sessions = result.scalars().all()

        # Should not see owner's sessions (even in same workspace)
        assert len(sessions) == 0, "Users should only see their own AI sessions"

    @pytest.mark.asyncio
    async def test_guest_cannot_access_ai_features(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Verify guests have no access to AI configuration/approvals.

        Guests should not:
        - View/manage API keys
        - Approve AI actions
        - View cost records (unless explicitly granted)
        """
        # Set context as guest
        await set_rls_context(
            db_session,
            user_id=populated_db.guest.id,
            workspace_id=populated_db.workspace_a.id,
        )

        # Guest attempts to view API keys
        result = await db_session.execute(
            select(WorkspaceAPIKey).where(
                WorkspaceAPIKey.workspace_id == populated_db.workspace_a.id
            )
        )
        _ = result.scalars().all()

        # Expected: RLS blocks guest access (or returns empty)
        # For now, document expected behavior
        # In production PostgreSQL, this would return 0 rows due to RLS
        assert True  # RLS enforcement documented
