"""TDD tests for NoteAIUpdateService — AI-initiated note content updates.

Tests written FIRST (TDD red phase), implementation follows.
Separate from user autosave endpoint for audit trail and conflict detection.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pilot_space.application.services.note.ai_update_service import (
    AIUpdateOperation,
    AIUpdatePayload,
    NoteAIUpdateService,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async database session."""
    return AsyncMock()


@pytest.fixture
def mock_note_repo() -> AsyncMock:
    """Mock note repository."""
    return AsyncMock()


@pytest.fixture
def ai_update_service(mock_session: AsyncMock, mock_note_repo: AsyncMock) -> NoteAIUpdateService:
    """Create service instance with mocked session and repo."""
    return NoteAIUpdateService(session=mock_session, note_repository=mock_note_repo)


def _doc(*nodes: dict[str, Any]) -> dict[str, Any]:
    """Helper to wrap nodes in a TipTap doc."""
    return {"type": "doc", "content": list(nodes)}


def _p(text: str, block_id: str | None = None) -> dict[str, Any]:
    """Create a paragraph node."""
    node: dict[str, Any] = {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _heading(text: str, level: int = 1, block_id: str | None = None) -> dict[str, Any]:
    """Create a heading node."""
    node: dict[str, Any] = {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }
    if block_id:
        node["attrs"]["id"] = block_id
    return node


def _inline_issue(
    issue_id: str = "issue-uuid",
    issue_key: str = "PS-123",
    title: str = "Bug fix",
) -> dict[str, Any]:
    """Create an inlineIssue node."""
    return {
        "type": "inlineIssue",
        "attrs": {
            "issueId": issue_id,
            "issueKey": issue_key,
            "title": title,
        },
    }


# ============================================================
# Setup and initialization tests
# ============================================================


class TestServiceInitialization:
    """Test service initialization."""

    def test_that_service_initializes_with_session(
        self, mock_session: AsyncMock, mock_note_repo: AsyncMock
    ) -> None:
        """Verify service initialization with session."""
        service = NoteAIUpdateService(session=mock_session, note_repository=mock_note_repo)
        assert service is not None
        assert service._session == mock_session


# ============================================================
# Replace block operation tests
# ============================================================


class TestReplaceBlockOperation:
    """Test REPLACE_BLOCK operation."""

    @pytest.mark.asyncio
    async def test_that_replace_block_updates_target_block_content(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify replace_block updates the target block content."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())
        original_content = _doc(_p("Original text", block_id=block_id))
        new_block_content = _p("Updated text", block_id=block_id)

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=2,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block_id,
                content=new_block_content,
            )

            result = await ai_update_service.execute(payload)

            assert result.success is True
            assert result.note_id == note_id
            assert block_id in result.affected_block_ids
            assert result.conflict is False

            updated_content = result.updated_content
            assert updated_content["type"] == "doc"
            blocks = updated_content["content"]
            assert len(blocks) == 1
            assert blocks[0]["attrs"]["id"] == block_id
            text_nodes = blocks[0]["content"]
            assert any(t.get("text") == "Updated text" for t in text_nodes)

    @pytest.mark.asyncio
    async def test_that_replace_block_fails_for_missing_block_id(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify replace_block raises error when block_id not found."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        existing_block_id = str(uuid.uuid4())
        missing_block_id = str(uuid.uuid4())

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=_doc(_p("Original", block_id=existing_block_id)),
            word_count=1,
        )

        mock_note_repo.get_by_id.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=missing_block_id,
                content=_p("New text"),
            )

            with pytest.raises(ValueError, match="not found"):
                await ai_update_service.execute(payload)

    @pytest.mark.asyncio
    async def test_that_replace_block_fails_for_nonexistent_note(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify replace_block raises error when note doesn't exist."""
        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())

        mock_note_repo.get_by_id.return_value = None

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block_id,
                content=_p("New text"),
            )

            with pytest.raises(ValueError, match="not found"):
                await ai_update_service.execute(payload)

    @pytest.mark.asyncio
    async def test_that_replace_block_preserves_other_blocks(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify replace_block only updates target block and preserves others."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block1_id = str(uuid.uuid4())
        block2_id = str(uuid.uuid4())
        block3_id = str(uuid.uuid4())

        original_content = _doc(
            _p("Block 1", block_id=block1_id),
            _p("Block 2 - will be replaced", block_id=block2_id),
            _p("Block 3", block_id=block3_id),
        )

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=10,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block2_id,
                content=_p("Block 2 - UPDATED", block_id=block2_id),
            )

            result = await ai_update_service.execute(payload)

            assert result.success is True
            assert len(result.affected_block_ids) == 1
            assert block2_id in result.affected_block_ids

            blocks = result.updated_content["content"]
            assert len(blocks) == 3
            assert blocks[0]["attrs"]["id"] == block1_id
            assert blocks[0]["content"][0]["text"] == "Block 1"
            assert blocks[1]["attrs"]["id"] == block2_id
            assert blocks[1]["content"][0]["text"] == "Block 2 - UPDATED"
            assert blocks[2]["attrs"]["id"] == block3_id
            assert blocks[2]["content"][0]["text"] == "Block 3"


