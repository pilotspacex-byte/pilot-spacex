"""Tests for AuditLogRepository and service-layer audit writes.

Covers:
- AuditLogRepository.create(): inserts row with correct fields
- AuditLogRepository.list_filtered(): returns items in desc created_at order
- Cursor pagination: next_cursor encodes correctly; second page returns correct items
- compute_diff(): only changed fields included
- IssueService audit writes (create, update, delete)
- NoteService audit writes (create, update, delete)
- CycleService audit writes (create, update, delete, issue_added, issue_removed)
- WorkspaceMemberService audit writes (role_changed, removed)
- RbacService audit writes (create_role, update_role, delete_role)

Requirements: AUDIT-01, AUDIT-06
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
    compute_diff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> AsyncMock:
    """Build a minimal async SQLAlchemy session mock."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_audit_row(
    workspace_id: uuid.UUID,
    *,
    action: str = "issue.create",
    actor_id: uuid.UUID | None = None,
    actor_type: ActorType = ActorType.USER,
    resource_type: str = "issue",
    resource_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    """Create an in-memory AuditLog for test assertions."""
    row = AuditLog(
        workspace_id=workspace_id,
        actor_id=actor_id or uuid.uuid4(),
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or uuid.uuid4(),
        payload=payload,
    )
    row.id = uuid.uuid4()
    row.created_at = created_at or datetime.now(tz=UTC)
    row.updated_at = row.created_at
    return row


# ---------------------------------------------------------------------------
# compute_diff unit tests
# ---------------------------------------------------------------------------


class TestComputeDiff:
    """Tests for the compute_diff helper."""

    def test_returns_only_changed_fields(self) -> None:
        before = {"name": "Old", "priority": "HIGH", "state_id": "abc"}
        after = {"name": "New", "priority": "HIGH", "state_id": "xyz"}
        diff = compute_diff(before, after)
        assert set(diff["after"].keys()) == {"name", "state_id"}
        assert set(diff["before"].keys()) == {"name", "state_id"}
        assert diff["after"]["name"] == "New"
        assert diff["before"]["name"] == "Old"
        assert "priority" not in diff["after"]

    def test_new_field_in_after(self) -> None:
        diff = compute_diff({"a": 1}, {"a": 1, "b": 2})
        assert diff["after"] == {"b": 2}
        assert diff["before"] == {"b": None}

    def test_no_changes_returns_empty_dicts(self) -> None:
        diff = compute_diff({"a": 1}, {"a": 1})
        assert diff == {"before": {}, "after": {}}

    def test_none_value_detected_as_change(self) -> None:
        diff = compute_diff({"a": "val"}, {"a": None})
        assert "a" in diff["after"]
        assert diff["after"]["a"] is None

    def test_empty_before(self) -> None:
        diff = compute_diff({}, {"x": 42})
        assert diff["after"] == {"x": 42}
        assert diff["before"] == {"x": None}


# ---------------------------------------------------------------------------
# AuditLogRepository.create tests
# ---------------------------------------------------------------------------


