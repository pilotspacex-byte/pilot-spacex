"""Repository for workspace hook configuration rules.

Phase 83 -- workspace hooks API. Every read/write for the
``workspace_hook_configs`` table flows through this repository.
The service layer owns the DD-003 invariant guard, pattern validation,
rule limits, and cache invalidation; the repository is a thin
data-access shell.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from pilot_space.infrastructure.database.models.workspace_hook_config import (
    WorkspaceHookConfig,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceHookConfigRepository:
    """CRUD access for ``workspace_hook_configs``.

    All queries filter by ``workspace_id`` and respect RLS policies
    applied by the migration. Priority ordering (ASC) ensures the
    evaluator processes rules in correct precedence order.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_id(self, hook_id: uuid.UUID) -> WorkspaceHookConfig | None:
        """Return a single hook config by primary key, or None."""
        result = await self._session.execute(
            select(WorkspaceHookConfig).where(WorkspaceHookConfig.id == hook_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
    ) -> WorkspaceHookConfig | None:
        """Return the hook config matching ``(workspace_id, name)`` or None."""
        result = await self._session.execute(
            select(WorkspaceHookConfig).where(
                WorkspaceHookConfig.workspace_id == workspace_id,
                WorkspaceHookConfig.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
        *,
        include_disabled: bool = False,
    ) -> list[WorkspaceHookConfig]:
        """Return all hook configs for a workspace, ordered by priority ASC.

        Args:
            workspace_id: Owning workspace.
            include_disabled: If False (default), only return enabled rules.
        """
        stmt = (
            select(WorkspaceHookConfig)
            .where(WorkspaceHookConfig.workspace_id == workspace_id)
            .order_by(WorkspaceHookConfig.priority)
        )
        if not include_disabled:
            stmt = stmt.where(WorkspaceHookConfig.is_enabled.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_enabled_for_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceHookConfig]:
        """Return only enabled rules for a workspace, ordered by priority.

        This is the evaluator hot path -- only enabled rules matter
        at hook evaluation time.
        """
        result = await self._session.execute(
            select(WorkspaceHookConfig)
            .where(
                WorkspaceHookConfig.workspace_id == workspace_id,
                WorkspaceHookConfig.is_enabled.is_(True),
            )
            .order_by(WorkspaceHookConfig.priority)
        )
        return list(result.scalars().all())

    async def count_for_workspace(self, workspace_id: uuid.UUID) -> int:
        """Return total rule count for a workspace (including disabled).

        Used by the service layer to enforce the 50-rule-per-workspace limit.
        """
        result = await self._session.execute(
            select(func.count())
            .select_from(WorkspaceHookConfig)
            .where(WorkspaceHookConfig.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        tool_pattern: str,
        action: str,
        event_type: str,
        priority: int,
        description: str | None,
        created_by: uuid.UUID,
        updated_by: uuid.UUID,
    ) -> WorkspaceHookConfig:
        """Insert a new hook config row.

        Args:
            workspace_id: Owning workspace.
            name: Human-readable rule name (unique per workspace).
            tool_pattern: Glob, regex, or exact match pattern.
            action: One of ``allow`` | ``deny`` | ``require_approval``.
            event_type: Hook event type.
            priority: Evaluation order (lower = higher priority).
            description: Optional description.
            created_by: User who created the rule.
            updated_by: User who last modified the rule.

        Returns:
            The persisted WorkspaceHookConfig row.
        """
        row = WorkspaceHookConfig(
            workspace_id=workspace_id,
            name=name,
            tool_pattern=tool_pattern,
            action=action,
            event_type=event_type,
            priority=priority,
            description=description,
            created_by=created_by,
            updated_by=updated_by,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(
        self,
        hook: WorkspaceHookConfig,
        **kwargs: str | int | bool | uuid.UUID | None,
    ) -> WorkspaceHookConfig:
        """Update mutable fields on an existing hook config.

        Accepted kwargs: name, tool_pattern, action, event_type, priority,
        description, is_enabled, updated_by.

        Returns:
            The updated WorkspaceHookConfig row.
        """
        allowed_fields = {
            "name",
            "tool_pattern",
            "action",
            "event_type",
            "priority",
            "description",
            "is_enabled",
            "updated_by",
        }
        for field, value in kwargs.items():
            if field not in allowed_fields:
                msg = f"Cannot update field: {field}"
                raise ValueError(msg)
            setattr(hook, field, value)
        await self._session.flush()
        return hook

    async def delete(self, hook: WorkspaceHookConfig) -> None:
        """Hard-delete a hook config row."""
        await self._session.delete(hook)
        await self._session.flush()


__all__ = ["WorkspaceHookConfigRepository"]
