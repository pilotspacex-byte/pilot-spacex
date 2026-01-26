"""Repository for AI approval requests.

Provides database access for human-in-the-loop approval requests.
Supports filtering by status, workspace, and pagination.

T073: Approval repository for database operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select

from pilot_space.infrastructure.database.models.ai_approval_request import (
    AIApprovalRequest,
    ApprovalStatus,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class ApprovalRepository:
    """Repository for AI approval requests.

    Provides specialized queries for approval workflow:
    - List pending requests for workspace
    - Count pending by workspace
    - Filter by status
    - Update status and resolution fields
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session.
        """
        self.session = session
        self.model_class = AIApprovalRequest

    async def get_by_id(self, approval_id: uuid.UUID) -> AIApprovalRequest | None:
        """Get approval request by ID.

        Args:
            approval_id: Approval request ID.

        Returns:
            Approval request or None.
        """
        query = select(AIApprovalRequest).where(AIApprovalRequest.id == approval_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        *,
        status: ApprovalStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[AIApprovalRequest], int]:
        """List approval requests for a workspace with filtering.

        Args:
            workspace_id: Workspace ID to filter by.
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            Tuple of (requests list, total count).
        """
        # Build base query
        conditions = [AIApprovalRequest.workspace_id == workspace_id]
        if status:
            conditions.append(AIApprovalRequest.status == status)

        # Count query
        count_query = select(func.count()).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Data query
        data_query = (
            select(AIApprovalRequest)
            .where(and_(*conditions))
            .order_by(AIApprovalRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(data_query)
        requests = result.scalars().all()

        return requests, total

    async def count_pending(self, workspace_id: uuid.UUID) -> int:
        """Count pending approval requests for a workspace.

        Args:
            workspace_id: Workspace ID.

        Returns:
            Number of pending requests.
        """
        query = select(func.count()).where(
            and_(
                AIApprovalRequest.workspace_id == workspace_id,
                AIApprovalRequest.status == ApprovalStatus.PENDING,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def resolve(
        self,
        approval_id: uuid.UUID,
        *,
        approved: bool,
        resolved_by: uuid.UUID,
        resolution_note: str | None = None,
    ) -> AIApprovalRequest | None:
        """Resolve an approval request.

        Args:
            approval_id: Request ID to resolve.
            approved: True to approve, False to reject.
            resolved_by: User ID who resolved.
            resolution_note: Optional note.

        Returns:
            Updated request or None if not found.
        """
        request = await self.get_by_id(approval_id)
        if not request:
            return None

        # Update fields
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.resolved_at = datetime.now(UTC)
        request.resolved_by = resolved_by
        request.resolution_note = resolution_note

        await self.session.commit()
        await self.session.refresh(request)

        return request

    async def expire_stale_requests(self, now: datetime) -> int:
        """Mark expired pending requests as expired.

        Args:
            now: Current time to compare against.

        Returns:
            Number of requests expired.
        """
        from sqlalchemy import update

        stmt = (
            update(AIApprovalRequest)
            .where(
                and_(
                    AIApprovalRequest.status == ApprovalStatus.PENDING,
                    AIApprovalRequest.expires_at < now,
                )
            )
            .values(
                status=ApprovalStatus.EXPIRED,
                resolved_at=now,
                resolution_note="Request expired without response",
            )
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount  # type: ignore[return-value]


__all__ = ["ApprovalRepository"]
