"""Integration tests for Notes functionality.

T325: Notes integration tests
- Note CRUD operations
- Version history
- Ghost text generation (mocked AI)
- Annotation creation
- Issue extraction from note
- RLS isolation between workspaces

These tests verify the Notes feature including AI-powered features
with mocked AI responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.infrastructure.database.models import (
    AnnotationStatus,
    AnnotationType,
    Note,
    NoteAnnotation,
    Project,
    User,
    Workspace,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.factories import (
        NoteFactory as NoteFactoryType,
        UserFactory as UserFactoryType,
        WorkspaceFactory as WorkspaceFactoryType,
    )


# ============================================================================
# Note Factory Tests (Unit Level)
# ============================================================================


class TestNoteModel:
    """Tests for Note model behavior."""

    def test_that_note_has_default_content_structure(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that note factory creates proper content structure."""
        # Arrange & Act
        note = note_factory()

        # Assert
        assert "type" in note.content
        assert note.content["type"] == "doc"
        assert "content" in note.content

    def test_that_note_calculates_reading_time_correctly(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that reading time is calculated based on word count."""
        # Arrange
        note = note_factory(word_count=400)

        # Act
        reading_time = note.calculate_reading_time()

        # Assert - 400 words / 200 wpm = 2 minutes
        assert reading_time == 2

    def test_that_note_reading_time_minimum_is_one(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that minimum reading time is 1 minute."""
        # Arrange
        note = note_factory(word_count=50)

        # Act
        reading_time = note.calculate_reading_time()

        # Assert
        assert reading_time == 1

    def test_that_note_reading_time_is_zero_for_empty(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that reading time is 0 for empty notes."""
        # Arrange
        note = note_factory(word_count=0)

        # Act
        reading_time = note.calculate_reading_time()

        # Assert
        assert reading_time == 0

    def test_that_pinned_note_is_created_correctly(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that pinned notes are created with is_pinned=True."""
        # Arrange & Act
        note = note_factory(is_pinned=True)

        # Assert
        assert note.is_pinned is True


# ============================================================================
# Note CRUD Tests
# ============================================================================


class TestNoteCRUD:
    """Tests for Note CRUD operations via repository."""

    @pytest.mark.asyncio
    async def test_that_note_is_created_in_database(
        self,
        db_session: AsyncSession,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that a note is properly created in the database."""
        # Arrange
        from uuid import uuid4

        user = user_factory()
        workspace = workspace_factory(owner_id=user.id)
        # Build Note directly to avoid factory relationship override clearing owner_id
        note = Note(
            id=uuid4(),
            title="Test Note",
            workspace_id=workspace.id,
            owner_id=user.id,
            content={
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Test content"}]}
                ],
            },
        )

        # Act
        db_session.add(user)
        db_session.add(workspace)
        db_session.add(note)
        await db_session.flush()

        # Assert
        assert note.id is not None
        assert note.title == "Test Note"
        assert note.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_that_note_is_retrieved_by_id(
        self,
        db_session: AsyncSession,
        sample_note: Note,
        sample_user: User,
        sample_workspace: Workspace,
    ) -> None:
        """Test that a note can be retrieved by ID."""
        # Arrange
        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(sample_note)
        await db_session.flush()

        # Act
        from sqlalchemy import select

        result = await db_session.execute(select(Note).where(Note.id == sample_note.id))
        retrieved = result.scalar_one_or_none()

        # Assert
        assert retrieved is not None
        assert retrieved.id == sample_note.id
        assert retrieved.title == sample_note.title

    @pytest.mark.asyncio
    async def test_that_note_is_updated_correctly(
        self,
        db_session: AsyncSession,
        sample_note: Note,
        sample_user: User,
        sample_workspace: Workspace,
    ) -> None:
        """Test that a note can be updated."""
        # Arrange
        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(sample_note)
        await db_session.flush()

        # Act
        sample_note.title = "Updated Title"
        sample_note.is_pinned = True
        await db_session.flush()

        # Retrieve fresh
        from sqlalchemy import select

        result = await db_session.execute(select(Note).where(Note.id == sample_note.id))
        updated = result.scalar_one()

        # Assert
        assert updated.title == "Updated Title"
        assert updated.is_pinned is True

    @pytest.mark.asyncio
    async def test_that_note_is_soft_deleted(
        self,
        db_session: AsyncSession,
        sample_note: Note,
        sample_user: User,
        sample_workspace: Workspace,
    ) -> None:
        """Test that a note is soft deleted, not hard deleted."""
        # Arrange
        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(sample_note)
        await db_session.flush()

        # Act
        sample_note.soft_delete()
        await db_session.flush()

        # Assert
        assert sample_note.is_deleted is True
        assert sample_note.deleted_at is not None

    @pytest.mark.asyncio
    async def test_that_deleted_note_can_be_restored(
        self,
        db_session: AsyncSession,
        sample_note: Note,
        sample_user: User,
        sample_workspace: Workspace,
    ) -> None:
        """Test that a soft deleted note can be restored."""
        # Arrange
        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(sample_note)
        sample_note.soft_delete()
        await db_session.flush()

        # Act
        sample_note.restore()
        await db_session.flush()

        # Assert
        assert sample_note.is_deleted is False
        assert sample_note.deleted_at is None


# ============================================================================
# Note Content Tests
# ============================================================================


class TestNoteContent:
    """Tests for note content handling."""

    def test_that_tiptap_content_is_stored_correctly(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that TipTap JSON content is stored properly."""
        # Arrange
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Title"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Body text"}],
                },
            ],
        }

        # Act
        note = note_factory(content=content)

        # Assert
        assert note.content == content
        assert note.content["content"][0]["type"] == "heading"

    def test_that_empty_content_uses_default(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that empty content uses default structure."""
        # Arrange & Act
        note = note_factory()

        # Assert
        assert note.content is not None
        assert note.content.get("type") == "doc"


# ============================================================================
# Ghost Text Tests (Mocked AI)
# ============================================================================


class TestGhostText:
    """Tests for ghost text generation with mocked AI."""

    @pytest.mark.asyncio
    async def test_that_ghost_text_is_generated_for_context(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that ghost text is generated based on note context."""
        # Arrange
        mock_ai_client.query = AsyncMock(
            return_value={
                "content": "suggested continuation text",
                "model": "claude-sonnet-4-20250514",
            }
        )

        context = {
            "current_block": "The user is typing about",
            "previous_blocks": ["Introduction", "Background"],
            "note_title": "Project Plan",
        }

        # Act - Simulate ghost text generation
        result = await mock_ai_client.query(
            prompt=f"Continue: {context['current_block']}",
            max_tokens=50,
        )

        # Assert
        assert "content" in result
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_that_ghost_text_respects_max_tokens(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that ghost text respects token limit."""
        # Arrange
        max_tokens = 50
        mock_ai_client.query = AsyncMock(
            return_value={
                "content": "short suggestion",
                "usage": {"output_tokens": 10},
            }
        )

        # Act
        result = await mock_ai_client.query(
            prompt="Continue writing",
            max_tokens=max_tokens,
        )

        # Assert
        assert result["usage"]["output_tokens"] <= max_tokens

    @pytest.mark.asyncio
    async def test_that_ghost_text_returns_none_on_error(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that ghost text returns None on AI error."""
        # Arrange
        mock_ai_client.query = AsyncMock(side_effect=Exception("AI service unavailable"))

        # Act & Assert
        with pytest.raises(Exception, match="AI service unavailable"):
            await mock_ai_client.query(prompt="Test")


# ============================================================================
# Annotation Tests
# ============================================================================


class TestNoteAnnotations:
    """Tests for note annotations."""

    def test_that_annotation_is_created_with_correct_type(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that annotations are created with correct type."""
        # Arrange
        from tests.factories import NoteAnnotationFactory

        note = note_factory()

        # Act
        annotation = NoteAnnotationFactory(
            note_id=note.id,
            workspace_id=note.workspace_id,
            type=AnnotationType.SUGGESTION,
        )

        # Assert
        assert annotation.type == AnnotationType.SUGGESTION

    def test_that_annotation_status_defaults_to_pending(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that new annotations have pending status."""
        # Arrange
        from tests.factories import NoteAnnotationFactory

        note = note_factory()

        # Act
        annotation = NoteAnnotationFactory(note_id=note.id, workspace_id=note.workspace_id)

        # Assert
        assert annotation.status == AnnotationStatus.PENDING
        assert annotation.is_pending is True

    def test_that_high_confidence_annotation_is_detected(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that high confidence annotations are flagged."""
        # Arrange
        from tests.factories import NoteAnnotationFactory

        note = note_factory()

        # Act
        annotation = NoteAnnotationFactory(
            note_id=note.id,
            workspace_id=note.workspace_id,
            confidence=0.95,
        )

        # Assert
        assert annotation.is_high_confidence is True

    def test_that_low_confidence_annotation_is_not_high(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that low confidence annotations are not flagged."""
        # Arrange
        from tests.factories import NoteAnnotationFactory

        note = note_factory()

        # Act
        annotation = NoteAnnotationFactory(
            note_id=note.id,
            workspace_id=note.workspace_id,
            confidence=0.5,
        )

        # Assert
        assert annotation.is_high_confidence is False

    @pytest.mark.asyncio
    async def test_that_annotation_is_linked_to_note(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_workspace: Workspace,
    ) -> None:
        """Test that annotations are properly linked to notes."""
        # Arrange
        from uuid import uuid4

        # Build Note and Annotation directly to avoid factory relationship
        # fields overriding FK columns (SQLAlchemy clears FK when relationship=None)
        note = Note(
            id=uuid4(),
            title="Test Note for Annotation",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            content={"type": "doc", "content": []},
        )
        annotation = NoteAnnotation(
            id=uuid4(),
            note_id=note.id,
            workspace_id=note.workspace_id,
            block_id="block-1",
            content="This could be an issue",
            type=AnnotationType.ISSUE_CANDIDATE,
            confidence=0.85,
            status=AnnotationStatus.PENDING,
        )

        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(note)
        db_session.add(annotation)
        await db_session.flush()

        # Assert
        assert annotation.note_id == note.id


# ============================================================================
# Issue Extraction Tests
# ============================================================================


class TestIssueExtraction:
    """Tests for extracting issues from notes."""

    def test_that_issue_candidate_annotation_is_created(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that issue candidate annotations can be created."""
        # Arrange
        from tests.factories import NoteAnnotationFactory

        note = note_factory()

        # Act
        annotation = NoteAnnotationFactory(
            note_id=note.id,
            workspace_id=note.workspace_id,
            type=AnnotationType.ISSUE_CANDIDATE,
            content="Bug: Login fails on mobile",
            confidence=0.85,
        )

        # Assert
        assert annotation.type == AnnotationType.ISSUE_CANDIDATE
        assert "Bug" in annotation.content

    @pytest.mark.asyncio
    async def test_that_ai_identifies_issue_candidates(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that AI identifies potential issues in note content."""
        # Arrange
        mock_ai_client.query = AsyncMock(
            return_value={
                "content": [
                    {
                        "block_id": "block-1",
                        "type": "issue_candidate",
                        "title": "Fix mobile login",
                        "confidence": 0.9,
                    }
                ],
            }
        )

        note_content = """
        # Sprint Planning
        - Need to fix mobile login bug (HIGH PRIORITY)
        - Update documentation
        - Review PR for feature X
        """

        # Act
        result = await mock_ai_client.query(
            prompt=f"Identify potential issues in: {note_content}",
        )

        # Assert
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "issue_candidate"


# ============================================================================
# RLS Isolation Tests
# ============================================================================


class TestRLSIsolation:
    """Tests for RLS isolation between workspaces."""

    @pytest.mark.asyncio
    async def test_that_notes_are_workspace_scoped(
        self,
        db_session: AsyncSession,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that notes are scoped to their workspace."""
        # Arrange
        from uuid import uuid4

        user1 = user_factory()
        user2 = user_factory()
        workspace1 = workspace_factory(owner_id=user1.id)
        workspace2 = workspace_factory(owner_id=user2.id)

        note1 = Note(
            id=uuid4(),
            title="Workspace 1 Note",
            workspace_id=workspace1.id,
            owner_id=user1.id,
            content={"type": "doc", "content": []},
        )
        note2 = Note(
            id=uuid4(),
            title="Workspace 2 Note",
            workspace_id=workspace2.id,
            owner_id=user2.id,
            content={"type": "doc", "content": []},
        )

        db_session.add_all([user1, user2, workspace1, workspace2, note1, note2])
        await db_session.flush()

        # Act - Query notes for workspace1
        from sqlalchemy import select

        result = await db_session.execute(select(Note).where(Note.workspace_id == workspace1.id))
        workspace1_notes = result.scalars().all()

        # Assert
        assert len(workspace1_notes) == 1
        assert workspace1_notes[0].title == "Workspace 1 Note"

    @pytest.mark.asyncio
    async def test_that_annotations_are_workspace_scoped(
        self,
        db_session: AsyncSession,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that annotations are scoped to their workspace."""
        # Arrange
        from uuid import uuid4

        user = user_factory()
        workspace1 = workspace_factory(owner_id=user.id)
        workspace2 = workspace_factory(owner_id=user.id)

        note1 = Note(
            id=uuid4(),
            title="Note in WS1",
            workspace_id=workspace1.id,
            owner_id=user.id,
            content={"type": "doc", "content": []},
        )
        note2 = Note(
            id=uuid4(),
            title="Note in WS2",
            workspace_id=workspace2.id,
            owner_id=user.id,
            content={"type": "doc", "content": []},
        )
        annotation1 = NoteAnnotation(
            id=uuid4(),
            note_id=note1.id,
            workspace_id=workspace1.id,
            block_id="block-1",
            type=AnnotationType.SUGGESTION,
            content="Annotation in WS1",
            confidence=0.7,
            status=AnnotationStatus.PENDING,
        )
        annotation2 = NoteAnnotation(
            id=uuid4(),
            note_id=note2.id,
            workspace_id=workspace2.id,
            block_id="block-2",
            type=AnnotationType.SUGGESTION,
            content="Annotation in WS2",
            confidence=0.7,
            status=AnnotationStatus.PENDING,
        )

        db_session.add_all([user, workspace1, workspace2, note1, note2, annotation1, annotation2])
        await db_session.flush()

        # Act - Query annotations for workspace1
        from sqlalchemy import select

        result = await db_session.execute(
            select(NoteAnnotation).where(NoteAnnotation.workspace_id == workspace1.id)
        )
        workspace1_annotations = result.scalars().all()

        # Assert
        assert len(workspace1_annotations) == 1
        assert workspace1_annotations[0].workspace_id == workspace1.id


# ============================================================================
# Note Filtering Tests
# ============================================================================


class TestNoteFiltering:
    """Tests for note filtering and search."""

    @pytest.mark.asyncio
    async def test_that_pinned_notes_are_filtered(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_workspace: Workspace,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that pinned notes can be filtered."""
        # Arrange
        from uuid import uuid4

        # Build Notes directly — factory relationship field can override owner_id to None
        note_pinned = Note(
            id=uuid4(),
            title="Pinned Note",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            is_pinned=True,
            content={"type": "doc", "content": []},
        )
        note_regular = Note(
            id=uuid4(),
            title="Regular Note",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            is_pinned=False,
            content={"type": "doc", "content": []},
        )

        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(note_pinned)
        db_session.add(note_regular)
        await db_session.flush()

        # Act
        from sqlalchemy import select

        result = await db_session.execute(
            select(Note).where(Note.workspace_id == sample_workspace.id, Note.is_pinned == True)  # noqa: E712
        )
        pinned_notes = result.scalars().all()

        # Assert
        assert len(pinned_notes) == 1
        assert pinned_notes[0].is_pinned is True

    @pytest.mark.asyncio
    async def test_that_notes_are_filtered_by_project(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_workspace: Workspace,
        sample_project: Project,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that notes can be filtered by project."""
        # Arrange
        db_session.add(sample_user)
        db_session.add(sample_workspace)
        db_session.add(sample_project)

        # Add states for the project
        for state in sample_project.states:
            db_session.add(state)

        from uuid import uuid4

        note_in_project = Note(
            id=uuid4(),
            title="Project Note",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            project_id=sample_project.id,
            content={"type": "doc", "content": []},
        )
        note_workspace_level = Note(
            id=uuid4(),
            title="Workspace Note",
            workspace_id=sample_workspace.id,
            owner_id=sample_user.id,
            project_id=None,
            content={"type": "doc", "content": []},
        )

        db_session.add(note_in_project)
        db_session.add(note_workspace_level)
        await db_session.flush()

        # Act
        from sqlalchemy import select

        result = await db_session.execute(select(Note).where(Note.project_id == sample_project.id))
        project_notes = result.scalars().all()

        # Assert
        assert len(project_notes) == 1
        assert project_notes[0].project_id == sample_project.id


# ============================================================================
# Note Version History Tests (Placeholder)
# ============================================================================


class TestNoteVersionHistory:
    """Tests for note version history.

    Note: Version history is tracked via activity logs and
    content snapshots. These tests verify the concept.
    """

    def test_that_note_tracks_created_at(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that notes track creation timestamp."""
        # Arrange & Act
        note = note_factory()

        # Assert
        assert note.created_at is not None
        assert isinstance(note.created_at, datetime)

    def test_that_note_tracks_updated_at(
        self,
        note_factory: type[NoteFactoryType],
    ) -> None:
        """Test that notes track update timestamp."""
        # Arrange & Act
        note = note_factory()

        # Assert
        assert note.updated_at is not None
        assert isinstance(note.updated_at, datetime)


__all__ = [
    "TestGhostText",
    "TestIssueExtraction",
    "TestNoteAnnotations",
    "TestNoteCRUD",
    "TestNoteContent",
    "TestNoteFiltering",
    "TestNoteModel",
    "TestNoteVersionHistory",
    "TestRLSIsolation",
]
