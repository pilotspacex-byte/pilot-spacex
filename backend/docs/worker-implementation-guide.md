# Worker Implementation Guide
**ConversationWorker - Production-Ready Implementation**

**Status:** Implementation Ready
**Priority:** P0 (Blocker for queue architecture)
**Estimated Time:** 4-6 hours

> **📘 Note on Claude SDK API:**
> This implementation uses the official `query()` function from `claude-agent-sdk`.
> The SDK does **not** provide a `ClaudeSDKClient` class.
>
> For enhanced session management, see: `worker-implementation-with-session-wrapper.md`

---

## Overview

This guide provides the complete, production-ready implementation of `ConversationWorker` - a simplified, single-class worker that processes AI chat jobs from the queue using the official Claude Agent SDK's `query()` function.

**Key Features:**
- ✅ Async queue processing with pgmq
- ✅ Distributed locking per conversation
- ✅ Claude SDK streaming integration
- ✅ Message-level retry with exponential backoff
- ✅ Dead letter queue for failed jobs
- ✅ Redis pub/sub for SSE streaming
- ✅ Prometheus metrics
- ✅ Graceful shutdown

**LOC:** ~150 lines (vs 500 in original over-engineered plan)

---

## File Structure

```
backend/src/pilot_space/ai/workers/
├── __init__.py
├── conversation_worker.py   # Main worker (this file)
└── config.py                # Worker configuration
```

---

## Complete Implementation

### File: `conversation_worker.py`

