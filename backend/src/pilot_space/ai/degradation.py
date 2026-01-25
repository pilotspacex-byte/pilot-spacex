"""Graceful degradation for AI features.

Provides fallback behavior when AI providers are unavailable,
ensuring the application remains functional without AI.

T091d: Graceful degradation for AI features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DegradationLevel(Enum):
    """Levels of AI service degradation.

    Attributes:
        FULL: AI services fully available.
        PARTIAL: Some AI features limited.
        DISABLED: AI features disabled, fallbacks active.
    """

    FULL = "full"
    PARTIAL = "partial"
    DISABLED = "disabled"


@dataclass
class DegradedResponse(Generic[T]):
    """Response wrapper indicating degradation status.

    Attributes:
        data: The response data (may be fallback).
        degraded: Whether fallback was used.
        level: Current degradation level.
        message: User-facing message about degradation.
        original_error: The error that triggered degradation.
    """

    data: T
    degraded: bool = False
    level: DegradationLevel = DegradationLevel.FULL
    message: str | None = None
    original_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response.

        Returns:
            Dictionary with degradation metadata.
        """
        result: dict[str, Any] = {
            "degraded": self.degraded,
            "degradation_level": self.level.value,
        }
        if self.message:
            result["message"] = self.message
        return result


class GhostTextFallback:
    """Fallback behavior for ghost text suggestions.

    When AI is unavailable, ghost text gracefully degrades by:
    - Returning empty suggestion with status message
    - Not disrupting user's typing experience
    """

    UNAVAILABLE_MESSAGE = "AI suggestions temporarily unavailable"
    RATE_LIMITED_MESSAGE = "AI suggestions rate limited, please wait"

    @classmethod
    def empty_suggestion(
        cls,
        *,
        rate_limited: bool = False,
        error_message: str | None = None,
    ) -> DegradedResponse[dict[str, Any]]:
        """Return empty ghost text suggestion.

        Args:
            rate_limited: Whether this is due to rate limiting.
            error_message: Original error message for logging.

        Returns:
            DegradedResponse with empty suggestion.
        """
        message = cls.RATE_LIMITED_MESSAGE if rate_limited else cls.UNAVAILABLE_MESSAGE

        logger.info(
            "Ghost text degraded to empty suggestion",
            extra={
                "rate_limited": rate_limited,
                "original_error": error_message,
            },
        )

        return DegradedResponse(
            data={
                "suggestion": "",
                "cursor_position": None,
                "metadata": {"degraded": True},
            },
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=message,
            original_error=error_message,
        )


class MarginAnnotationFallback:
    """Fallback behavior for margin annotations.

    When AI is unavailable, margin annotations gracefully degrade by:
    - Hiding the annotation panel entirely
    - Preserving existing annotations
    - Showing status indicator
    """

    UNAVAILABLE_MESSAGE = "AI analysis temporarily unavailable"

    @classmethod
    def hidden_panel(
        cls,
        *,
        preserve_existing: bool = True,
        error_message: str | None = None,
    ) -> DegradedResponse[dict[str, Any]]:
        """Return hidden panel response.

        Args:
            preserve_existing: Whether to keep existing annotations visible.
            error_message: Original error message for logging.

        Returns:
            DegradedResponse indicating panel should be hidden.
        """
        logger.info(
            "Margin annotations degraded to hidden panel",
            extra={
                "preserve_existing": preserve_existing,
                "original_error": error_message,
            },
        )

        return DegradedResponse(
            data={
                "annotations": [],
                "panel_visible": False,
                "preserve_existing": preserve_existing,
                "metadata": {"degraded": True},
            },
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=cls.UNAVAILABLE_MESSAGE,
            original_error=error_message,
        )

    @classmethod
    def empty_annotations(
        cls,
        *,
        error_message: str | None = None,
    ) -> DegradedResponse[list[Any]]:
        """Return empty annotation list.

        Args:
            error_message: Original error message for logging.

        Returns:
            DegradedResponse with empty list.
        """
        return DegradedResponse(
            data=[],
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=cls.UNAVAILABLE_MESSAGE,
            original_error=error_message,
        )


