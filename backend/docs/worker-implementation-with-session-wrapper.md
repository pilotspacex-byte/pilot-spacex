# Worker Implementation with Session Wrapper
**ConversationWorker - Enhanced with Session Management**

**Status:** Implementation Ready
**Date:** 2026-01-30
**Note:** Uses session wrapper around `query()` for cleaner session management

---

## Overview

This enhanced implementation wraps the Claude SDK's `query()` function in a **session-aware client** for better multi-turn conversation management. While the official SDK doesn't provide a `ClaudeSDKClient` class, this wrapper provides similar benefits:

- ✅ Automatic session_id management
- ✅ Conversation state tracking
- ✅ Cleaner API for workers
- ✅ Easy session resumption
- ✅ Built on official `query()` function

---

## Architecture

```
ConversationWorker
    ↓
ConversationSession (wrapper)
    ↓
query() (official SDK function)
    ↓
Claude API
```

**Key Difference:**
- **Before:** Worker calls `query()` directly, manually manages session_id
- **After:** Worker uses `ConversationSession` wrapper for cleaner API

---

## Session Wrapper Implementation

### File: `backend/src/pilot_space/ai/sdk/session_client.py`

```python
"""Session wrapper for Claude Agent SDK.

Provides a stateful client interface around the SDK's query() function
for better multi-turn conversation management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator
from uuid import UUID

from claude_agent_sdk import ClaudeAgentOptions, Message, query

if TYPE_CHECKING:
    from pilot_space.ai.sdk.approval_handler import ApprovalHandler

logger = logging.getLogger(__name__)


class ConversationSession:
    """Stateful wrapper around Claude SDK query() for multi-turn conversations.

    Provides a client-like interface while using the official query() function
    internally. Manages session_id and conversation state automatically.

    Example:
        ```python
        session = ConversationSession(
            session_id="existing-uuid",  # or None for new session
            api_key=api_key,
            workspace_id=workspace_id
        )

        # First message
        async for event in session.stream("Hello"):
            print(event)

        # Subsequent messages (same session)
        async for event in session.stream("Tell me more"):
            print(event)  # Has full context from previous messages

        # Session ID is automatically managed
        print(session.session_id)  # UUID of the conversation
        ```

    Attributes:
        session_id: UUID of the conversation (auto-generated or resumed)
        api_key: Anthropic API key
        workspace_id: Workspace UUID (for context)
        user_id: User UUID (for context)
        model: Claude model to use
        allowed_tools: List of tools the agent can use
        approval_handler: Optional handler for human-in-the-loop
        message_count: Number of messages sent in this session
    """

    def __init__(
        self,
        session_id: str | UUID | None = None,
        api_key: str | None = None,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        model: str = "claude-sonnet-4-5",
        allowed_tools: list[str] | None = None,
        approval_handler: ApprovalHandler | None = None,
    ):
        """Initialize conversation session.

        Args:
            session_id: Existing session ID to resume, or None for new session
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            workspace_id: Workspace UUID
            user_id: User UUID
            model: Claude model to use
            allowed_tools: List of tools agent can use
            approval_handler: Optional approval handler for destructive actions
        """
        self.session_id = str(session_id) if session_id else None
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.model = model
        self.allowed_tools = allowed_tools or [
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Glob",
            "Grep",
            "WebFetch",
            "WebSearch",
        ]
        self.approval_handler = approval_handler
        self.message_count = 0
        self._initialized = False

    async def stream(
        self,
        message: str,
        **options_override,
    ) -> AsyncIterator[Message]:
        """Stream response from Claude for the given message.

        Automatically manages session resumption and tracks conversation state.

        Args:
            message: User message to send
            **options_override: Optional overrides for ClaudeAgentOptions

        Yields:
            Message events from Claude SDK

        Example:
            ```python
            async for event in session.stream("Explain async/await"):
                if event.type == "text_delta":
                    print(event.content, end="")
            ```
        """
        # Build SDK options
        options = ClaudeAgentOptions(
            model=self.model,
            resume=self.session_id,  # Automatic session resumption
            allowed_tools=self.allowed_tools,
            permission_mode="default",
            **options_override,
        )

        # Add approval hooks if handler provided
        if self.approval_handler:
            options.hooks = self._build_hooks()

        # Set API key if provided
        if self.api_key:
            import os
            original_key = os.getenv("ANTHROPIC_API_KEY")
            os.environ["ANTHROPIC_API_KEY"] = self.api_key

        try:
            # Stream from SDK (official query() function)
            async for event in query(prompt=message, options=options):
                # Capture session_id from init message
                if not self._initialized and hasattr(event, 'subtype') and event.subtype == 'init':
                    if hasattr(event, 'session_id'):
                        self.session_id = event.session_id
                        self._initialized = True
                        logger.info(f"Session initialized: {self.session_id}")

                yield event

            # Increment message count
            self.message_count += 1

        finally:
            # Restore original API key
            if self.api_key and original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key

    async def send(self, message: str, **options_override) -> str:
        """Send message and return complete response text.

        Non-streaming convenience method that collects all text.

        Args:
            message: User message to send
            **options_override: Optional overrides for ClaudeAgentOptions

        Returns:
            Complete response text from Claude

        Example:
            ```python
            response = await session.send("What is 2+2?")
            print(response)  # "2+2 equals 4."
            ```
        """
        accumulated = ""

        async for event in self.stream(message, **options_override):
            if event.type == "text_delta":
                accumulated += event.content

        return accumulated

    def _build_hooks(self) -> dict:
        """Build SDK hooks for approval workflow."""
        if not self.approval_handler:
            return {}

        return {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|Bash",
                    "hooks": [self.approval_handler.request_approval],
                }
            ]
        }

    def get_metadata(self) -> dict:
        """Get session metadata.

        Returns:
            Dictionary with session info
        """
        return {
            "session_id": self.session_id,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "model": self.model,
            "message_count": self.message_count,
            "initialized": self._initialized,
        }


class SessionManager:
    """Manages multiple conversation sessions.

    Provides session lifecycle management: create, get, resume, close.
    """

    def __init__(self):
        self._sessions: dict[str, ConversationSession] = {}

    async def get_or_create(
        self,
        session_id: str | UUID | None = None,
        **session_kwargs,
    ) -> ConversationSession:
        """Get existing session or create new one.

        Args:
            session_id: Session ID to resume, or None for new session
            **session_kwargs: Arguments for ConversationSession constructor

        Returns:
            ConversationSession instance
        """
        session_key = str(session_id) if session_id else None

        # Return existing session if found
        if session_key and session_key in self._sessions:
            logger.info(f"Resuming session: {session_key}")
            return self._sessions[session_key]

        # Create new session
        session = ConversationSession(session_id=session_id, **session_kwargs)

        # Store for reuse
        if session.session_id:
            self._sessions[session.session_id] = session

        logger.info(f"Created new session: {session.session_id or 'pending'}")
        return session

    async def close_session(self, session_id: str | UUID):
        """Close and remove session from cache.

        Args:
            session_id: Session ID to close
        """
        session_key = str(session_id)
        if session_key in self._sessions:
            del self._sessions[session_key]
            logger.info(f"Closed session: {session_key}")

    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
```

