"""GetImplementContext service for the pilot-implement feature.

Returns all context required by PilotSpaceAgent to implement an issue:
issue details, linked note blocks, GitHub repository info, workspace/project
metadata, and a pre-computed suggested branch name.

Authorization: requester must be the issue assignee, or have admin/owner role
in the workspace.

Import note: api.v1.schemas.implement_context is imported inside execute() to
avoid a circular dependency through the api.v1 package __init__ (which imports
routers that import container that imports this module during initialization).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from pilot_space.infrastructure.database.repositories import (
        IntegrationRepository,
        IssueRepository,
        NoteIssueLinkRepository,
        NoteRepository,
        WorkspaceRepository,
    )

logger = get_logger(__name__)

_MAX_BRANCH_LEN = 60
_MAX_NOTE_BLOCKS = 3


# ============================================================================
# Payload / Result
# ============================================================================


@dataclass
class GetImplementContextPayload:
    """Input for GetImplementContextService.execute.

    Attributes:
        issue_id: UUID of the issue to fetch context for.
        workspace_id: UUID of the workspace (for RLS scoping).
        requester_id: UUID of the requesting user (for authorization).
    """

    issue_id: UUID
    workspace_id: UUID
    requester_id: UUID


@dataclass
class GetImplementContextResult:
    """Output from GetImplementContextService.execute.

    Attributes:
        context: ImplementContextResponse instance (typed as Any to avoid
            the circular import from api.v1.__init__ at module-load time;
            the actual type is always ImplementContextResponse at runtime).
    """

    context: Any  # pilot_space.api.v1.schemas.implement_context.ImplementContextResponse


# ============================================================================
# Internal intermediate types (plain dataclasses — no Pydantic at module level)
# ============================================================================


@dataclass
class _RepoInfo:
    """Intermediate repository info before schema construction."""

    clone_url: str
    default_branch: str
    provider: str  # "github" | "gitlab"


@dataclass
class _NoteBlockInfo:
    """Intermediate linked-note info before schema construction."""

    note_title: str
    relevant_blocks: list[str] = field(default_factory=list)


# ============================================================================
# Pure helper functions
# ============================================================================


def _slugify(text: str) -> str:
    """Convert text to a URL-safe, git-branch-safe slug.

    Args:
        text: Raw text to slugify.

    Returns:
        Lowercase alphanumeric string with hyphens.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _build_suggested_branch(sequence_id: int, title: str) -> str:
    """Compute the suggested feature branch name.

    Format: ``feat/ps-{sequence_id}-{slug}`` capped at 60 characters.
    Trailing hyphens are stripped after truncation.

    Args:
        sequence_id: Numeric sequence ID of the issue.
        title: Issue title.

    Returns:
        Branch name string, at most 60 characters.
    """
    slug = _slugify(title)
    branch = f"feat/ps-{sequence_id}-{slug}"
    return branch[:_MAX_BRANCH_LEN].rstrip("-")


def _extract_text_blocks(content: dict[str, Any]) -> list[str]:
    """Recursively extract text from TipTap ProseMirror JSON content.

    Walks the ``content`` array of a TipTap document and collects text
    from ``text`` nodes into paragraph-level strings. Returns at most
    ``_MAX_NOTE_BLOCKS`` non-empty paragraphs.

    Args:
        content: TipTap JSON document (the ``content`` JSONB column of Note).

    Returns:
        List of text strings from content blocks (max 3).
    """
    blocks: list[str] = []

    def _collect_text(node: Any, out: list[str]) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "text":
            text = node.get("text", "")
            if text:
                out.append(text)
        for child in node.get("content", []):
            _collect_text(child, out)

    def _walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("type", "")
        children = node.get("content", [])

        if node_type in ("paragraph", "heading", "bulletList", "orderedList"):
            texts: list[str] = []
            _collect_text(node, texts)
            joined = " ".join(texts).strip()
            if joined:
                blocks.append(joined)
                if len(blocks) >= _MAX_NOTE_BLOCKS:
                    return
        else:
            for child in children:
                if len(blocks) >= _MAX_NOTE_BLOCKS:
                    return
                _walk(child)

    _walk(content)
    return blocks[:_MAX_NOTE_BLOCKS]


