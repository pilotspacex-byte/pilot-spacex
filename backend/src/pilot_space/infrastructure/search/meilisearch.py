"""Meilisearch client for Pilot Space.

Provides async full-text search with:
- Typo tolerance
- Faceted filtering
- Workspace-scoped search
- Real-time index updates

Indexes:
- issues: Issue search with state/label filters
- notes: Note content search
- pages: Page/document search
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

import httpx
import orjson

from pilot_space.infrastructure.search.config import (
    DEFAULT_INDEX_SETTINGS,
    INDEX_CONFIGS,
    IndexName,
)
from pilot_space.infrastructure.search.models import (
    SearchHit,
    SearchResult,
    TaskInfo,
)

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
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


class MeilisearchError(Exception):
    """Base exception for Meilisearch errors."""


class MeilisearchConnectionError(MeilisearchError):
    """Failed to connect to Meilisearch."""


class MeilisearchIndexError(MeilisearchError):
    """Index operation failed."""


class MeilisearchSearchError(MeilisearchError):
    """Search operation failed."""


class MeilisearchClient:
    """Async Meilisearch client with workspace-scoped operations.

    Provides type-safe search and indexing for Pilot Space entities.
    All search operations automatically filter by workspace_id for multi-tenancy.
    """

    def __init__(
        self,
        meilisearch_url: str,
        api_key: str | None = None,
        *,
        request_timeout: float = 30.0,
    ) -> None:
        """Initialize Meilisearch client.

        Args:
            meilisearch_url: Meilisearch server URL.
            api_key: API key for authentication (optional for local dev).
            request_timeout: Request timeout in seconds.
        """
        self._base_url = meilisearch_url.rstrip("/")
        self._api_key = api_key
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
            }
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=httpx.Timeout(self._request_timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | list[dict[str, Any]] | list[str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Execute HTTP request to Meilisearch.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            path: API path.
            json_data: Request body (auto-serialized).
            params: Query parameters.

        Returns:
            Response JSON data.

        Raises:
            MeilisearchConnectionError: If connection fails.
            MeilisearchError: If request fails.
        """
        client = await self._get_client()

        try:
            response = await client.request(
                method,
                path,
                content=orjson.dumps(json_data) if json_data is not None else None,
                params=params,
            )

            if response.status_code == 404:
                return {}

            response.raise_for_status()

            if not response.content:
                return {}

            return response.json()
        except httpx.ConnectError as e:
            logger.exception("Failed to connect to Meilisearch")
            raise MeilisearchConnectionError(f"Connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.exception("Meilisearch request failed: %s", e.response.text)
            raise MeilisearchError(
                f"Request failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.exception("Meilisearch request error")
            raise MeilisearchError(f"Request error: {e}") from e

    # =========================================================================
    # Health & Status
    # =========================================================================

    async def is_healthy(self) -> bool:
        """Check if Meilisearch is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            response = await self._request("GET", "/health")
            return isinstance(response, dict) and response.get("status") == "available"
        except MeilisearchError:
            return False

    async def get_version(self) -> str | None:
        """Get Meilisearch version.

        Returns:
            Version string or None if unavailable.
        """
        try:
            response = await self._request("GET", "/version")
            if isinstance(response, dict):
                return response.get("pkgVersion")
        except MeilisearchError:
            pass
        return None

    # =========================================================================
    # Index Management
    # =========================================================================

    async def create_index(
        self,
        index_name: str | IndexName,
        *,
        primary_key: str = "id",
    ) -> TaskInfo:
        """Create a new index. Returns existing if already present."""
        index = str(index_name)

        try:
            response = await self._request(
                "POST",
                "/indexes",
                json_data={
                    "uid": index,
                    "primaryKey": primary_key,
                },
            )
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.info("Index %s creation queued (task %d)", index, task.task_uid)
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            if "already exists" in str(e).lower():
                logger.debug("Index %s already exists", index)
                return TaskInfo(
                    task_uid=0,
                    index_uid=index,
                    status="succeeded",
                    task_type="indexCreation",
                )
            raise MeilisearchIndexError(f"Failed to create index: {e}") from e

    async def delete_index(self, index_name: str | IndexName) -> TaskInfo:
        """Delete an index and all its documents."""
        index = str(index_name)

        try:
            response = await self._request("DELETE", f"/indexes/{index}")
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.info("Index %s deletion queued (task %d)", index, task.task_uid)
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchIndexError(f"Failed to delete index: {e}") from e

    async def update_settings(
        self,
        index_name: str | IndexName,
        settings: dict[str, Any] | None = None,
    ) -> TaskInfo:
        """Update index settings. Uses predefined defaults if settings is None."""
        index = str(index_name)

        # Use predefined config if available, merge with defaults
        if settings is None:
            settings = {
                **DEFAULT_INDEX_SETTINGS,
                **INDEX_CONFIGS.get(index, {}),
            }

        try:
            response = await self._request(
                "PATCH",
                f"/indexes/{index}/settings",
                json_data=settings,
            )
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.info("Index %s settings update queued (task %d)", index, task.task_uid)
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchIndexError(f"Failed to update settings: {e}") from e

    async def get_settings(self, index_name: str | IndexName) -> dict[str, Any]:
        """Get current index settings."""
        index = str(index_name)

        try:
            response = await self._request("GET", f"/indexes/{index}/settings")
            if isinstance(response, dict):
                return response
        except MeilisearchError:
            pass
        return {}

    # =========================================================================
    # Document Operations
    # =========================================================================

    async def index_document(
        self,
        index_name: str | IndexName,
        document: dict[str, Any],
    ) -> TaskInfo:
        """Add or update a single document (must have "id" field)."""
        return await self.index_documents(index_name, [document])

    async def index_documents(
        self,
        index_name: str | IndexName,
        documents: list[dict[str, Any]],
    ) -> TaskInfo:
        """Add or update multiple documents (batch). Documents must have "id" field."""
        if not documents:
            return TaskInfo(
                task_uid=0,
                index_uid=str(index_name),
                status="succeeded",
                task_type="documentAdditionOrUpdate",
            )

        index = str(index_name)

        try:
            response = await self._request(
                "POST",
                f"/indexes/{index}/documents",
                json_data=documents,
            )
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.debug(
                    "Indexed %d documents to %s (task %d)",
                    len(documents),
                    index,
                    task.task_uid,
                )
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchIndexError(f"Failed to index documents: {e}") from e

    async def delete_document(
        self,
        index_name: str | IndexName,
        document_id: str | UUID,
    ) -> TaskInfo:
        """Delete a document by ID."""
        index = str(index_name)
        doc_id = str(document_id)

        try:
            response = await self._request(
                "DELETE",
                f"/indexes/{index}/documents/{doc_id}",
            )
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.debug("Deleted document %s from %s (task %d)", doc_id, index, task.task_uid)
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchIndexError(f"Failed to delete document: {e}") from e

    async def delete_documents(
        self,
        index_name: str | IndexName,
        document_ids: list[str | UUID],
    ) -> TaskInfo:
        """Delete multiple documents by IDs (batch)."""
        if not document_ids:
            return TaskInfo(
                task_uid=0,
                index_uid=str(index_name),
                status="succeeded",
                task_type="documentDeletion",
            )

        index = str(index_name)
        ids = [str(doc_id) for doc_id in document_ids]

        try:
            response = await self._request(
                "POST",
                f"/indexes/{index}/documents/delete-batch",
                json_data=ids,
            )
            if isinstance(response, dict):
                task = TaskInfo.from_response(response)
                logger.debug(
                    "Deleted %d documents from %s (task %d)",
                    len(ids),
                    index,
                    task.task_uid,
                )
                return task
            raise MeilisearchIndexError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchIndexError(f"Failed to delete documents: {e}") from e

    async def get_document(
        self,
        index_name: str | IndexName,
        document_id: str | UUID,
    ) -> dict[str, Any] | None:
        """Get a document by ID. Returns None if not found."""
        index = str(index_name)
        doc_id = str(document_id)

        try:
            response = await self._request(
                "GET",
                f"/indexes/{index}/documents/{doc_id}",
            )
            return response if isinstance(response, dict) else None
        except MeilisearchError:
            return None

    # =========================================================================
    # Search Operations
    # =========================================================================

    def _build_filter_string(
        self,
        workspace_id: str | UUID | None,
        filters: dict[str, Any] | None,
        filter_string: str | None,
    ) -> str | None:
        """Build combined filter expression for search."""
        filter_parts: list[str] = []

        # Always filter by workspace if provided
        if workspace_id:
            filter_parts.append(f'workspace_id = "{workspace_id}"')

        # Add is_deleted filter by default
        filter_parts.append("is_deleted = false")

        # Add custom filters
        if filters:
            for key, filter_value in filters.items():
                if isinstance(filter_value, bool):
                    filter_parts.append(f"{key} = {str(filter_value).lower()}")
                elif isinstance(filter_value, list):
                    # Build IN clause with filter list values
                    # Cast to list[Any] to satisfy type checker
                    value_items = cast("list[Any]", filter_value)
                    filter_list: list[str] = [str(item) for item in value_items]
                    values_str = ", ".join(f'"{v}"' for v in filter_list)
                    filter_parts.append(f"{key} IN [{values_str}]")
                elif filter_value is not None:
                    filter_parts.append(f'{key} = "{filter_value}"')

        # Add raw filter string
        if filter_string:
            filter_parts.append(f"({filter_string})")

        return " AND ".join(filter_parts) if filter_parts else None

    async def search(
        self,
        index_name: str | IndexName,
        query: str,
        *,
        workspace_id: str | UUID | None = None,
        filters: dict[str, Any] | None = None,
        filter_string: str | None = None,
        facets: list[str] | None = None,
        sort: list[str] | None = None,
        offset: int = 0,
        limit: int = 20,
        attributes_to_retrieve: list[str] | None = None,
        attributes_to_highlight: list[str] | None = None,
        show_ranking_score: bool = False,
    ) -> SearchResult:
        """Search documents with workspace filtering and multi-tenancy support."""
        index = str(index_name)
        limit = min(max(limit, 1), 1000)

        # Build filter expression
        combined_filter = self._build_filter_string(workspace_id, filters, filter_string)

        # Build search request
        search_params: dict[str, Any] = {
            "q": query,
            "offset": offset,
            "limit": limit,
        }

        if combined_filter:
            search_params["filter"] = combined_filter
        if sort:
            search_params["sort"] = sort
        if facets:
            search_params["facets"] = facets
        if attributes_to_retrieve:
            search_params["attributesToRetrieve"] = attributes_to_retrieve
        if attributes_to_highlight:
            search_params["attributesToHighlight"] = attributes_to_highlight
            search_params["highlightPreTag"] = "<mark>"
            search_params["highlightPostTag"] = "</mark>"
        if show_ranking_score:
            search_params["showRankingScore"] = True

        try:
            response = await self._request(
                "POST",
                f"/indexes/{index}/search",
                json_data=search_params,
            )
            if isinstance(response, dict):
                result = SearchResult.from_response(response, query)
                logger.debug(
                    "Search '%s' in %s: %d hits in %dms",
                    query[:50],
                    index,
                    result.total_hits,
                    result.processing_time_ms,
                )
                return result
            raise MeilisearchSearchError(f"Unexpected response: {response}")
        except MeilisearchError as e:
            raise MeilisearchSearchError(f"Search failed: {e}") from e

    async def search_issues(
        self,
        query: str,
        workspace_id: str | UUID,
        *,
        project_id: str | UUID | None = None,
        state_ids: list[str | UUID] | None = None,
        label_ids: list[str | UUID] | None = None,
        priority: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> SearchResult:
        """Search issues with common filters (project, state, labels, priority)."""
        filters: dict[str, Any] = {}

        if project_id:
            filters["project_id"] = str(project_id)
        if state_ids:
            filters["state_id"] = [str(sid) for sid in state_ids]
        if label_ids:
            filters["label_ids"] = [str(lid) for lid in label_ids]
        if priority is not None:
            filters["priority"] = priority

        return await self.search(
            IndexName.ISSUES,
            query,
            workspace_id=workspace_id,
            filters=filters,
            sort=["created_at:desc"],
            offset=offset,
            limit=limit,
            facets=["state_id", "priority", "label_ids"],
        )

    async def search_notes(
        self,
        query: str,
        workspace_id: str | UUID,
        *,
        project_id: str | UUID | None = None,
        owner_id: str | UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> SearchResult:
        """Search notes with common filters (project, owner)."""
        filters: dict[str, Any] = {"is_archived": False}

        if project_id:
            filters["project_id"] = str(project_id)
        if owner_id:
            filters["owner_id"] = str(owner_id)

        return await self.search(
            IndexName.NOTES,
            query,
            workspace_id=workspace_id,
            filters=filters,
            sort=["updated_at:desc"],
            offset=offset,
            limit=limit,
        )

    # =========================================================================
    # Initialization & Setup
    # =========================================================================

    async def initialize_indexes(self) -> None:
        """Create and configure all predefined indexes (idempotent).

        Call during application startup to ensure indexes exist
        with correct settings.
        """
        for index_name in IndexName:
            # Create index
            await self.create_index(index_name)
            # Apply settings
            await self.update_settings(index_name)

        logger.info("Initialized all Pilot Space search indexes")

    async def wait_for_task(
        self,
        task_uid: int,
        *,
        max_wait_seconds: float = 30.0,
        poll_interval: float = 0.5,
    ) -> dict[str, Any]:
        """Wait for an async task to complete. Raises on failure or timeout."""
        elapsed = 0.0
        while elapsed < max_wait_seconds:
            response = await self._request("GET", f"/tasks/{task_uid}")
            if isinstance(response, dict):
                status = response.get("status")
                if status == "succeeded":
                    return response
                if status == "failed":
                    error = response.get("error", {})
                    raise MeilisearchError(
                        f"Task {task_uid} failed: {error.get('message', 'Unknown error')}"
                    )
                # Still processing
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            else:
                raise MeilisearchError(f"Unexpected task response: {response}")

        raise MeilisearchError(f"Task {task_uid} timed out after {max_wait_seconds}s")