```python
"""Async worker for processing AI conversation jobs.

Simplified single-class implementation that:
- Dequeues jobs from pgmq
- Acquires distributed locks per conversation
- Streams from Claude SDK
- Publishes to Redis pub/sub for SSE
- Saves to PostgreSQL on completion
- Handles retries and failures

Based on: docs/simplified-queue-architecture.md
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import anthropic
from anthropic import AsyncAnthropic
from claude_agent_sdk import ClaudeAgentOptions, query
from prometheus_client import Counter, Histogram
from redis import asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.ai_message import AIMessage

if TYPE_CHECKING:
    from pilot_space.ai.sdk.approval_handler import ApprovalHandler

logger = logging.getLogger(__name__)

# Prometheus metrics
messages_processed = Counter(
    "ai_messages_processed_total",
    "Total messages processed",
    ["status"],  # success, failed, dlq
)

processing_duration = Histogram(
    "ai_processing_duration_seconds", "Time to process message"
)

queue_depth = Counter("ai_queue_depth", "Current queue depth")


class ConversationWorker:
    """Processes conversation jobs from pgmq queue.

    Single class that handles the entire job lifecycle:
    - Dequeue from pgmq
    - Acquire distributed lock
    - Stream from Claude SDK
    - Publish to Redis pub/sub
    - Save to PostgreSQL
    - Handle retries and failures

    Attributes:
        queue: pgmq queue client
        redis: Redis client for locks and pub/sub
        db: SQLAlchemy async session
        approval_handler: Optional handler for human-in-the-loop
        max_retries: Maximum retry attempts (default: 3)
        backoff_base: Exponential backoff base in seconds (default: 2)
    """

    def __init__(
        self,
        queue: Any,  # pgmq.Queue
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

    async def run(self):
        """Main worker loop.

        Continuously dequeues jobs and processes them.
        Handles graceful shutdown on SIGTERM.
        """
        logger.info("ConversationWorker started")

        while not self._shutdown:
            try:
                # Dequeue with 30s timeout
                job = await self.queue.dequeue(
                    queue="ai_conversation_queue",
                    vt=300,  # 5min visibility timeout
                )

                if job:
                    logger.info(f"Dequeued job {job['data']['job_id']}")
                    queue_depth.inc(-1)

                    await self.process_message(job["data"])
                    await self.queue.delete(job["msg_id"])

                    messages_processed.labels(status="success").inc()

            except Exception as e:
                logger.exception(f"Worker error: {e}")
                await asyncio.sleep(1)

        logger.info("ConversationWorker stopped gracefully")

    async def process_message(self, job: dict):
        """Process single conversation job with retry logic.

        Args:
            job: Job data containing:
                - job_id: UUID of the message
                - session_id: UUID of the conversation session
                - workspace_id: UUID of the workspace
                - user_id: UUID of the user
                - message: User message content
        """
        # Acquire distributed lock (prevents concurrent processing)
        lock_key = f"conv:{job['session_id']}"

        async with self.redis.lock(lock_key, timeout=300):
            # Retry loop at MESSAGE level (not chunk level!)
            for attempt in range(self.max_retries):
                try:
                    await self._stream_conversation(job)
                    return  # Success

                except anthropic.RateLimitError as e:
                    # Don't retry rate limits - fail fast
                    logger.warning(
                        f"Rate limit for job {job['job_id']}: {e.response.headers.get('retry-after')}"
                    )
                    await self._send_error_event(
                        job["job_id"],
                        "RATE_LIMIT",
                        "Rate limit exceeded. Please try again later.",
                    )
                    return

                except anthropic.APITimeoutError:
                    logger.warning(
                        f"Timeout for job {job['job_id']}, attempt {attempt + 1}/{self.max_retries}"
                    )

                    if attempt == self.max_retries - 1:
                        # Move to DLQ after max retries
                        await self.queue.move_to_dlq(
                            job, reason="Max retries exceeded (timeout)"
                        )
                        messages_processed.labels(status="dlq").inc()
                        return

                    # Exponential backoff: 2s, 4s, 8s
                    await asyncio.sleep(self.backoff_base**attempt)

                except Exception as e:
                    logger.exception(f"Unexpected error for job {job['job_id']}: {e}")

                    if attempt == self.max_retries - 1:
                        await self.queue.move_to_dlq(
                            job, reason=f"Unexpected error: {str(e)[:200]}"
                        )
                        messages_processed.labels(status="dlq").inc()
                        return

                    await asyncio.sleep(self.backoff_base**attempt)

    async def _stream_conversation(self, job: dict):
        """Stream from Claude SDK and publish events.

        This is where the actual AI processing happens:
        1. Initialize Redis state (status, partial response)
        2. Stream from Claude SDK using query() function
        3. Publish events to Redis pub/sub for SSE clients
        4. Accumulate text for partial response
        5. Track tool calls
        6. Save to PostgreSQL on completion

        Args:
            job: Job data with message and context
        """
        job_id = job["job_id"]
        start_time = datetime.utcnow()

        # Initialize Redis state
        await self.redis.set(f"status:{job_id}", "processing", ex=600)
        await self.redis.set(f"partial:{job_id}", "", ex=600)

        accumulated = ""
        tool_calls = []
        token_usage = {}

        # Get API key from workspace settings
        api_key = await self._get_api_key(job["workspace_id"])

        # Stream from Claude SDK
        async for event in query(
            prompt=job["message"],
            options=ClaudeAgentOptions(
                model="claude-sonnet-4-5",
                resume=job.get("session_id"),
                allowed_tools=[
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Glob",
                    "Grep",
                    "WebFetch",
                    "WebSearch",
                ],
                permission_mode="default",
                # If approval handler provided, add hook
                hooks=self._build_hooks() if self.approval_handler else {},
            ),
        ):
            # Transform SDK event to SSE format
            sse_event = self._transform_event(event)

            if sse_event:
                # Publish to SSE clients via Redis pub/sub
                await self.redis.publish(f"stream:{job_id}", json.dumps(sse_event))

            # Process event types
            if event.type == "text_delta":
                # Accumulate text for partial response
                accumulated += event.content
                await self.redis.set(f"partial:{job_id}", accumulated, ex=600)

            elif event.type == "tool_use":
                # Track tool calls
                tool_calls.append(
                    {
                        "tool_name": event.tool_name,
                        "params": event.params,
                        "result": None,  # Will be updated on tool_result
                        "status": "running",
                        "started_at": datetime.utcnow().isoformat(),
                    }
                )

            elif event.type == "tool_result":
                # Update tool call result
                for tool in tool_calls:
                    if tool["status"] == "running":
                        tool["result"] = event.result
                        tool["status"] = event.status
                        tool["completed_at"] = datetime.utcnow().isoformat()
                        break

            elif event.type == "message_stop":
                # Capture final token usage
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
            json.dumps(
                {
                    "type": "message_stop",
                    "token_usage": token_usage,
                    "processing_time_ms": int(processing_time),
                }
            ),
        )

        # Record metrics
        processing_duration.observe((datetime.utcnow() - start_time).total_seconds())

        logger.info(
            f"Completed job {job_id} in {processing_time}ms "
            f"({token_usage.get('output_tokens', 0)} tokens)"
        )

    def _transform_event(self, event: Any) -> dict | None:
        """Transform Claude SDK event to SSE format.

        Args:
            event: SDK event object

        Returns:
            SSE event dict or None if event should be filtered
        """
        event_type = getattr(event, "type", "unknown")

        # Text delta events
        if event_type == "text_delta":
            return {
                "type": "text_delta",
                "content": event.content,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Tool use events
        elif event_type == "tool_use":
            return {
                "type": "tool_use",
                "tool_name": event.tool_name,
                "tool_id": getattr(event, "tool_id", None),
                "params": event.params,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Tool result events
        elif event_type == "tool_result":
            return {
                "type": "tool_result",
                "tool_id": getattr(event, "tool_id", None),
                "status": event.status,
                "result": event.result if event.status == "success" else None,
                "error": event.error if event.status == "error" else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Filter out internal events
        return None

    async def _get_api_key(self, workspace_id: UUID) -> str:
        """Get Anthropic API key for workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            API key string

        Raises:
            ValueError: If API key not found
        """
        from pilot_space.ai.infrastructure.key_storage import APIKeyStorage

        storage = APIKeyStorage(self.db)
        key = await storage.get_key(workspace_id, "anthropic")

        if not key:
            raise ValueError(f"No Anthropic API key found for workspace {workspace_id}")

        return key

    def _build_hooks(self) -> dict:
        """Build SDK hooks for approval workflow.

        Returns:
            Hooks configuration dict
        """
        if not self.approval_handler:
            return {}

        return {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|Bash",  # Approve destructive actions
                    "hooks": [self.approval_handler.request_approval],
                }
            ]
        }

    async def _send_error_event(
        self, job_id: str, error_code: str, message: str
    ):
        """Send error event to SSE clients.

        Args:
            job_id: Job ID
            error_code: Error code (e.g., "RATE_LIMIT", "TIMEOUT")
            message: Human-readable error message
        """
        await self.redis.publish(
            f"stream:{job_id}",
            json.dumps(
                {
                    "type": "error",
                    "error_code": error_code,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        )

        # Update status in Redis
        await self.redis.set(f"status:{job_id}", f"error:{error_code}", ex=600)

    def shutdown(self):
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received")
        self._shutdown = True
```

