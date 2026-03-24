"""EditorPlugin SQLAlchemy model.

Workspace-installed editor plugin with a JS bundle and manifest.
Each plugin registers custom block types, slash commands, and actions
in the editor. The JS bundle is stored in Supabase Storage; the manifest
(JSON) is persisted here for fast querying.

Distinct from WorkspacePlugin (Phase 19) which stores GitHub-sourced
skill markdown content for the AI agent.

Source: Phase 45, PLUG-01..03
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class EditorPlugin(WorkspaceScopedModel):
    """Editor plugin installed in a workspace.

    Inherits id (UUID PK), workspace_id (FK + index), is_deleted, deleted_at,
    created_at, updated_at from WorkspaceScopedModel.

    Attributes:
        name: Plugin identifier (alphanumeric + hyphens, e.g. 'my-chart-plugin').
        version: Semver string (e.g. '1.0.0').
        display_name: Human-readable name shown in plugin manager UI.
        description: Optional long description.
        author: Plugin author name or organization.
        status: 'enabled' or 'disabled'. Default 'enabled'.
        manifest: Full plugin manifest JSON (permissions, blockTypes, etc.).
        storage_path: Path to the JS bundle in Supabase Storage.
    """

    __tablename__ = "editor_plugins"  # type: ignore[assignment]

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    author: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'enabled'"),
    )
    manifest: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    __table_args__ = (
        # Unique constraint: one plugin name per workspace (non-deleted).
        Index(
            "uq_editor_plugins_workspace_name",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EditorPlugin(id={self.id}, "
            f"workspace_id={self.workspace_id}, "
            f"name={self.name!r}, version={self.version!r}, "
            f"status={self.status!r})>"
        )


__all__ = ["EditorPlugin"]