# ============================================================
# Append blocks operation tests
# ============================================================


class TestAppendBlocksOperation:
    """Test APPEND_BLOCKS operation."""

    @pytest.mark.asyncio
    async def test_that_append_blocks_inserts_after_target(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify append_blocks inserts new blocks after specified block."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block1_id = str(uuid.uuid4())
        block2_id = str(uuid.uuid4())
        new_block_id = str(uuid.uuid4())

        original_content = _doc(
            _p("Block 1", block_id=block1_id),
            _p("Block 2", block_id=block2_id),
        )

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=4,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            new_blocks = [_p("New Block", block_id=new_block_id)]

            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.APPEND_BLOCKS,
                after_block_id=block1_id,
                content={"blocks": new_blocks},
            )

            result = await ai_update_service.execute(payload)

            assert result.success is True
            assert new_block_id in result.affected_block_ids

            blocks = result.updated_content["content"]
            assert len(blocks) == 3
            assert blocks[0]["attrs"]["id"] == block1_id
            assert blocks[1]["attrs"]["id"] == new_block_id
            assert blocks[2]["attrs"]["id"] == block2_id

    @pytest.mark.asyncio
    async def test_that_append_blocks_at_end_when_no_after_block_id(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify append_blocks appends at end when no after_block_id."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block1_id = str(uuid.uuid4())
        new_block_id = str(uuid.uuid4())

        original_content = _doc(_p("Block 1", block_id=block1_id))

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=2,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            new_blocks = [_p("Appended Block", block_id=new_block_id)]

            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.APPEND_BLOCKS,
                content={"blocks": new_blocks},
            )

            result = await ai_update_service.execute(payload)

            assert result.success is True
            blocks = result.updated_content["content"]
            assert len(blocks) == 2
            assert blocks[0]["attrs"]["id"] == block1_id
            assert blocks[1]["attrs"]["id"] == new_block_id

    @pytest.mark.asyncio
    async def test_that_append_blocks_preserves_existing_content(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify append_blocks doesn't modify existing blocks."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block1_id = str(uuid.uuid4())
        block2_id = str(uuid.uuid4())
        new_block_id = str(uuid.uuid4())

        original_content = _doc(
            _heading("Title", level=1, block_id=block1_id),
            _p("Paragraph", block_id=block2_id),
        )

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=2,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            new_blocks = [_p("New content", block_id=new_block_id)]

            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.APPEND_BLOCKS,
                content={"blocks": new_blocks},
            )

            result = await ai_update_service.execute(payload)

            blocks = result.updated_content["content"]
            assert len(blocks) == 3
            assert blocks[0]["type"] == "heading"
            assert blocks[0]["attrs"]["level"] == 1
            assert blocks[0]["content"][0]["text"] == "Title"
            assert blocks[1]["type"] == "paragraph"
            assert blocks[1]["content"][0]["text"] == "Paragraph"


# ============================================================
# Insert inline issue operation tests
# ============================================================


