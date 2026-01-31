"""Reconnection support mixin for ConversationWorker.

Stores partial responses and events in Redis for recovery after disconnect.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from pilot_space.ai.streaming.sse_handler import SSEEvent
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)


class ReconnectionMixin:
    """Mixin to add reconnection support to ConversationWorker.

    Stores:
    1. Partial responses as they stream (for recovery)
    2. All events in order (for catchup after disconnect)
    3. Stream active flag (for reconnection detection)
    """

    redis: RedisClient  # Provided by parent class

    async def start_stream_session(self, job_id: UUID):
        """Initialize stream session for reconnection support.

        Call this before starting to stream events.
        """
        # Set stream active flag (TTL 10 minutes)
        await self.redis.setex(
            f"stream:active:{job_id}",
            600,  # 10 minutes
            "1"
        )

        # Initialize partial response storage
        await self.redis.setex(
            f"partial:response:{job_id}",
            600,
            ""
        )

        # Initialize events list
        await self.redis.delete(f"stream:events:{job_id}")

        logger.debug(f"Stream session started for job {job_id}")

    async def store_stream_event(
        self,
        job_id: UUID,
        event: SSEEvent,
        event_index: int
    ):
        """Store event for catchup after disconnect.

        Events are stored in Redis list with 5-minute TTL.
        Frontend can fetch missed events using /stream/{job_id}/events
        """
        event_data = {
            "index": event_index,
            "type": event.type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat() if hasattr(event, "timestamp") else None
        }

        # Append to events list
        events_key = f"stream:events:{job_id}"
        await self.redis.rpush(events_key, json.dumps(event_data))
        await self.redis.expire(events_key, 300)  # 5 minutes

        # Update partial response if text_delta
        if event.type == "text_delta":
            await self._append_partial_response(job_id, event.data.get("content", ""))

    async def _append_partial_response(self, job_id: UUID, content: str):
        """Append to partial response storage.

        This allows users to see what was generated before disconnect.
        """
        partial_key = f"partial:response:{job_id}"

        # Get current partial response (raw bytes, no JSON)
        current = await self.redis.get_raw(partial_key)
        current_text = current.decode() if current else ""

        # Append new content
        updated = current_text + content

        # Store with 10-minute TTL
        await self.redis.setex(partial_key, 600, updated)

    async def end_stream_session(self, job_id: UUID, success: bool = True):
        """End stream session and cleanup reconnection data.

        Call this after stream completes or fails.
        """
        # Remove active flag
        await self.redis.delete(f"stream:active:{job_id}")

        if success:
            # Keep events and partial response for 5 more minutes
            # (in case user wants to review)
            await self.redis.expire(f"stream:events:{job_id}", 300)
            await self.redis.expire(f"partial:response:{job_id}", 300)
        else:
            # Failed - keep for longer for debugging
            await self.redis.expire(f"stream:events:{job_id}", 3600)  # 1 hour
            await self.redis.expire(f"partial:response:{job_id}", 3600)

        logger.debug(
            f"Stream session ended for job {job_id} "
            f"(success={success})"
        )

    async def extend_stream_session(self, job_id: UUID):
        """Extend stream session TTL.

        Call this periodically during long-running streams
        to prevent session expiration.
        """
        await self.redis.expire(f"stream:active:{job_id}", 600)
        await self.redis.expire(f"partial:response:{job_id}", 600)


# Updated ConversationWorker with reconnection support

class ConversationWorkerWithReconnection(ReconnectionMixin):
    """ConversationWorker with reconnection support.

    Example integration:
    ```python
    async def _process_message(self, message: QueueMessage):
        # ... existing code ...

        # Start reconnection session
        await self.start_stream_session(job_id)

        try:
            event_index = 0

            async for event in client.stream(payload.message):
                # Store event for catchup
                await self.store_stream_event(job_id, event, event_index)
                event_index += 1

                # Publish to SSE (existing code)
                await self._publish_event(job_id, event)

                # Extend session every 2 minutes
                if event_index % 50 == 0:
                    await self.extend_stream_session(job_id)

            # Stream completed successfully
            await self.end_stream_session(job_id, success=True)

        except Exception as e:
            # Stream failed
            await self.end_stream_session(job_id, success=False)
            raise
    ```
    """
