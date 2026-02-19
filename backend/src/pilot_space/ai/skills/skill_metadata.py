"""UI metadata for skills.

Maps skill name → category, icon (lucide-react), and example prompts.
This is the single source of truth for frontend UI metadata that doesn't
belong in SKILL.md frontmatter.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SkillUIMetadata:
    """UI-specific metadata for a skill."""

    category: str = "general"
    icon: str = "Sparkles"
    examples: list[str] = field(default_factory=list)


SKILL_UI_METADATA: dict[str, SkillUIMetadata] = {
    "extract-issues": SkillUIMetadata(
        category="issues",
        icon="ListTodo",
        examples=["Extract issues from this note", "Find actionable items in the selected text"],
    ),
    "enhance-issue": SkillUIMetadata(
        category="issues",
        icon="Sparkles",
        examples=["Enhance this issue with details", "Add acceptance criteria"],
    ),
    "recommend-assignee": SkillUIMetadata(
        category="issues",
        icon="UserCog",
        examples=["Who should work on this?", "Recommend an assignee"],
    ),
    "find-duplicates": SkillUIMetadata(
        category="issues",
        icon="Copy",
        examples=["Find similar issues", "Check for duplicates"],
    ),
    "decompose-tasks": SkillUIMetadata(
        category="planning",
        icon="Network",
        examples=["Break this into subtasks", "Decompose into implementation steps"],
    ),
    "generate-diagram": SkillUIMetadata(
        category="documentation",
        icon="GitBranch",
        examples=["Create a flowchart", "Generate architecture diagram"],
    ),
    "improve-writing": SkillUIMetadata(
        category="writing",
        icon="PenTool",
        examples=["Improve this text", "Make this clearer"],
    ),
    "summarize": SkillUIMetadata(
        category="notes",
        icon="FileText",
        examples=["Summarize this note", "Create a brief summary"],
    ),
    "create-note-from-chat": SkillUIMetadata(
        category="notes",
        icon="FilePlus",
        examples=["Create a note from this conversation", "Save chat as note"],
    ),
    "generate-digest": SkillUIMetadata(
        category="notes",
        icon="Newspaper",
        examples=["Generate workspace digest", "What happened this week?"],
    ),
    "speckit-pm-guide": SkillUIMetadata(
        category="planning",
        icon="BookOpen",
        examples=["PM guide for this project", "Create a spec template"],
    ),
    "generate-pm-blocks": SkillUIMetadata(
        category="planning",
        icon="LayoutDashboard",
        examples=[
            "Generate PM blocks for sprint planning",
            "Create a risk register and timeline for this project",
        ],
    ),
    "generate-code": SkillUIMetadata(
        category="engineering",
        icon="Code2",
        examples=[
            "Generate a FastAPI endpoint for invitations",
            "Create a React component for user cards",
        ],
    ),
    "write-tests": SkillUIMetadata(
        category="engineering",
        icon="FlaskConical",
        examples=["Write tests for this service", "Generate unit tests for this component"],
    ),
    "generate-migration": SkillUIMetadata(
        category="engineering",
        icon="Database",
        examples=[
            "Generate a migration to add priority column",
            "Create migration for the events table",
        ],
    ),
    "review-code": SkillUIMetadata(
        category="review",
        icon="GitPullRequest",
        examples=["Review this endpoint for security issues", "Check this code for correctness"],
    ),
    "review-architecture": SkillUIMetadata(
        category="review",
        icon="Layers",
        examples=["Review this architecture design", "What are the scalability risks here?"],
    ),
    "scan-security": SkillUIMetadata(
        category="review",
        icon="ShieldAlert",
        examples=["Scan this code for vulnerabilities", "Check for OWASP Top 10 issues"],
    ),
}

_DEFAULT_METADATA = SkillUIMetadata()


def get_skill_ui_metadata(skill_name: str) -> SkillUIMetadata:
    """Return UI metadata for a skill, with sensible defaults for unknown skills."""
    return SKILL_UI_METADATA.get(skill_name, _DEFAULT_METADATA)
