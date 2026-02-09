"""Unit tests for DigestJobHandler and DigestContextBuilder (H057).

Tests for DigestContextBuilder:
- Empty workspace returns zero chars
- Builds issues summary with state counts
- Budget truncation at MAX_CONTEXT_CHARS

Tests for DigestJobHandler:
- Skip on recent digest (cooldown)
- Skip on no activity
- Parse suggestions from valid JSON
- Parse suggestions from markdown code block
- Parse suggestions from invalid JSON returns empty list
- Fallback suggestions returns empty list
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.jobs.digest_context import DigestContextBuilder
from pilot_space.ai.jobs.digest_job import DigestJobHandler
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import State
from pilot_space.infrastructure.database.models.workspace_digest import (
    WorkspaceDigest,
)


@contextmanager
def _mock_advisory_lock():
    """Mock pg_try_advisory_xact_lock for SQLite test sessions."""
    original_execute = AsyncSession.execute

    async def _patched_execute(self, statement, *args, **kwargs):
        stmt_str = str(statement) if not isinstance(statement, str) else statement
        if "pg_try_advisory_xact_lock" in stmt_str:
            mock_result = MagicMock()
            mock_result.scalar.return_value = True
            return mock_result
        return await original_execute(self, statement, *args, **kwargs)

    with patch.object(AsyncSession, "execute", _patched_execute):
        yield


@pytest.mark.asyncio
class TestDigestContextBuilder:
    """Test suite for DigestContextBuilder."""

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_empty_workspace_zero_chars(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Empty workspace returns context with total_chars=0."""
        builder = DigestContextBuilder(db_session)

        context = await builder.build(workspace_id)

        assert context.workspace_id == workspace_id
        assert context.total_chars == 0
        assert len(context.sections) == 0

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_builds_issues_summary(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Builds issues summary with state group counts."""
        # Create project
        project = Project(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name="Test Project",
            identifier="TEST",
        )
        db_session.add(project)
        await db_session.flush()

        # Create states (using valid StateGroup enum values)
        state_backlog = State(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project.id,
            name="Backlog",
            group="unstarted",
            color="#999999",
        )
        state_started = State(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project.id,
            name="In Progress",
            group="started",
            color="#0000FF",
        )
        db_session.add(state_backlog)
        db_session.add(state_started)
        await db_session.flush()

        # Create issues (updated in last 7 days)
        now = datetime.now(tz=UTC)
        issue1 = Issue(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project.id,
            name="Issue 1",
            sequence_id=1,
            state_id=state_backlog.id,
            updated_at=now - timedelta(days=1),
        )
        issue2 = Issue(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            project_id=project.id,
            name="Issue 2",
            sequence_id=2,
            state_id=state_started.id,
            updated_at=now - timedelta(days=2),
        )
        db_session.add(issue1)
        db_session.add(issue2)
        await db_session.flush()

        builder = DigestContextBuilder(db_session)
        context = await builder.build(workspace_id)

        # Should have Issues Summary section
        assert "Issues Summary" in context.sections
        issues_text = context.sections["Issues Summary"]

        # Should contain counts
        assert "unstarted: 1" in issues_text
        assert "started: 1" in issues_text
        assert "Total: 2" in issues_text

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_budget_truncation(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Sections are truncated at MAX_CONTEXT_CHARS."""
        from pilot_space.ai.jobs.digest_context import MAX_CONTEXT_CHARS

        # Create many notes to exceed budget
        for i in range(100):
            note = Note(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                owner_id=user_id,
                title=f"Note {i}" * 50,  # Long title
                content='{"type": "doc", "content": []}',
                updated_at=datetime.now(tz=UTC) - timedelta(days=1),
            )
            db_session.add(note)
        await db_session.flush()

        builder = DigestContextBuilder(db_session)
        context = await builder.build(workspace_id)

        # Total chars should not exceed budget
        assert context.total_chars <= MAX_CONTEXT_CHARS

        # At least one section should be present
        assert len(context.sections) > 0


class TestDigestJobHandler:
    """Test suite for DigestJobHandler."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_seed_workspace")
    async def test_skip_on_recent_digest(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Returns 'skipped' if recent digest exists within cooldown."""
        # Create recent digest
        recent_digest = WorkspaceDigest(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            generated_at=datetime.now(tz=UTC) - timedelta(minutes=10),
            generated_by="scheduled",
            suggestions=json.dumps([]),
        )
        db_session.add(recent_digest)
        await db_session.flush()

        with _mock_advisory_lock():
            handler = DigestJobHandler(db_session)
            payload = {"workspace_id": str(workspace_id), "trigger": "scheduled"}

            result = await handler.handle(payload)

        assert result["status"] == "skipped"
        assert result["reason"] == "cooldown"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_seed_workspace")
    async def test_skip_on_no_activity(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Returns 'skipped' with reason 'no_activity' if workspace is empty."""
        with _mock_advisory_lock():
            handler = DigestJobHandler(db_session)
            payload = {"workspace_id": str(workspace_id), "trigger": "scheduled"}

            result = await handler.handle(payload)

        assert result["status"] == "skipped"
        assert result["reason"] == "no_activity"

    @pytest.mark.parametrize(
        ("response_text", "expected_count"),
        [
            # Valid JSON array
            (
                json.dumps(
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "category": "stale_issues",
                            "title": "Test",
                            "description": "Test desc",
                            "relevance_score": 0.8,
                        }
                    ]
                ),
                1,
            ),
            # Markdown code block
            (
                f"""```json
{
                    json.dumps(
                        [
                            {
                                "id": str(uuid.uuid4()),
                                "category": "unlinked_notes",
                                "title": "Test 2",
                                "description": "Test desc 2",
                                "relevance_score": 0.7,
                            }
                        ]
                    )
                }
```""",
                1,
            ),
        ],
    )
    def test_parse_suggestions_valid(
        self,
        response_text: str,
        expected_count: int,
    ) -> None:
        """Parse suggestions from valid JSON and markdown code blocks."""
        result = DigestJobHandler._parse_suggestions(response_text)

        assert isinstance(result, list)
        assert len(result) == expected_count
        if result:
            assert "id" in result[0]
            assert "category" in result[0]

    def test_parse_suggestions_invalid(self) -> None:
        """Invalid JSON returns empty list."""
        invalid_json = "This is not JSON at all"

        result = DigestJobHandler._parse_suggestions(invalid_json)

        assert result == []

    def test_fallback_suggestions(self) -> None:
        """Fallback suggestions returns empty list."""
        result = DigestJobHandler._fallback_suggestions()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_seed_workspace")
    async def test_generate_with_mocked_llm(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Test full flow with mocked LLM call."""
        # Create some activity
        note = Note(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            owner_id=user_id,
            title="Test Note",
            content='{"type": "doc", "content": []}',
            updated_at=datetime.now(tz=UTC) - timedelta(days=1),
        )
        db_session.add(note)
        await db_session.flush()

        # Mock Anthropic client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = json.dumps(
            [
                {
                    "id": str(uuid.uuid4()),
                    "category": "stale_issues",
                    "title": "Generated suggestion",
                    "description": "Test",
                    "relevance_score": 0.9,
                }
            ]
        )
        mock_response.content = [mock_text_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        # Patch lazy imports at their source modules
        with (
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
            patch("pilot_space.ai.infrastructure.key_storage.SecureKeyStorage") as mock_key_storage,
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_storage_instance = AsyncMock()
            mock_storage_instance.get_api_key = AsyncMock(return_value="fake-api-key")
            mock_key_storage.return_value = mock_storage_instance

            mock_settings_instance = MagicMock()
            mock_settings_instance.encryption_key.get_secret_value.return_value = (
                "fake-encryption-key"
            )
            mock_settings.return_value = mock_settings_instance

            with _mock_advisory_lock():
                handler = DigestJobHandler(db_session)
                payload = {"workspace_id": str(workspace_id), "trigger": "manual"}

                result = await handler.handle(payload)

            assert result["status"] == "completed"
            assert result["suggestion_count"] == 1
