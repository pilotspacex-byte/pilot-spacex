"""Skills API router.

Lists user-invocable skills discovered from the skills template directory,
serves per-skill detail (markdown body + reference-file metadata), and
streams reference-file bytes.

No auth required — skill list is not workspace-specific (it reflects the
filesystem-backed templates directory checked into the repo).

Security: the file-stream endpoint accepts an arbitrary
``{file_path:path}`` URL segment. The combination of ``Path.resolve()``
plus ``is_relative_to(skill_root)`` mitigates path-traversal attacks
(``..``, absolute paths, URL-encoded escapes, and symlinks resolving
outside the skill directory). T-91-01 — see test_skills_router.py for
the complete vector list.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from pilot_space.ai.skills.skill_discovery import (
    SkillDetail,
    SkillInfo,
    discover_skills,
    get_skill_detail,
)
from pilot_space.api.v1.schemas.skills import (
    ReferenceFileMeta,
    SkillDetailResponse,
    SkillListResponse,
    SkillResponse,
)
from pilot_space.config import get_settings
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


def _to_response(info: SkillInfo) -> SkillResponse:
    return SkillResponse(
        name=info.name,
        description=info.description,
        category=info.category,
        icon=info.icon,
        examples=info.examples,
        slug=info.slug,
        feature_module=info.feature_module,
        reference_files=info.reference_files,
        updated_at=info.updated_at,
    )


def _to_detail_response(detail: SkillDetail) -> SkillDetailResponse:
    info = detail.info
    return SkillDetailResponse(
        name=info.name,
        description=info.description,
        category=info.category,
        icon=info.icon,
        examples=info.examples,
        slug=info.slug,
        feature_module=info.feature_module,
        updated_at=info.updated_at,
        body=detail.body,
        reference_files=[
            ReferenceFileMeta(
                name=r.name,
                path=r.path,
                size_bytes=r.size_bytes,
                mime_type=r.mime_type,
            )
            for r in detail.reference_files
        ],
    )


@router.get(
    "",
    response_model=SkillListResponse,
    summary="List available skills",
    description="Returns user-invocable skills parsed from templates/skills/ SKILL.md files.",
)
async def list_skills() -> SkillListResponse:
    """List all user-invocable skills with UI metadata."""
    settings = get_settings()
    skills_dir = settings.system_templates_dir / "skills"
    skills = discover_skills(skills_dir)
    return SkillListResponse(skills=[_to_response(s) for s in skills])


@router.get(
    "/{slug}",
    response_model=SkillDetailResponse,
    summary="Get a single skill with body + reference-file metadata",
)
async def get_skill(slug: str) -> SkillDetailResponse:
    """Return SkillDetailResponse for ``slug`` or 404 if unknown / non-invocable.

    ``get_skill_detail`` performs the slug-containment check internally, so
    this handler does not need to repeat the resolve+is_relative_to dance.
    """
    settings = get_settings()
    skills_dir = settings.system_templates_dir / "skills"
    detail = get_skill_detail(skills_dir, slug)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return _to_detail_response(detail)


@router.get(
    "/{slug}/files/{file_path:path}",
    summary="Stream a skill reference file",
    responses={
        200: {"description": "File bytes", "content": {"*/*": {}}},
        403: {"description": "Path traversal attempt"},
        404: {"description": "Skill or file not found"},
    },
)
async def get_skill_file(slug: str, file_path: str) -> FileResponse:
    """Stream the bytes of a reference file inside ``slug``.

    Path-traversal mitigation (T-91-01): both the slug-resolved skill root
    AND the candidate target are run through ``Path.resolve()``; the
    target must be ``is_relative_to`` the skill root. This rejects:
      - ``..`` at any depth (parent escape)
      - Absolute paths (``/etc/passwd``)
      - URL-encoded escapes (``%2e%2e/``) — FastAPI decodes; check still triggers
      - Symlinks resolving outside the skill directory
    All vectors are tested in ``tests/unit/api/test_skills_router.py``.
    """
    settings = get_settings()
    skills_dir = settings.system_templates_dir / "skills"

    # Slug containment — defends against `slug == "../etc"`.
    if not skills_dir.is_dir():
        raise HTTPException(status_code=404, detail="Skill not found")
    skills_dir_resolved = skills_dir.resolve()
    skill_root_resolved = (skills_dir / slug).resolve()
    if not skill_root_resolved.is_relative_to(skills_dir_resolved):
        raise HTTPException(status_code=404, detail="Skill not found")
    if not skill_root_resolved.is_dir():
        raise HTTPException(status_code=404, detail="Skill not found")

    # File-path containment.
    candidate = (skill_root_resolved / file_path).resolve()
    if not candidate.is_relative_to(skill_root_resolved):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # SKILL.md is exposed via the detail endpoint, not the raw-file endpoint.
    if candidate.name == "SKILL.md":
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(candidate.name, strict=False)
    return FileResponse(
        path=candidate,
        media_type=mime or "application/octet-stream",
        filename=candidate.name,
    )