---

## Enhanced Worker Implementation

### File: `backend/src/pilot_space/ai/workers/conversation_worker.py`

```python
"""Async worker with session wrapper for cleaner conversation management."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import anthropic
from prometheus_client import Counter, Histogram
from redis import asyncio as aioredis
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.sdk.session_client import ConversationSession, SessionManager
from pilot_space.infrastructure.database.models.ai_message import AIMessage

if TYPE_CHECKING:
    from pilot_space.ai.sdk.approval_handler import ApprovalHandler

logger = logging.getLogger(__name__)

# Metrics
messages_processed = Counter(
    "ai_messages_processed_total",
    "Total messages processed",
    ["status"],
)

processing_duration = Histogram(
    "ai_processing_duration_seconds",
    "Time to process message"
)


class ConversationWorker:
    """Processes conversation jobs using session wrapper.

    Enhanced with ConversationSession for cleaner session management.
    """

    def __init__(
        self,
        queue: Any,
        redis: aioredis.Redis,
        db: AsyncSession,
        approval_handler: ApprovalHandler | None = None,
        max_retries: int = 3,
        backoff_base: int = 2,
    ):
        self.queue = queue
        self.redis = redis
        self.db = db
        self.approval_handler = approval_handler
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._shutdown = False

        # Session manager for conversation state
        self.session_manager = SessionManager()

    async def run(self):
        """Main worker loop."""
        logger.info("ConversationWorker started")

        while not self._shutdown:
            try:
                job = await self.queue.dequeue(
                    queue="ai_conversation_queue",
                    vt=300,
                )

                if job:
                    logger.info(f"Dequeued job {job['data']['job_id']}")
                    await self.process_message(job["data"])
                    await self.queue.delete(job["msg_id"])
                    messages_processed.labels(status="success").inc()

            except Exception as e:
                logger.exception(f"Worker error: {e}")
                await asyncio.sleep(1)

        logger.info("ConversationWorker stopped gracefully")

    async def process_message(self, job: dict):
        """Process single conversation job with retry logic."""

        lock_key = f"conv:{job['session_id']}"

        async with self.redis.lock(lock_key, timeout=300):
            # Retry loop at MESSAGE level
            for attempt in range(self.max_retries):
                try:
                    await self._stream_conversation(job)
                    return  # Success

                except anthropic.RateLimitError as e:
                    logger.warning(f"Rate limit for job {job['job_id']}: {e}")
                    await self._send_error_event(
                        job["job_id"],
                        "RATE_LIMIT",
                        "Rate limit exceeded. Please try again later.",
                    )
                    return

                except anthropic.APITimeoutError:
                    logger.warning(
                        f"Timeout for job {job['job_id']}, "
                        f"attempt {attempt + 1}/{self.max_retries}"
                    )

                    if attempt == self.max_retries - 1:
                        await self.queue.move_to_dlq(
                            job, reason="Max retries exceeded (timeout)"
                        )
                        messages_processed.labels(status="dlq").inc()
                        return

                    await asyncio.sleep(self.backoff_base ** attempt)

                except Exception as e:
                    logger.exception(f"Unexpected error for job {job['job_id']}: {e}")

                    if attempt == self.max_retries - 1:
                        await self.queue.move_to_dlq(
                            job, reason=f"Unexpected error: {str(e)[:200]}"
                        )
                        messages_processed.labels(status="dlq").inc()
                        return

                    await asyncio.sleep(self.backoff_base ** attempt)

    async def _stream_conversation(self, job: dict):
        """Stream from Claude SDK using session wrapper.

        ENHANCED: Uses ConversationSession for cleaner session management.
        """
        job_id = job["job_id"]
        start_time = datetime.utcnow()

        # Initialize Redis state
        await self.redis.set(f"status:{job_id}", "processing", ex=600)
        await self.redis.set(f"partial:{job_id}", "", ex=600)

        # Get API key
        api_key = await self._get_api_key(job["workspace_id"])

        # Get or create session (automatic resumption!)
        session = await self.session_manager.get_or_create(
            session_id=job.get("session_id"),
            api_key=api_key,
            workspace_id=job["workspace_id"],
            user_id=job["user_id"],
            model="claude-sonnet-4-5",
            approval_handler=self.approval_handler,
        )

        accumulated = ""
        tool_calls = []
        token_usage = {}

        # Stream from session (cleaner API!)
        async for event in session.stream(job["message"]):
            # Transform to SSE
            sse_event = self._transform_event(event)

            if sse_event:
                # Publish to SSE clients
                await self.redis.publish(
                    f"stream:{job_id}",
                    json.dumps(sse_event)
                )

            # Process events
            if event.type == "text_delta":
                accumulated += event.content
                await self.redis.set(f"partial:{job_id}", accumulated, ex=600)

            elif event.type == "tool_use":
                tool_calls.append({
                    "tool_name": event.tool_name,
                    "params": event.params,
                    "result": None,
                    "status": "running",
                    "started_at": datetime.utcnow().isoformat(),
                })

            elif event.type == "tool_result":
                for tool in tool_calls:
                    if tool["status"] == "running":
                        tool["result"] = event.result
                        tool["status"] = event.status
                        tool["completed_at"] = datetime.utcnow().isoformat()
                        break

            elif event.type == "message_stop":
                token_usage = {
                    "input_tokens": event.input_tokens,
                    "output_tokens": event.output_tokens,
                    "cache_read_tokens": getattr(event, "cache_read_tokens", 0),
                    "cache_creation_tokens": getattr(event, "cache_creation_tokens", 0),
                }

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Save to PostgreSQL
        await self.db.execute(
            update(AIMessage)
            .where(AIMessage.job_id == UUID(job_id))
            .values(
                content=accumulated,
                tool_calls=tool_calls,
                token_usage=token_usage,
                processing_time_ms=int(processing_time),
                completed_at=datetime.utcnow(),
            )
        )
        await self.db.commit()

        # Cleanup Redis
        await self.redis.delete(f"partial:{job_id}")
        await self.redis.set(f"status:{job_id}", "completed", ex=60)

        # Send final event
        await self.redis.publish(
            f"stream:{job_id}",
            json.dumps({
                "type": "message_stop",
                "token_usage": token_usage,
                "processing_time_ms": int(processing_time),
            })
        )

        # Record metrics
        processing_duration.observe(
            (datetime.utcnow() - start_time).total_seconds()
        )

        logger.info(
            f"Completed job {job_id} in {processing_time}ms "
            f"({token_usage.get('output_tokens', 0)} tokens) "
            f"[Session: {session.session_id}, Messages: {session.message_count}]"
        )

    def _transform_event(self, event: Any) -> dict | None:
        """Transform Claude SDK event to SSE format."""
        event_type = getattr(event, "type", "unknown")

        if event_type == "text_delta":
            return {
                "type": "text_delta",
                "content": event.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        elif event_type == "tool_use":
            return {
                "type": "tool_use",
                "tool_name": event.tool_name,
                "tool_id": getattr(event, "tool_id", None),
                "params": event.params,
                "timestamp": datetime.utcnow().isoformat(),
            }
        elif event_type == "tool_result":
            return {
                "type": "tool_result",
                "tool_id": getattr(event, "tool_id", None),
                "status": event.status,
                "result": event.result if event.status == "success" else None,
                "error": event.error if event.status == "error" else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return None

    async def _get_api_key(self, workspace_id: UUID) -> str:
        """Get Anthropic API key for workspace."""
        from pilot_space.ai.infrastructure.key_storage import APIKeyStorage

        storage = APIKeyStorage(self.db)
        key = await storage.get_key(workspace_id, "anthropic")

        if not key:
            raise ValueError(
                f"No Anthropic API key found for workspace {workspace_id}"
            )

        return key

    async def _send_error_event(self, job_id: str, error_code: str, message: str):
        """Send error event to SSE clients."""
        await self.redis.publish(
            f"stream:{job_id}",
            json.dumps({
                "type": "error",
                "error_code": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            })
        )

        await self.redis.set(f"status:{job_id}", f"error:{error_code}", ex=600)

    def shutdown(self):
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received")
        self._shutdown = True
```

