"""FastAPI routers for Pilot Space API v1.

Available routers:
- auth: Authentication and authorization
- workspaces: Workspace management
- workspace_notes: Workspace-scoped note routes
- workspace_notes_ai: AI-specific note operations (content updates)
- note_templates: Reusable note templates (system + workspace-scoped)
- projects: Project management
- issues: Issue tracking with AI enhancement
- cycles: Sprint/cycle management
- ai_attachments: Chat context attachment upload/delete
- ai_chat: Conversational AI chat endpoint
- ai_configuration: Workspace AI/LLM provider configuration
- integrations: GitHub and Slack integration
- webhooks: Inbound webhook handlers
"""

from __future__ import annotations

from pilot_space.api.v1.routers.admin import router as admin_router
from pilot_space.api.v1.routers.ai_approvals import router as ai_approvals_router
from pilot_space.api.v1.routers.ai_attachments import router as ai_attachments_router
from pilot_space.api.v1.routers.ai_chat import router as ai_chat_router
from pilot_space.api.v1.routers.ai_configuration import router as ai_configuration_router
from pilot_space.api.v1.routers.ai_costs import router as ai_costs_router
from pilot_space.api.v1.routers.ai_drive import router as ai_drive_router
from pilot_space.api.v1.routers.ai_extraction import router as ai_extraction_router
from pilot_space.api.v1.routers.ai_governance import router as ai_governance_router
from pilot_space.api.v1.routers.ai_sessions import router as ai_sessions_router
from pilot_space.api.v1.routers.ai_tasks import router as ai_tasks_router
from pilot_space.api.v1.routers.audit import router as audit_router
from pilot_space.api.v1.routers.auth import router as auth_router
from pilot_space.api.v1.routers.auth_sso import router as auth_sso_router
from pilot_space.api.v1.routers.block_ownership import router as block_ownership_router
from pilot_space.api.v1.routers.custom_roles import router as custom_roles_router
from pilot_space.api.v1.routers.cycles import router as cycles_router
from pilot_space.api.v1.routers.dependency_graph import router as dependency_graph_router
from pilot_space.api.v1.routers.ghost_text import router as ghost_text_router
from pilot_space.api.v1.routers.github_links import router as github_links_router
from pilot_space.api.v1.routers.homepage import (
    notes_from_chat_router as homepage_notes_from_chat_router,
    router as homepage_router,
)
from pilot_space.api.v1.routers.integrations import router as integrations_router
from pilot_space.api.v1.routers.intents import router as intents_router
from pilot_space.api.v1.routers.issue_implement import router as issue_implement_router
from pilot_space.api.v1.routers.issues import router as issues_router
from pilot_space.api.v1.routers.issues_ai import router as issues_ai_router
from pilot_space.api.v1.routers.issues_ai_context import router as issues_ai_context_router
from pilot_space.api.v1.routers.issues_ai_context_streaming import (
    router as issues_ai_context_streaming_router,
)
from pilot_space.api.v1.routers.knowledge_graph import (
    issues_kg_router as knowledge_graph_issues_router,
    projects_kg_router as knowledge_graph_projects_router,
    router as knowledge_graph_router,
)
from pilot_space.api.v1.routers.mcp_tools import router as mcp_tools_router
from pilot_space.api.v1.routers.memory import router as memory_router
from pilot_space.api.v1.routers.note_templates import router as note_templates_router
from pilot_space.api.v1.routers.note_versions import router as note_versions_router
from pilot_space.api.v1.routers.note_yjs_state import router as note_yjs_state_router
from pilot_space.api.v1.routers.notifications import router as notifications_router
from pilot_space.api.v1.routers.onboarding import router as onboarding_router
from pilot_space.api.v1.routers.pm_blocks import router as pm_blocks_router
from pilot_space.api.v1.routers.pm_capacity import router as pm_capacity_router
from pilot_space.api.v1.routers.pm_dependency_graph import router as pm_dependency_graph_router
from pilot_space.api.v1.routers.pm_release_notes import router as pm_release_notes_router
from pilot_space.api.v1.routers.pm_sprint_board import router as pm_sprint_board_router
from pilot_space.api.v1.routers.project_artifacts import router as project_artifacts_router
from pilot_space.api.v1.routers.projects import router as projects_router
from pilot_space.api.v1.routers.related_issues import router as related_issues_router
from pilot_space.api.v1.routers.role_skills import (
    role_templates_router,
    router as role_skills_router,
)
from pilot_space.api.v1.routers.scim import router as scim_router
from pilot_space.api.v1.routers.sessions import router as workspace_sessions_router
from pilot_space.api.v1.routers.skill_approvals import router as skill_approvals_router
from pilot_space.api.v1.routers.skill_templates import router as skill_templates_router
from pilot_space.api.v1.routers.skills import router as skills_router
from pilot_space.api.v1.routers.user_skills import router as user_skills_router
from pilot_space.api.v1.routers.webhooks import router as webhooks_router
from pilot_space.api.v1.routers.workspace_ai_settings import router as workspace_ai_settings_router
from pilot_space.api.v1.routers.workspace_artifact_annotations import (
    router as workspace_artifact_annotations_router,
)
from pilot_space.api.v1.routers.workspace_cycles import router as workspace_cycles_router
from pilot_space.api.v1.routers.workspace_encryption import router as workspace_encryption_router
from pilot_space.api.v1.routers.workspace_feature_toggles import (
    router as workspace_feature_toggles_router,
)
from pilot_space.api.v1.routers.workspace_invitations import router as workspace_invitations_router
from pilot_space.api.v1.routers.workspace_issue_branches import (
    router as workspace_issue_branches_router,
)
from pilot_space.api.v1.routers.workspace_issues import router as workspace_issues_router
from pilot_space.api.v1.routers.workspace_mcp_servers import (
    mcp_oauth_callback_router,
    router as workspace_mcp_servers_router,
)
from pilot_space.api.v1.routers.workspace_members import router as workspace_members_router
from pilot_space.api.v1.routers.workspace_note_annotations import (
    annotations_router as workspace_note_annotations_router,
)
from pilot_space.api.v1.routers.workspace_note_issue_links import (
    router as workspace_note_issue_links_router,
)
from pilot_space.api.v1.routers.workspace_note_links import (
    router as workspace_note_links_router,
)
from pilot_space.api.v1.routers.workspace_notes import router as workspace_notes_router
from pilot_space.api.v1.routers.workspace_notes_ai import router as workspace_notes_ai_router
from pilot_space.api.v1.routers.workspace_quota import router as workspace_quota_router
from pilot_space.api.v1.routers.workspace_tasks import router as workspace_tasks_router
from pilot_space.api.v1.routers.workspaces import router as workspaces_router
from pilot_space.infrastructure.logging import get_logger

