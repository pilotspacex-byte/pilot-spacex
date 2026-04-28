"""Schemas for the AI chat message envelope (Phase 87.1 Plan 03).

This module ships the :class:`InlineArtifactRefSchema` carried on
assistant ``ChatMessage.artifacts`` per the contract defined at
``frontend/src/components/chat/InlineArtifactCard.tsx:62``:

.. code-block:: ts

    export interface InlineArtifactRef {
      id: string;
      type: ArtifactTokenKey;       // 'MD' | 'HTML' | …
      title?: string;
      updatedAt?: string;
      snippet?: string;
      projectName?: string;
      projectColor?: string;
      variant?: 'full' | 'group' | 'compact';
    }

The schema uses :class:`BaseSchema` so JSON is camelCase by default
(``updatedAt``, ``projectName``) — accepts both forms on input via
``populate_by_name=True``. ``variant`` and ``group`` from the
frontend type are intentionally NOT serialised: variant is derived
client-side from ``type`` (compact for tier-2 file types like MD/HTML)
and ``group`` is reserved for future grouped-artifact rendering.

The actual hydration logic lives in
:class:`pilot_space.application.services.ai.message_artifacts_resolver
.MessageArtifactsResolver`. The router layer
(``api/v1/routers/ai_sessions.py:resume_session``) calls the resolver
and attaches the resulting refs onto each assistant message's
``msg_dict["artifacts"]`` field — the response model
:class:`SessionResumeResponse` already accepts free-form
``messages: list[dict[str, Any]]``, so no schema change is required
there.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class InlineArtifactRefSchema(BaseSchema):
    """Lightweight artifact reference attached to assistant chat messages.

    Mirrors the frontend ``InlineArtifactRef`` contract verbatim. The
    backend NEVER includes a signed URL on this envelope — the frontend
    re-fetches via the existing ``/artifacts/{id}/url`` endpoint.

    Attributes:
        id: Artifact UUID (stable cross-session reference).
        type: Phase 85 :code:`ArtifactTokenKey` (``"MD"`` | ``"HTML"`` |
            …). Backend-derived from filename extension; not stored.
        title: Display title; backend supplies the original filename.
        updated_at: ISO 8601 timestamp; serialised as ``updatedAt``.
        snippet: Optional preview snippet (reserved; not populated in
            87.1).
        project_name: Project label when artifact is project-scoped;
            ``None`` for AI-generated artifacts.
    """

    id: UUID = Field(description="Artifact UUID")
    type: str = Field(
        description="ArtifactTokenKey ('MD' | 'HTML' | …) derived server-side"
    )
    title: str | None = Field(default=None, description="Display title (filename)")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp (ISO 8601)"
    )
    snippet: str | None = Field(
        default=None, description="Optional preview snippet (reserved)"
    )
    project_name: str | None = Field(
        default=None, description="Project label or null for AI-generated artifacts"
    )


class ChatMessageArtifactsEnvelope(BaseSchema):
    """Optional envelope for the `artifacts` field on assistant chat messages.

    Phase 87.1 Plan 03 ships this as a documentation contract for Wave 4
    — the actual chat-replay endpoint
    (``api/v1/routers/ai_sessions.py:resume_session``) returns
    ``SessionResumeResponse.messages`` typed as ``list[dict[str, Any]]``,
    so it carries this field as free-form JSON. Codifying the shape
    here gives the frontend a stable typed reference and the test suite
    a single place to assert on serialisation.
    """

    artifacts: list[InlineArtifactRefSchema] | None = Field(
        default=None,
        description=(
            "Inline artifact references attached by the resolver on chat "
            "reload. None when the message did not produce artifacts."
        ),
    )


__all__ = ["ChatMessageArtifactsEnvelope", "InlineArtifactRefSchema"]
