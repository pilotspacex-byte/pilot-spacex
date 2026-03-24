"""Editor plugin service -- PLUG-01..03.

Handles editor plugin upload, listing, toggle, and deletion.
Plugin JS bundles are stored in Supabase Storage; manifest metadata
is persisted in the editor_plugins DB table.

Source: Phase 45, PLUG-01..03
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.database.models.editor_plugin import EditorPlugin
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.editor_plugin_repository import (
        EditorPluginRepository,
    )
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Manifest validation constants
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_MAX_BUNDLE_SIZE = 1 * 1024 * 1024  # 1 MB

# Supabase Storage bucket for editor plugin JS bundles
_PLUGIN_BUCKET = "editor-plugins"


class EditorPluginService:
    """Service for uploading, listing, toggling, and deleting editor plugins.

    Plugins are uploaded as a multipart form with a JSON manifest string
    and a JS bundle file. The service validates the manifest, stores the
    bundle in Supabase Storage, and persists the metadata in the DB.
    """

    def __init__(
        self,
        session: AsyncSession,
        editor_plugin_repo: EditorPluginRepository,
        storage_client: SupabaseStorageClient,
    ) -> None:
        """Initialize with a database session, repository, and storage client.

        Args:
            session: Active async database session.
            editor_plugin_repo: Repository for EditorPlugin entities.
            storage_client: Supabase Storage client for bundle uploads.
        """
        self._session = session
        self._repo = editor_plugin_repo
        self._storage = storage_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_plugin(
        self,
        workspace_id: UUID,
        manifest_dict: dict[str, Any],
        js_content: bytes,
    ) -> EditorPlugin:
        """Upload a new editor plugin or update an existing one.

        Validates the manifest, stores the JS bundle in Supabase Storage,
        and creates (or updates) the database record.

        Args:
            workspace_id: Target workspace UUID.
            manifest_dict: Parsed JSON manifest dict.
            js_content: Raw bytes of the JS bundle.

        Returns:
            Created or updated EditorPlugin entity.

        Raises:
            ValueError: If manifest is invalid or bundle exceeds size limit.
        """
        self._validate_manifest(manifest_dict)
        if len(js_content) > _MAX_BUNDLE_SIZE:
            msg = f"Bundle size {len(js_content)} exceeds maximum {_MAX_BUNDLE_SIZE} bytes"
            raise ValueError(msg)

        name: str = manifest_dict["name"]
        version: str = manifest_dict["version"]
        entrypoint: str = manifest_dict.get("entrypoint", "index.js")

        # Upload JS bundle to Supabase Storage
        storage_path = f"plugins/{workspace_id}/{name}/{version}/{entrypoint}"
        await self._storage.upload_object(
            bucket=_PLUGIN_BUCKET,
            key=storage_path,
            data=js_content,
            content_type="application/javascript",
        )
        logger.info(
            "editor_plugin_bundle_uploaded",
            workspace_id=str(workspace_id),
            name=name,
            version=version,
            storage_path=storage_path,
            size=len(js_content),
        )

        # Check for existing plugin with same name
        existing = await self._repo.get_by_name(workspace_id, name)
        if existing is not None:
            # Update existing plugin
            existing.version = version
            existing.display_name = manifest_dict.get("displayName", name)
            existing.description = manifest_dict.get("description", "")
            existing.author = manifest_dict.get("author", "")
            existing.manifest = manifest_dict
            existing.storage_path = storage_path
            updated = await self._repo.update(existing)
            logger.info(
                "editor_plugin_updated",
                plugin_id=str(updated.id),
                name=name,
                version=version,
            )
            return updated

        # Create new plugin
        plugin = EditorPlugin(
            workspace_id=workspace_id,
            name=name,
            version=version,
            display_name=manifest_dict.get("displayName", name),
            description=manifest_dict.get("description", ""),
            author=manifest_dict.get("author", ""),
            status="enabled",
            manifest=manifest_dict,
            storage_path=storage_path,
        )
        created = await self._repo.create(plugin)
        logger.info(
            "editor_plugin_created",
            plugin_id=str(created.id),
            name=name,
            version=version,
        )
        return created

    async def list_plugins(
        self,
        workspace_id: UUID,
    ) -> Sequence[EditorPlugin]:
        """List all non-deleted editor plugins for a workspace.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            All non-deleted EditorPlugin rows.
        """
        return await self._repo.list_by_workspace(workspace_id)

    async def get_enabled_plugins(
        self,
        workspace_id: UUID,
    ) -> Sequence[EditorPlugin]:
        """List enabled editor plugins for a workspace.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Enabled EditorPlugin rows.
        """
        return await self._repo.get_enabled_by_workspace(workspace_id)

    async def toggle_plugin(
        self,
        plugin_id: UUID,
        status: str,
    ) -> EditorPlugin:
        """Toggle a plugin's enabled/disabled status.

        Args:
            plugin_id: The plugin UUID.
            status: Target status ('enabled' or 'disabled').

        Returns:
            Updated EditorPlugin entity.

        Raises:
            ValueError: If plugin not found or status is invalid.
        """
        if status not in ("enabled", "disabled"):
            msg = f"Invalid status '{status}'. Must be 'enabled' or 'disabled'."
            raise ValueError(msg)

        plugin = await self._repo.get_by_id(plugin_id)
        if plugin is None or plugin.is_deleted:
            msg = "Plugin not found"
            raise ValueError(msg)

        plugin.status = status
        updated = await self._repo.update(plugin)
        logger.info(
            "editor_plugin_toggled",
            plugin_id=str(plugin_id),
            status=status,
        )
        return updated

    async def delete_plugin(
        self,
        plugin_id: UUID,
    ) -> None:
        """Delete an editor plugin (hard delete) and remove bundle from storage.

        Args:
            plugin_id: The plugin UUID.

        Raises:
            ValueError: If plugin not found.
        """
        plugin = await self._repo.get_by_id(plugin_id)
        if plugin is None or plugin.is_deleted:
            msg = "Plugin not found"
            raise ValueError(msg)

        # Remove bundle from storage (non-fatal)
        try:
            await self._storage.delete_object(
                bucket=_PLUGIN_BUCKET,
                key=plugin.storage_path,
            )
        except Exception:
            logger.warning(
                "editor_plugin_storage_delete_failed",
                plugin_id=str(plugin_id),
                storage_path=plugin.storage_path,
                exc_info=True,
            )

        await self._repo.hard_delete(plugin_id)
        logger.info(
            "editor_plugin_deleted",
            plugin_id=str(plugin_id),
            name=plugin.name,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_manifest(manifest: dict[str, Any]) -> None:
        """Validate plugin manifest schema.

        Required fields: name (alphanumeric+hyphens), version (semver), entrypoint.

        Args:
            manifest: Parsed JSON manifest dict.

        Raises:
            ValueError: If any required field is missing or invalid.
        """
        name = manifest.get("name")
        if not name or not isinstance(name, str):
            msg = "Manifest 'name' is required and must be a non-empty string"
            raise ValueError(msg)
        if not _NAME_PATTERN.match(name):
            msg = f"Manifest 'name' must be lowercase alphanumeric with hyphens, got '{name}'"
            raise ValueError(msg)

        version = manifest.get("version")
        if not version or not isinstance(version, str):
            msg = "Manifest 'version' is required and must be a non-empty string"
            raise ValueError(msg)
        if not _SEMVER_PATTERN.match(version):
            msg = f"Manifest 'version' must be semver (e.g. '1.0.0'), got '{version}'"
            raise ValueError(msg)

        entrypoint = manifest.get("entrypoint")
        if not entrypoint or not isinstance(entrypoint, str):
            msg = "Manifest 'entrypoint' is required and must be a non-empty string"
            raise ValueError(msg)


__all__ = ["EditorPluginService"]
