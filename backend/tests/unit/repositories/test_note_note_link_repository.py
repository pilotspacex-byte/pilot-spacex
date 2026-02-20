"""Unit tests for NoteNoteLinkRepository.

Tests CRUD operations and query methods for note-to-note links.
Uses in-memory SQLite database with transaction rollback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from pilot_space.infrastructure.database.models import (
    Note,
    User,
    Workspace,
)
from pilot_space.infrastructure.database.models.note_note_link import (
    NoteNoteLinkType,
)
from pilot_space.infrastructure.database.repositories.note_note_link_repository import (
    NoteNoteLinkRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(id=uuid4(), name="Test Workspace", slug="test-ws", owner_id=uuid4())
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a user for tests."""
    u = User(id=uuid4(), email="test@example.com", display_name="Test User")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def source_note(db_session: AsyncSession, workspace: Workspace, user: User) -> Note:
    """Create source note for tests."""
    note = Note(
        id=uuid4(),
        title="Source Note",
        workspace_id=workspace.id,
        owner_id=user.id,
    )
    db_session.add(note)
    await db_session.flush()
    return note


@pytest.fixture
async def target_note(db_session: AsyncSession, workspace: Workspace, user: User) -> Note:
    """Create target note for tests."""
    note = Note(
        id=uuid4(),
        title="Target Note",
        workspace_id=workspace.id,
        owner_id=user.id,
    )
    db_session.add(note)
    await db_session.flush()
    return note


@pytest.fixture
async def second_target(db_session: AsyncSession, workspace: Workspace, user: User) -> Note:
    """Create a second target note for tests."""
    note = Note(
        id=uuid4(),
        title="Second Target",
        workspace_id=workspace.id,
        owner_id=user.id,
    )
    db_session.add(note)
    await db_session.flush()
    return note


@pytest.fixture
def repo(db_session: AsyncSession) -> NoteNoteLinkRepository:
    """Create repository instance."""
    return NoteNoteLinkRepository(session=db_session)


class TestCreateLink:
    """Tests for create_link method."""

    async def test_create_inline_link(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Create an inline link between two notes."""
        link = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )

        assert link.id is not None
        assert link.source_note_id == source_note.id
        assert link.target_note_id == target_note.id
        assert link.link_type == NoteNoteLinkType.INLINE
        assert link.block_id is None
        assert link.workspace_id == workspace.id

    async def test_create_embed_link_with_block_id(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Create an embed link with a block_id."""
        link = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.EMBED,
            workspace_id=workspace.id,
            block_id="block-abc-123",
        )

        assert link.link_type == NoteNoteLinkType.EMBED
        assert link.block_id == "block-abc-123"

    async def test_create_multiple_links_to_different_targets(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
        second_target: Note,
    ) -> None:
        """Create links from one source to multiple targets."""
        link1 = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )
        link2 = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=second_target.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )

        assert link1.id != link2.id
        assert link1.target_note_id == target_note.id
        assert link2.target_note_id == second_target.id


class TestFindBySource:
    """Tests for find_by_source method."""

    async def test_find_outgoing_links(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
        second_target: Note,
    ) -> None:
        """Find all outgoing links from a source note."""
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=second_target.id,
            link_type=NoteNoteLinkType.EMBED,
            workspace_id=workspace.id,
        )

        links = await repo.find_by_source(
            source_note_id=source_note.id,
            workspace_id=workspace.id,
        )

        assert len(links) == 2

    async def test_find_by_source_empty(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
    ) -> None:
        """Return empty list when no outgoing links exist."""
        links = await repo.find_by_source(
            source_note_id=source_note.id,
            workspace_id=workspace.id,
        )

        assert links == []

    async def test_find_by_source_excludes_deleted(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Soft-deleted links are excluded from results."""
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )
        await repo.delete_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        links = await repo.find_by_source(
            source_note_id=source_note.id,
            workspace_id=workspace.id,
        )

        assert links == []


class TestFindByTarget:
    """Tests for find_by_target method (backlinks)."""

    async def test_find_backlinks(
        self,
        db_session: AsyncSession,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
        user: User,
    ) -> None:
        """Find all incoming links (backlinks) to a target note."""
        # Create another source note
        another_source = Note(
            id=uuid4(),
            title="Another Source",
            workspace_id=workspace.id,
            owner_id=user.id,
        )
        db_session.add(another_source)
        await db_session.flush()

        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )
        await repo.create_link(
            source_note_id=another_source.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.EMBED,
            workspace_id=workspace.id,
        )

        backlinks = await repo.find_by_target(
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        assert len(backlinks) == 2

    async def test_find_by_target_empty(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        target_note: Note,
    ) -> None:
        """Return empty list when no backlinks exist."""
        backlinks = await repo.find_by_target(
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        assert backlinks == []


class TestFindExisting:
    """Tests for find_existing method (idempotency check)."""

    async def test_find_existing_link(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Find an existing link by source+target+block_id."""
        created = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
            block_id="block-1",
        )

        found = await repo.find_existing(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            block_id="block-1",
            workspace_id=workspace.id,
        )

        assert found is not None
        assert found.id == created.id

    async def test_find_existing_with_null_block_id(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Find existing unanchored link (block_id=None)."""
        created = await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )

        found = await repo.find_existing(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            block_id=None,
            workspace_id=workspace.id,
        )

        assert found is not None
        assert found.id == created.id

    async def test_find_existing_returns_none_when_not_found(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Return None when no matching link exists."""
        found = await repo.find_existing(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            block_id=None,
            workspace_id=workspace.id,
        )

        assert found is None

    async def test_find_existing_different_block_id(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Different block_id returns None (not the same link)."""
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
            block_id="block-1",
        )

        found = await repo.find_existing(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            block_id="block-2",
            workspace_id=workspace.id,
        )

        assert found is None


class TestDeleteLink:
    """Tests for delete_link method."""

    async def test_soft_delete_link(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Soft-delete links between source and target."""
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )

        count = await repo.delete_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        assert count == 1

    async def test_delete_returns_zero_when_none_found(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Return 0 when no links exist to delete."""
        count = await repo.delete_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        assert count == 0

    async def test_delete_multiple_links_between_same_notes(
        self,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
    ) -> None:
        """Delete all links between two notes (different blocks)."""
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
            block_id="block-1",
        )
        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.EMBED,
            workspace_id=workspace.id,
            block_id="block-2",
        )

        count = await repo.delete_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            workspace_id=workspace.id,
        )

        assert count == 2


class TestWorkspaceIsolation:
    """Tests for workspace-scoped RLS enforcement."""

    async def test_find_by_source_respects_workspace(
        self,
        db_session: AsyncSession,
        repo: NoteNoteLinkRepository,
        workspace: Workspace,
        source_note: Note,
        target_note: Note,
        user: User,
    ) -> None:
        """Links from another workspace are not returned."""
        other_ws = Workspace(id=uuid4(), name="Other WS", slug="other-ws", owner_id=uuid4())
        db_session.add(other_ws)
        await db_session.flush()

        await repo.create_link(
            source_note_id=source_note.id,
            target_note_id=target_note.id,
            link_type=NoteNoteLinkType.INLINE,
            workspace_id=workspace.id,
        )

        # Query with wrong workspace should return empty
        links = await repo.find_by_source(
            source_note_id=source_note.id,
            workspace_id=other_ws.id,
        )

        assert links == []