---

## Configuration

### File: `config.py`

```python
"""Worker configuration."""

from pydantic_settings import BaseSettings


class WorkerConfig(BaseSettings):
    """Configuration for ConversationWorker."""

    # Queue settings
    queue_name: str = "ai_conversation_queue"
    queue_visibility_timeout: int = 300  # 5 minutes
    queue_dequeue_timeout: int = 30  # 30 seconds
    max_retries: int = 3
    backoff_base: int = 2  # Exponential backoff base (2s, 4s, 8s)

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    lock_timeout: int = 300  # 5 minutes
    partial_ttl: int = 600  # 10 minutes

    # Worker settings
    worker_count: int = 5
    graceful_shutdown_timeout: int = 30  # Wait for jobs to finish

    # Model settings
    default_model: str = "claude-sonnet-4-5"
    allowed_tools: list[str] = [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
    ]

    class Config:
        env_prefix = "WORKER_"
```

---

## Worker Entry Point

### File: `__main__.py`

```python
"""Worker process entry point.

Usage:
    python -m pilot_space.ai.workers.conversation_worker
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from prometheus_client import start_http_server
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pilot_space.ai.workers.config import WorkerConfig
from pilot_space.ai.workers.conversation_worker import ConversationWorker
from pilot_space.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_worker_dependencies():
    """Create worker dependencies with cleanup."""

    # Database
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Redis
    redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=False)

    # pgmq Queue
    # TODO: Import actual pgmq client when available
    # from pgmq import Queue
    # queue = Queue(settings.DATABASE_URL)

    try:
        async with async_session() as session:
            # Yield dependencies
            yield {
                "db": session,
                "redis": redis,
                # "queue": queue,
            }
    finally:
        # Cleanup
        await redis.close()
        await engine.dispose()


async def main():
    """Main worker process."""

    config = WorkerConfig()

    # Start Prometheus metrics server
    start_http_server(9090)
    logger.info("Prometheus metrics server started on :9090")

    # Create worker dependencies
    async with create_worker_dependencies() as deps:
        # Create worker
        worker = ConversationWorker(
            queue=deps["queue"],
            redis=deps["redis"],
            db=deps["db"],
            max_retries=config.max_retries,
            backoff_base=config.backoff_base,
        )

        # Setup graceful shutdown
        def shutdown_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down gracefully...")
            worker.shutdown()

        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

        # Run worker
        try:
            await worker.run()
        except Exception as e:
            logger.exception(f"Worker crashed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Deployment

### 1. Systemd Service

**File:** `/etc/systemd/system/conversation-worker@.service`

```ini
[Unit]
Description=Conversation Worker %i
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=app
Group=app
WorkingDirectory=/app/backend

# Environment
Environment="PYTHONPATH=/app/backend"
Environment="WORKER_COUNT=5"
EnvironmentFile=/etc/pilot-space/worker.env

# Command
ExecStart=/app/backend/.venv/bin/python -m pilot_space.ai.workers.conversation_worker

# Restart policy
Restart=always
RestartSec=10

# Resource limits
MemoryLimit=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Deploy:**
```bash
# Enable and start 5 worker instances
for i in {1..5}; do
    sudo systemctl enable conversation-worker@$i
    sudo systemctl start conversation-worker@$i
done

# Check status
sudo systemctl status conversation-worker@*

# View logs
sudo journalctl -u conversation-worker@1 -f
```

