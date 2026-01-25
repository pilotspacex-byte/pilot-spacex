"""Meilisearch index configurations.

Contains index settings, configurations, and predefined index names.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class IndexName(StrEnum):
    """Predefined index names for Pilot Space.

    Index naming convention: lowercase, plural entity names.
    """

    ISSUES = "issues"
    NOTES = "notes"
    PAGES = "pages"


# Default index settings for typo-tolerant search
DEFAULT_INDEX_SETTINGS: dict[str, Any] = {
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {
            "oneTypo": 4,
            "twoTypos": 8,
        },
    },
    "pagination": {
        "maxTotalHits": 1000,
    },
}

# Index-specific configurations
INDEX_CONFIGS: dict[str, dict[str, Any]] = {
    IndexName.ISSUES: {
        "searchableAttributes": [
            "title",
            "description",
            "sequence_id",
            "labels",
        ],
        "filterableAttributes": [
            "workspace_id",
            "project_id",
            "state_id",
            "priority",
            "assignee_id",
            "label_ids",
            "is_deleted",
        ],
        "sortableAttributes": [
            "created_at",
            "updated_at",
            "priority",
            "sequence_id",
        ],
        "displayedAttributes": [
            "id",
            "title",
            "description",
            "sequence_id",
            "workspace_id",
            "project_id",
            "state_id",
            "priority",
            "assignee_id",
            "labels",
            "created_at",
            "updated_at",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
    },
    IndexName.NOTES: {
        "searchableAttributes": [
            "title",
            "content_text",
            "tags",
        ],
        "filterableAttributes": [
            "workspace_id",
            "project_id",
            "owner_id",
            "is_archived",
            "is_deleted",
        ],
        "sortableAttributes": [
            "created_at",
            "updated_at",
        ],
        "displayedAttributes": [
            "id",
            "title",
            "content_preview",
            "workspace_id",
            "project_id",
            "owner_id",
            "tags",
            "created_at",
            "updated_at",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
    },
    IndexName.PAGES: {
        "searchableAttributes": [
            "title",
            "content_text",
        ],
        "filterableAttributes": [
            "workspace_id",
            "project_id",
            "parent_id",
            "is_deleted",
        ],
        "sortableAttributes": [
            "created_at",
            "updated_at",
            "title",
        ],
        "displayedAttributes": [
            "id",
            "title",
            "content_preview",
            "workspace_id",
            "project_id",
            "parent_id",
            "created_at",
            "updated_at",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
    },
}
