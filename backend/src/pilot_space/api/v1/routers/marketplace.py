"""Marketplace REST API endpoints.

REST API for workspace-scoped marketplace operations:
- GET    /{workspace_id}/marketplace/listings            -> search/browse (200)
- GET    /{workspace_id}/marketplace/listings/{id}       -> detail (200)
- POST   /{workspace_id}/marketplace/listings            -> publish (201)
- POST   /{workspace_id}/marketplace/listings/{id}/versions   -> new version (201)
- GET    /{workspace_id}/marketplace/listings/{id}/versions   -> version history (200)
- POST   /{workspace_id}/marketplace/listings/{id}/install    -> install (201/200)
- POST   /{workspace_id}/marketplace/listings/{id}/reviews    -> create/update review (200)
- GET    /{workspace_id}/marketplace/listings/{id}/reviews    -> list reviews (200)
- GET    /{workspace_id}/marketplace/updates              -> check updates (200)
- POST   /{workspace_id}/marketplace/installed/{id}/update -> apply update (200)

Source: Phase 054, P54-04
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from pilot_space.api.v1.dependencies import (
    MarketplaceInstallServiceDep,
    MarketplaceReviewServiceDep,
    MarketplaceServiceDep,
)
from pilot_space.api.v1.schemas.marketplace import (
    InstallResponse,
    MarketplaceListingCreate,
    MarketplaceListingResponse,
    MarketplaceSearchResponse,
    MarketplaceVersionCreate,
    MarketplaceVersionResponse,
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewResponse,
    UpdateApplyResponse,
    UpdateCheckResponse,
)
from pilot_space.application.services.skill.marketplace_install_service import (
    InstallPayload,
)
from pilot_space.application.services.skill.marketplace_review_service import (
    ReviewPayload,
)
from pilot_space.application.services.skill.marketplace_service import (
    CreateVersionPayload,
    PublishListingPayload,
    SearchPayload,
)
from pilot_space.dependencies import CurrentUserId, DbSession, WorkspaceAdminId, WorkspaceMemberId
from pilot_space.infrastructure.database.rls import set_rls_context

router = APIRouter(
    prefix="/{workspace_id}/marketplace",
    tags=["Marketplace"],
)


# ---------------------------------------------------------------------------
# 1. GET /listings -- Search/browse marketplace listings
# ---------------------------------------------------------------------------


@router.get(
    "/listings",
    response_model=MarketplaceSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search marketplace listings",
)
async def search_listings(
    workspace_id: WorkspaceMemberId,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceServiceDep,
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=1, le=5),
    sort: str = Query(default="popular"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MarketplaceSearchResponse:
    """Search and browse marketplace listings with optional filters."""
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.search(
        SearchPayload(
            query=query,
            category=category,
            min_rating=min_rating,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    )
    return MarketplaceSearchResponse(
        items=[MarketplaceListingResponse.model_validate(item) for item in result.items],
        total=result.total,
        has_next=result.has_next,
    )


# ---------------------------------------------------------------------------
# 2. GET /listings/{listing_id} -- Listing detail
# ---------------------------------------------------------------------------


@router.get(
    "/listings/{listing_id}",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get marketplace listing detail",
)
async def get_listing(
    workspace_id: WorkspaceMemberId,
    listing_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceServiceDep,
) -> MarketplaceListingResponse:
    """Get a single marketplace listing by ID."""
    await set_rls_context(session, current_user_id, workspace_id)
    listing = await service.get_listing(listing_id)
    return MarketplaceListingResponse.model_validate(listing)


# ---------------------------------------------------------------------------
# 3. POST /listings -- Publish a skill to marketplace (admin only)
# ---------------------------------------------------------------------------


@router.post(
    "/listings",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a skill to marketplace",
)
async def publish_listing(
    workspace_id: WorkspaceAdminId,
    body: MarketplaceListingCreate,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceServiceDep,
    skill_template_id: UUID = Query(...),
) -> MarketplaceListingResponse:
    """Publish a workspace skill template to the marketplace."""
    await set_rls_context(session, current_user_id, workspace_id)
    listing = await service.publish_listing(
        PublishListingPayload(
            workspace_id=workspace_id,
            skill_template_id=skill_template_id,
            user_id=current_user_id,
            name=body.name,
            description=body.description,
            author=body.author,
            category=body.category,
            version=body.version,
            long_description=body.long_description,
            icon=body.icon,
            tags=body.tags,
            screenshots=body.screenshots,
            graph_data=body.graph_data,
        )
    )
    return MarketplaceListingResponse.model_validate(listing)


# ---------------------------------------------------------------------------
# 4. POST /listings/{listing_id}/versions -- Create new version (admin only)
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/versions",
    response_model=MarketplaceVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new version for a listing",
)
async def create_version(
    workspace_id: WorkspaceAdminId,
    listing_id: UUID,
    body: MarketplaceVersionCreate,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceServiceDep,
) -> MarketplaceVersionResponse:
    """Create a new version for an existing marketplace listing."""
    await set_rls_context(session, current_user_id, workspace_id)
    version = await service.create_version(
        CreateVersionPayload(
            workspace_id=workspace_id,
            listing_id=listing_id,
            version=body.version,
            skill_content=body.skill_content,
            changelog=body.changelog,
            graph_data=body.graph_data,
        )
    )
    return MarketplaceVersionResponse.model_validate(version)


# ---------------------------------------------------------------------------
# 5. GET /listings/{listing_id}/versions -- Version history
# ---------------------------------------------------------------------------


@router.get(
    "/listings/{listing_id}/versions",
    response_model=list[MarketplaceVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get version history for a listing",
)
async def get_versions(
    workspace_id: WorkspaceMemberId,
    listing_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceServiceDep,
) -> list[MarketplaceVersionResponse]:
    """Get all versions of a marketplace listing."""
    await set_rls_context(session, current_user_id, workspace_id)
    versions = await service.get_versions(listing_id)
    return [MarketplaceVersionResponse.model_validate(v) for v in versions]


# ---------------------------------------------------------------------------
# 6. POST /listings/{listing_id}/install -- Install to workspace
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/install",
    response_model=InstallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install a marketplace listing",
)
async def install_listing(
    workspace_id: WorkspaceMemberId,
    listing_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceInstallServiceDep,
) -> InstallResponse:
    """Install a marketplace listing into the workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.install(
        InstallPayload(
            workspace_id=workspace_id,
            listing_id=listing_id,
            user_id=current_user_id,
        )
    )
    return InstallResponse(
        skill_template_id=result.skill_template.id,
        already_installed=result.already_installed,
    )


