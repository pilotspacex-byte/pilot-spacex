"""Unit tests for CreateNoteFromChatService (H056).

Tests:
- Creates note from chat session
- TipTap blocks structure (blockquotes for user, paragraphs for assistant)
- Session not found raises ValueError
- Empty session creates note with empty paragraph
- System messages excluded from content
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from pilot_space.application.services.note.create_note_from_chat_service import (
    CreateNoteFromChatPayload,
    CreateNoteFromChatService,
)
from pilot_space.infrastructure.database.models.note import Note


def _insert_ai_session(
    session_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str = "Test Chat",
) -> text:
    """Build raw SQL INSERT for an ai_session to avoid ORM selectin issues."""
    return text(
        """
        INSERT INTO ai_sessions (id, workspace_id, user_id, agent_name, session_data, expires_at, created_at, updated_at)
        VALUES (:id, :ws, :uid, :agent, :data, :exp, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    ), {
        "id": str(session_id),
        "ws": str(workspace_id),
        "uid": str(user_id),
        "agent": "pilot_space",
        "data": "{}",
        "exp": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
    }


def _insert_ai_message(
    msg_id: uuid.UUID,
    session_id: uuid.UUID,
    role: str,
    content: str,
) -> tuple:
    """Build raw SQL INSERT for an ai_message."""
    return text(
        """
        INSERT INTO ai_messages (id, session_id, role, content, created_at)
        VALUES (:id, :sid, :role, :content, CURRENT_TIMESTAMP)
        """
    ), {
        "id": str(msg_id),
        "sid": str(session_id),
        "role": role,
        "content": content,
    }


async def _create_note_via_service(
    db_session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    title: str,
) -> uuid.UUID:
    """Execute service with patched get/refresh to avoid selectin greenlet issues.

    SQLite stores UUIDs as TEXT, so ``session.get(AISession, uuid_obj)`` fails.
    We patch ``session.get`` to use a raw SELECT and manually attach messages,
    and patch ``session.refresh`` to no-op (avoids selectin cascade).
    """
    from pilot_space.infrastructure.database.models.ai_message import AIMessage
    from pilot_space.infrastructure.database.models.ai_session import AISession

    service = CreateNoteFromChatService(db_session)
    payload = CreateNoteFromChatPayload(
        workspace_id=workspace_id,
        user_id=user_id,
        chat_session_id=session_id,
        title=title,
    )

    # Replacement for session.get that works with SQLite TEXT UUIDs
    _original_get = db_session.get

    async def _patched_get(model: type, ident: object, **kw: object) -> object | None:
        if model is AISession:
            # Use noload('*') to prevent selectin cascading (MissingGreenlet)
            # Use text() filter to bypass UUID type processor for SQLite TEXT columns
            str_id = str(ident)
            q = (
                select(AISession)
                .options(noload("*"))
                .filter(text("ai_sessions.id = :sid").bindparams(sid=str_id))
            )
            result = await db_session.execute(q)
            ai_session = result.scalar_one_or_none()
            if ai_session is not None:
                # Manually load messages without selectin cascade
                msg_q = (
                    select(AIMessage)
                    .options(noload("*"))
                    .filter(text("ai_messages.session_id = :sid").bindparams(sid=str_id))
                    .order_by(AIMessage.created_at)
                )
                msg_result = await db_session.execute(msg_q)
                ai_session.messages = list(msg_result.scalars().all())
            return ai_session
        return await _original_get(model, ident, **kw)

    async def _noop_refresh(entity: object, *_a: object, **_kw: object) -> None:
        pass

    with (
        patch.object(db_session, "get", side_effect=_patched_get),
        patch.object(db_session, "refresh", side_effect=_noop_refresh),
    ):
        result = await service.execute(payload)

    return result.note_id


