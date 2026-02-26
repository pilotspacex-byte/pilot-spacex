"""FastAPI dependency injection.

Provides request-scoped dependencies for authentication, database, services,
and AI infrastructure. This package re-exports all symbols from submodules
so that existing imports via ``pilot_space.dependencies`` continue to work.

Submodules:
    - auth: Authentication, authorization, user sync
    - workspace: Workspace context resolution
    - services: Domain service factories (issue, activity)
    - ai: AI context, configuration, infrastructure, SDK, agents
"""

from __future__ import annotations

# Re-export AI dependencies
from pilot_space.dependencies.ai import (
    ApprovalServiceDep,
    CostTrackerDep,
    GhostTextServiceDep,
    KeyStorageDep,
    PermissionHandlerDep,
    PilotSpaceAgentDep,
    ProviderSelectorDep,
    QueueClientDep,
    RedisDep,
    ResilientExecutorDep,
    SessionHandlerDep,
    SessionManagerDep,
    SkillRegistryDep,
    ToolRegistryDep,
    get_ai_config,
    get_ai_config_or_demo,
    get_ai_context_service,
    get_approval_service_dep,
    get_cost_tracker_dep,
    get_ghost_text_service,
    get_key_storage,
    get_permission_handler_dep,
    get_pilotspace_agent,
    get_provider_selector,
    get_queue_client,
    get_redis_client,
    get_refine_ai_context_service,
    get_resilient_executor,
    get_session_handler_dep,
    get_session_manager,
    get_skill_registry_dep,
    get_tool_registry,
    get_user_api_keys,
)

# Re-export auth dependencies
from pilot_space.dependencies.auth import (
    CurrentUser,
    CurrentUserId,
    DbSession,
    SyncedUserId,
    WorkspaceAdminId,
    WorkspaceMemberId,
    ensure_user_synced,
    get_auth,
    get_current_user,
    get_current_user_id,
    get_session,
    get_token_from_header,
    require_workspace_admin,
    require_workspace_member,
)

# Re-export service dependencies
from pilot_space.dependencies.services import (
    AttachmentUploadServiceDep,
    ChatAttachmentRepositoryDep,
    get_activity_service,
    get_attachment_upload_service,
    get_chat_attachment_repository,
    get_create_issue_service,
    get_get_issue_service,
    get_list_issues_service,
    get_update_issue_service,
)

# Re-export workspace dependencies
from pilot_space.dependencies.workspace import (
    get_current_workspace_id,
    get_db_session_dep,
)

# Alias for backward compatibility
get_db_session = get_db_session_dep

__all__ = [
    "ApprovalServiceDep",
    "AttachmentUploadServiceDep",
    "ChatAttachmentRepositoryDep",
    "CostTrackerDep",
    "CurrentUser",
    "CurrentUserId",
    "DbSession",
    "GhostTextServiceDep",
    "KeyStorageDep",
    "PermissionHandlerDep",
    "PilotSpaceAgentDep",
    "ProviderSelectorDep",
    "QueueClientDep",
    "RedisDep",
    "ResilientExecutorDep",
    "SessionHandlerDep",
    "SessionManagerDep",
    "SkillRegistryDep",
    "SyncedUserId",
    "ToolRegistryDep",
    "WorkspaceAdminId",
    "WorkspaceMemberId",
    "ensure_user_synced",
    "get_activity_service",
    "get_ai_config",
    "get_ai_config_or_demo",
    "get_ai_context_service",
    "get_approval_service_dep",
    "get_attachment_upload_service",
    "get_auth",
    "get_chat_attachment_repository",
    "get_cost_tracker_dep",
    "get_create_issue_service",
    "get_current_user",
    "get_current_user_id",
    "get_current_workspace_id",
    "get_db_session",
    "get_db_session_dep",
    "get_get_issue_service",
    "get_ghost_text_service",
    "get_key_storage",
    "get_list_issues_service",
    "get_permission_handler_dep",
    "get_pilotspace_agent",
    "get_provider_selector",
    "get_queue_client",
    "get_redis_client",
    "get_refine_ai_context_service",
    "get_resilient_executor",
    "get_session",
    "get_session_handler_dep",
    "get_session_manager",
    "get_skill_registry_dep",
    "get_token_from_header",
    "get_tool_registry",
    "get_update_issue_service",
    "get_user_api_keys",
    "require_workspace_admin",
    "require_workspace_member",
]
