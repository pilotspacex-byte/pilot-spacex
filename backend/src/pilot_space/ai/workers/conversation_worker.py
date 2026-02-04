"""Background worker for queue-based conversational AI processing.

Dequeues chat jobs from Supabase Queue, uses ClaudeSDKClient for persistent
multi-turn conversations, and publishes SSE events to Redis pub/sub.

Architecture:
    POST /ai/chat → enqueue(ai_chat, payload) → return {job_id, stream_url}
    GET /ai/chat/stream/{job_id} → Redis SUBSCRIBE(chat:stream:{job_id})
    ConversationWorker → dequeue() → ClaudeSDKClient.send_message() → PUBLISH per chunk

Client Pool:
    Maintains persistent ClaudeSDKClient instances keyed by session_id.
    Clients are reused across turns and evicted after IDLE_TIMEOUT (5 min).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import ChatInput
from pilot_space.ai.workers.reconnection_mixin import ReconnectionMixin
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient

    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)


@dataclass
class PooledClient:
    """A pooled ClaudeSDKClient with metadata for lifecycle management.

    Attributes:
        client: Connected ClaudeSDKClient instance.
        last_used: Monotonic timestamp of last use.
        workspace_id: Workspace this client belongs to.
        user_id: User this client belongs to.
    """

    client: ClaudeSDKClient
    last_used: float
    workspace_id: UUID
    user_id: UUID


class ConversationWorker(ReconnectionMixin):
    """Background worker: dequeue → ClaudeSDKClient → Redis pub/sub.

    Polls the AI_CHAT queue for jobs, processes each with a persistent
    ClaudeSDKClient, and publishes SSE events to Redis channels.

    Supports:
    - Multi-turn conversations via session-based client pool
    - Reconnection via stored events in Redis lists
    - Automatic retry with dead-letter queue on repeated failure
    - Idle client eviction after IDLE_TIMEOUT
    """

    IDLE_TIMEOUT = 300  # 5 minutes — evict idle clients

    def __init__(
        self,
        queue: SupabaseQueueClient,
        redis: RedisClient,
        agent: PilotSpaceAgent,
        session_handler: SessionHandler | None,
    ) -> None:
        """Initialize conversation worker.

        Args:
            queue: Supabase queue client for dequeue/ack/nack.
            redis: Redis client for pub/sub and event storage.
            agent: Fully initialized PilotSpaceAgent.
            session_handler: Session handler for multi-turn (None if Redis down).
        """
        self.queue = queue
        self.redis = redis
        self.agent = agent
        self.session_handler = session_handler
        self._running = False
        self._clients: dict[str, PooledClient] = {}

    async def start(self) -> None:
        """Poll loop: dequeue → process → ack/nack with periodic cleanup."""
        self._running = True
        cleanup_counter = 0
        logger.info("ConversationWorker started, polling ai_chat queue")
        while self._running:
            try:
                messages = await self.queue.dequeue(
                    QueueName.AI_CHAT, batch_size=1, visibility_timeout=600
                )
                if messages:
                    await self._process(messages[0])
                else:
                    await asyncio.sleep(1.0)

                cleanup_counter += 1
                if cleanup_counter >= 60:
                    await self._cleanup_idle_clients()
                    cleanup_counter = 0
            except asyncio.CancelledError:
                logger.info("ConversationWorker cancelled")
                break
            except Exception:
                logger.exception("Worker poll error")
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        """Signal the worker to stop polling and disconnect all clients."""
        self._running = False
        for sid in list(self._clients):
            await self._evict_client(sid)
        logger.info("ConversationWorker stopped, all clients disconnected")

    async def _process(self, message: object) -> None:
        """Process single chat job from queue.

        Uses ClaudeSDKClient from pool (or creates new) for persistent
        multi-turn conversation support.

        Args:
            message: Queue message with payload containing job details.
        """
        payload = message.payload  # type: ignore[attr-defined]
        job_id = UUID(payload["job_id"])
        channel = f"chat:stream:{job_id}"
        session_id = payload.get("session_id")
        start_time = time.monotonic()

        try:
            await self.start_stream_session(job_id)

            chat_input = ChatInput(
                message=payload["message"],
                session_id=UUID(session_id) if session_id else None,
                context=payload.get("context", {}),
                user_id=UUID(payload["user_id"]),
                workspace_id=UUID(payload["workspace_id"]),
            )
            agent_context = AgentContext(
                workspace_id=UUID(payload["workspace_id"]),
                user_id=UUID(payload["user_id"]),
            )

            # Get or create client from pool
            client, query_session_id = await self._get_or_create_client(
                session_id, chat_input, agent_context
            )

            # Send message via query() and stream response
            await client.query(chat_input.message, session_id=query_session_id)

            event_index = 0
            async for msg in client.receive_response():
                sse_event = self.agent.transform_sdk_message(msg, agent_context)
                if sse_event:
                    await self.redis.publish(channel, sse_event)
                    await self._store_sse_event(job_id, sse_event, event_index)
                    event_index += 1
                    if event_index % 50 == 0:
                        await self.extend_stream_session(job_id)

            # Cache client for session reuse
            if query_session_id != "default" and query_session_id not in self._clients:
                self._cache_client(query_session_id, client, chat_input)

            # Signal completion
            done_data = {
                "type": "stream_end",
                "session_id": query_session_id if query_session_id != "default" else session_id,
            }
            await self.redis.publish(channel, f"data: {json.dumps(done_data)}\n\n")
            await self.end_stream_session(job_id, success=True)
            await self.queue.ack(QueueName.AI_CHAT, message.id)  # type: ignore[attr-defined]

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.info("Job %s complete: %d events in %dms", job_id, event_index, elapsed_ms)

        except Exception as e:
            logger.exception("Job %s failed", job_id)
            await self.end_stream_session(job_id, success=False)
            error_event = json.dumps({"type": "error", "message": str(e)})
            await self.redis.publish(channel, f"data: {error_event}\n\n")

            # Evict failed client
            if session_id and session_id in self._clients:
                await self._evict_client(session_id)

            msg_id = message.id  # type: ignore[attr-defined]
            attempts = getattr(message, "attempts", 0)
            if attempts < 2:
                await self.queue.nack(QueueName.AI_CHAT, msg_id, error=str(e))
            else:
                await self.queue.move_to_dead_letter(
                    QueueName.AI_CHAT,
                    msg_id,
                    error=str(e),
                    original_payload=payload,
                )

    async def _get_or_create_client(
        self,
        session_id: str | None,
        chat_input: ChatInput,
        context: AgentContext,
    ) -> tuple[ClaudeSDKClient, str]:
        """Get existing client for session or create new one.

        Args:
            session_id: Existing session ID to look up in pool.
            chat_input: Chat input for client creation.
            context: Agent context for client creation.

        Returns:
            Tuple of (connected ClaudeSDKClient, session_id for query()).
        """
        if session_id and session_id in self._clients:
            pooled = self._clients[session_id]
            pooled.last_used = time.monotonic()
            return pooled.client, session_id

        client, query_session_id = await self.agent.create_client(chat_input, context)
        await client.connect()
        return client, query_session_id

    def _cache_client(
        self,
        session_id: str,
        client: ClaudeSDKClient,
        chat_input: ChatInput,
    ) -> None:
        """Cache a connected client for future session reuse.

        Args:
            session_id: Session ID to key the client.
            client: Connected ClaudeSDKClient.
            chat_input: Original input with workspace/user metadata.
        """
        self._clients[session_id] = PooledClient(
            client=client,
            last_used=time.monotonic(),
            workspace_id=chat_input.workspace_id or UUID(int=0),
            user_id=chat_input.user_id or UUID(int=0),
        )

    async def _evict_client(self, session_id: str) -> None:
        """Disconnect and remove a client from the pool.

        Args:
            session_id: Session ID of client to evict.
        """
        if session_id in self._clients:
            pooled = self._clients.pop(session_id)
            try:
                await pooled.client.disconnect()
            except Exception:
                logger.warning("Error disconnecting client %s", session_id)

    async def _cleanup_idle_clients(self) -> None:
        """Evict clients idle longer than IDLE_TIMEOUT."""
        now = time.monotonic()
        expired = [sid for sid, p in self._clients.items() if now - p.last_used > self.IDLE_TIMEOUT]
        for sid in expired:
            logger.info("Evicting idle client %s", sid)
            await self._evict_client(sid)

    async def _store_sse_event(self, job_id: UUID, sse_chunk: str, event_index: int) -> None:
        """Store SSE event for reconnection catch-up.

        Args:
            job_id: Queue job identifier.
            sse_chunk: SSE-formatted event string.
            event_index: Sequence number of this event.
        """
        events_key = f"stream:events:{job_id}"
        await self.redis.rpush(events_key, sse_chunk)
        await self.redis.expire(events_key, 300)  # 5 min TTL

        # Accumulate text deltas for partial response recovery
        if '"text_delta"' in sse_chunk:
            try:
                data_str = sse_chunk.replace("data: ", "").strip()
                data = json.loads(data_str)
                content = data.get("content", "")
                if content:
                    partial_key = f"partial:response:{job_id}"
                    current = await self.redis.get_raw(partial_key)
                    current_text = current.decode() if current else ""
                    await self.redis.setex(partial_key, 600, current_text + content)
            except (json.JSONDecodeError, ValueError):
                pass
