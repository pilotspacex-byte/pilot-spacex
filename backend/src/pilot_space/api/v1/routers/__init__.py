"""FastAPI routers for Pilot Space API v1.

Available routers:
- auth: Authentication and authorization
- workspaces: Workspace management
- workspace_notes: Workspace-scoped note routes
- workspace_notes_ai: AI-specific note operations (content updates)
- projects: Project management
- issues: Issue tracking with AI enhancement
- notes: Note canvas
- cycles: Sprint/cycle management
- ai_chat: Conversational AI chat endpoint
- ai_configuration: Workspace AI/LLM provider configuration
- integrations: GitHub and Slack integration
- webhooks: Inbound webhook handlers
"""

from __future__ import annotations

import logging

from pilot_space.api.v1.routers.ai_approvals import router as ai_approvals_router
from pilot_space.api.v1.routers.ai_chat import router as ai_chat_router
from pilot_space.api.v1.routers.ai_configuration import router as ai_configuration_router
from pilot_space.api.v1.routers.ai_costs import router as ai_costs_router
from pilot_space.api.v1.routers.ai_extraction import router as ai_extraction_router
from pilot_space.api.v1.routers.ai_sessions import router as ai_sessions_router
from pilot_space.api.v1.routers.ai_tasks import router as ai_tasks_router
from pilot_space.api.v1.routers.auth import router as auth_router
from pilot_space.api.v1.routers.cycles import router as cycles_router
from pilot_space.api.v1.routers.ghost_text import router as ghost_text_router
from pilot_space.api.v1.routers.integrations import router as integrations_router
from pilot_space.api.v1.routers.issues import router as issues_router
from pilot_space.api.v1.routers.issues_ai import router as issues_ai_router
from pilot_space.api.v1.routers.issues_ai_context import router as issues_ai_context_router
from pilot_space.api.v1.routers.issues_ai_context_streaming import (
    router as issues_ai_context_streaming_router,
)
from pilot_space.api.v1.routers.mcp_tools import router as mcp_tools_router
from pilot_space.api.v1.routers.notes import router as notes_router
from pilot_space.api.v1.routers.projects import router as projects_router
from pilot_space.api.v1.routers.webhooks import router as webhooks_router
from pilot_space.api.v1.routers.workspace_ai_settings import router as workspace_ai_settings_router
from pilot_space.api.v1.routers.workspace_cycles import router as workspace_cycles_router
from pilot_space.api.v1.routers.workspace_invitations import router as workspace_invitations_router
from pilot_space.api.v1.routers.workspace_issues import router as workspace_issues_router
from pilot_space.api.v1.routers.workspace_members import router as workspace_members_router
from pilot_space.api.v1.routers.workspace_notes import router as workspace_notes_router
from pilot_space.api.v1.routers.workspace_notes_ai import router as workspace_notes_ai_router
from pilot_space.api.v1.routers.workspaces import router as workspaces_router
from pilot_space.config import get_settings

# These routers depend on deleted agent modules (pre-005 architecture).
# They will be migrated to PilotSpaceAgent skill/subagent pattern.
# Lazy imports with fallback to prevent startup failure.
_logger = logging.getLogger(__name__)

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

# Conditional import for debug router (development only)
_settings = get_settings()
debug_router = None
if _settings.is_development:
    from pilot_space.api.v1.routers.debug import router as debug_router

__all__ = [
    "ai_annotations_router",
    "ai_approvals_router",
    "ai_chat_router",
    "ai_configuration_router",
    "ai_costs_router",
    "ai_extraction_router",
    "ai_pr_review_router",
    "ai_router",
    "ai_sessions_router",
    "ai_tasks_router",
    "auth_router",
    "cycles_router",
    "debug_router",
    "ghost_text_router",
    "integrations_router",
    "issues_ai_context_router",
    "issues_ai_context_streaming_router",
    "issues_ai_router",
    "issues_router",
    "mcp_tools_router",
    "notes_ai_router",
    "notes_router",
    "projects_router",
    "webhooks_router",
    "workspace_ai_settings_router",
    "workspace_cycles_router",
    "workspace_invitations_router",
    "workspace_issues_router",
    "workspace_members_router",
    "workspace_notes_ai_router",
    "workspace_notes_router",
    "workspaces_router",
]
