"""WorkspacePlugin SQLAlchemy model.

Workspace-installed plugin from a GitHub repository. Each plugin maps to a
single skill file (SKILL.md + references/) fetched from a remote repo.

Source: Phase 19, SKRG-01..05
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class WorkspacePlugin(WorkspaceScopedModel):
    """Workspace-installed plugin from a GitHub repo.

    Each row represents one skill installed into a workspace from a remote
    repository. The partial unique index on (workspace_id, repo_owner,
    repo_name, skill_name) WHERE is_deleted = false prevents duplicate
    installs while allowing re-install after soft-delete.

    Attributes:
        repo_url: Full GitHub repository URL.
        repo_owner: GitHub owner/org (e.g., 'acme-corp').
        repo_name: GitHub repository name (e.g., 'pilot-skills').
        skill_name: Skill identifier within the repo (e.g., 'code-review').
        display_name: Human-readable name shown in UI.
        description: Optional long description of the plugin.
        skill_content: SKILL.md-format markdown content.
        references: JSONB array of reference file paths/contents.
        installed_sha: Git commit SHA at install/update time.
        is_active: Whether this plugin is active (injected into agent context).
        installed_by: User who installed/updated this plugin.
    """

    __tablename__ = "workspace_plugins"  # type: ignore[assignment]

    repo_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    repo_owner: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    repo_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    references: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONBCompat,
        nullable=False,
        default=list,
    )
    installed_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    installed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        # Partial unique index: one skill per repo per workspace.
        # Soft-deleted rows excluded — allows re-install after delete.
        Index(
            "uq_workspace_plugins_workspace_skill",
            "workspace_id",
            "repo_owner",
            "repo_name",
            "skill_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Hot-path index for materializer: get_active_by_workspace query
        Index(
            "ix_workspace_plugins_workspace_active",
            "workspace_id",
            "is_active",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "[ACTIVE]" if self.is_active else "[INACTIVE]"
        return (
            f"<WorkspacePlugin(workspace_id={self.workspace_id}, "
            f"repo={self.repo_owner}/{self.repo_name}, "
            f"skill={self.skill_name} {status})>"
        )


__all__ = ["WorkspacePlugin"]
