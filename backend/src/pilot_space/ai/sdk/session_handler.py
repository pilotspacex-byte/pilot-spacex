"""Session handler for multi-turn Claude Agent SDK conversations.

Manages conversation state across multiple requests, handling:
- Message history persistence (Redis)
- Token budget management (8000 token limit)
- Session lifecycle (30 minute TTL)
- Context window optimization

Reference: docs/architect/claude-agent-sdk-architecture.md
Design Decisions: DD-058 (SDK mode for streaming)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.session.session_manager import AIMessage, SessionNotFoundError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.session.session_manager import AISession, SessionManager
    from pilot_space.infrastructure.database.models.ai_task import TaskStatus


@dataclass
class ConversationMessage:
    """Single message in a conversation.

    Attributes:
        role: Message role (user, assistant, system)
        content: Message content (text or structured blocks)
        timestamp: When message was created
        tokens: Estimated token count
        metadata: Additional metadata (cost, model, etc.)
    """

    role: str
    content: str | list[dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_sdk_format(self) -> dict[str, Any]:
        """Convert to Claude Agent SDK message format."""
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class ConversationSession:
    """Multi-turn conversation session.

    Attributes:
        session_id: Unique session identifier
        workspace_id: Workspace UUID for RLS
        user_id: User UUID for attribution
        agent_name: Agent this session belongs to
        messages: Conversation message history
        created_at: Session creation time
        updated_at: Last update time
        total_tokens: Cumulative token count
        total_cost_usd: Cumulative cost in USD
        metadata: Additional session metadata
    """

    session_id: UUID
    workspace_id: UUID
    user_id: UUID
    agent_name: str
    context_id: UUID | None = None
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if session has exceeded TTL (30 minutes)."""
        ttl = timedelta(minutes=30)
        return datetime.now(UTC) - self.updated_at > ttl

    def add_message(self, message: ConversationMessage) -> None:
        """Add message to session history.

        Updates total_tokens and updated_at timestamp.
        """
        self.messages.append(message)
        self.total_tokens += message.tokens
        self.updated_at = datetime.now(UTC)

    def get_messages_for_sdk(self, max_tokens: int = 8000) -> list[dict[str, Any]]:
        """Get messages in SDK format, respecting token budget.

        Implements sliding window: keeps most recent messages that fit
        within max_tokens limit. Always includes system message if present.

        Args:
            max_tokens: Maximum tokens to include (default: 8000)

        Returns:
            List of messages in Claude Agent SDK format
        """
        if not self.messages:
            return []

        # Separate system messages from conversation
        system_messages = [m for m in self.messages if m.role == "system"]
        conversation_messages = [m for m in self.messages if m.role != "system"]

        # Calculate system message tokens
        system_tokens = sum(m.tokens for m in system_messages)
        remaining_budget = max_tokens - system_tokens

        # Add messages from most recent, staying within budget
        included_messages: list[ConversationMessage] = []
        current_tokens = 0

        for message in reversed(conversation_messages):
            if current_tokens + message.tokens > remaining_budget:
                break
            included_messages.insert(0, message)
            current_tokens += message.tokens

        # Combine system + conversation messages
        all_messages = system_messages + included_messages
        return [m.to_sdk_format() for m in all_messages]


