"""FastAPI routers for Pilot Space API v1.

Available routers:
- auth: Authentication and authorization
- workspaces: Workspace management
- workspace_notes: Workspace-scoped note routes
- projects: Project management
- issues: Issue tracking with AI enhancement
- notes: Note canvas
- notes_ai: AI features for notes (ghost text, annotations)
- cycles: Sprint/cycle management
- ai: AI feature endpoints (ghost text, PR review, context)
- ai_configuration: Workspace AI/LLM provider configuration
- integrations: GitHub and Slack integration
- webhooks: Inbound webhook handlers
"""

from __future__ import annotations

from pilot_space.api.v1.routers.ai import router as ai_router
from pilot_space.api.v1.routers.ai_annotations import router as ai_annotations_router
from pilot_space.api.v1.routers.ai_approvals import router as ai_approvals_router
from pilot_space.api.v1.routers.ai_configuration import router as ai_configuration_router
from pilot_space.api.v1.routers.ai_costs import router as ai_costs_router
from pilot_space.api.v1.routers.ai_extraction import router as ai_extraction_router
from pilot_space.api.v1.routers.ai_pr_review import router as ai_pr_review_router
from pilot_space.api.v1.routers.auth import router as auth_router
from pilot_space.api.v1.routers.cycles import router as cycles_router
from pilot_space.api.v1.routers.integrations import router as integrations_router
from pilot_space.api.v1.routers.issues import router as issues_router
from pilot_space.api.v1.routers.issues_ai import router as issues_ai_router
from pilot_space.api.v1.routers.issues_ai_context import router as issues_ai_context_router
from pilot_space.api.v1.routers.issues_ai_context_streaming import (
    router as issues_ai_context_streaming_router,
)
from pilot_space.api.v1.routers.notes import router as notes_router
from pilot_space.api.v1.routers.notes_ai import router as notes_ai_router
from pilot_space.api.v1.routers.projects import router as projects_router
from pilot_space.api.v1.routers.webhooks import router as webhooks_router
from pilot_space.api.v1.routers.workspace_issues import router as workspace_issues_router
from pilot_space.api.v1.routers.workspace_notes import router as workspace_notes_router
from pilot_space.api.v1.routers.workspaces import router as workspaces_router

# Conditional import for debug router (development only)
from pilot_space.config import get_settings

_settings = get_settings()
debug_router = None
if _settings.is_development:
    from pilot_space.api.v1.routers.debug import router as debug_router

__all__ = [
    "ai_annotations_router",
    "ai_approvals_router",
    "ai_configuration_router",
    "ai_costs_router",
    "ai_extraction_router",
    "ai_pr_review_router",
    "ai_router",
    "auth_router",
    "cycles_router",
    "debug_router",
    "integrations_router",
    "issues_ai_context_router",
    "issues_ai_context_streaming_router",
    "issues_ai_router",
    "issues_router",
    "notes_ai_router",
    "notes_router",
    "projects_router",
    "webhooks_router",
    "workspace_issues_router",
    "workspace_notes_router",
    "workspaces_router",
]
