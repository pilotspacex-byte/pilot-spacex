"""Tests for AuditLog SQLAlchemy model.

Covers:
- AuditLog instantiation with USER actor fields stored correctly
- AuditLog instantiation with AI actor fields stored correctly
- AuditLog has no soft_delete method (immutable — no SoftDeleteMixin)
- ActorType enum values are UPPERCASE strings
- AuditLog has correct composite indexes defined

Requirements: AUDIT-01
"""

from __future__ import annotations

import uuid

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog


class TestAuditLogInstantiation:
    """Tests for AuditLog model field storage."""

    def test_create_with_user_actor(self) -> None:
        """AuditLog created with USER actor stores all fields correctly."""
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=ActorType.USER,
            action="issue.create",
            resource_type="issue",
            resource_id=resource_id,
            payload={"before": {}, "after": {"name": "Test Issue"}},
            ip_address="10.0.0.1",
        )

        assert row.workspace_id == workspace_id
        assert row.actor_id == actor_id
        assert row.actor_type == ActorType.USER
        assert row.action == "issue.create"
        assert row.resource_type == "issue"
        assert row.resource_id == resource_id
        assert row.payload == {"before": {}, "after": {"name": "Test Issue"}}
        assert row.ip_address == "10.0.0.1"

    def test_create_with_ai_actor(self) -> None:
        """AuditLog created with AI actor stores ai_* fields correctly."""
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=ActorType.AI,
            action="issue.ai_enhanced",
            resource_type="issue",
            resource_id=uuid.uuid4(),
            payload={"before": {}, "after": {}},
            ai_input={"prompt": "enhance this issue"},
            ai_output={"enhanced_description": "Better description"},
            ai_model="claude-sonnet-4-5",
            ai_token_cost=250,
            ai_rationale="Enhanced clarity and completeness",
        )

        assert row.actor_type == ActorType.AI
        assert row.ai_input == {"prompt": "enhance this issue"}
        assert row.ai_output == {"enhanced_description": "Better description"}
        assert row.ai_model == "claude-sonnet-4-5"
        assert row.ai_token_cost == 250
        assert row.ai_rationale == "Enhanced clarity and completeness"

    def test_create_with_system_actor_null_actor_id(self) -> None:
        """AuditLog created with SYSTEM actor can have NULL actor_id."""
        row = AuditLog(
            workspace_id=uuid.uuid4(),
            actor_id=None,
            actor_type=ActorType.SYSTEM,
            action="workspace_setting.retention_updated",
            resource_type="workspace_setting",
            resource_id=None,
            payload={"before": {"retention_days": 90}, "after": {"retention_days": 30}},
        )

        assert row.actor_id is None
        assert row.actor_type == ActorType.SYSTEM
        assert row.resource_id is None

    def test_no_soft_delete_method(self) -> None:
        """AuditLog must not have soft_delete — it is immutable, not soft-deletable."""
        row = AuditLog(
            workspace_id=uuid.uuid4(),
            actor_id=None,
            actor_type=ActorType.SYSTEM,
            action="test.action",
            resource_type="test",
        )

        assert not hasattr(row, "soft_delete"), (
            "AuditLog should not have soft_delete — it must not inherit SoftDeleteMixin"
        )
        assert not hasattr(row, "is_deleted"), (
            "AuditLog should not have is_deleted — SoftDeleteMixin must not be inherited"
        )
        assert not hasattr(row, "deleted_at"), (
            "AuditLog should not have deleted_at — SoftDeleteMixin must not be inherited"
        )


class TestActorTypeEnum:
    """Tests for the ActorType enum."""

    def test_actor_type_user_is_uppercase_string(self) -> None:
        """ActorType.USER value must be 'USER' (uppercase)."""
        assert ActorType.USER.value == "USER"

    def test_actor_type_system_is_uppercase_string(self) -> None:
        """ActorType.SYSTEM value must be 'SYSTEM' (uppercase)."""
        assert ActorType.SYSTEM.value == "SYSTEM"

    def test_actor_type_ai_is_uppercase_string(self) -> None:
        """ActorType.AI value must be 'AI' (uppercase)."""
        assert ActorType.AI.value == "AI"

    def test_actor_type_is_str_enum(self) -> None:
        """ActorType values must be strings (str Enum)."""
        assert isinstance(ActorType.USER.value, str)
        assert isinstance(ActorType.SYSTEM.value, str)
        assert isinstance(ActorType.AI.value, str)


class TestAuditLogTableStructure:
    """Tests for AuditLog table-level structure."""

    def test_tablename_is_audit_log(self) -> None:
        """AuditLog table must be named 'audit_log' (not 'audit_logs')."""
        assert AuditLog.__tablename__ == "audit_log"

    def test_composite_indexes_defined(self) -> None:
        """AuditLog must define composite indexes for workspace-scoped queries."""
        index_names = {idx.name for idx in AuditLog.__table_args__}
        assert "ix_audit_log_workspace_created" in index_names
        assert "ix_audit_log_workspace_actor" in index_names
        assert "ix_audit_log_workspace_action" in index_names
        assert "ix_audit_log_workspace_resource_type" in index_names

    def test_repr_includes_action_and_actor_type(self) -> None:
        """AuditLog.__repr__ should include action and actor_type for debugging."""
        row = AuditLog(
            workspace_id=uuid.uuid4(),
            actor_type=ActorType.USER,
            action="issue.create",
            resource_type="issue",
        )
        r = repr(row)
        assert "issue.create" in r
        assert "USER" in r