def _derive_repo_info(integration: Any) -> _RepoInfo:
    """Derive repository URL and default branch from an Integration model.

    Priority:
    1. ``settings["default_repository"]`` → ``https://github.com/<owner/repo>``
    2. First entry in ``settings["repositories"]``
    3. ``external_account_name`` (org-level URL as last resort)

    Args:
        integration: Active GitHub Integration ORM instance.

    Returns:
        _RepoInfo with clone_url and default_branch.

    Raises:
        ValueError: If clone_url cannot be derived from available settings.
    """
    settings: dict[str, Any] = integration.settings or {}
    default_branch: str = settings.get("default_branch", "main")

    default_repo: str | None = settings.get("default_repository")
    if default_repo:
        return _RepoInfo(
            clone_url=f"https://github.com/{default_repo}",
            default_branch=default_branch,
            provider="github",
        )

    repositories: list[str] = settings.get("repositories", [])
    if repositories:
        return _RepoInfo(
            clone_url=f"https://github.com/{repositories[0]}",
            default_branch=default_branch,
            provider="github",
        )

    org_name: str | None = integration.external_account_name
    if not org_name:
        raise NotFoundError(
            "GitHub integration has no default_repository, repositories list, "
            "or external_account_name — cannot derive clone_url"
        )
    return _RepoInfo(
        clone_url=f"https://github.com/{org_name}",
        default_branch=default_branch,
        provider="github",
    )


# ============================================================================
# Service
# ============================================================================


