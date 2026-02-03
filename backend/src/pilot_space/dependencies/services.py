"""Service layer dependencies.

Provides request-scoped factory functions for domain service instances
(issue services, activity service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.dependencies.auth import get_session

if TYPE_CHECKING:
    from pilot_space.application.services.issue import (
        ActivityService,
        CreateIssueService,
        GetIssueService,
        ListIssuesService,
        UpdateIssueService,
    )


# ============================================================================
# Issue Service Dependencies
# ============================================================================


async def get_create_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreateIssueService:
    """Get CreateIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured CreateIssueService.
    """
    from pilot_space.application.services.issue import CreateIssueService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

    return CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )


async def get_update_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UpdateIssueService:
    """Get UpdateIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured UpdateIssueService.
    """
    from pilot_space.application.services.issue import UpdateIssueService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

    return UpdateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )


async def get_get_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GetIssueService:
    """Get GetIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured GetIssueService.
    """
    from pilot_space.application.services.issue import GetIssueService
    from pilot_space.infrastructure.database.repositories import IssueRepository

    return GetIssueService(
        issue_repository=IssueRepository(session),
    )


async def get_list_issues_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ListIssuesService:
    """Get ListIssuesService instance.

    Args:
        session: Database session.

    Returns:
        Configured ListIssuesService.
    """
    from pilot_space.application.services.issue import ListIssuesService
    from pilot_space.infrastructure.database.repositories import IssueRepository

    return ListIssuesService(
        issue_repository=IssueRepository(session),
    )


async def get_activity_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActivityService:
    """Get ActivityService instance.

    Args:
        session: Database session.

    Returns:
        Configured ActivityService.
    """
    from pilot_space.application.services.issue import ActivityService
    from pilot_space.infrastructure.database.repositories import ActivityRepository

    return ActivityService(
        activity_repository=ActivityRepository(session),
    )