class SessionHandler:
    """Handler for managing Claude Agent SDK conversation sessions.

    Manages session lifecycle (create, retrieve, persist, delete),
    token budgets, TTL, context windows, and task progress tracking (T072).
    """

    def __init__(
        self,
        session_manager: SessionManager,
        db_session: AsyncSession | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._db_session = db_session

    @property
    def session_manager(self) -> SessionManager:
        """Public accessor for background tasks that need a fresh db session."""
        return self._session_manager

    # Type Conversion Adapters
    # Bridge between AISession (SessionManager) ↔ ConversationSession (SessionHandler)

    def _to_conversation_session(self, ai_session: AISession) -> ConversationSession:
        """Convert AISession to ConversationSession.

        Args:
            ai_session: AISession from SessionManager

        Returns:
            ConversationSession for SDK integration layer
        """
        # Convert AIMessage to ConversationMessage
        messages = [
            ConversationMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                tokens=msg.tokens or 0,
                metadata={"cost_usd": msg.cost_usd} if msg.cost_usd else {},
            )
            for msg in ai_session.messages
        ]

        # Calculate total tokens from messages
        total_tokens = sum(msg.tokens for msg in messages)

        return ConversationSession(
            session_id=ai_session.id,
            workspace_id=ai_session.workspace_id,
            user_id=ai_session.user_id,
            agent_name=ai_session.agent_name,
            context_id=ai_session.context_id,
            messages=messages,
            created_at=ai_session.created_at,
            updated_at=ai_session.updated_at,
            total_tokens=total_tokens,
            total_cost_usd=ai_session.total_cost_usd,
            metadata=ai_session.context,  # Map context → metadata
        )

    def _to_ai_message(
        self,
        role: str,
        content: str | list[dict[str, Any]],
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> AIMessage:
        """Convert message parameters to AIMessage.

        Args:
            role: Message role (user, assistant, system)
            content: Message content (str or structured blocks)
            tokens: Token count
            metadata: Additional metadata (e.g., cost_usd)

        Returns:
            AIMessage for SessionManager
        """
        # Convert content to string if it's structured (list of blocks)
        content_str = content if isinstance(content, str) else json.dumps(content)

        # Extract cost from metadata if present
        cost_usd = metadata.get("cost_usd") if metadata else None

        return AIMessage(
            role=role,
            content=content_str,
            tokens=tokens,
            cost_usd=cost_usd,
        )

    async def create_session(
        self,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
        context_id: UUID | None = None,
    ) -> ConversationSession:
        """Create new conversation session.

        Args:
            workspace_id: Workspace UUID for RLS
            user_id: User UUID for attribution
            agent_name: Agent this session belongs to
            metadata: Additional session metadata (maps to AISession.context)
            context_id: Optional entity ID (note_id, issue_id) for session lookup

        Returns:
            ConversationSession with new session_id

        Raises:
            AIError: If session creation fails
        """
        # Create AISession via SessionManager
        ai_session = await self._session_manager.create_session(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_name=agent_name,
            context_id=context_id,
            initial_context=metadata or {},
        )

        # Convert to ConversationSession
        return self._to_conversation_session(ai_session)

    async def get_session(
        self,
        session_id: UUID,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> ConversationSession | None:
        """Retrieve existing session by ID with optional ownership validation.

        Args:
            session_id: Session UUID
            workspace_id: If provided, validates session belongs to this workspace
            user_id: If provided, validates session belongs to this user

        Returns:
            ConversationSession if found, valid, and not expired. None otherwise.
        """
        try:
            ai_session = await self._session_manager.get_session(session_id)
        except SessionNotFoundError:
            return None

        session = self._to_conversation_session(ai_session)

        if workspace_id is not None and session.workspace_id != workspace_id:
            logger.warning(
                "Session %s workspace mismatch: expected %s, got %s",
                session_id,
                workspace_id,
                session.workspace_id,
            )
            return None

        if user_id is not None and session.user_id != user_id:
            logger.warning(
                "Session %s user mismatch: expected %s, got %s",
                session_id,
                user_id,
                session.user_id,
            )
            return None

        return session

    async def get_session_by_context(
        self,
        user_id: UUID,
        workspace_id: UUID,
        agent_name: str,
        context_id: UUID,
    ) -> ConversationSession | None:
        """Find active session by context entity (note_id, issue_id, etc).

        Lookup order:
        1. Redis index (fast, <30min TTL)
        2. PostgreSQL fallback (durable, 24h TTL)

        Args:
            user_id: User UUID for index lookup
            workspace_id: Workspace UUID for ownership validation
            agent_name: Agent name (e.g. "conversation")
            context_id: Context entity UUID (note_id, issue_id, project_id)

        Returns:
            ConversationSession if found and valid, None otherwise.
        """
        # 1. Try Redis index (fast path)
        ai_session = await self._session_manager.get_active_session(
            user_id=user_id,
            agent_name=agent_name,
            context_id=context_id,
        )

        # 2. Fall back to PostgreSQL if Redis expired
        if ai_session is None and self._db_session is not None:
            from pilot_space.ai.sdk.session_store import SessionStore

            store = SessionStore(self._session_manager, self._db_session)
            ai_session = await store.load_by_context(
                user_id=user_id,
                agent_name=agent_name,
                context_id=context_id,
            )

        if ai_session is None:
            return None

        session = self._to_conversation_session(ai_session)

        if session.workspace_id != workspace_id:
            logger.warning(
                "Session for context %s workspace mismatch: expected %s, got %s",
                context_id,
                workspace_id,
                session.workspace_id,
            )
            return None

        return session

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str | list[dict[str, Any]],
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add message to session.

        Args:
            session_id: Session UUID
            role: Message role (user, assistant, system)
            content: Message content (str or structured blocks)
            tokens: Token count for this message
            metadata: Additional metadata (e.g., cost_usd)

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session has expired
        """
        # Convert to AIMessage
        ai_message = self._to_ai_message(role, content, tokens, metadata)

        # Update session via SessionManager
        await self._session_manager.update_session(
            session_id,
            message=ai_message,
        )

    async def update_cost(
        self,
        session_id: UUID,
        cost_usd: float,
    ) -> None:
        """Update session cost.

        Args:
            session_id: Session UUID
            cost_usd: Cost delta to add to total

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session has expired
        """
        # Update session cost via SessionManager
        await self._session_manager.update_session(
            session_id,
            cost_delta=cost_usd,
        )

    async def fork_session(
        self,
        source_session_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ConversationSession:
        """Fork a session by copying its message history into a new session.

        Creates a branch for "what-if" exploration. The new session gets a
        copy of all messages from the source, enabling divergent conversations.
        Limit: 3 forks per source session.

        Args:
            source_session_id: Session to fork from.
            workspace_id: Workspace UUID for new session.
            user_id: User UUID for new session.

        Returns:
            New ConversationSession with copied messages.

        Raises:
            SessionNotFoundError: If source session doesn't exist.
            ValueError: If fork limit exceeded (max 3 per source).
        """
        source = await self.get_session(source_session_id)
        if not source:
            raise SessionNotFoundError(source_session_id)

        # Check fork limit (stored in metadata)
        fork_count = source.metadata.get("fork_count", 0)
        if fork_count >= 3:
            raise ValueError(f"Fork limit reached for session {source_session_id} (max 3)")

        # Create new session with fork metadata
        fork_metadata = {
            "forked_from": str(source_session_id),
            "fork_count": 0,
        }
        forked = await self.create_session(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=source.agent_name,
            metadata=fork_metadata,
        )

        # Copy messages from source to forked session
        for msg in source.messages:
            await self.add_message(
                session_id=forked.session_id,
                role=msg.role,
                content=msg.content,
                tokens=msg.tokens,
                metadata=msg.metadata,
            )

        # Increment fork count on source
        source.metadata["fork_count"] = fork_count + 1
        await self._session_manager.update_session(
            source_session_id,
            context_update=source.metadata,
        )

        return forked

    async def persist_session(self, session_id: UUID) -> bool:
        """Persist a Redis session to PostgreSQL after chat stream completes."""
        if self._db_session is None:
            logger.debug("No db_session, skipping session persistence")
            return False

        from pilot_space.ai.sdk.session_store import SessionStore

        store = SessionStore(self._session_manager, self._db_session)
        return await store.save_to_db(session_id)

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session.

        Args:
            session_id: Session UUID to delete

        Returns:
            True if session was deleted, False if session not found

        Note:
            Uses end_session() from SessionManager which marks session as ended.
        """
        try:
            return await self._session_manager.end_session(session_id)
        except SessionNotFoundError:
            return False

    # Task Progress Management (T072)

    async def create_task(
        self,
        session_id: UUID,
        subject: str,
        description: str | None = None,
        owner: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """Create a new task for the session.

        Args:
            session_id: Session ID this task belongs to.
            subject: Brief task title (imperative form).
            description: Optional detailed description.
            owner: Optional agent name or "user".
            metadata: Optional task metadata.

        Returns:
            Created task ID.

        Raises:
            ValueError: If db_session is not available.
        """
        if not self._db_session:
            raise ValueError("Database session required for task management")

        from pilot_space.infrastructure.database.repositories.ai_task_repository import (
            AITaskRepository,
        )

        repo = AITaskRepository(self._db_session)
        task = await repo.create_task(
            session_id=session_id,
            subject=subject,
            description=description,
            owner=owner,
            task_metadata=metadata,
        )
        return task.id

    async def update_task_progress(
        self,
        task_id: UUID,
        progress: int,
        status: TaskStatus | str | None = None,
        current_step: str | None = None,
    ) -> bool:
        """Update task progress.

        Args:
            task_id: Task ID to update.
            progress: Progress percentage (0-100).
            status: Optional new status (pending/in_progress/completed/failed/blocked).
            current_step: Optional description of current step.

        Returns:
            True if updated successfully, False if task not found.

        Raises:
            ValueError: If db_session is not available.
        """
        if not self._db_session:
            raise ValueError("Database session required for task management")

        from pilot_space.infrastructure.database.models.ai_task import TaskStatus as TS
        from pilot_space.infrastructure.database.repositories.ai_task_repository import (
            AITaskRepository,
        )

        # Convert string status to TaskStatus enum
        status_enum: TS | None = None
        if status:
            status_enum = TS(status)

        repo = AITaskRepository(self._db_session)
        task = await repo.update_progress(
            task_id,
            progress=progress,
            status=status_enum,
        )

        # Update metadata with current step if provided
        if task and current_step:
            if task.task_metadata is None:
                task.task_metadata = {}
            task.task_metadata["current_step"] = current_step
            await self._db_session.flush()

        return task is not None

    async def complete_task(self, task_id: UUID) -> bool:
        """Mark task as completed (100% progress).

        Args:
            task_id: Task ID to complete.

        Returns:
            True if completed successfully, False if task not found.

        Raises:
            ValueError: If db_session is not available.
        """
        if not self._db_session:
            raise ValueError("Database session required for task management")

        from pilot_space.infrastructure.database.repositories.ai_task_repository import (
            AITaskRepository,
        )

        repo = AITaskRepository(self._db_session)
        task = await repo.complete_task(task_id)

        # Unblock dependent tasks
        if task:
            await repo.unblock_dependent_tasks(task_id)

        return task is not None

    async def fail_task(
        self,
        task_id: UUID,
        error_message: str | None = None,
    ) -> bool:
        """Mark task as failed.

        Args:
            task_id: Task ID to fail.
            error_message: Optional error message.

        Returns:
            True if failed successfully, False if task not found.

        Raises:
            ValueError: If db_session is not available.
        """
        if not self._db_session:
            raise ValueError("Database session required for task management")

        from pilot_space.infrastructure.database.repositories.ai_task_repository import (
            AITaskRepository,
        )

        repo = AITaskRepository(self._db_session)
        task = await repo.fail_task(task_id, error_message)
        return task is not None

    async def get_session_tasks(
        self,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all tasks for a session.

        Args:
            session_id: Session ID.

        Returns:
            List of task dictionaries.

        Raises:
            ValueError: If db_session is not available.
        """
        if not self._db_session:
            raise ValueError("Database session required for task management")

        from pilot_space.infrastructure.database.repositories.ai_task_repository import (
            AITaskRepository,
        )

        repo = AITaskRepository(self._db_session)
        tasks = await repo.get_by_session(session_id)

        return [
            {
                "id": str(task.id),
                "subject": task.subject,
                "description": task.description,
                "status": task.status.value,
                "progress": task.progress,
                "owner": task.owner,
                "metadata": task.task_metadata,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ]
