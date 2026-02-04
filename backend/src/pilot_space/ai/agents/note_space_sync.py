"""Note Space Sync Service.

Bidirectional synchronization between database (TipTap JSONContent)
and agent workspace space folder (Markdown files).

When the PilotSpace AI agent processes a note, it needs the note content
available as a markdown file in the agent's workspace. This service syncs
note content between the database and the space folder.

Architecture:
- sync_note_to_space: DB (TipTap JSON) → Space (Markdown file)
- sync_space_to_note: Space (Markdown file) → DB diff computation
- Uses ContentConverter for TipTap ↔ Markdown conversion
- Uses NoteRepository for database access
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.application.services.note.content_converter import (
    BlockChange,
    ContentConverter,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class NoteSpaceSync:
    """Syncs note content between database and agent workspace space folder.

    Provides bidirectional synchronization:
    - To space: Loads note from DB, converts to Markdown, writes to space
    - From space: Reads Markdown, converts to TipTap, computes diff vs DB

    File structure in space:
        {space_path}/notes/note-{uuid}.md

    All Markdown files preserve block IDs via HTML comments for round-trip fidelity.
    """

    NOTES_DIR = "notes"

    def __init__(self, converter: ContentConverter | None = None) -> None:
        """Initialize NoteSpaceSync.

        Args:
            converter: ContentConverter instance for TipTap ↔ Markdown conversion.
                      If None, creates a new instance.
        """
        self._converter = converter or ContentConverter()

    def note_file_path(self, space_path: Path, note_id: UUID) -> Path:
        """Get the file path for a note's markdown file in the space.

        Args:
            space_path: Path to workspace root (from SpaceContext.path)
            note_id: UUID of the note

        Returns:
            Path to the markdown file: {space_path}/notes/note-{uuid}.md
        """
        return space_path / self.NOTES_DIR / f"note-{note_id}.md"

    async def sync_note_to_space(
        self,
        space_path: Path,
        note_id: UUID,
        session: AsyncSession,
    ) -> Path:
        """Load note from DB, convert to markdown, write to space folder.

        Workflow:
        1. Load note from database via NoteRepository
        2. Convert TipTap JSON to Markdown via ContentConverter
        3. Write markdown to {space_path}/notes/note-{uuid}.md
        4. Return the file path

        Args:
            space_path: Path to workspace root (from SpaceContext.path)
            note_id: UUID of the note to sync
            session: Database session for repository access

        Returns:
            Path to the written markdown file

        Raises:
            ValueError: If note not found in database
        """
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        # Load note from database
        repo = NoteRepository(session)
        note = await repo.get_by_id(note_id)
        if note is None:
            raise ValueError(f"Note not found: {note_id}")

        # Convert TipTap JSON to Markdown
        markdown = self._converter.tiptap_to_markdown(note.content)

        # Write to space folder
        return await self.write_note_markdown(space_path, note_id, markdown)

    async def sync_space_to_note(
        self,
        space_path: Path,
        note_id: UUID,
        session: AsyncSession,
    ) -> list[BlockChange]:
        """Read markdown from space, convert to TipTap, compute diff vs DB.

        Workflow:
        1. Read markdown from {space_path}/notes/note-{uuid}.md
        2. Convert Markdown to TipTap JSON via ContentConverter
        3. Load current note from database
        4. Compute block-level diff between space and database versions
        5. Return list of changes (for approval/application)

        This method does NOT modify the database. It only computes the diff.
        The caller is responsible for reviewing and applying changes.

        Args:
            space_path: Path to workspace root (from SpaceContext.path)
            note_id: UUID of the note to sync
            session: Database session for repository access

        Returns:
            List of block changes detected between space and database

        Raises:
            FileNotFoundError: If markdown file not found in space
            ValueError: If note not found in database
        """
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        # Read markdown from space
        markdown = await self.read_note_markdown(space_path, note_id)
        if markdown is None:
            raise FileNotFoundError(
                f"Note markdown file not found: {self.note_file_path(space_path, note_id)}"
            )

        # Convert Markdown to TipTap JSON
        new_content = self._converter.markdown_to_tiptap(markdown)

        # Load current note from database
        repo = NoteRepository(session)
        note = await repo.get_by_id(note_id)
        if note is None:
            raise ValueError(f"Note not found: {note_id}")

        # Compute block-level diff
        return self._converter.compute_block_diff(
            old_content=note.content,
            new_content=new_content,
        )

    async def read_note_markdown(self, space_path: Path, note_id: UUID) -> str | None:
        """Read the markdown file for a note from the space.

        Args:
            space_path: Path to workspace root (from SpaceContext.path)
            note_id: UUID of the note

        Returns:
            Markdown content as string, or None if file doesn't exist
        """
        def _read_sync():
            file_path = self.note_file_path(space_path, note_id)
            if not file_path.exists():
                return None
            return file_path.read_text(encoding="utf-8")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_sync)

    async def write_note_markdown(
        self,
        space_path: Path,
        note_id: UUID,
        markdown: str,
    ) -> Path:
        """Write markdown content for a note to the space folder.

        Creates the notes directory if it doesn't exist.
        Overwrites the file if it already exists.

        Args:
            space_path: Path to workspace root (from SpaceContext.path)
            note_id: UUID of the note
            markdown: Markdown content to write

        Returns:
            Path to the written file
        """
        def _write_sync():
            file_path = self.note_file_path(space_path, note_id)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(markdown, encoding="utf-8")
            return file_path

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _write_sync)
