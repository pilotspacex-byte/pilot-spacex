"""Repository for Yjs document state persistence.

Encapsulates raw SQL for the note_yjs_states table (binary blob store,
not a standard BaseModel entity). Parameterized queries only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class NoteYjsStateRepository:
    """Data access for note_yjs_states (note_id -> binary Yjs state)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_state(self, note_id: UUID) -> bytes | None:
        """Return persisted Yjs state bytes, or None if no state exists."""
        result = await self._session.execute(
            text("SELECT state FROM note_yjs_states WHERE note_id = :note_id"),
            {"note_id": str(note_id)},
        )
        row = result.fetchone()
        return bytes(row[0]) if row else None

    async def upsert_state(self, note_id: UUID, state: bytes) -> None:
        """Insert or replace Yjs state for the given note."""
        await self._session.execute(
            text(
                "INSERT INTO note_yjs_states (note_id, state, updated_at) "
                "VALUES (:note_id, :state, now()) "
                "ON CONFLICT (note_id) "
                "DO UPDATE SET state = EXCLUDED.state, updated_at = now()"
            ),
            {"note_id": str(note_id), "state": state},
        )
        await self._session.commit()