# These routers depend on deleted agent modules (pre-005 architecture).
# They will be migrated to PilotSpaceAgent skill/subagent pattern.
# Lazy imports with fallback to prevent startup failure.
_logger = get_logger(__name__)

ai_router = None
ai_annotations_router = None
ai_pr_review_router = None
notes_ai_router = None

try:
    from pilot_space.api.v1.routers.ai import router as ai_router  # type: ignore[assignment]
except ImportError:
    _logger.warning("ai_router unavailable: legacy agent modules removed")

try:
    from pilot_space.api.v1.routers.ai_annotations import (
        router as ai_annotations_router,  # type: ignore[assignment]
    )
except ImportError:
    _logger.warning("ai_annotations_router unavailable: margin_annotation_agent_sdk removed")

try:
    from pilot_space.api.v1.routers.ai_pr_review import (
        router as ai_pr_review_router,  # type: ignore[assignment]
    )
except ImportError:
    _logger.warning("ai_pr_review_router unavailable: pr_review_agent removed")

try:
    from pilot_space.api.v1.routers.notes_ai import (
        router as notes_ai_router,  # type: ignore[assignment]
    )
except ImportError:
    _logger.warning("notes_ai_router unavailable: get_sdk_orchestrator removed")

# Debug router removed (was development-only mock generator)
debug_router = None

__all__ = [
    "admin_router",
    "ai_annotations_router",
    "ai_approvals_router",
    "ai_attachments_router",
    "ai_chat_router",
    "ai_configuration_router",
    "ai_costs_router",
    "ai_drive_router",
    "ai_extraction_router",
    "ai_governance_router",
    "ai_pr_review_router",
    "ai_router",
    "ai_sessions_router",
    "ai_tasks_router",
    "audit_router",
    "auth_router",
    "auth_sso_router",
    "block_ownership_router",
    "custom_roles_router",
    "cycles_router",
    "debug_router",
    "dependency_graph_router",
    "ghost_text_router",
    "github_links_router",
    "homepage_notes_from_chat_router",
    "homepage_router",
    "integrations_router",
    "intents_router",
    "issue_implement_router",
    "issues_ai_context_router",
    "issues_ai_context_streaming_router",
    "issues_ai_router",
    "issues_router",
    "knowledge_graph_issues_router",
    "knowledge_graph_projects_router",
    "knowledge_graph_router",
    "mcp_oauth_callback_router",
    "mcp_tools_router",
    "memory_router",
    "note_templates_router",
    "note_versions_router",
    "note_yjs_state_router",
    "notes_ai_router",
    "notifications_router",
    "onboarding_router",
    "pm_blocks_router",
    "pm_capacity_router",
    "pm_dependency_graph_router",
    "pm_release_notes_router",
    "pm_sprint_board_router",
    "project_artifacts_router",
    "projects_router",
    "related_issues_router",
    "role_skills_router",
    "role_templates_router",
    "scim_router",
    "skill_approvals_router",
    "skill_templates_router",
    "skills_router",
    "user_skills_router",
    "webhooks_router",
    "workspace_ai_settings_router",
    "workspace_artifact_annotations_router",
    "workspace_cycles_router",
    "workspace_encryption_router",
    "workspace_feature_toggles_router",
    "workspace_invitations_router",
    "workspace_issue_branches_router",
    "workspace_issues_router",
    "workspace_mcp_servers_router",
    "workspace_members_router",
    "workspace_note_annotations_router",
    "workspace_note_issue_links_router",
    "workspace_note_links_router",
    "workspace_notes_ai_router",
    "workspace_notes_router",
    "workspace_quota_router",
    "workspace_sessions_router",
    "workspace_tasks_router",
    "workspaces_router",
]
