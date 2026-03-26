"""Skills API router.

Lists user-invocable skills discovered from the skills template directory.
No auth required — skill list is not workspace-specific.
"""

from __future__ import annotations

from fastapi import APIRouter

from pilot_space.ai.skills.skill_discovery import SkillInfo, discover_skills
from pilot_space.api.v1.schemas.skills import SkillListResponse, SkillResponse
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
