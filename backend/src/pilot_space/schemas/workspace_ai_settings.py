"""Domain schemas for WorkspaceAISettingsService return types.

WorkspaceAISettingsResponse and WorkspaceAISettingsUpdateResponse live in
``api/v1/schemas/workspace`` and are returned directly by the service.  This
module exposes thin domain aliases so the service layer can reference domain
types without importing from the API layer in the future.

Currently these are thin wrappers that re-export the API-level schemas, which
already carry ``from_attributes=True`` and are stable contracts.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIProviderStatus(BaseModel):
    """Provider API key status for a workspace.

    Mirrors ``api/v1/schemas/workspace.ProviderStatus`` at the domain layer.
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    service_type: str
    is_configured: bool
    is_valid: bool | None = None
    last_validated_at: datetime | None = None
    base_url: str | None = None
    model_name: str | None = None


class AISettingsResult(BaseModel):
    """Full AI settings response for a workspace.

    Mirrors ``api/v1/schemas/workspace.WorkspaceAISettingsResponse`` at the
    domain layer so services are not coupled to API schemas.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    providers: list[AIProviderStatus]
    default_llm_provider: str
    default_embedding_provider: str
    cost_limit_usd: float | None = None


__all__ = [
    "AIProviderStatus",
    "AISettingsResult",
]
