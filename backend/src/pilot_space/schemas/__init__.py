"""Domain-level Pydantic schemas for service return types.

These schemas live at the application/domain boundary. Services return these
types; routers may map them to API-level DTOs in ``api/v1/schemas/`` if needed.

All schemas use ``model_config = ConfigDict(from_attributes=True)`` for ORM
compatibility and are frozen where the result is immutable.
"""

from pilot_space.schemas.action_button import ActionButtonResult
from pilot_space.schemas.admin_dashboard import (
    QuotaConfig,
    RecentAIAction,
    TopMember,
    WorkspaceDetail,
    WorkspaceOverview,
)
from pilot_space.schemas.ai_governance import (
    AIStatus,
    GovernanceAction,
    RollbackEligibility,
    RollbackResult,
)
from pilot_space.schemas.attachment_management import (
    IngestResult,
    SignedUrlResult,
)
from pilot_space.schemas.capacity_plan import (
    CapacityPlanResponse,
    MemberCapacity,
)
from pilot_space.schemas.mcp_server import McpServerResult
from pilot_space.schemas.note_template import NoteTemplateResult
from pilot_space.schemas.sprint_board import (
    SprintBoardCard,
    SprintBoardLane,
    SprintBoardResponse,
    TransitionProposal,
)
from pilot_space.schemas.workspace_ai_settings import (
    AIProviderStatus,
    AISettingsResult,
)

__all__ = [
    "AIProviderStatus",
    "AISettingsResult",
    "AIStatus",
    "ActionButtonResult",
    "CapacityPlanResponse",
    "GovernanceAction",
    "IngestResult",
    "McpServerResult",
    "MemberCapacity",
    "NoteTemplateResult",
    "QuotaConfig",
    "RecentAIAction",
    "RollbackEligibility",
    "RollbackResult",
    "SignedUrlResult",
    "SprintBoardCard",
    "SprintBoardLane",
    "SprintBoardResponse",
    "TopMember",
    "TransitionProposal",
    "WorkspaceDetail",
    "WorkspaceOverview",
]
