"""Repository for WorkspaceAIPolicy CRUD operations.

Provides per-role x per-action-type AI approval policy access.
Absence of a row means fall back to hardcoded ApprovalLevel defaults in ApprovalService.

AIGOV-01: WorkspaceAIPolicyRepository — Phase 4 AI Governance.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from pilot_space.infrastructure.database.models.workspace_ai_policy import WorkspaceAIPolicy

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceAIPolicyRepository:
    """CRUD repository for WorkspaceAIPolicy rows.

    Each row overrides the hardcoded ApprovalLevel threshold for a specific
    (workspace_id, role, action_type) triple. Absence of a row means fall back
    to ApprovalService level defaults.

    Usage:
        repo = WorkspaceAIPolicyRepository(session)
        policy = await repo.get(workspace_id, "MEMBER", "extract_issues")
        if policy is not None:
            use(policy.requires_approval)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(
        self,
        workspace_id: uuid.UUID,
        role: str,
        action_type: str,
    ) -> WorkspaceAIPolicy | None:
        """Get policy row for (workspace_id, role, action_type).

        Args:
            workspace_id: Workspace UUID.
            role: Role string (e.g. 'MEMBER', 'ADMIN').
            action_type: Action type string (e.g. 'extract_issues').

        Returns:
            WorkspaceAIPolicy row or None if not configured.
        """
        result = await self._session.execute(
            select(WorkspaceAIPolicy).where(
                WorkspaceAIPolicy.workspace_id == workspace_id,
                WorkspaceAIPolicy.role == role,
                WorkspaceAIPolicy.action_type == action_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        workspace_id: uuid.UUID,
        role: str,
        action_type: str,
        requires_approval: bool,
    ) -> WorkspaceAIPolicy:
        """Create or update a policy row.

        Args:
            workspace_id: Workspace UUID.
            role: Role string.
            action_type: Action type string.
            requires_approval: True to require approval; False to auto-execute.

        Returns:
            Created or updated WorkspaceAIPolicy.
        """
        policy = await self.get(workspace_id, role, action_type)
        if policy is None:
            policy = WorkspaceAIPolicy(
                workspace_id=workspace_id,
                role=role,
                action_type=action_type,
                requires_approval=requires_approval,
            )
            self._session.add(policy)
        else:
            policy.requires_approval = requires_approval
        await self._session.flush()
        return policy

    async def list_for_workspace(self, workspace_id: uuid.UUID) -> list[WorkspaceAIPolicy]:
        """List all policy rows for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of WorkspaceAIPolicy rows (may be empty).
        """
        result = await self._session.execute(
            select(WorkspaceAIPolicy).where(WorkspaceAIPolicy.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def delete(
        self,
        workspace_id: uuid.UUID,
        role: str,
        action_type: str,
    ) -> None:
        """Delete a policy row if it exists.

        Args:
            workspace_id: Workspace UUID.
            role: Role string.
            action_type: Action type string.
        """
        policy = await self.get(workspace_id, role, action_type)
        if policy:
            await self._session.delete(policy)
            await self._session.flush()


__all__ = ["WorkspaceAIPolicyRepository"]
