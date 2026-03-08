"""Tests for AI action audit recording via AuditLogHook.

Covers:
- AuditLogHook writes a row with actor_type=AI after PostToolUse event
- ai_model, ai_token_cost, ai_rationale are populated from tool use result
- actor_id is the human user who triggered the AI action
- AuditLogHook only fires for relevant tool use events
- AuditLogHook is non-fatal: errors do not propagate to the AI action

Requirements: AUDIT-02
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAuditLogHookPostToolUse:
    """Tests for AuditLogHook.on_post_tool_use() writing audit rows."""

    @pytest.mark.asyncio
    async def test_writes_row_with_ai_actor_type(self) -> None:
        """After PostToolUse, AuditLogHook must write a row with actor_type=AI."""
        from pilot_space.ai.sdk.hooks import AuditLogHook
        from pilot_space.infrastructure.database.models.audit_log import ActorType

        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        hook = AuditLogHook(audit_repo=audit_repo)

        tool_use_result = MagicMock()
        tool_use_result.tool_name = "create_issue"
        tool_use_result.input = {"name": "Test Issue", "workspace_id": str(workspace_id)}
        tool_use_result.output = {"issue_id": str(uuid.uuid4())}
        tool_use_result.model = "claude-sonnet-4-5"
        tool_use_result.token_usage = MagicMock()
        tool_use_result.token_usage.total_tokens = 200
        tool_use_result.rationale = "User requested issue creation"

        context = MagicMock()
        context.workspace_id = workspace_id
        context.user_id = user_id

        await hook.on_post_tool_use(tool_use_result, context)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["actor_type"] == ActorType.AI
        assert call_kwargs["actor_id"] == user_id
        assert call_kwargs["workspace_id"] == workspace_id

    @pytest.mark.asyncio
    async def test_populates_ai_fields_from_tool_use_result(self) -> None:
        """AuditLogHook must populate ai_model, ai_token_cost, ai_rationale."""
        from pilot_space.ai.sdk.hooks import AuditLogHook

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        hook = AuditLogHook(audit_repo=audit_repo)

        tool_use_result = MagicMock()
        tool_use_result.tool_name = "update_issue"
        tool_use_result.input = {"issue_id": str(uuid.uuid4()), "name": "Updated"}
        tool_use_result.output = {"success": True}
        tool_use_result.model = "claude-opus-4-5"
        tool_use_result.token_usage = MagicMock()
        tool_use_result.token_usage.total_tokens = 350
        tool_use_result.rationale = "Updating as requested by user"

        context = MagicMock()
        context.workspace_id = uuid.uuid4()
        context.user_id = uuid.uuid4()

        await hook.on_post_tool_use(tool_use_result, context)

        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["ai_model"] == "claude-opus-4-5"
        assert call_kwargs["ai_token_cost"] == 350
        assert call_kwargs["ai_rationale"] == "Updating as requested by user"
        assert call_kwargs["ai_input"] is not None
        assert call_kwargs["ai_output"] is not None

    @pytest.mark.asyncio
    async def test_hook_is_non_fatal_on_db_error(self) -> None:
        """AuditLogHook must not propagate exceptions — audit failures are non-fatal."""
        from pilot_space.ai.sdk.hooks import AuditLogHook

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(side_effect=Exception("DB connection error"))

        hook = AuditLogHook(audit_repo=audit_repo)

        tool_use_result = MagicMock()
        tool_use_result.tool_name = "create_issue"
        tool_use_result.input = {}
        tool_use_result.output = {}
        tool_use_result.model = "claude-sonnet-4-5"
        tool_use_result.token_usage = MagicMock()
        tool_use_result.token_usage.total_tokens = 0
        tool_use_result.rationale = None

        context = MagicMock()
        context.workspace_id = uuid.uuid4()
        context.user_id = uuid.uuid4()

        # Must not raise even if audit repo fails
        await hook.on_post_tool_use(tool_use_result, context)
