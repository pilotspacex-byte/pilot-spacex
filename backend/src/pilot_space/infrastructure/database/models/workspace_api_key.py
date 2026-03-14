"""WorkspaceAPIKey SQLAlchemy model.

Stores encrypted API keys for AI providers per workspace (DD-002 BYOK).
Keys are encrypted using Fernet symmetric encryption.

References:
- T006: Create workspace_api_keys migration
- specs/004-mvp-agents-build/tasks/P2-T006-T010.md
- docs/DESIGN_DECISIONS.md#DD-002
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base, TimestampMixin, WorkspaceScopedMixin

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceAPIKey(Base, TimestampMixin, WorkspaceScopedMixin):
    """Encrypted API key storage for AI providers.

    Implements BYOK (Bring Your Own Key) model per DD-002.
    Each workspace can have one key per provider (anthropic, openai, google).

    Attributes:
        workspace_id: Reference to parent workspace.
        provider: LLM provider name (anthropic, openai, google).
        encrypted_key: Fernet-encrypted API key.
        is_valid: Whether the key has been validated.
        last_validated_at: Last successful validation timestamp.
        validation_error: Error message from last failed validation.
    """

    __tablename__ = "workspace_api_keys"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", name="uq_workspace_api_keys_workspace_provider"
        ),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    # Provider (anthropic, openai, google)
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="LLM provider name",
    )

    # Encrypted API key (Supabase Vault or Fernet)
    encrypted_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Fernet-encrypted API key",
    )

    # Validation status
    is_valid: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Whether the key has been successfully validated",
    )

    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last successful validation",
    )

    validation_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message from last failed validation",
    )

    base_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Custom base URL for provider API",
    )

    model_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Default model name override",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="api_keys",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceAPIKey(workspace_id={self.workspace_id}, "
            f"provider={self.provider}, is_valid={self.is_valid})>"
        )