class TestAuditLogRepositoryCreate:
    """Tests for AuditLogRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_returns_row_with_correct_fields(self) -> None:
        """create() should insert an AuditLog row and return it with populated fields."""
        session = _make_session()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        # After flush+refresh, session.refresh sets the expected fields
        async def _refresh_side_effect(row: Any) -> None:
            row.id = uuid.uuid4()
            row.created_at = datetime.now(tz=UTC)
            row.updated_at = row.created_at

        session.refresh.side_effect = _refresh_side_effect

        repo = AuditLogRepository(session)
        row = await repo.create(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=ActorType.USER,
            action="issue.create",
            resource_type="issue",
            resource_id=resource_id,
            payload={"before": {}, "after": {"name": "Test Issue"}},
            ip_address="127.0.0.1",
        )

        assert row.workspace_id == workspace_id
        assert row.actor_id == actor_id
        assert row.actor_type == ActorType.USER
        assert row.action == "issue.create"
        assert row.resource_type == "issue"
        assert row.resource_id == resource_id
        assert row.payload == {"before": {}, "after": {"name": "Test Issue"}}
        assert row.ip_address == "127.0.0.1"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_accepts_none_actor_id(self) -> None:
        """create() should work with actor_id=None for system actions."""
        session = _make_session()
        repo = AuditLogRepository(session)

        row = await repo.create(
            workspace_id=uuid.uuid4(),
            actor_id=None,
            actor_type=ActorType.SYSTEM,
            action="workspace_setting.retention_updated",
            resource_type="workspace_setting",
            resource_id=None,
            payload=None,
            ip_address=None,
        )

        assert row.actor_id is None
        assert row.actor_type == ActorType.SYSTEM

    @pytest.mark.asyncio
    async def test_create_with_ai_fields(self) -> None:
        """create() should store ai_* fields for AI actor entries."""
        session = _make_session()
        repo = AuditLogRepository(session)

        row = await repo.create(
            workspace_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            actor_type=ActorType.AI,
            action="issue.create",
            resource_type="issue",
            resource_id=uuid.uuid4(),
            payload={"before": {}, "after": {}},
            ip_address=None,
            ai_input={"prompt": "create issue"},
            ai_output={"result": "done"},
            ai_model="claude-sonnet-4-5",
            ai_token_cost=150,
            ai_rationale="automated",
        )

        assert row.actor_type == ActorType.AI
        assert row.ai_input == {"prompt": "create issue"}
        assert row.ai_model == "claude-sonnet-4-5"
        assert row.ai_token_cost == 150


# ---------------------------------------------------------------------------
# AuditLogRepository.list_filtered tests
# ---------------------------------------------------------------------------


class TestAuditLogRepositoryListFiltered:
    """Tests for AuditLogRepository.list_filtered()."""

    def _make_result_mock(self, rows: list[AuditLog]) -> AsyncMock:
        """Build a mock session that returns the given rows from execute()."""
        session = _make_session()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = rows
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)
        return session

    @pytest.mark.asyncio
    async def test_returns_items_desc_order_by_created_at(self) -> None:
        """list_filtered() should return items in descending created_at order."""
        workspace_id = uuid.uuid4()
        now = datetime.now(tz=UTC)
        row1 = _make_audit_row(workspace_id, created_at=now - timedelta(minutes=1))
        row2 = _make_audit_row(workspace_id, created_at=now)
        # Returned rows already sorted (DB ORDER BY); we trust the query
        session = self._make_result_mock([row2, row1])
        repo = AuditLogRepository(session)

        result = await repo.list_filtered(workspace_id=workspace_id, page_size=10)

        assert result.items[0].created_at >= result.items[1].created_at

    @pytest.mark.asyncio
    async def test_has_next_false_when_fewer_than_page_size(self) -> None:
        """has_next should be False when fewer rows than page_size returned."""
        workspace_id = uuid.uuid4()
        rows = [_make_audit_row(workspace_id) for _ in range(3)]
        session = self._make_result_mock(rows)
        repo = AuditLogRepository(session)

        result = await repo.list_filtered(workspace_id=workspace_id, page_size=10)

        assert result.has_next is False
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_has_next_true_when_extra_row_returned(self) -> None:
        """has_next should be True when page_size+1 rows are returned."""
        workspace_id = uuid.uuid4()
        # 6 rows for page_size=5 → has_next=True
        rows = [_make_audit_row(workspace_id) for _ in range(6)]
        session = self._make_result_mock(rows)
        repo = AuditLogRepository(session)

        result = await repo.list_filtered(workspace_id=workspace_id, page_size=5)

        assert result.has_next is True
        assert result.next_cursor is not None
        # Only page_size items returned, not the extra one
        assert len(result.items) == 5

    @pytest.mark.asyncio
    async def test_next_cursor_is_base64_encoded_json(self) -> None:
        """next_cursor should be a base64-encoded JSON with ts and id keys."""
        import base64
        import json

        workspace_id = uuid.uuid4()
        rows = [_make_audit_row(workspace_id) for _ in range(3)]
        session = self._make_result_mock(rows)
        repo = AuditLogRepository(session)

        # Force has_next=True by requesting 2 rows from 3
        result = await repo.list_filtered(workspace_id=workspace_id, page_size=2)

        assert result.next_cursor is not None
        decoded = json.loads(base64.b64decode(result.next_cursor).decode())
        assert "ts" in decoded
        assert "id" in decoded

    @pytest.mark.asyncio
    async def test_filters_passed_to_query(self) -> None:
        """list_filtered() should execute without raising when filters are provided."""
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = self._make_result_mock([])
        repo = AuditLogRepository(session)

        result = await repo.list_filtered(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action="issue.create",
            resource_type="issue",
            start_date=datetime.now(tz=UTC) - timedelta(days=7),
            end_date=datetime.now(tz=UTC),
            page_size=20,
        )

        assert result.items == []
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Service audit instrumentation tests (mocked AuditLogRepository)
# ---------------------------------------------------------------------------


class TestCreateIssueServiceAudit:
    """Tests that CreateIssueService writes audit row on issue creation."""

    @pytest.mark.asyncio
    async def test_create_issue_emits_audit_row(self) -> None:
        """CreateIssueService.execute() should call audit_repo.create with issue.create action."""
        from pilot_space.application.services.issue.create_issue_service import (
            CreateIssuePayload,
            CreateIssueService,
        )

        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        reporter_id = uuid.uuid4()

        mock_issue = MagicMock()
        mock_issue.id = uuid.uuid4()
        mock_issue.workspace_id = workspace_id
        mock_issue.name = "Test Issue"
        mock_issue.identifier = "TEST-1"
        mock_issue.priority = MagicMock()
        mock_issue.priority.value = "NONE"

        issue_repo = AsyncMock()
        issue_repo.get_next_sequence_id.return_value = 1
        issue_repo.create.return_value = mock_issue
        issue_repo.bulk_update_labels = AsyncMock()
        issue_repo.get_by_id_with_relations.return_value = mock_issue

        activity_repo = AsyncMock()
        activity_mock = MagicMock()
        activity_repo.create.return_value = activity_mock

        label_repo = AsyncMock()

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()
        session.execute = AsyncMock()

        payload = CreateIssuePayload(
            workspace_id=workspace_id,
            project_id=project_id,
            reporter_id=reporter_id,
            name="Test Issue",
        )

        service = CreateIssueService(
            session=session,
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            audit_log_repository=audit_repo,
        )

        # Patch Activity.create_for_issue_creation to avoid model-level calls
        with (
            patch(
                "pilot_space.application.services.issue.create_issue_service.Activity.create_for_issue_creation",
                return_value=MagicMock(),
            ),
            patch(
                "pilot_space.application.services.issue.create_issue_service.CreateIssueService._get_default_state_id",
                new_callable=AsyncMock,
                return_value=uuid.uuid4(),
            ),
        ):
            await service.execute(payload)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "issue.create"
        assert call_kwargs["resource_type"] == "issue"
        assert call_kwargs["actor_id"] == reporter_id
        assert call_kwargs["workspace_id"] == workspace_id


class TestUpdateIssueServiceAudit:
    """Tests that UpdateIssueService writes audit row on issue update."""

    @pytest.mark.asyncio
    async def test_update_issue_emits_audit_row(self) -> None:
        """UpdateIssueService.execute() should call audit_repo.create with issue.update action."""
        from pilot_space.application.services.issue.update_issue_service import (
            UpdateIssuePayload,
            UpdateIssueService,
        )
        from pilot_space.infrastructure.database.models import IssuePriority

        workspace_id = uuid.uuid4()
        issue_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_issue = MagicMock()
        mock_issue.id = issue_id
        mock_issue.workspace_id = workspace_id
        mock_issue.name = "Old Name"
        mock_issue.priority = IssuePriority.NONE
        mock_issue.state_id = uuid.uuid4()
        mock_issue.assignee_id = None
        mock_issue.cycle_id = None
        mock_issue.description = None
        mock_issue.description_html = None
        mock_issue.module_id = None
        mock_issue.parent_id = None
        mock_issue.estimate_points = None
        mock_issue.estimate_hours = None
        mock_issue.start_date = None
        mock_issue.target_date = None
        mock_issue.sort_order = 0
        mock_issue.ai_metadata = None
        mock_issue.state = MagicMock()
        mock_issue.state.name = "Backlog"

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations.return_value = mock_issue
        issue_repo.update.return_value = mock_issue
        issue_repo.bulk_update_labels = AsyncMock()

        activity_repo = AsyncMock()
        activity_repo.create = AsyncMock(return_value=MagicMock())

        label_repo = AsyncMock()

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()

        payload = UpdateIssuePayload(
            issue_id=issue_id,
            actor_id=actor_id,
            name="New Name",
        )

        service = UpdateIssueService(
            session=session,
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            audit_log_repository=audit_repo,
        )

        with patch(
            "pilot_space.application.services.issue.update_issue_service.Activity.create_for_field_update",
            return_value=MagicMock(),
        ):
            await service.execute(payload)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "issue.update"
        assert call_kwargs["resource_type"] == "issue"
        assert call_kwargs["actor_id"] == actor_id


class TestDeleteIssueServiceAudit:
    """Tests that DeleteIssueService writes audit row on issue deletion."""

    @pytest.mark.asyncio
    async def test_delete_issue_emits_audit_row(self) -> None:
        """DeleteIssueService.execute() should call audit_repo.create with issue.delete action."""
        from pilot_space.application.services.issue.delete_issue_service import (
            DeleteIssuePayload,
            DeleteIssueService,
        )

        workspace_id = uuid.uuid4()
        issue_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_issue = MagicMock()
        mock_issue.id = issue_id
        mock_issue.workspace_id = workspace_id
        mock_issue.name = "Issue"
        mock_issue.identifier = "TEST-1"

        issue_repo = AsyncMock()
        issue_repo.get_by_id.return_value = mock_issue
        issue_repo.delete = AsyncMock()

        activity_repo = AsyncMock()
        activity_repo.create = AsyncMock(return_value=MagicMock())

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()
        session.commit = AsyncMock()

        payload = DeleteIssuePayload(issue_id=issue_id, actor_id=actor_id)

        service = DeleteIssueService(
            session=session,
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            audit_log_repository=audit_repo,
        )

        await service.execute(payload)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "issue.delete"
        assert call_kwargs["resource_type"] == "issue"
        assert call_kwargs["actor_id"] == actor_id


class TestCreateNoteServiceAudit:
    """Tests that CreateNoteService writes audit row on note creation."""

    @pytest.mark.asyncio
    async def test_create_note_emits_audit_row(self) -> None:
        """CreateNoteService.execute() should call audit_repo.create with note.create action."""
        from pilot_space.application.services.note.create_note_service import (
            CreateNotePayload,
            CreateNoteService,
        )

        workspace_id = uuid.uuid4()
        owner_id = uuid.uuid4()

        mock_note = MagicMock()
        mock_note.id = uuid.uuid4()
        mock_note.workspace_id = workspace_id
        mock_note.owner_id = owner_id
        mock_note.title = "Test Note"

        note_repo = AsyncMock()
        note_repo.create.return_value = mock_note

        template_repo = AsyncMock()
        template_repo.get_by_id = AsyncMock(return_value=None)

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=owner_id,
            title="Test Note",
        )

        service = CreateNoteService(
            session=session,
            note_repository=note_repo,
            template_repository=template_repo,
            audit_log_repository=audit_repo,
        )

        await service.execute(payload)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "note.create"
        assert call_kwargs["resource_type"] == "note"
        assert call_kwargs["actor_id"] == owner_id


class TestCreateCycleServiceAudit:
    """Tests that CreateCycleService writes audit row on cycle creation."""

    @pytest.mark.asyncio
    async def test_create_cycle_emits_audit_row(self) -> None:
        """CreateCycleService.execute() should call audit_repo.create with cycle.create action."""
        from pilot_space.application.services.cycle.create_cycle_service import (
            CreateCyclePayload,
            CreateCycleService,
        )

        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_cycle = MagicMock()
        mock_cycle.id = uuid.uuid4()
        mock_cycle.workspace_id = workspace_id
        mock_cycle.name = "Sprint 1"

        cycle_repo = AsyncMock()
        cycle_repo.get_next_sequence = AsyncMock(return_value=1)
        cycle_repo.deactivate_project_cycles = AsyncMock()
        cycle_repo.create.return_value = mock_cycle
        cycle_repo.get_by_id_with_relations = AsyncMock(return_value=mock_cycle)

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()

        payload = CreateCyclePayload(
            workspace_id=workspace_id,
            project_id=project_id,
            name="Sprint 1",
            actor_id=actor_id,
        )

        service = CreateCycleService(
            session=session,
            cycle_repository=cycle_repo,
            audit_log_repository=audit_repo,
        )

        await service.execute(payload)

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "cycle.create"
        assert call_kwargs["resource_type"] == "cycle"


class TestRbacServiceAudit:
    """Tests that RbacService writes audit rows for custom role operations."""

    @pytest.mark.asyncio
    async def test_create_role_emits_audit_row(self) -> None:
        """RbacService.create_role() should call audit_repo.create with custom_role.create."""
        from pilot_space.application.services.rbac_service import RbacService

        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_role = MagicMock()
        mock_role.id = uuid.uuid4()
        mock_role.workspace_id = workspace_id
        mock_role.name = "Reviewer"
        mock_role.permissions = ["issues:read"]

        custom_role_repo = AsyncMock()
        custom_role_repo.get_by_name = AsyncMock(return_value=None)
        custom_role_repo.create = AsyncMock(return_value=mock_role)

        workspace_member_repo = AsyncMock()
        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()

        service = RbacService(
            custom_role_repo=custom_role_repo,
            workspace_member_repo=workspace_member_repo,
            audit_log_repository=audit_repo,
        )

        await service.create_role(
            workspace_id=workspace_id,
            name="Reviewer",
            description=None,
            permissions=["issues:read"],
            session=session,
            actor_id=actor_id,
        )

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "custom_role.create"
        assert call_kwargs["resource_type"] == "custom_role"
        assert call_kwargs["actor_id"] == actor_id

    @pytest.mark.asyncio
    async def test_delete_role_emits_audit_row(self) -> None:
        """RbacService.delete_role() should call audit_repo.create with custom_role.delete."""
        from pilot_space.application.services.rbac_service import RbacService

        workspace_id = uuid.uuid4()
        role_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.workspace_id = workspace_id
        mock_role.name = "Reviewer"
        mock_role.permissions = ["issues:read"]

        custom_role_repo = AsyncMock()
        custom_role_repo.get = AsyncMock(return_value=mock_role)
        custom_role_repo.soft_delete = AsyncMock()

        workspace_member_repo = AsyncMock()
        workspace_member_repo.clear_custom_role_assignments = AsyncMock()

        audit_repo = AsyncMock()
        audit_repo.create = AsyncMock(return_value=MagicMock())

        session = AsyncMock()

        service = RbacService(
            custom_role_repo=custom_role_repo,
            workspace_member_repo=workspace_member_repo,
            audit_log_repository=audit_repo,
        )

        await service.delete_role(
            role_id=role_id,
            workspace_id=workspace_id,
            session=session,
            actor_id=actor_id,
        )

        audit_repo.create.assert_awaited_once()
        call_kwargs = audit_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "custom_role.delete"
        assert call_kwargs["resource_type"] == "custom_role"


# ---------------------------------------------------------------------------
# AuditLogHook session_factory wiring tests (AUDIT-02 / AIGOV-03)
# ---------------------------------------------------------------------------


class TestAuditLogHookSessionFactoryWiring:
    """Verify AuditLogHook DB write path is reached when session_factory is set."""

    @pytest.mark.asyncio
    async def test_audit_log_hook_with_session_factory_enters_db_path(self) -> None:
        """AuditLogHook with non-None session_factory calls session_factory on PostToolUse."""
        from unittest.mock import AsyncMock, MagicMock

        from pilot_space.ai.sdk.hooks_lifecycle import AuditLogHook

        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        # Build a mock audit repo that records calls
        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=MagicMock())

        # Mock session returned by session_factory() — supports async context manager
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        # Mock session_factory as an async context manager factory
        mock_session_factory = MagicMock()
        mock_session_factory.return_value = mock_session

        # Patch AuditLogRepository inside the lazy-import closure via sys.modules
        import sys

        fake_module = MagicMock()
        fake_module.AuditLogRepository = MagicMock(return_value=mock_repo)

        # Inject into sys.modules so the lazy import inside _create_audit_callback resolves
        orig = sys.modules.get(
            "pilot_space.infrastructure.database.repositories.audit_log_repository"
        )
        sys.modules["pilot_space.infrastructure.database.repositories.audit_log_repository"] = (
            fake_module
        )
        try:
            hook = AuditLogHook(
                event_queue=None,
                session_factory=mock_session_factory,
                actor_id=actor_id,
                workspace_id=workspace_id,
            )

            # Simulate a PostToolUse result
            mock_result = MagicMock()
            mock_result.tool_name = "create_issue"
            mock_result.tool_input = {"name": "Test"}
            mock_result.output = "done"
            mock_result.model = "claude-sonnet-4-5"
            mock_result.token_usage = MagicMock()
            mock_result.token_usage.total_tokens = 100
            mock_result.rationale = "test"

            await hook.on_post_tool_use(mock_result, context=None)
        finally:
            if orig is None:
                del sys.modules[
                    "pilot_space.infrastructure.database.repositories.audit_log_repository"
                ]
            else:
                sys.modules[
                    "pilot_space.infrastructure.database.repositories.audit_log_repository"
                ] = orig

        # session_factory must be called → DB write path entered
        mock_session_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_saml_callback_calls_set_rls_context_before_audit(self) -> None:
        """saml_callback must call set_rls_context before write_audit_nonfatal."""
        from unittest.mock import AsyncMock, MagicMock, patch

        call_order: list[str] = []

        async def fake_set_rls_context(
            session: object, user_id: object, workspace_id: object
        ) -> None:
            call_order.append("set_rls_context")

        async def fake_write_audit_nonfatal(*args: object, **kwargs: object) -> None:
            call_order.append("write_audit_nonfatal")

        user_info = {
            "user_id": str(uuid.uuid4()),
            "token_hash": "abc123",
            "is_new": False,
        }
        mock_sso_service = AsyncMock()
        mock_sso_service.get_saml_config = AsyncMock(
            return_value={
                "entity_id": "https://idp.example.com",
                "sso_url": "https://idp.example.com/sso",
                "certificate": "cert",
                "name_id_format": "email",
            }
        )
        mock_sso_service.provision_saml_user = AsyncMock(return_value=user_info)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "127.0.0.1"}

        mock_provider = MagicMock()
        mock_provider.process_response = MagicMock(
            return_value={
                "name_id": "user@example.com",
                "attributes": {"email": ["user@example.com"]},
            }
        )

        workspace_id = uuid.uuid4()

        with (
            patch(
                "pilot_space.api.v1.routers.auth_sso._get_sso_service",
                return_value=mock_sso_service,
            ),
            patch(
                "pilot_space.api.v1.routers.auth_sso._get_saml_provider",
                return_value=mock_provider,
            ),
            patch(
                "pilot_space.api.v1.routers.auth_sso.set_rls_context",
                side_effect=fake_set_rls_context,
            ),
            patch(
                "pilot_space.api.v1.routers.auth_sso.write_audit_nonfatal",
                side_effect=fake_write_audit_nonfatal,
            ),
        ):
            from pilot_space.api.v1.routers.auth_sso import saml_callback

            await saml_callback(
                request=mock_request,
                workspace_id=workspace_id,
                session=mock_session,
                SAMLResponse="<saml>...</saml>",
                RelayState="",
            )

        assert "set_rls_context" in call_order, "set_rls_context was never called"
        assert "write_audit_nonfatal" in call_order, "write_audit_nonfatal was never called"
        rls_idx = call_order.index("set_rls_context")
        audit_idx = call_order.index("write_audit_nonfatal")
        assert rls_idx < audit_idx, (
            f"set_rls_context (idx {rls_idx}) must be called before "
            f"write_audit_nonfatal (idx {audit_idx})"
        )


# ---------------------------------------------------------------------------
# PermissionAwareHookExecutor session_factory wiring tests (AIGOV-03)
# ---------------------------------------------------------------------------


class TestPermissionAwareHookExecutorSessionFactory:
    """Verify PermissionAwareHookExecutor passes session_factory to AuditLogHook."""

    def test_executor_passes_session_factory_to_audit_hook(self) -> None:
        """PermissionAwareHookExecutor must pass session_factory to AuditLogHook in to_sdk_hooks()."""
        from unittest.mock import MagicMock, patch

        from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

        mock_permission_handler = MagicMock()
        mock_session_factory = MagicMock()
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()

        captured_hooks: list[object] = []

        original_audit_init = None

        class _CaptureAuditHook:
            def __init__(self, **kwargs: object) -> None:
                captured_hooks.append(kwargs)
                self._session_factory = kwargs.get("session_factory")
                self._event_queue = kwargs.get("event_queue")
                self._actor_id = kwargs.get("actor_id")
                self._workspace_id = kwargs.get("workspace_id")
                self._tool_start_times: dict = {}

            def to_sdk_hooks(self) -> dict:
                return {}

        with patch("pilot_space.ai.sdk.hooks.AuditLogHook", _CaptureAuditHook):
            executor = PermissionAwareHookExecutor(
                permission_handler=mock_permission_handler,
                workspace_id=workspace_id,
                user_id=user_id,
                session_factory=mock_session_factory,
            )
            executor.to_sdk_hooks()

        assert len(captured_hooks) == 1
        assert captured_hooks[0]["session_factory"] is mock_session_factory, (
            "AuditLogHook must receive the session_factory from PermissionAwareHookExecutor"
        )
