"""Search infrastructure for Pilot Space.

Backend: Meilisearch (typo-tolerant full-text search)

Indexes:
- issues: Issue search with filters
- notes: Note content search
- pages: Page/document search
"""

from pilot_space.infrastructure.search.meilisearch import (
    DEFAULT_INDEX_SETTINGS,
    INDEX_CONFIGS,
    IndexName,
    MeilisearchClient,
    MeilisearchConnectionError,
    MeilisearchError,
    MeilisearchIndexError,
    MeilisearchSearchError,
    SearchHit,
    SearchResult,
    TaskInfo,
)

__all__ = [
    "DEFAULT_INDEX_SETTINGS",
    "INDEX_CONFIGS",
    "IndexName",
    "MeilisearchClient",
    "MeilisearchConnectionError",
    "MeilisearchError",
    "MeilisearchIndexError",
    "MeilisearchSearchError",
    "SearchHit",
    "SearchResult",
    "TaskInfo",
]
