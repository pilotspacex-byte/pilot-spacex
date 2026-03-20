"""Skill generation prompt templates.

Prompts for AI-powered SKILL.md content generation.
Used by GenerateRoleSkillService to produce personalized skill profiles.

The prompt requests JSON output including skill_content, suggested_role_name,
suggested_tags, and suggested_usage.
"""

from __future__ import annotations

SKILL_GENERATION_PROMPT_TEMPLATE = """\
You are an expert technical writer creating a personalized AI skill profile \
for an SDLC platform. Generate a SKILL.md document that configures how an AI assistant \
should interact with and support this team member.

## Input

**Role type**: {role_type}
**Role display name**: {display_name}
**User's name for this role**: {name}
**Experience description**: {experience_description}

## Reference Template

Use this template as structural guidance (do not copy verbatim):

{template_content}

## Output Requirements

Return a JSON object with exactly four keys:
1. "skill_content": The full SKILL.md content in markdown format. Include:
   - A heading with the role name
   - Context section describing the role
   - Experience & Background section with the user's experience
   - Sections covering expertise areas, communication preferences, and focus areas
   - Personalized based on the experience description
   - 200-500 words total
2. "suggested_role_name": A concise, professional role title (2-4 words) \
derived from the experience description. Include seniority level if evident \
(e.g., "Senior Developer", "Lead Architect"). If the user provided a role name, \
use it as-is.
3. "suggested_tags": A list of 3-8 short ability tags representing key skills \
(e.g., ["FastAPI", "React", "Testing", "CI/CD", "Clean Architecture"]). \
Tags should be concise technology names, methodologies, or domain areas — \
max 30 characters each.
4. "suggested_usage": A 1-2 sentence description of when and how this skill \
should be activated (e.g., "Use when reviewing Python backend code or designing \
REST API endpoints. Activate for architecture decisions and performance optimization.").

Return ONLY valid JSON, no markdown code fences, no extra text.\
"""


def build_skill_generation_prompt(
    role_type: str,
    display_name: str,
    template_content: str,
    experience_description: str,
    role_name: str | None,
) -> str:
    """Build the prompt for AI skill content generation.

    Formats the template with provided context values.

    Args:
        role_type: The SDLC role type (e.g., "developer", "tester").
        display_name: Human-readable role name from template (e.g., "Developer").
        template_content: Default SKILL.md content from template for reference.
        experience_description: User's natural language experience input.
        role_name: Optional custom role name; falls back to display_name.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    name = role_name or display_name

    # Escape curly braces in user-provided content to prevent format string injection.
    safe_experience = experience_description.replace("{", "{{").replace("}", "}}")
    safe_template = template_content.replace("{", "{{").replace("}", "}}")

    return SKILL_GENERATION_PROMPT_TEMPLATE.format(
        role_type=role_type,
        display_name=display_name,
        name=name,
        experience_description=safe_experience,
        template_content=safe_template,
    )


__all__ = [
    "SKILL_GENERATION_PROMPT_TEMPLATE",
    "build_skill_generation_prompt",
]