---

## Benefits of Session Wrapper

### 1. Cleaner API

**Before (direct query()):**
```python
async for event in query(
    prompt=message,
    options=ClaudeAgentOptions(
        model="claude-sonnet-4-5",
        resume=session_id,  # Manual session management
        allowed_tools=[...],
        permission_mode="default"
    )
):
    yield event
```

**After (with wrapper):**
```python
session = await session_manager.get_or_create(session_id=session_id)

async for event in session.stream(message):  # Automatic session management
    yield event
```

### 2. Automatic Session Resumption

```python
# First message
session = ConversationSession()
await session.stream("Hello")
print(session.session_id)  # "uuid-abc-123"

# Second message (auto-resumes)
await session.stream("Tell me more")  # Has full context from "Hello"
```

### 3. Session State Tracking

```python
metadata = session.get_metadata()
print(metadata)
# {
#     "session_id": "uuid-abc-123",
#     "workspace_id": "uuid-workspace",
#     "user_id": "uuid-user",
#     "model": "claude-sonnet-4-5",
#     "message_count": 3,
#     "initialized": True
# }
```

### 4. Centralized Session Management

```python
# Session manager tracks all active sessions
manager = SessionManager()

# Get or create
session1 = await manager.get_or_create(session_id="uuid-1")
session2 = await manager.get_or_create(session_id="uuid-2")

# Reuse existing
session1_again = await manager.get_or_create(session_id="uuid-1")
assert session1 is session1_again  # Same instance

# Track active sessions
print(manager.get_active_count())  # 2
```

