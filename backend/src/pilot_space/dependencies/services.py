"""Service layer dependencies.

Provides request-scoped factory functions for domain service instances
(issue services, activity service, attachment upload service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.dependencies.auth import get_session

if TYPE_CHECKING:
    from pilot_space.application.services.ai.attachment_upload_service import (
        AttachmentUploadService,
    )
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


# ============================================================================
# Attachment Service Dependencies
# ============================================================================


async def get_attachment_upload_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AttachmentUploadService:
    """Get AttachmentUploadService instance.

    Args:
        request: FastAPI request (used to access the DI container).
        session: Database session.

    Returns:
        Configured AttachmentUploadService.
    """
    from pilot_space.application.services.ai.attachment_upload_service import (
        AttachmentUploadService,
    )
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )

    return AttachmentUploadService(
        session=session,
        storage_client=request.app.state.container.storage_client(),
        attachment_repo=ChatAttachmentRepository(session),
    )


AttachmentUploadServiceDep = Annotated[
    "AttachmentUploadService", Depends(get_attachment_upload_service)
]


async def get_chat_attachment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatAttachmentRepository:
    """Get ChatAttachmentRepository instance.

    Args:
        session: Database session.

    Returns:
        Configured ChatAttachmentRepository.
    """
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )

    return ChatAttachmentRepository(session)


if TYPE_CHECKING:
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )

ChatAttachmentRepositoryDep = Annotated[
    "ChatAttachmentRepository", Depends(get_chat_attachment_repository)
]


# ============================================================================
# Drive Service Dependencies
# ============================================================================


async def get_drive_oauth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> DriveOAuthService:
    """Get DriveOAuthService instance.

    Args:
        session: Database session.
        request: FastAPI request for accessing Redis from app state.

    Returns:
        Configured DriveOAuthService with optional Redis for PKCE state.
    """
    from pilot_space.application.services.ai.drive_oauth_service import DriveOAuthService
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
        DriveCredentialRepository,
    )

    redis_client = None
    if hasattr(request.app.state, "container"):
        container = request.app.state.container
        redis_client = container.redis_client()

    return DriveOAuthService(
        credential_repo=DriveCredentialRepository(session),
        settings=get_settings(),
        redis_client=redis_client,
    )


async def get_drive_file_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> DriveFileService:
    """Get DriveFileService instance.

    Args:
        session: Database session.
        request: FastAPI request for accessing Redis from app state.

    Returns:
        Configured DriveFileService with injected DriveOAuthService for token refresh.
    """
    from pilot_space.application.services.ai.drive_file_service import DriveFileService
    from pilot_space.application.services.ai.drive_oauth_service import DriveOAuthService
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )
    from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
        DriveCredentialRepository,
    )

    settings = get_settings()
    credential_repo = DriveCredentialRepository(session)

    container = request.app.state.container
    redis_client = container.redis_client()
    storage_client = container.storage_client()

    oauth_service = DriveOAuthService(
        credential_repo=credential_repo,
        settings=settings,
        redis_client=redis_client,
    )

    return DriveFileService(
        credential_repo=credential_repo,
        attachment_repo=ChatAttachmentRepository(session),
        storage_client=storage_client,
        settings=settings,
        oauth_service=oauth_service,
    )


if TYPE_CHECKING:
    from pilot_space.application.services.ai.drive_file_service import DriveFileService
    from pilot_space.application.services.ai.drive_oauth_service import DriveOAuthService

DriveOAuthServiceDep = Annotated["DriveOAuthService", Depends(get_drive_oauth_service)]
DriveFileServiceDep = Annotated["DriveFileService", Depends(get_drive_file_service)]