# ---------------------------------------------------------------------------
# 7. POST /listings/{listing_id}/reviews -- Create/update review
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update a review",
)
async def create_or_update_review(
    workspace_id: WorkspaceMemberId,
    listing_id: UUID,
    body: ReviewCreateRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceReviewServiceDep,
) -> ReviewResponse:
    """Create or update the current user's review for a listing."""
    await set_rls_context(session, current_user_id, workspace_id)
    review = await service.create_or_update(
        ReviewPayload(
            workspace_id=workspace_id,
            listing_id=listing_id,
            user_id=current_user_id,
            rating=body.rating,
            review_text=body.review_text,
        )
    )
    return ReviewResponse.model_validate(review)


# ---------------------------------------------------------------------------
# 8. GET /listings/{listing_id}/reviews -- List reviews
# ---------------------------------------------------------------------------


@router.get(
    "/listings/{listing_id}/reviews",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reviews for a listing",
)
async def list_reviews(
    workspace_id: WorkspaceMemberId,
    listing_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceReviewServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReviewListResponse:
    """List reviews for a marketplace listing with pagination."""
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.list_reviews(listing_id, limit=limit, offset=offset)
    return ReviewListResponse(
        items=[ReviewResponse.model_validate(r) for r in result.items],
        total=result.total,
        has_next=result.has_next,
    )


# ---------------------------------------------------------------------------
# 9. GET /updates -- Check for available updates
# ---------------------------------------------------------------------------


@router.get(
    "/updates",
    response_model=list[UpdateCheckResponse],
    status_code=status.HTTP_200_OK,
    summary="Check for available updates",
)
async def check_updates(
    workspace_id: WorkspaceMemberId,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceInstallServiceDep,
) -> list[UpdateCheckResponse]:
    """Check for available updates on installed marketplace templates."""
    await set_rls_context(session, current_user_id, workspace_id)
    results = await service.check_updates(workspace_id)
    return [
        UpdateCheckResponse(
            template_id=r.template_id,
            template_name=r.template_name,
            installed_version=r.installed_version,
            available_version=r.available_version,
            listing_id=r.listing_id,
        )
        for r in results
    ]


# ---------------------------------------------------------------------------
# 10. POST /installed/{template_id}/update -- Apply update
# ---------------------------------------------------------------------------


@router.post(
    "/installed/{template_id}/update",
    response_model=UpdateApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply an update to an installed template",
)
async def apply_update(
    workspace_id: WorkspaceMemberId,
    template_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
    service: MarketplaceInstallServiceDep,
) -> UpdateApplyResponse:
    """Update an installed marketplace template to the latest version."""
    await set_rls_context(session, current_user_id, workspace_id)
    updated_template = await service.update_installed(workspace_id, template_id)
    return UpdateApplyResponse(
        updated=True,
        new_version=updated_template.installed_version or "0.0.0",
        template_id=updated_template.id,
    )


__all__ = ["router"]