---

## Usage Examples

### Example 1: Simple Conversation

```python
from pilot_space.ai.sdk.session_client import ConversationSession

# Create session
session = ConversationSession(api_key="sk-...")

# Send messages
async for event in session.stream("What is async/await?"):
    if event.type == "text_delta":
        print(event.content, end="")

# Continue conversation (same session)
async for event in session.stream("Can you give an example?"):
    if event.type == "text_delta":
        print(event.content, end="")

print(f"\nSession ID: {session.session_id}")
print(f"Messages sent: {session.message_count}")
```

### Example 2: Resume Existing Session

```python
# Resume from previous conversation
session = ConversationSession(
    session_id="uuid-from-database",
    api_key="sk-..."
)

# Claude has full context from previous messages
async for event in session.stream("Continue where we left off"):
    print(event)
```

### Example 3: Non-Streaming

```python
session = ConversationSession(api_key="sk-...")

# Simple request-response
response = await session.send("What is 2+2?")
print(response)  # "2+2 equals 4."

# With options
response = await session.send(
    "Fix the bug in auth.py",
    allowed_tools=["Read", "Edit"]
)
```

### Example 4: Session Manager

```python
manager = SessionManager()

# Create session for user
session = await manager.get_or_create(
    session_id=user_session_id,
    api_key=api_key,
    workspace_id=workspace_id
)

# Process message
async for event in session.stream(user_message):
    yield event

# Later, reuse same session
session = await manager.get_or_create(session_id=user_session_id)
async for event in session.stream(next_message):
    yield event

# Clean up
await manager.close_session(user_session_id)
```

