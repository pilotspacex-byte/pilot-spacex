"""Unit tests for MarketplaceReviewService.

Tests review creation (upsert), rating aggregation, pagination,
and ownership-checked deletion.

Source: Phase 54, P54-03
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.skill.marketplace_review_service import (
    MarketplaceReviewService,
    ReviewListResult,
    ReviewPayload,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(session: AsyncMock) -> MarketplaceReviewService:
    return MarketplaceReviewService(session=session)


# --- create_or_update ---


@pytest.mark.asyncio
async def test_create_review_new_creates_and_updates_avg(
    service: MarketplaceReviewService,
) -> None:
    """New review: creates review, recalculates avg_rating, updates listing."""
    payload = ReviewPayload(
        workspace_id=uuid4(),
        listing_id=uuid4(),
        user_id=uuid4(),
        rating=4,
        review_text="Great skill!",
    )
    mock_listing = MagicMock()
    mock_review = MagicMock()

    with (
        patch.object(
            service._listing_repo,
            "get_by_id",
            return_value=mock_listing,
        ) as mock_get_listing,
        patch.object(
            service._review_repo,
            "get_by_user_and_listing",
            return_value=None,
        ) as mock_get_existing,
        patch.object(
            service._review_repo,
            "create",
            return_value=mock_review,
        ) as mock_create,
        patch.object(
            service._review_repo,
            "get_avg_rating",
            return_value=4.0,
        ) as mock_avg,
        patch.object(
            service._listing_repo,
            "update_avg_rating",
        ) as mock_update_avg,
    ):
        result = await service.create_or_update(payload)

    assert result is mock_review
    mock_get_listing.assert_awaited_once_with(payload.listing_id)
    mock_get_existing.assert_awaited_once_with(payload.user_id, payload.listing_id)
    mock_create.assert_awaited_once_with(
        workspace_id=payload.workspace_id,
        listing_id=payload.listing_id,
        user_id=payload.user_id,
        rating=4,
        review_text="Great skill!",
    )
    mock_avg.assert_awaited_once_with(payload.listing_id)
    mock_update_avg.assert_awaited_once_with(payload.listing_id, 4.0)


@pytest.mark.asyncio
async def test_create_review_existing_updates_in_place(
    service: MarketplaceReviewService,
) -> None:
    """Existing review: updates rating and text, recalculates avg."""
    payload = ReviewPayload(
        workspace_id=uuid4(),
        listing_id=uuid4(),
        user_id=uuid4(),
        rating=5,
        review_text="Updated review",
    )
    existing_review = MagicMock()
    existing_review.rating = 3
    existing_review.review_text = "Old review"

    mock_listing = MagicMock()

    with (
        patch.object(
            service._listing_repo,
            "get_by_id",
            return_value=mock_listing,
        ),
        patch.object(
            service._review_repo,
            "get_by_user_and_listing",
            return_value=existing_review,
        ),
        patch.object(
            service._review_repo,
            "update",
            return_value=existing_review,
        ) as mock_update,
        patch.object(
            service._review_repo,
            "get_avg_rating",
            return_value=4.5,
        ),
        patch.object(
            service._listing_repo,
            "update_avg_rating",
        ),
    ):
        result = await service.create_or_update(payload)

    assert result is existing_review
    assert existing_review.rating == 5
    assert existing_review.review_text == "Updated review"
    mock_update.assert_awaited_once_with(existing_review)


@pytest.mark.asyncio
async def test_create_review_invalid_rating_raises_validation_error(
    service: MarketplaceReviewService,
) -> None:
    """Rating outside 1-5 raises ValidationError."""
    for bad_rating in [0, 6, -1, 100]:
        payload = ReviewPayload(
            workspace_id=uuid4(),
            listing_id=uuid4(),
            user_id=uuid4(),
            rating=bad_rating,
        )
        with pytest.raises(ValidationError, match="[Rr]ating"):
            await service.create_or_update(payload)


@pytest.mark.asyncio
async def test_create_review_listing_not_found_raises(
    service: MarketplaceReviewService,
) -> None:
    """Non-existent listing raises NotFoundError."""
    payload = ReviewPayload(
        workspace_id=uuid4(),
        listing_id=uuid4(),
        user_id=uuid4(),
        rating=3,
    )
    with patch.object(
        service._listing_repo,
        "get_by_id",
        return_value=None,
    ):
        with pytest.raises(NotFoundError, match="[Ll]isting"):
            await service.create_or_update(payload)


# --- list_reviews ---


@pytest.mark.asyncio
async def test_list_reviews_pagination_has_next(
    service: MarketplaceReviewService,
) -> None:
    """list_reviews detects has_next by fetching limit+1 items."""
    listing_id = uuid4()
    # Return limit+1 items to signal has_next=True
    mock_reviews = [MagicMock() for _ in range(6)]

    with patch.object(
        service._review_repo,
        "get_by_listing",
        return_value=mock_reviews,
    ) as mock_get:
        result = await service.list_reviews(listing_id, limit=5, offset=0)

    assert isinstance(result, ReviewListResult)
    assert len(result.items) == 5
    assert result.has_next is True
    mock_get.assert_awaited_once_with(listing_id, limit=6, offset=0)

    # Return exactly limit items -> has_next=False
    mock_reviews_exact = [MagicMock() for _ in range(5)]
    with patch.object(
        service._review_repo,
        "get_by_listing",
        return_value=mock_reviews_exact,
    ):
        result2 = await service.list_reviews(listing_id, limit=5, offset=0)

    assert len(result2.items) == 5
    assert result2.has_next is False


# --- delete_review ---


@pytest.mark.asyncio
async def test_delete_review_wrong_user_raises_forbidden(
    service: MarketplaceReviewService,
) -> None:
    """Deleting someone else's review raises ForbiddenError."""
    review_id = uuid4()
    owner_id = uuid4()
    other_user_id = uuid4()

    mock_review = MagicMock()
    mock_review.user_id = owner_id
    mock_review.listing_id = uuid4()

    with patch.object(
        service._review_repo,
        "get_by_id",
        return_value=mock_review,
    ):
        with pytest.raises(ForbiddenError):
            await service.delete_review(review_id, other_user_id)


@pytest.mark.asyncio
async def test_delete_review_success(
    service: MarketplaceReviewService,
) -> None:
    """Successful delete: soft-deletes and recalculates avg."""
    review_id = uuid4()
    user_id = uuid4()
    listing_id = uuid4()

    mock_review = MagicMock()
    mock_review.user_id = user_id
    mock_review.listing_id = listing_id

    with (
        patch.object(
            service._review_repo,
            "get_by_id",
            return_value=mock_review,
        ),
        patch.object(
            service._review_repo,
            "update",
            return_value=mock_review,
        ) as mock_update,
        patch.object(
            service._review_repo,
            "get_avg_rating",
            return_value=3.5,
        ),
        patch.object(
            service._listing_repo,
            "update_avg_rating",
        ) as mock_update_avg,
    ):
        await service.delete_review(review_id, user_id)

    mock_review.soft_delete.assert_called_once()
    mock_update.assert_awaited_once_with(mock_review)
    mock_update_avg.assert_awaited_once_with(listing_id, 3.5)
