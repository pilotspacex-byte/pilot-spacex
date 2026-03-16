"""AIConfiguration SQLAlchemy model.

Stores workspace-level LLM provider settings with encrypted API keys (FR-022).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    KIMI = "kimi"
    GLM = "glm"
    CUSTOM = "custom"


class AIConfiguration(WorkspaceScopedModel):
    """Workspace-level AI/LLM configuration.

    Stores provider-specific settings and encrypted API keys for BYOK (Bring Your Own Key).
    Each workspace can have one configuration per provider.

    Attributes:
        workspace_id: Reference to parent workspace.
        provider: LLM provider (anthropic, openai, google).
        api_key_encrypted: Encrypted API key for the provider.
        is_active: Whether this configuration is active.
        settings: Provider-specific settings (model preferences, etc.).
        usage_limits: Optional usage limits and quotas.
    """

    __tablename__ = "ai_configurations"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_ai_config_workspace_provider"),
        Index("ix_ai_configurations_workspace_provider", "workspace_id", "provider"),
        {"schema": None},
    )

    # Provider configuration
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(
            LLMProvider,
            name="llm_provider",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Encrypted API key (use cryptography.fernet for encryption)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Provider-specific settings
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=dict,
        doc="Provider-specific settings (default model, temperature, etc.)",
    )

    # Usage limits
    usage_limits: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        doc="Optional usage limits (daily_tokens, monthly_budget, etc.)",
    )

    # Custom/OpenAI-compatible provider fields
    base_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="OpenAI-compatible API base URL (required for custom, optional for kimi/glm)",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="Human-readable provider label shown in UI (optional for all providers)",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="ai_configurations",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AIConfiguration(workspace_id={self.workspace_id}, provider={self.provider})>"