@pytest.mark.asyncio
class TestCreateNoteFromChatService:
    """Test suite for CreateNoteFromChatService."""

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_creates_note_from_chat(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Creates note from chat session with source_chat_session_id."""
        session_id = uuid.uuid4()

        stmt, params = _insert_ai_session(session_id, workspace_id, user_id)
        await db_session.execute(stmt, params)

        for role, content in [("user", "Hello, AI!"), ("assistant", "Hello! How can I help you?")]:
            stmt, params = _insert_ai_message(uuid.uuid4(), session_id, role, content)
            await db_session.execute(stmt, params)
        await db_session.flush()

        note_id = await _create_note_via_service(
            db_session, workspace_id, user_id, session_id, "My Note from Chat"
        )

        # Verify note was created
        query = select(Note).options(noload("*")).where(Note.id == note_id)
        note_result = await db_session.execute(query)
        note = note_result.scalar_one()

        assert note.title == "My Note from Chat"
        assert note.source_chat_session_id == session_id
        assert note.workspace_id == workspace_id
        assert note.owner_id == user_id

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_tiptap_blocks_structure(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """TipTap content has blockquotes for user, paragraphs for assistant."""
        session_id = uuid.uuid4()

        stmt, params = _insert_ai_session(session_id, workspace_id, user_id)
        await db_session.execute(stmt, params)

        for role, content in [
            ("user", "This is a user message"),
            ("assistant", "This is an assistant response"),
        ]:
            stmt, params = _insert_ai_message(uuid.uuid4(), session_id, role, content)
            await db_session.execute(stmt, params)
        await db_session.flush()

        note_id = await _create_note_via_service(
            db_session, workspace_id, user_id, session_id, "Test Note"
        )

        # Fetch note and check content structure
        query = select(Note).options(noload("*")).where(Note.id == note_id)
        note_result = await db_session.execute(query)
        note = note_result.scalar_one()

        content = json.loads(note.content) if isinstance(note.content, str) else note.content

        assert content["type"] == "doc"
        assert "content" in content
        assert len(content["content"]) == 2

        # First block: blockquote (user)
        user_block = content["content"][0]
        assert user_block["type"] == "blockquote"
        assert user_block["content"][0]["type"] == "paragraph"
        assert user_block["content"][0]["content"][0]["text"] == "This is a user message"

        # Second block: paragraph (assistant)
        assistant_block = content["content"][1]
        assert assistant_block["type"] == "paragraph"
        assert assistant_block["content"][0]["text"] == "This is an assistant response"

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_session_not_found(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Non-existent session_id raises ValueError."""
        non_existent_session_id = uuid.uuid4()

        service = CreateNoteFromChatService(db_session)
        payload = CreateNoteFromChatPayload(
            workspace_id=workspace_id,
            user_id=user_id,
            chat_session_id=non_existent_session_id,
            title="Test Note",
        )

        with pytest.raises(ValueError, match="not found"):
            await service.execute(payload)

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_empty_session_creates_empty_note(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Session with no messages creates note with empty paragraph."""
        session_id = uuid.uuid4()

        stmt, params = _insert_ai_session(session_id, workspace_id, user_id, title="Empty Chat")
        await db_session.execute(stmt, params)
        await db_session.flush()

        note_id = await _create_note_via_service(
            db_session, workspace_id, user_id, session_id, "Empty Note"
        )

        query = select(Note).options(noload("*")).where(Note.id == note_id)
        note_result = await db_session.execute(query)
        note = note_result.scalar_one()

        content = json.loads(note.content) if isinstance(note.content, str) else note.content

        # Should have single empty paragraph
        assert content["type"] == "doc"
        assert len(content["content"]) == 1
        assert content["content"][0]["type"] == "paragraph"
        assert content["content"][0]["content"] == []

    @pytest.mark.usefixtures("_seed_workspace")
    async def test_system_messages_excluded(
        self,
        db_session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """System role messages are skipped in content."""
        session_id = uuid.uuid4()

        stmt, params = _insert_ai_session(session_id, workspace_id, user_id)
        await db_session.execute(stmt, params)

        for role, content in [
            ("system", "You are a helpful assistant"),
            ("user", "Hello"),
            ("assistant", "Hi there!"),
        ]:
            stmt, params = _insert_ai_message(uuid.uuid4(), session_id, role, content)
            await db_session.execute(stmt, params)
        await db_session.flush()

        note_id = await _create_note_via_service(
            db_session, workspace_id, user_id, session_id, "Test Note"
        )

        query = select(Note).options(noload("*")).where(Note.id == note_id)
        note_result = await db_session.execute(query)
        note = note_result.scalar_one()

        content = json.loads(note.content) if isinstance(note.content, str) else note.content

        # Should only have 2 blocks (user + assistant; system excluded)
        assert len(content["content"]) == 2
        assert content["content"][0]["type"] == "blockquote"
        assert content["content"][1]["type"] == "paragraph"
