"""Pydantic v2 schemas for workspace plugin endpoints.

Request/response models for plugin browse, install, update check,
and GitHub credential management.

Source: Phase 19, SKRG-01..05
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkspacePluginBrowseRequest(BaseModel):
    """Request to browse skills in a GitHub repository.

    Attributes:
        repo_url: Full GitHub repository URL.
    """

    model_config = ConfigDict(strict=True)

    repo_url: str


class SkillListItem(BaseModel):
    """A single skill available in a GitHub repository.

    Attributes:
        skill_name: Directory name under skills/.
        display_name: Human-readable name from SKILL.md frontmatter.
        description: Optional description from SKILL.md frontmatter.
    """

    skill_name: str
    display_name: str
    description: str | None = None


class WorkspacePluginInstallRequest(BaseModel):
    """Request to install a plugin from a GitHub repository.

    Attributes:
        repo_url: Full GitHub repository URL.
        skill_name: Skill directory name to install.
    """

    model_config = ConfigDict(strict=True)

    repo_url: str
    skill_name: str


class WorkspacePluginResponse(BaseModel):
    """Response for an installed workspace plugin.

    Attributes:
        id: Plugin UUID.
        workspace_id: Workspace UUID.
        repo_url: GitHub repository URL.
        skill_name: Skill directory name.
        display_name: Human-readable name.
        description: Optional description.
        installed_sha: Git commit SHA at install time.
        is_active: Whether the plugin is active.
        has_update: Whether a newer version is available upstream.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    repo_url: str
    skill_name: str
    display_name: str
    description: str | None = None
    installed_sha: str
    is_active: bool
    has_update: bool = False


class WorkspacePluginUpdateCheckResponse(BaseModel):
    """Response for the update check endpoint.

    Attributes:
        plugins: List of installed plugins with has_update status.
    """

    plugins: list[WorkspacePluginResponse]


class WorkspaceGithubCredentialRequest(BaseModel):
    """Request to save a workspace GitHub PAT.

    Attributes:
        pat: Raw GitHub personal access token (will be encrypted on save).
    """

    model_config = ConfigDict(strict=True)

    pat: str


class WorkspaceGithubCredentialResponse(BaseModel):
    """Response for GitHub credential status (never exposes the raw PAT).

    Attributes:
        has_pat: Whether a PAT is configured for this workspace.
    """

    has_pat: bool


__all__ = [
    "SkillListItem",
    "WorkspaceGithubCredentialRequest",
    "WorkspaceGithubCredentialResponse",
    "WorkspacePluginBrowseRequest",
    "WorkspacePluginInstallRequest",
    "WorkspacePluginResponse",
    "WorkspacePluginUpdateCheckResponse",
]