---

## Testing

### Unit Tests

```python
import pytest
from pilot_space.ai.sdk.session_client import ConversationSession

@pytest.mark.asyncio
async def test_session_initialization():
    """Verify session initializes correctly."""
    session = ConversationSession(
        api_key="test-key",
        model="claude-sonnet-4-5"
    )

    assert session.session_id is None  # Not initialized until first message
    assert session.message_count == 0
    assert session.model == "claude-sonnet-4-5"

@pytest.mark.asyncio
async def test_session_resumption():
    """Verify session can be resumed."""
    session = ConversationSession(
        session_id="existing-uuid",
        api_key="test-key"
    )

    assert session.session_id == "existing-uuid"

@pytest.mark.asyncio
async def test_session_manager():
    """Verify session manager tracks sessions."""
    manager = SessionManager()

    # Create first session
    session1 = await manager.get_or_create(
        session_id="uuid-1",
        api_key="test-key"
    )

    # Get same session again
    session1_again = await manager.get_or_create(session_id="uuid-1")
    assert session1 is session1_again

    # Create different session
    session2 = await manager.get_or_create(
        session_id="uuid-2",
        api_key="test-key"
    )

    assert manager.get_active_count() == 2

    # Close session
    await manager.close_session("uuid-1")
    assert manager.get_active_count() == 1
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_worker_with_session_wrapper():
    """Verify worker uses session wrapper correctly."""

    worker = ConversationWorker(...)

    job = {
        "job_id": "test-job",
        "session_id": "test-session",
        "workspace_id": "test-workspace",
        "user_id": "test-user",
        "message": "Hello"
    }

    await worker.process_message(job)

    # Verify session was created
    assert worker.session_manager.get_active_count() > 0

    # Verify message was saved
    message = await db.get(AIMessage, job_id="test-job")
    assert message.completed_at is not None
```

---

## Migration from Direct query()

### Before (Old Worker)

```python
async for event in query(
    prompt=job['message'],
    options=ClaudeAgentOptions(
        model="claude-sonnet-4-5",
        resume=job.get('session_id'),
        allowed_tools=[...],
    )
):
    yield event
```

### After (Session Wrapper)

```python
session = await self.session_manager.get_or_create(
    session_id=job.get('session_id'),
    api_key=api_key,
    workspace_id=job['workspace_id'],
    user_id=job['user_id'],
)

async for event in session.stream(job['message']):
    yield event
```

**Benefits:**
- ✅ Automatic session_id management
- ✅ Session state tracking (message_count, etc.)
- ✅ Cleaner, more readable code
- ✅ Easier to test and mock
- ✅ Still uses official `query()` function internally

---

## File Structure

```
backend/src/pilot_space/ai/
├── sdk/
│   ├── __init__.py
│   ├── session_client.py          # NEW: Session wrapper
│   ├── approval_handler.py         # Existing
│   └── permission_handler.py       # Existing
├── workers/
│   ├── __init__.py
│   ├── conversation_worker.py      # UPDATED: Uses session wrapper
│   └── config.py
└── ...
```

---

## Summary

**What Changed:**
1. Created `ConversationSession` wrapper class
2. Created `SessionManager` for session lifecycle
3. Updated `ConversationWorker` to use session wrapper
4. Cleaner API while still using official `query()` function

**What Stayed the Same:**
- Still uses `query()` from `claude_agent_sdk` internally
- Same functionality and behavior
- Same error handling and retry logic
- Same SSE streaming and Redis pub/sub

**Benefits:**
- ✅ Cleaner, more maintainable code
- ✅ Automatic session management
- ✅ Session state tracking
- ✅ Easier to test
- ✅ Better abstraction for workers

**Note:** This wrapper is built on top of the **official** `query()` function. The Claude Agent SDK does not provide a `ClaudeSDKClient` class - this wrapper provides similar benefits while using the correct API.
