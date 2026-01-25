"""Search data models and types.

Contains search-related dataclasses and type definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchHit:
    """Single search result.

    Attributes:
        id: Document ID.
        score: Relevance score (optional).
        document: Full document data.
        highlights: Highlighted matching text (optional).
    """

    id: str
    document: dict[str, Any]
    score: float | None = None
    highlights: dict[str, list[str]] = field(
        default_factory=lambda: {}  # noqa: PIE807
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchHit:
        """Create SearchHit from Meilisearch response."""
        return cls(
            id=str(data.get("id", "")),
            document=data,
            score=data.get("_rankingScore"),
            highlights=data.get("_formatted", {}),
        )


@dataclass
class SearchResult:
    """Search result with pagination info.

    Attributes:
        hits: List of matching documents.
        query: Original search query.
        processing_time_ms: Time taken in milliseconds.
        total_hits: Total matching documents (estimated).
        offset: Current offset for pagination.
        limit: Maximum results returned.
        facets: Facet distribution (if requested).
    """

    hits: list[SearchHit]
    query: str
    processing_time_ms: int = 0
    total_hits: int = 0
    offset: int = 0
    limit: int = 20
    facets: dict[str, dict[str, int]] = field(
        default_factory=lambda: {}  # noqa: PIE807
    )

    @classmethod
    def from_response(cls, response: dict[str, Any], query: str) -> SearchResult:
        """Create SearchResult from Meilisearch response."""
        hits = [SearchHit.from_dict(hit) for hit in response.get("hits", [])]
        return cls(
            hits=hits,
            query=query,
            processing_time_ms=response.get("processingTimeMs", 0),
            total_hits=response.get("estimatedTotalHits", len(hits)),
            offset=response.get("offset", 0),
            limit=response.get("limit", 20),
            facets=response.get("facetDistribution", {}),
        )

    @property
    def is_empty(self) -> bool:
        """Check if search returned no results."""
        return len(self.hits) == 0

    @property
    def has_more(self) -> bool:
        """Check if there are more results to fetch."""
        return self.offset + len(self.hits) < self.total_hits


@dataclass
class TaskInfo:
    """Meilisearch async task information.

    Attributes:
        task_uid: Unique task identifier.
        index_uid: Index the task operates on.
        status: Task status (enqueued, processing, succeeded, failed).
        task_type: Type of task (indexAddition, settingsUpdate, etc.).
    """

    task_uid: int
    index_uid: str | None
    status: str
    task_type: str

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> TaskInfo:
        """Create TaskInfo from Meilisearch response."""
        return cls(
            task_uid=response.get("taskUid", 0),
            index_uid=response.get("indexUid"),
            status=response.get("status", "unknown"),
            task_type=response.get("type", "unknown"),
        )