class IssueEnhancementFallback:
    """Fallback behavior for issue enhancement.

    When AI is unavailable, issue enhancement gracefully degrades by:
    - Returning the original issue unchanged
    - Skipping AI-generated fields
    """

    UNAVAILABLE_MESSAGE = "AI enhancement temporarily unavailable"

    @classmethod
    def return_original(
        cls,
        original: dict[str, Any],
        *,
        error_message: str | None = None,
    ) -> DegradedResponse[dict[str, Any]]:
        """Return original issue without AI enhancement.

        Args:
            original: The original issue data.
            error_message: Original error message for logging.

        Returns:
            DegradedResponse with original data.
        """
        logger.info(
            "Issue enhancement degraded to original",
            extra={
                "issue_id": original.get("id"),
                "original_error": error_message,
            },
        )

        # Add metadata indicating AI fields are missing
        result = {
            **original,
            "ai_enhanced": False,
            "ai_suggestions": None,
            "ai_labels": None,
            "ai_priority": None,
        }

        return DegradedResponse(
            data=result,
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=cls.UNAVAILABLE_MESSAGE,
            original_error=error_message,
        )


class IssueExtractionFallback:
    """Fallback behavior for issue extraction from notes.

    When AI is unavailable, issue extraction gracefully degrades by:
    - Returning empty extraction with guidance
    - Allowing manual issue creation
    """

    UNAVAILABLE_MESSAGE = (
        "AI issue extraction temporarily unavailable. Please create issues manually."
    )

    @classmethod
    def empty_extraction(
        cls,
        *,
        error_message: str | None = None,
    ) -> DegradedResponse[dict[str, Any]]:
        """Return empty extraction result.

        Args:
            error_message: Original error message for logging.

        Returns:
            DegradedResponse with empty extraction.
        """
        logger.info(
            "Issue extraction degraded to empty result",
            extra={"original_error": error_message},
        )

        return DegradedResponse(
            data={
                "extracted_issues": [],
                "suggestions": [],
                "metadata": {"degraded": True, "manual_creation_required": True},
            },
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=cls.UNAVAILABLE_MESSAGE,
            original_error=error_message,
        )


class DuplicateDetectionFallback:
    """Fallback behavior for duplicate issue detection.

    When AI is unavailable, duplicate detection gracefully degrades by:
    - Returning no duplicates found
    - Logging for later analysis
    """

    UNAVAILABLE_MESSAGE = "AI duplicate detection temporarily unavailable"

    @classmethod
    def no_duplicates(
        cls,
        *,
        error_message: str | None = None,
    ) -> DegradedResponse[list[Any]]:
        """Return no duplicates result.

        Args:
            error_message: Original error message for logging.

        Returns:
            DegradedResponse with empty duplicate list.
        """
        logger.info(
            "Duplicate detection degraded to empty result",
            extra={"original_error": error_message},
        )

        return DegradedResponse(
            data=[],
            degraded=True,
            level=DegradationLevel.DISABLED,
            message=cls.UNAVAILABLE_MESSAGE,
            original_error=error_message,
        )


def graceful_degradation(
    fallback_fn: Any,
) -> Any:
    """Decorator for graceful degradation of AI operations.

    Wraps an async function to catch AI errors and return fallback.

    Args:
        fallback_fn: Function to call for fallback response.

    Returns:
        Decorator function.

    Usage:
        @graceful_degradation(GhostTextFallback.empty_suggestion)
        async def generate_ghost_text(context: str) -> dict:
            ...
    """
    from functools import wraps

    from pilot_space.ai.exceptions import AIError

    def decorator(
        func: Callable[..., Awaitable[T]],
    ) -> Callable[..., Awaitable[DegradedResponse[T] | T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> DegradedResponse[T] | T:
            try:
                result = await func(*args, **kwargs)
                # Wrap successful result if not already wrapped
                if isinstance(result, DegradedResponse):
                    return result  # pyright: ignore[reportUnknownVariableType]
                return result
            except AIError as e:
                logger.warning(
                    "AI operation failed, using fallback",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                return fallback_fn(error_message=str(e))
            except Exception as e:
                logger.exception(
                    "Unexpected error in AI operation, using fallback",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                return fallback_fn(error_message=str(e))

        return wrapper

    return decorator


__all__ = [
    "DegradationLevel",
    "DegradedResponse",
    "DuplicateDetectionFallback",
    "GhostTextFallback",
    "IssueEnhancementFallback",
    "IssueExtractionFallback",
    "MarginAnnotationFallback",
    "graceful_degradation",
]
