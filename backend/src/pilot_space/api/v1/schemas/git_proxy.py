"""Pydantic schemas for git proxy API endpoints.

Request/response models for the /api/v1/git/* proxy router that fronts
GitHub/GitLab operations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ============================================================================
# Response schemas
# ============================================================================


class ChangedFileSchema(BaseModel):
    """A file changed between two refs."""

    path: str
    status: str
    additions: int = 0
    deletions: int = 0
    patch: str | None = None


class GitStatusResponse(BaseModel):
    """Response for GET /repos/{owner}/{repo}/status."""

    files: list[ChangedFileSchema]
    branch: str
    total_files: int
    truncated: bool = False


class FileContentResponse(BaseModel):
    """Response for GET /repos/{owner}/{repo}/files/{path}."""

    content: str
    encoding: str = "utf-8"
    sha: str = ""
    size: int = 0


class BranchSchema(BaseModel):
    """Branch metadata."""

    name: str
    sha: str
    is_default: bool = False
    is_protected: bool = False


class BranchListResponse(BaseModel):
    """Response for GET /repos/{owner}/{repo}/branches."""

    branches: list[BranchSchema]
    page: int = 1
    per_page: int = 30


class CommitResponse(BaseModel):
    """Response for POST /repos/{owner}/{repo}/commits."""

    sha: str
    html_url: str
    message: str


class CreatePRResponse(BaseModel):
    """Response for POST /repos/{owner}/{repo}/pulls."""

    number: int
    html_url: str
    title: str
    draft: bool = False


# ============================================================================
# Request schemas
# ============================================================================


class CreateBranchRequest(BaseModel):
    """Request for POST /repos/{owner}/{repo}/branches."""

    name: str
    from_ref: str


class FileChangeSchema(BaseModel):
    """A file to be included in a commit."""

    path: str
    content: str
    encoding: str = "utf-8"
    action: str = "update"


class CommitRequest(BaseModel):
    """Request for POST /repos/{owner}/{repo}/commits."""

    branch: str
    message: str = Field(..., min_length=1, description="Commit message (non-empty)")
    files: list[FileChangeSchema] = Field(
        ..., min_length=1, description="Files to commit (non-empty)"
    )


class CreatePRRequest(BaseModel):
    """Request for POST /repos/{owner}/{repo}/pulls."""

    title: str
    body: str = ""
    head: str
    base: str
    draft: bool = False


__all__ = [
    "BranchListResponse",
    "BranchSchema",
    "ChangedFileSchema",
    "CommitRequest",
    "CommitResponse",
    "CreateBranchRequest",
    "CreatePRRequest",
    "CreatePRResponse",
    "FileChangeSchema",
    "FileContentResponse",
    "GitStatusResponse",
]
