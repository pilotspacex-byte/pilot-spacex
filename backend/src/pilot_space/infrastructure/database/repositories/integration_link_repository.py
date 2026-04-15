"""IntegrationLink repository for commit/PR/branch linking.

T176: Create IntegrationLinkRepository for issue linking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models import (
    IntegrationLink,
    IntegrationLinkType,
)
from pilot_space.infrastructure.database.repositories.base import (
    BaseRepository,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class IntegrationLinkRepository(BaseRepository[IntegrationLink]):
    """Repository for IntegrationLink entities.

    Provides:
    - Issue-scoped queries for linked commits/PRs
    - External ID lookups for idempotent linking
    - Batch operations for sync
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, IntegrationLink)

    async def get_by_issue(
        self,
        issue_id: UUID,
        *,
        link_type: IntegrationLinkType | None = None,
        include_deleted: bool = False,
    ) -> Sequence[IntegrationLink]:
        """Get all links for an issue.

        Args:
            issue_id: Issue UUID.
            link_type: Filter by link type (optional).
            include_deleted: Whether to include soft-deleted links.

        Returns:
            List of integration links for the issue.
        """
        conditions: list[Any] = [IntegrationLink.issue_id == issue_id]

        if not include_deleted:
            conditions.append(IntegrationLink.is_deleted == False)  # noqa: E712
        if link_type:
            conditions.append(IntegrationLink.link_type == link_type)

        query = (
            select(IntegrationLink)
            .where(and_(*conditions))
            .options(joinedload(IntegrationLink.integration))
            .order_by(IntegrationLink.created_at.desc())
        )

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_by_external_id(
        self,
        integration_id: UUID,
        external_id: str,
        link_type: IntegrationLinkType,
    ) -> IntegrationLink | None:
        """Get link by external ID for idempotency check.

        Args:
            integration_id: Integration UUID.
            external_id: External ID (commit SHA, PR number).
            link_type: Type of link.

        Returns:
            IntegrationLink if exists, None otherwise.
        """
        query = select(IntegrationLink).where(
            and_(
                IntegrationLink.integration_id == integration_id,
                IntegrationLink.external_id == external_id,
                IntegrationLink.link_type == link_type,
                IntegrationLink.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_integration(
        self,
        integration_id: UUID,
        *,
        link_type: IntegrationLinkType | None = None,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> Sequence[IntegrationLink]:
        """Get all links for an integration.

        Args:
            integration_id: Integration UUID.
            link_type: Filter by link type (optional).
            limit: Maximum number of links to return.
            include_deleted: Whether to include soft-deleted links.

        Returns:
            List of integration links.
        """
        conditions: list[Any] = [IntegrationLink.integration_id == integration_id]

        if not include_deleted:
            conditions.append(IntegrationLink.is_deleted == False)  # noqa: E712
        if link_type:
            conditions.append(IntegrationLink.link_type == link_type)

        query = (
            select(IntegrationLink)
            .where(and_(*conditions))
            .options(joinedload(IntegrationLink.issue))
            .order_by(IntegrationLink.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def create_if_not_exists(
        self,
        link: IntegrationLink,
    ) -> tuple[IntegrationLink, bool]:
        """Create link if it doesn't already exist.

        Uses upsert semantics to avoid duplicates.

        Args:
            link: IntegrationLink to create.

        Returns:
            Tuple of (IntegrationLink, created) where created is True
            if the link was created, False if it already existed.
        """
        # Check for existing link
        existing = await self.get_by_external_id(
            integration_id=link.integration_id,
            external_id=link.external_id,
            link_type=link.link_type,
        )

        if existing:
            # Update link_metadata if changed
            if link.link_metadata != existing.link_metadata:
                existing.link_metadata = link.link_metadata
                existing.title = link.title
                existing.author_name = link.author_name
                existing.author_avatar_url = link.author_avatar_url
                await self.session.flush()
                await self.session.refresh(existing)
            return existing, False

        # Create new link
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        return link, True

    async def batch_create(
        self,
        links: Sequence[IntegrationLink],
    ) -> list[tuple[IntegrationLink, bool]]:
        """Create multiple links with idempotency check.

        Args:
            links: List of IntegrationLinks to create.

        Returns:
            List of tuples (IntegrationLink, created).
        """
        results: list[tuple[IntegrationLink, bool]] = []
        for link in links:
            result = await self.create_if_not_exists(link)
            results.append(result)
        return results

    async def get_commits_for_issue(
        self,
        issue_id: UUID,
    ) -> Sequence[IntegrationLink]:
        """Get commit links for an issue.

        Args:
            issue_id: Issue UUID.

        Returns:
            List of commit links.
        """
        return await self.get_by_issue(
            issue_id,
            link_type=IntegrationLinkType.COMMIT,
        )

    async def get_pull_requests_for_issue(
        self,
        issue_id: UUID,
    ) -> Sequence[IntegrationLink]:
        """Get PR links for an issue.

        Args:
            issue_id: Issue UUID.

        Returns:
            List of PR links.
        """
        return await self.get_by_issue(
            issue_id,
            link_type=IntegrationLinkType.PULL_REQUEST,
        )

    async def get_pull_requests_for_issues(
        self,
        issue_ids: list[UUID],
        workspace_id: UUID,
    ) -> Sequence[IntegrationLink]:
        """Get PR links for multiple issues in one query.

        Args:
            issue_ids: List of issue UUIDs to query.
            workspace_id: Workspace scope for RLS.

        Returns:
            List of PR-type integration links.
        """
        if not issue_ids:
            return []
        stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id.in_(issue_ids),
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.link_type == IntegrationLinkType.PULL_REQUEST,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_issue_in_workspace(
        self,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[IntegrationLink]:
        """Get integration links for a single issue within a workspace."""
        stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id == issue_id,
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_project_issues(
        self,
        project_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[IntegrationLink]:
        """Get integration links for all issues belonging to a project."""
        from pilot_space.infrastructure.database.models.issue import Issue as IssueModel

        stmt = select(IntegrationLink).where(
            IntegrationLink.issue_id.in_(
                select(IssueModel.id).where(
                    IssueModel.project_id == project_id,
                    IssueModel.workspace_id == workspace_id,
                    IssueModel.is_deleted == False,  # noqa: E712
                )
            ),
            IntegrationLink.workspace_id == workspace_id,
            IntegrationLink.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_issue(
        self,
        issue_id: UUID,
    ) -> dict[IntegrationLinkType, int]:
        """Count links by type for an issue.

        Args:
            issue_id: Issue UUID.

        Returns:
            Dict mapping link type to count.
        """
        from sqlalchemy import func

        query = (
            select(
                IntegrationLink.link_type,
                func.count(IntegrationLink.id).label("count"),
            )
            .where(
                and_(
                    IntegrationLink.issue_id == issue_id,
                    IntegrationLink.is_deleted == False,  # noqa: E712
                )
            )
            .group_by(IntegrationLink.link_type)
        )

        result = await self.session.execute(query)
        rows = result.all()

        # Use index access to get the count value (second column)
        # row[0] is link_type, row[1] is the count
        return {row[0]: int(row[1]) for row in rows}


__all__ = ["IntegrationLinkRepository"]
