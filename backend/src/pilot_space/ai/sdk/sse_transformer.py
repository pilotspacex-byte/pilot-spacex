"""SSE (Server-Sent Events) data class for AI streaming.

Provides the SSEEvent dataclass used by the transformation pipeline
in pilotspace_agent_helpers.transform_sdk_message().

Reference: DD-058 (SSE for AI Streaming)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SSEEvent:
    """Server-Sent Event for AI streaming.

    Attributes:
        event: Event type identifier.
        data: Event payload as JSON-serializable dict.
    """

    event: str
    data: dict[str, Any]

    def to_sse_string(self) -> str:
        """Convert to SSE format string.

        Returns:
            SSE-formatted string with event type and JSON data.
        """
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"
