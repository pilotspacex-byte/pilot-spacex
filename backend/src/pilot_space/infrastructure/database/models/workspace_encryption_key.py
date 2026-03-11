"""WorkspaceEncryptionKey SQLAlchemy model.

Stores the workspace-level Fernet key (encrypted with master key) for
envelope encryption of content fields (notes.body, issues.description).

Encryption is opt-in — workspaces without a record are in plaintext mode.

References:
- TENANT-02: Workspace BYOK encryption
- docs/DESIGN_DECISIONS.md
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base, TimestampMixin, WorkspaceScopedMixin

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceEncryptionKey(Base, TimestampMixin, WorkspaceScopedMixin):
    """Per-workspace encryption key stored via envelope encryption.

    The raw workspace Fernet key is encrypted with the system master key
    (ENCRYPTION_KEY env var) before storage. It is never returned to clients.

    One record per workspace (enforced by unique constraint on workspace_id).

    Attributes:
        id: Primary key UUID.
        workspace_id: Parent workspace (from WorkspaceScopedMixin).
        encrypted_workspace_key: Master-key-wrapped workspace Fernet key.
        key_hint: Last 8 chars of the raw key for UI identification.
        key_version: Monotonically increasing counter for key rotations.
    """

    __tablename__ = "workspace_encryption_keys"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            name="uq_workspace_encryption_key_workspace",
        ),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    # Master-key-encrypted workspace Fernet key — never exposed in API responses
    encrypted_workspace_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Fernet(master_key).encrypt(workspace_fernet_key)",
    )

    # Last 8 chars of the raw key for UI hint (not sensitive)
    key_hint: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        doc="Last 8 chars of raw key for identification",
    )

    # Previous master-encrypted key for dual-key fallback during rotation
    previous_encrypted_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Previous master-encrypted key for dual-key fallback during rotation",
    )

    # Monotonically increments on each PUT /encryption/key
    key_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        server_default="1",
        doc="Key version counter, increments on rotation",
    )

    # Relationship to parent workspace
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="encryption_key",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceEncryptionKey(workspace_id={self.workspace_id}, "
            f"key_version={self.key_version})>"
        )
