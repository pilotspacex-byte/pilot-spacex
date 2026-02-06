"""Pydantic schemas for Pilot Space API v1.

This package contains request/response models:
- base: Common schemas (pagination, errors)
- auth: Authentication schemas
- workspace: Workspace schemas
- project: Project schemas
- issue: Issue schemas with AI metadata
- note: Note and annotation schemas
- cycle: Sprint/cycle schemas
- ai_suggestion: AI enhancement response schemas
- ai_configuration: AI/LLM provider configuration schemas
"""

from __future__ import annotations

from pilot_space.api.v1.schemas.ai_configuration import (
    AIConfigurationCreate,
    AIConfigurationListResponse,
    AIConfigurationResponse,
    AIConfigurationTestRequest,
    AIConfigurationTestResponse,
    AIConfigurationUpdate,
)
from pilot_space.api.v1.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from pilot_space.api.v1.schemas.base import (
    BaseSchema,
    BulkResponse,
    DeleteResponse,
    EntitySchema,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    TimestampSchema,
)
from pilot_space.api.v1.schemas.cycle import (
    AddIssueToCycleRequest,
    BulkAddIssuesToCycleRequest,
    BurndownChartResponse,
    BurndownDataPoint,
    CycleBriefResponse,
    CycleCreateRequest,
    CycleListResponse,
    CycleMetricsResponse,
    CycleResponse,
    CycleUpdateRequest,
    RolloverCycleRequest,
    RolloverCycleResponse,
    VelocityChartResponse,
    VelocityDataPoint,
)
from pilot_space.api.v1.schemas.integration import (
    ConnectGitHubResponse,
    GitHubOAuthCallbackRequest,
    GitHubOAuthUrlResponse,
    GitHubRepositoriesResponse,
    GitHubRepositoryResponse,
    IntegrationLinkResponse,
    IntegrationLinksResponse,
    IntegrationListResponse,
    IntegrationResponse,
    LinkCommitRequest,
    LinkPullRequestRequest,
    SetupWebhookRequest,
    WebhookProcessResult,
    WebhookSetupResponse,
)
from pilot_space.api.v1.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdate,
    StateResponse,
)
from pilot_space.api.v1.schemas.workspace import (
    InvitationCreateRequest,
    InvitationResponse,
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

__all__ = [
    "AIConfigurationCreate",
    "AIConfigurationListResponse",
    "AIConfigurationResponse",
    "AIConfigurationTestRequest",
    "AIConfigurationTestResponse",
    "AIConfigurationUpdate",
    "AddIssueToCycleRequest",
    "BaseSchema",
    "BulkAddIssuesToCycleRequest",
    "BulkResponse",
    "BurndownChartResponse",
    "BurndownDataPoint",
    "ConnectGitHubResponse",
    "CycleBriefResponse",
    "CycleCreateRequest",
    "CycleListResponse",
    "CycleMetricsResponse",
    "CycleResponse",
    "CycleUpdateRequest",
    "DeleteResponse",
    "EntitySchema",
    "ErrorResponse",
    "GitHubOAuthCallbackRequest",
    "GitHubOAuthUrlResponse",
    "GitHubRepositoriesResponse",
    "GitHubRepositoryResponse",
    "HealthResponse",
    "IntegrationLinkResponse",
    "IntegrationLinksResponse",
    "IntegrationListResponse",
    "IntegrationResponse",
    "InvitationCreateRequest",
    "InvitationResponse",
    "LinkCommitRequest",
    "LinkPullRequestRequest",
    "LoginRequest",
    "PaginatedResponse",
    "PaginationParams",
    "ProjectCreate",
    "ProjectDetailResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "RolloverCycleRequest",
    "RolloverCycleResponse",
    "SetupWebhookRequest",
    "StateResponse",
    "SuccessResponse",
    "TimestampSchema",
    "TokenResponse",
    "UserProfileResponse",
    "UserProfileUpdateRequest",
    "VelocityChartResponse",
    "VelocityDataPoint",
    "WebhookProcessResult",
    "WebhookSetupResponse",
    "WorkspaceCreate",
    "WorkspaceDetailResponse",
    "WorkspaceMemberCreate",
    "WorkspaceMemberResponse",
    "WorkspaceMemberUpdate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
]