class TestInsertInlineIssueOperation:
    """Test INSERT_INLINE_ISSUE operation."""

    @pytest.mark.asyncio
    async def test_that_insert_inline_issue_adds_node_to_block(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify insert_inline_issue adds inlineIssue node to block."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())

        original_content = _doc(_p("Check this: ", block_id=block_id))

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=2,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            issue_node = _inline_issue(
                issue_id="issue-1",
                issue_key="PS-99",
                title="Fix bug",
            )

            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.INSERT_INLINE_ISSUE,
                block_id=block_id,
                issue_data=issue_node,
            )

            result = await ai_update_service.execute(payload)

            assert result.success is True
            assert block_id in result.affected_block_ids

            blocks = result.updated_content["content"]
            assert len(blocks) == 1

            content_nodes = blocks[0]["content"]
            assert len(content_nodes) == 2
            assert content_nodes[0]["type"] == "text"
            assert content_nodes[0]["text"] == "Check this: "
            assert content_nodes[1]["type"] == "inlineIssue"
            assert content_nodes[1]["attrs"]["issueKey"] == "PS-99"
            assert content_nodes[1]["attrs"]["issueId"] == "issue-1"

    @pytest.mark.asyncio
    async def test_that_insert_inline_issue_preserves_existing_text(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify insert_inline_issue preserves existing paragraph text."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())

        original_content = _doc(
            {
                "type": "paragraph",
                "attrs": {"id": block_id},
                "content": [
                    {"type": "text", "text": "Start "},
                    {"type": "text", "marks": [{"type": "bold"}], "text": "bold"},
                    {"type": "text", "text": " end."},
                ],
            }
        )

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=original_content,
            word_count=4,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            issue_node = _inline_issue(issue_id="issue-2", issue_key="PS-100")

            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.INSERT_INLINE_ISSUE,
                block_id=block_id,
                issue_data=issue_node,
            )

            result = await ai_update_service.execute(payload)

            blocks = result.updated_content["content"]
            content_nodes = blocks[0]["content"]

            assert len(content_nodes) == 4
            assert content_nodes[0]["text"] == "Start "
            assert content_nodes[1]["text"] == "bold"
            assert content_nodes[1]["marks"][0]["type"] == "bold"
            assert content_nodes[2]["text"] == " end."
            assert content_nodes[3]["type"] == "inlineIssue"


# ============================================================
# Audit and metadata tests
# ============================================================


class TestAuditMetadata:
    """Test audit trail and metadata tracking."""

    @pytest.mark.asyncio
    async def test_that_result_includes_affected_block_ids(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify result includes all affected block IDs."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block1_id = str(uuid.uuid4())
        block2_id = str(uuid.uuid4())

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=_doc(
                _p("Block 1", block_id=block1_id),
                _p("Block 2", block_id=block2_id),
            ),
            word_count=4,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block1_id,
                content=_p("Updated", block_id=block1_id),
            )

            result = await ai_update_service.execute(payload)

            assert isinstance(result.affected_block_ids, list)
            assert block1_id in result.affected_block_ids

    @pytest.mark.asyncio
    async def test_that_result_includes_updated_content(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify result includes the complete updated content."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=_doc(_p("Original", block_id=block_id)),
            word_count=1,
        )

        mock_note_repo.get_by_id.return_value = mock_note
        mock_note_repo.update.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block_id,
                content=_p("Updated", block_id=block_id),
            )

            result = await ai_update_service.execute(payload)

            assert result.updated_content is not None
            assert result.updated_content["type"] == "doc"
            assert "content" in result.updated_content


# ============================================================
# Edge cases and error handling tests
# ============================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_that_empty_content_raises_error(
        self, ai_update_service: NoteAIUpdateService, mock_note_repo: AsyncMock
    ) -> None:
        """Verify empty content raises appropriate error."""
        from pilot_space.infrastructure.database.models.note import Note

        note_id = uuid.uuid4()
        block_id = str(uuid.uuid4())

        mock_note = Note(
            id=note_id,
            workspace_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Note",
            content=_doc(_p("Text", block_id=block_id)),
            word_count=1,
        )

        mock_note_repo.get_by_id.return_value = mock_note

        with patch(
            "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
            return_value=mock_note_repo,
        ):
            payload = AIUpdatePayload(
                note_id=note_id,
                operation=AIUpdateOperation.REPLACE_BLOCK,
                block_id=block_id,
                content=None,
            )

            with pytest.raises(ValueError, match="content"):
                await ai_update_service.execute(payload)
