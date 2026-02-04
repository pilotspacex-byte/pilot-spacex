"""Integration test for note sync in PilotSpaceAgent.

Tests that the agent correctly syncs note content to workspace before processing queries.

Reference: Task 1.1 - Wire Note Sync into Agent Stream
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent

if TYPE_CHECKING:
    from uuid import UUID


@pytest.fixture
def mock_deps() -> dict[str, Any]:
    """Create mock dependencies for PilotSpaceAgent."""
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(),
        "cost_tracker": MagicMock(),
        "resilient_executor": MagicMock(),
        "permission_handler": MagicMock(),
        "session_handler": None,
        "skill_registry": MagicMock(),
        "space_manager": None,
    }


@pytest.fixture
def agent(mock_deps: dict[str, Any]) -> PilotSpaceAgent:
    """Create PilotSpaceAgent instance with mock dependencies."""
    return PilotSpaceAgent(**mock_deps)


@pytest.fixture
def context() -> AgentContext:
    """Create test AgentContext."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


@pytest.fixture
def note_id() -> UUID:
    """Generate a test note ID."""
    return uuid4()


@pytest.fixture
def mock_note(note_id: UUID) -> MagicMock:
    """Create a mock Note object."""
    note = MagicMock()
    note.id = note_id
    note.title = "Test Note"
    note.content = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1, "id": "block-1"},
                "content": [{"type": "text", "text": "Test Heading"}],
            },
            {
                "type": "paragraph",
                "attrs": {"id": "block-2"},
                "content": [{"type": "text", "text": "Test paragraph content."}],
            },
        ],
    }
    return note


class TestNoteSyncIntegration:
    """Test suite for note sync integration in PilotSpaceAgent."""

    @pytest.mark.asyncio
    async def test_sync_note_if_present_syncs_when_note_in_context(
        self,
        agent: PilotSpaceAgent,
        note_id: UUID,
        mock_note: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify that _sync_note_if_present syncs note when present in context."""
        # Arrange
        chat_input = ChatInput(
            message="Test message",
            context={"note": mock_note},
        )

        # Mock the database session and repository
        mock_session = AsyncMock()
        mock_db_note = MagicMock()
        mock_db_note.id = note_id
        mock_db_note.content = mock_note.content

        with (
            patch("pilot_space.infrastructure.database.get_db_session") as mock_get_session,
            patch(
                "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository"
            ) as mock_repo_class,
        ):
            # Configure mocks
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_db_note
            mock_repo_class.return_value = mock_repo

            # Act
            await agent._sync_note_if_present(chat_input, tmp_path)

            # Assert
            mock_repo.get_by_id.assert_called_once_with(note_id)

            # Verify markdown file was created
            expected_file = tmp_path / "notes" / f"note-{note_id}.md"
            assert expected_file.exists()

            # Verify markdown content
            markdown_content = expected_file.read_text()
            assert "# Test Heading" in markdown_content
            assert "Test paragraph content." in markdown_content
            assert "<!-- block:block-1 -->" in markdown_content
            assert "<!-- block:block-2 -->" in markdown_content

    @pytest.mark.asyncio
    async def test_sync_note_if_present_skips_when_no_note_in_context(
        self,
        agent: PilotSpaceAgent,
        tmp_path: Path,
    ) -> None:
        """Verify that _sync_note_if_present skips sync when no note in context."""
        # Arrange
        chat_input = ChatInput(
            message="Test message",
            context={},  # No note
        )

        # Act
        with patch("pilot_space.infrastructure.database.get_db_session") as mock_get_session:
            await agent._sync_note_if_present(chat_input, tmp_path)

            # Assert - session should not be created
            mock_get_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_note_if_present_logs_error_on_failure(
        self,
        agent: PilotSpaceAgent,
        note_id: UUID,
        mock_note: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify that _sync_note_if_present logs error but doesn't raise on failure."""
        # Arrange
        chat_input = ChatInput(
            message="Test message",
            context={"note": mock_note},
        )

        # Mock database session to raise an error
        with patch("pilot_space.infrastructure.database.get_db_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.side_effect = RuntimeError(
                "Database connection failed"
            )

            # Act - should not raise exception
            await agent._sync_note_if_present(chat_input, tmp_path)

            # Assert - error should be logged
            assert any(
                "Failed to sync note" in record.message and record.levelname == "ERROR"
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_sync_note_if_present_skips_when_note_has_no_id(
        self,
        agent: PilotSpaceAgent,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify that _sync_note_if_present skips sync when note has no id attribute."""
        # Arrange
        mock_note_no_id = MagicMock(spec=[])  # No 'id' attribute
        chat_input = ChatInput(
            message="Test message",
            context={"note": mock_note_no_id},
        )

        # Act
        with patch("pilot_space.infrastructure.database.get_db_session") as mock_get_session:
            await agent._sync_note_if_present(chat_input, tmp_path)

            # Assert - session should not be created
            mock_get_session.assert_not_called()

            # Warning should be logged
            assert any(
                "Note object missing 'id' attribute" in record.message
                and record.levelname == "WARNING"
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_sync_note_performance(
        self,
        agent: PilotSpaceAgent,
        note_id: UUID,
        tmp_path: Path,
    ) -> None:
        """Verify that note sync completes within performance threshold."""
        # Arrange - Create a large note (1000 blocks)
        large_content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": f"block-{i}"},
                    "content": [
                        {
                            "type": "text",
                            "text": f"Paragraph {i} with some test content that is reasonably long.",
                        }
                    ],
                }
                for i in range(1000)
            ],
        }

        mock_note = MagicMock()
        mock_note.id = note_id
        mock_note.content = large_content

        chat_input = ChatInput(
            message="Test message",
            context={"note": mock_note},
        )

        mock_session = AsyncMock()
        mock_db_note = MagicMock()
        mock_db_note.id = note_id
        mock_db_note.content = large_content

        # Act & Assert
        import time

        with (
            patch("pilot_space.infrastructure.database.get_db_session") as mock_get_session,
            patch(
                "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository"
            ) as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_db_note
            mock_repo_class.return_value = mock_repo

            start_time = time.time()
            await agent._sync_note_if_present(chat_input, tmp_path)
            elapsed_time = time.time() - start_time

            # Assert - sync should complete in < 100ms for 1000 blocks
            assert elapsed_time < 0.1, (
                f"Note sync took {elapsed_time * 1000:.2f}ms, expected < 100ms"
            )

            # Verify file was created
            expected_file = tmp_path / "notes" / f"note-{note_id}.md"
            assert expected_file.exists()