class GetImplementContextService:
    """Assemble implement context for a single issue.

    Authorization:
        Requester must be the issue assignee OR have ADMIN/OWNER role in
        the workspace.

    Steps:
        1. Fetch issue with relations (project, state, labels, note_links).
        2. Authorize requester as assignee or admin/owner.
        3. Fetch linked notes and extract relevant text blocks.
        4. Fetch active GitHub integration → build repository info.
        5. Fetch workspace for slug/name.
        6. Compute suggested branch name.
        7. Build and return ImplementContextResponse.
    """

    def __init__(
        self,
        issue_repository: IssueRepository,
        note_issue_link_repository: NoteIssueLinkRepository,
        note_repository: NoteRepository,
        integration_repository: IntegrationRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        """Initialize with injected repositories.

        Args:
            issue_repository: Issue data access.
            note_issue_link_repository: NoteIssueLink data access.
            note_repository: Note data access.
            integration_repository: Integration (GitHub/Slack) data access.
            workspace_repository: Workspace and member data access.
        """
        self._issue_repo = issue_repository
        self._note_link_repo = note_issue_link_repository
        self._note_repo = note_repository
        self._integration_repo = integration_repository
        self._workspace_repo = workspace_repository

    async def execute(
        self,
        payload: GetImplementContextPayload,
    ) -> GetImplementContextResult:
        """Assemble and return the implement context for an issue.

        Args:
            payload: Validated input containing issue_id, workspace_id,
                and requester_id.

        Returns:
            GetImplementContextResult with fully populated ImplementContextResponse.

        Raises:
            ValueError: If the issue does not exist, the workspace has no active
                GitHub integration, or the integration has insufficient settings
                to derive a repository URL.
            PermissionError: If the requester is neither the assignee nor an
                admin/owner in the workspace.
        """
        logger.info(
            "Assembling implement context",
            extra={
                "issue_id": str(payload.issue_id),
                "workspace_id": str(payload.workspace_id),
                "requester_id": str(payload.requester_id),
            },
        )

        # 1. Fetch issue with all relations
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if issue is None:
            raise NotFoundError(f"Issue not found: {payload.issue_id}")

        # 2. Authorize requester
        await self._authorize(
            issue=issue,
            requester_id=payload.requester_id,
            workspace_id=payload.workspace_id,
        )

        # 3. Fetch linked note blocks
        note_blocks = await self._fetch_linked_note_blocks(
            issue_id=payload.issue_id,
            workspace_id=payload.workspace_id,
        )

        # 4. Fetch GitHub integration
        integration = await self._integration_repo.get_active_github(payload.workspace_id)
        if integration is None:
            logger.warning(
                "No active GitHub integration found for workspace",
                extra={"workspace_id": str(payload.workspace_id)},
            )
            raise ValidationError("no_github_integration")

        repo_info = _derive_repo_info(integration)

        # 5. Fetch workspace
        workspace = await self._workspace_repo.get_by_id(payload.workspace_id)
        if workspace is None:
            raise NotFoundError(f"Workspace not found: {payload.workspace_id}")

        # 6. Build project context values
        project = issue.project
        raw_description: str = project.description or ""
        tech_stack_summary: str = raw_description[:300] or "No tech stack description provided."

        # 7. Compute suggested branch
        suggested_branch = _build_suggested_branch(
            sequence_id=issue.sequence_id,
            title=issue.name,
        )

        # Deferred import: avoids circular dependency through api.v1.__init__
        # (api.v1.__init__ → routers → repository_deps → container → services.issue)
        from pilot_space.api.v1.schemas.implement_context import (
            ImplementContextResponse,
            IssueDetail,
            LinkedNoteBlock,
            ProjectContext,
            RepositoryContext,
            WorkspaceContext,
        )

        context = ImplementContextResponse(
            issue=IssueDetail.from_issue(issue),
            linked_notes=[
                LinkedNoteBlock(
                    note_title=nb.note_title,
                    relevant_blocks=nb.relevant_blocks,
                )
                for nb in note_blocks
            ],
            repository=RepositoryContext(
                clone_url=repo_info.clone_url,
                default_branch=repo_info.default_branch,
                provider=repo_info.provider,  # type: ignore[arg-type]
            ),
            workspace=WorkspaceContext(
                slug=workspace.slug,
                name=workspace.name,
            ),
            project=ProjectContext(
                name=project.name,
                tech_stack_summary=tech_stack_summary,
            ),
            suggested_branch=suggested_branch,
        )

        logger.info(
            "Implement context assembled",
            extra={
                "issue_id": str(payload.issue_id),
                "identifier": issue.identifier,
                "linked_notes_count": len(note_blocks),
                "suggested_branch": suggested_branch,
            },
        )

        return GetImplementContextResult(context=context)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _authorize(
        self,
        issue: Any,
        requester_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Verify requester is authorized to access implement context.

        Authorization passes if the requester is:
        - The issue assignee, OR
        - An ADMIN or OWNER in the workspace.

        Args:
            issue: Issue ORM instance with assignee_id populated.
            requester_id: UUID of the requesting user.
            workspace_id: UUID of the workspace for role lookup.

        Raises:
            PermissionError: If neither condition is met.
        """
        is_assignee = issue.assignee_id is not None and str(issue.assignee_id) == str(requester_id)

        if is_assignee:
            return

        member_role = await self._workspace_repo.get_member_role(
            workspace_id=workspace_id,
            user_id=requester_id,
        )
        if member_role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
            return

        logger.warning(
            "Implement context access denied",
            extra={
                "requester_id": str(requester_id),
                "issue_id": str(issue.id),
                "member_role": member_role.value if member_role else None,
            },
        )
        raise ForbiddenError(
            "Only the issue assignee or workspace admins/owners can access implement context"
        )

    async def _fetch_linked_note_blocks(
        self,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> list[_NoteBlockInfo]:
        """Fetch NoteIssueLinks and extract up to 3 text blocks per note.

        Deduplicates by note_id so that multiple link types for the same note
        produce only one LinkedNoteBlock entry.

        Args:
            issue_id: UUID of the issue.
            workspace_id: UUID of the workspace (RLS scope).

        Returns:
            List of _NoteBlockInfo with title and relevant block excerpts.
        """
        links = await self._note_link_repo.get_by_issue(
            issue_id=issue_id,
            workspace_id=workspace_id,
        )

        if not links:
            return []

        result: list[_NoteBlockInfo] = []
        seen_note_ids: set[str] = set()

        for link in links:
            note_id_str = str(link.note_id)
            if note_id_str in seen_note_ids:
                continue
            seen_note_ids.add(note_id_str)

            # NoteIssueLink has lazy="joined" on note, so link.note is usually loaded.
            note = link.note if (link.note and not link.note.is_deleted) else None
            if note is None:
                note = await self._note_repo.get_by_id(link.note_id)

            if note is None or note.is_deleted:
                continue

            content: dict[str, Any] = note.content or {}
            blocks = _extract_text_blocks(content)

            result.append(
                _NoteBlockInfo(
                    note_title=note.title,
                    relevant_blocks=blocks,
                )
            )

        return result


__all__ = [
    "GetImplementContextPayload",
    "GetImplementContextResult",
    "GetImplementContextService",
]
