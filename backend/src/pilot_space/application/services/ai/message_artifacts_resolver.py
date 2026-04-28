"""MessageArtifactsResolver — Phase 87.1 Plan 03.

Hydrates the ``InlineArtifactRefSchema`` envelope for assistant chat
messages on reload. Persisted ``AIMessage.metadata['artifact_ids']`` is
opaque storage — the API serialises it into the same lightweight shape
the frontend's :code:`InlineArtifactCard` expects (verified at
``frontend/src/components/chat/InlineArtifactCard.tsx:62``).

Filename → ArtifactTokenKey mapping (single source of truth, no DB
column):

    ``*.md``  → ``type='MD'``
    ``*.html`` → ``type='HTML'``

Unknown extensions are silently dropped — the InlineArtifactRef contract
requires a typed ``type`` and emitting an unknown value would crash the
frontend renderer. Future formats (PDF, DOCX, …) extend the map in
Phase 87.2/87.3.

Workspace isolation is enforced at the repository query
(``WHERE workspace_id = :ws AND is_deleted = false AND status = 'ready'``)
so cross-workspace ids in adversarially-tampered metadata are dropped
silently (T-87.1-03-01). The resolver also caps ids at 50 per message
before the query (defence in depth — extraction-time cap lives in
``pilotspace_stream_utils.extract_artifact_ids_from_blocks``).

Signed URLs are NEVER produced or persisted here. The frontend
re-fetches them on demand via the existing ``/artifacts/{id}/url``
endpoint (T-87.1-03-03 information disclosure mitigation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from pilot_space.api.v1.schemas.ai_messages import InlineArtifactRefSchema

if TYPE_CHECKING:
    from datetime import datetime


# Hardcoded extension → ArtifactTokenKey map. Keep in sync with the
# Phase 85 ArtifactTokenKey enum on the frontend
# (`frontend/src/lib/artifact-tokens.ts`). Extensions are checked
# case-insensitively. The map is intentionally small — Phase 87.1
# ships MD + HTML only; 87.2 extends to DOCX/XLSX, 87.3 to PDF.
_EXT_TO_TYPE: dict[str, str] = {
    ".md": "MD",
    ".html": "HTML",
}

# Defence-in-depth cap on artifact_ids per message at resolver time.
# extract_artifact_ids_from_blocks already caps at 50 at write time
# (T-87.1-03-05) — duplicating here so an adversarially-crafted JSONB
# row can't exhaust the batch query.
_PER_MESSAGE_CAP = 50


class _ArtifactRow(Protocol):
    """Minimal contract the resolver needs from a fetched artifact row."""

    id: UUID
    workspace_id: UUID
    filename: str
    is_deleted: bool
    status: str
    updated_at: datetime


class _ArtifactBatchRepo(Protocol):
    async def list_by_ids_for_workspace(
        self,
        ids: list[UUID],
        workspace_id: UUID,
    ) -> list[_ArtifactRow]: ...


@dataclass(frozen=True)
class ResolveArtifactsPayload:
    """Input to :meth:`MessageArtifactsResolver.resolve`.

    Attributes:
        workspace_id: Caller's workspace; the resolver filters all rows
            by this. Must come from the authenticated session, NOT from
            user input or message metadata.
        metadata_by_message_id: Map of assistant-message ``id`` →
            ``AIMessage.metadata`` dict (or ``None``). Only entries
            whose metadata carries a non-empty ``artifact_ids`` list
            participate in the batch query.
    """

    workspace_id: UUID
    metadata_by_message_id: dict[UUID, dict[str, Any] | None]


class MessageArtifactsResolver:
    """Hydrates per-message ``InlineArtifactRefSchema`` lists from JSONB
    metadata.

    Single batched SELECT for the union of all referenced ids — avoids
    N+1 across messages on chat reload.
    """

    def __init__(self, *, repo: _ArtifactBatchRepo) -> None:
        self._repo = repo

    async def resolve(
        self,
        payload: ResolveArtifactsPayload,
    ) -> dict[UUID, list[InlineArtifactRefSchema]]:
        # 1. Collect referenced ids per message, capped at _PER_MESSAGE_CAP.
        ids_by_message: dict[UUID, list[UUID]] = {}
        all_ids: set[UUID] = set()
        for msg_id, meta in payload.metadata_by_message_id.items():
            if not meta:
                continue
            raw = meta.get("artifact_ids")
            if not isinstance(raw, list):
                continue
            parsed: list[UUID] = []
            for entry in raw[:_PER_MESSAGE_CAP]:
                if not isinstance(entry, str):
                    continue
                try:
                    parsed.append(UUID(entry))
                except (ValueError, TypeError):
                    continue
            if parsed:
                ids_by_message[msg_id] = parsed
                all_ids.update(parsed)

        if not all_ids:
            return {}

        # 2. Single batched fetch (workspace + lifecycle filters in repo).
        rows = await self._repo.list_by_ids_for_workspace(
            ids=list(all_ids),
            workspace_id=payload.workspace_id,
        )
        rows_by_id: dict[UUID, _ArtifactRow] = {r.id: r for r in rows}

        # 3. Build per-message ref lists, preserving the original order
        #    of artifact_ids in metadata. Drop unresolved ids silently —
        #    they may be cross-workspace, deleted, pending_upload, or
        #    have an unknown extension.
        out: dict[UUID, list[InlineArtifactRefSchema]] = {}
        for msg_id, ids in ids_by_message.items():
            refs: list[InlineArtifactRefSchema] = []
            for aid in ids:
                row = rows_by_id.get(aid)
                if row is None:
                    continue
                ref = _row_to_ref(row)
                if ref is not None:
                    refs.append(ref)
            if refs:
                out[msg_id] = refs
        return out


def _row_to_ref(row: _ArtifactRow) -> InlineArtifactRefSchema | None:
    """Build an InlineArtifactRefSchema from an artifact row.

    Returns ``None`` when the filename's extension is not in
    ``_EXT_TO_TYPE`` — emitting an unknown ``type`` would violate the
    frontend ArtifactTokenKey contract.
    """
    fname = row.filename or ""
    lower = fname.lower()
    type_key: str | None = None
    for ext, token in _EXT_TO_TYPE.items():
        if lower.endswith(ext):
            type_key = token
            break
    if type_key is None:
        return None
    return InlineArtifactRefSchema(
        id=row.id,
        type=type_key,
        title=fname,
        updated_at=row.updated_at,
    )


__all__ = [
    "MessageArtifactsResolver",
    "ResolveArtifactsPayload",
]