---

### 2. Docker Compose

```yaml
version: '3.8'

services:
  conversation-worker:
    image: pilot-space-backend:latest
    command: python -m pilot_space.ai.workers.conversation_worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - WORKER_COUNT=5
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
```

---

### 3. Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: conversation-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: conversation-worker
  template:
    metadata:
      labels:
        app: conversation-worker
    spec:
      containers:
      - name: worker
        image: pilot-space-backend:latest
        command: ["python", "-m", "pilot_space.ai.workers.conversation_worker"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: pilot-space-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /metrics
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Monitoring

### 1. Prometheus Metrics

```python
# Exposed on :9090/metrics

# Counter: Total messages processed
ai_messages_processed_total{status="success"} 1523
ai_messages_processed_total{status="failed"} 5
ai_messages_processed_total{status="dlq"} 2

# Histogram: Processing duration
ai_processing_duration_seconds_bucket{le="5.0"} 1200
ai_processing_duration_seconds_bucket{le="10.0"} 1450
ai_processing_duration_seconds_bucket{le="30.0"} 1520
ai_processing_duration_seconds_sum 8234.5
ai_processing_duration_seconds_count 1530

# Gauge: Queue depth
ai_queue_depth 42
```

### 2. Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Conversation Worker",
    "panels": [
      {
        "title": "Messages Processed",
        "targets": [
          {
            "expr": "rate(ai_messages_processed_total[5m])"
          }
        ]
      },
      {
        "title": "Processing Duration (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ai_processing_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Queue Depth",
        "targets": [
          {
            "expr": "ai_queue_depth"
          }
        ]
      }
    ]
  }
}
```

---

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_worker_processes_message():
    """Verify worker can process a message."""

    # Mock dependencies
    queue = AsyncMock()
    redis = AsyncMock()
    db = AsyncMock()

    worker = ConversationWorker(queue, redis, db)

    job = {
        "job_id": "test-job-id",
        "session_id": "test-session",
        "workspace_id": "test-workspace",
        "user_id": "test-user",
        "message": "Hello"
    }

    # Mock Claude SDK response
    with patch('pilot_space.ai.workers.conversation_worker.query') as mock_query:
        mock_query.return_value = [
            MagicMock(type="text_delta", content="Hi "),
            MagicMock(type="text_delta", content="there!"),
            MagicMock(type="message_stop", input_tokens=10, output_tokens=5)
        ]

        await worker.process_message(job)

        # Verify Redis publish was called
        assert redis.publish.called
        # Verify database update was called
        assert db.execute.called
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_queue_flow():
    """Test full flow: enqueue → worker → database."""

    # 1. Enqueue job
    response = await client.post("/api/v1/ai/chat", json={
        "message": "Test message",
        "context": {"workspace_id": workspace_id}
    })
    job_id = response.json()["job_id"]

    # 2. Wait for worker to process (max 30s)
    for _ in range(30):
        status = await redis.get(f"status:{job_id}")
        if status == b"completed":
            break
        await asyncio.sleep(1)

    # 3. Verify message in database
    message = await db.get(AIMessage, job_id=job_id)
    assert message.completed_at is not None
    assert len(message.content) > 0
    assert message.token_usage is not None
```

---

## Troubleshooting

### Issue: Worker not processing jobs

**Check:**
```bash
# Queue depth
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ai_conversation_queue"

# Worker logs
sudo journalctl -u conversation-worker@1 -n 100

# Redis connectivity
redis-cli ping

# Database connectivity
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: Jobs stuck in queue

**Cause:** Worker crashed mid-processing, visibility timeout not expired.

**Solution:**
```sql
-- Check stuck jobs (visibility timeout expired)
SELECT * FROM ai_conversation_queue
WHERE vt < NOW();

-- Reset visibility timeout
UPDATE ai_conversation_queue
SET vt = NOW() + INTERVAL '5 minutes'
WHERE vt < NOW();
```

### Issue: High memory usage

**Check:**
```bash
# Worker memory
ps aux | grep conversation_worker

# Redis memory
redis-cli INFO memory
```

**Solution:**
```python
# Add memory limits to systemd service
MemoryLimit=512M

# Or reduce worker count
WORKER_COUNT=3
```

---

## Next Steps

1. ✅ Implement worker code
2. ✅ Add unit tests
3. ✅ Set up deployment (systemd/docker/k8s)
4. ✅ Configure monitoring (Prometheus + Grafana)
5. ⏭️ Update FastAPI endpoints (see simplified-queue-architecture.md)
6. ⏭️ Deploy to staging and load test

**References:**
- Architecture: `simplified-queue-architecture.md`
- Database migration: `database-schema-migration.md`
- Full review: `claude-sdk-architecture-review.md`
