"""IntentDetectionService: detect work intents from text via Sonnet structured output.

T-008: detect(text, source) -> WorkIntent[]
T-009: Intent detection LLM prompt with few-shot examples
T-010: Chat-priority window (Redis lock, 3s TTL)

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.exceptions import ProviderUnavailableError
from pilot_space.ai.infrastructure.resilience import ResilientExecutor, RetryConfig
from pilot_space.ai.providers.provider_selector import ProviderSelector, TaskType
from pilot_space.domain.work_intent import DedupStatus, IntentStatus, WorkIntent
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.database.repositories.intent_repository import (
        WorkIntentRepository,
    )

logger = get_logger(__name__)

# Chat-priority window: Redis key pattern and TTL
_CHAT_LOCK_KEY_PREFIX = "intent_lock:"
_CHAT_LOCK_TTL_SECONDS = 3

# Minimum confidence threshold for detected intents
_MIN_CONFIDENCE = 0.3
_CLARIFICATION_THRESHOLD = 0.7


class IntentSource(StrEnum):
    """Source of the text being analyzed for intents."""

    CHAT = "chat"
    NOTE = "note"


_DETECTION_PROMPT = """\
You are an AI assistant that detects work intents from user text.

A work intent is a task or action the user wants to accomplish, expressed directly or implied.
Extract all distinct intents from the text.

For each intent, produce:
- "what": Precise, actionable description of what should be done (required)
- "why": Motivation or business reason behind the intent (optional, null if unclear)
- "constraints": List of constraints as strings (optional, null if none)
- "acceptance": List of acceptance criteria as strings (optional, null if none)
- "confidence": Float between 0.0 and 1.0 indicating how certain you are this is an intent

Guidelines:
- Confidence >= 0.9: Explicit, unambiguous intent ("create a login page")
- Confidence 0.7-0.9: Clear intent with some ambiguity ("we need authentication")
- Confidence < 0.7: Implied or vague intent (include but flag for clarification)
- Return [] (empty array) if no intents are detected
- Maximum 10 intents per call
- Each "what" must be unique and specific

Few-shot examples:

--- Example 1 (chat source) ---
User text: "Can you create a user registration form with email validation and a password field?"
Output:
[
  {
    "what": "Create a user registration form with email validation and password field",
    "why": "Enable new users to sign up for the application",
    "constraints": ["Must include email validation", "Must include password field"],
    "acceptance": ["Form submits successfully with valid data", "Validation errors shown for invalid input"],
    "confidence": 0.97
  }
]

--- Example 2 (chat source) ---
User text: "The API is too slow, we should probably cache things."
Output:
[
  {
    "what": "Implement caching layer for API responses",
    "why": "Improve API performance which is currently too slow",
    "constraints": null,
    "acceptance": ["API response time improves measurably"],
    "confidence": 0.72
  }
]

--- Example 3 (chat source) ---
User text: "Let me know if you have questions about the project."
Output: []

--- Example 4 (note source) ---
User text: "TODO: Add rate limiting to all public endpoints. Also we need to write tests for the auth module."
Output:
[
  {
    "what": "Add rate limiting to all public API endpoints",
    "why": "Protect the system from abuse and ensure fair usage",
    "constraints": null,
    "acceptance": ["Rate limiting applied to all public endpoints", "Appropriate 429 responses returned"],
    "confidence": 0.95
  },
  {
    "what": "Write tests for the auth module",
    "why": "Ensure auth module correctness and prevent regressions",
    "constraints": null,
    "acceptance": ["Test coverage > 80% for auth module"],
    "confidence": 0.95
  }
]

--- Example 5 (note source) ---
User text: "Meeting notes: Discussed migration strategy. Team seems to want something simpler."
Output:
[
  {
    "what": "Design a simpler database migration strategy",
    "why": "Team expressed preference for a simpler approach during meeting",
    "constraints": null,
    "acceptance": null,
    "confidence": 0.55
  }
]

--- Example 6 (note source) ---
User text: "We talked about deployment a bit. Not sure what direction to go."
Output: []

--- Example 7 (chat source) ---
User text: "Fix the bug in the payment processing module where decimal amounts are rounded incorrectly, and also update the API docs."
Output:
[
  {
    "what": "Fix decimal rounding bug in payment processing module",
    "why": "Incorrect rounding causes financial calculation errors",
    "constraints": null,
    "acceptance": ["Decimal amounts are preserved correctly", "Existing tests pass"],
    "confidence": 0.95
  },
  {
    "what": "Update API documentation",
    "why": null,
    "constraints": null,
    "acceptance": ["API docs reflect current behavior"],
    "confidence": 0.88
  }
]

--- Example 8 (note source) ---
User text: "Architecture review notes: We need a service mesh for inter-service communication. Also consider adding distributed tracing."
Output:
[
  {
    "what": "Implement service mesh for inter-service communication",
    "why": "Improve inter-service communication management",
    "constraints": null,
    "acceptance": ["Service-to-service communication routed through mesh"],
    "confidence": 0.88
  },
  {
    "what": "Add distributed tracing to the system",
    "why": "Improve observability across services",
    "constraints": null,
    "acceptance": ["Traces visible across service boundaries"],
    "confidence": 0.75
  }
]

Now analyze the following text and return ONLY a valid JSON array (no markdown, no extra text):

Source type: {source}
Text: {text}
"""


@dataclass(frozen=True, slots=True)
class DetectIntentPayload:
    """Payload for intent detection."""

    workspace_id: UUID
    text: str
    source: IntentSource
    source_block_id: UUID | None = None
    owner: str | None = None


@dataclass(frozen=True, slots=True)
class DetectIntentResult:
    """Result from intent detection."""

    intents: list[WorkIntent]
    detection_model: str
    total_detected: int
    chat_lock_was_active: bool = False


def _parse_llm_response(
    raw: str,
    workspace_id: UUID,
    source: IntentSource,
    source_block_id: UUID | None,
    owner: str | None,
) -> list[WorkIntent]:
    """Parse LLM JSON response into WorkIntent domain objects.

    Args:
        raw: Raw LLM text response.
        workspace_id: Workspace UUID for scoping.
        source: Source of the detection request.
        source_block_id: Optional TipTap block reference.
        owner: Optional owner string.

    Returns:
        List of WorkIntent domain objects.
    """
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON for intent detection", extra={"raw": text[:200]})
        return []

    if not isinstance(data, list):
        logger.warning("LLM returned non-list for intent detection")
        return []

    intents: list[WorkIntent] = []
    for item in data[:10]:  # Cap at 10
        if not isinstance(item, dict):
            continue
        what = item.get("what", "").strip()
        if not what:
            continue
        confidence = float(item.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        intent = WorkIntent(
            workspace_id=workspace_id,
            what=what,
            why=item.get("why"),
            constraints=item.get("constraints"),
            acceptance=item.get("acceptance"),
            confidence=confidence,
            status=IntentStatus.DETECTED,
            dedup_status=DedupStatus.PENDING,
            source_block_id=source_block_id,
            owner=owner,
        )
        intents.append(intent)

    return intents


class IntentDetectionService:
    """Detects work intents from text via Claude Sonnet structured output.

    Implements:
    - T-008: detect(text, source) -> WorkIntent[]
    - T-009: Intent detection LLM prompt with few-shot examples
    - T-010: Chat-priority window (Redis lock, 3s TTL)

    Chat source sets a Redis lock. Note source checks the lock and discards
    if chat detection is in progress (prevents duplicate intents).
    """

    def __init__(
        self,
        session: AsyncSession,
        intent_repository: WorkIntentRepository,
        redis_client: RedisClient,
    ) -> None:
        self._session = session
        self._intent_repo = intent_repository
        self._redis = redis_client

    async def detect(self, payload: DetectIntentPayload) -> DetectIntentResult:
        """Detect work intents from text.

        For chat sources: Sets Redis lock for 3s to block note detection.
        For note sources: Checks Redis lock; returns empty if chat active.

        Args:
            payload: Detection parameters including text and source.

        Returns:
            DetectIntentResult with detected and persisted WorkIntent list.
        """
        chat_lock_was_active = False

        if payload.source == IntentSource.NOTE:
            # T-010: If chat lock is active, discard note detection
            lock_key = f"{_CHAT_LOCK_KEY_PREFIX}{payload.workspace_id}"
            lock_val = await self._redis.get(lock_key)
            if lock_val is not None:
                logger.info(
                    "Chat-priority lock active, skipping note intent detection",
                    extra={"workspace_id": str(payload.workspace_id)},
                )
                return DetectIntentResult(
                    intents=[],
                    detection_model="skipped",
                    total_detected=0,
                    chat_lock_was_active=True,
                )
        elif payload.source == IntentSource.CHAT:
            # T-010: Set chat lock for 3s
            lock_key = f"{_CHAT_LOCK_KEY_PREFIX}{payload.workspace_id}"
            await self._redis.set(lock_key, "1", ttl=_CHAT_LOCK_TTL_SECONDS)

        if not payload.text.strip():
            return DetectIntentResult(
                intents=[],
                detection_model="noop",
                total_detected=0,
                chat_lock_was_active=chat_lock_was_active,
            )

        # Call LLM for structured intent detection
        llm_intents, model = await self._call_llm(
            payload.text, payload.source, payload.workspace_id
        )

        # Persist detected intents
        persisted: list[WorkIntent] = []
        for intent in llm_intents:
            # Override fields from payload
            intent.source_block_id = payload.source_block_id
            intent.owner = payload.owner
            model_obj = await self._persist_intent(intent)
            persisted.append(model_obj)

        logger.info(
            "Intent detection complete",
            extra={
                "workspace_id": str(payload.workspace_id),
                "source": payload.source,
                "detected": len(persisted),
                "model": model,
            },
        )

        return DetectIntentResult(
            intents=persisted,
            detection_model=model,
            total_detected=len(persisted),
            chat_lock_was_active=chat_lock_was_active,
        )

    async def _call_llm(
        self,
        text: str,
        source: IntentSource,
        workspace_id: UUID,
    ) -> tuple[list[WorkIntent], str]:
        """Call Sonnet for structured intent detection.

        Returns:
            Tuple of (intents list, model name used).
        """
        api_key = await self._resolve_api_key(workspace_id)
        if api_key is None:
            logger.info("No API key available for intent detection, returning empty")
            return [], "noop"

        selector = ProviderSelector()
        config = selector.select_with_config(TaskType.ISSUE_EXTRACTION)
        model = config.model

        prompt = _DETECTION_PROMPT.replace("{source}", source.value).replace("{text}", text[:8000])

        executor = ResilientExecutor()
        retry_config = RetryConfig(max_retries=2, base_delay_seconds=1.0)

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key)

            async def _call_api() -> str:
                response = await client.messages.create(
                    model=model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                for block in response.content:
                    if block.type == "text":
                        return block.text
                return "[]"

            raw = await executor.execute(
                provider="anthropic",
                operation=_call_api,
                timeout_sec=30.0,
                retry_config=retry_config,
            )

            intents = _parse_llm_response(
                raw,
                workspace_id=workspace_id,
                source=source,
                source_block_id=None,  # Set per-intent in caller
                owner=None,
            )
            return intents, model

        except ProviderUnavailableError:
            logger.warning("Anthropic provider unavailable for intent detection")
            return [], "noop"
        except Exception:
            logger.exception("Intent detection LLM call failed")
            return [], "noop"

    async def _persist_intent(self, intent: WorkIntent) -> WorkIntent:
        """Persist a domain WorkIntent to the DB model and return it.

        Args:
            intent: Domain WorkIntent to persist.

        Returns:
            Persisted WorkIntent (domain entity reconstructed from ORM model).
        """
        from pilot_space.infrastructure.database.models.work_intent import (
            WorkIntent as DBWorkIntent,
        )

        db_model = DBWorkIntent(
            workspace_id=intent.workspace_id,
            what=intent.what,
            why=intent.why,
            constraints=intent.constraints,
            acceptance=intent.acceptance,
            confidence=intent.confidence,
            status=intent.status,
            dedup_status=intent.dedup_status,
            source_block_id=intent.source_block_id,
            owner=intent.owner,
            parent_intent_id=intent.parent_intent_id,
            dedup_hash=intent.dedup_hash,
        )

        created = await self._intent_repo.create(db_model)
        await self._session.flush()

        # Return as domain entity
        return WorkIntent(
            id=created.id,
            workspace_id=created.workspace_id,
            what=created.what,
            why=created.why,
            constraints=created.constraints,
            acceptance=created.acceptance,
            confidence=created.confidence,
            status=IntentStatus(created.status.value),
            dedup_status=DedupStatus(created.dedup_status.value),
            source_block_id=created.source_block_id,
            owner=created.owner,
            parent_intent_id=created.parent_intent_id,
            dedup_hash=created.dedup_hash,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def _resolve_api_key(self, workspace_id: UUID) -> str | None:
        """Resolve Anthropic API key from workspace Vault or app-level settings."""
        try:
            from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
            from pilot_space.config import get_settings

            settings = get_settings()
            encryption_key = settings.encryption_key.get_secret_value()
            if encryption_key:
                storage = SecureKeyStorage(self._session, encryption_key)
                key = await storage.get_api_key(workspace_id, "anthropic", "llm")
                if key:
                    return key
        except (ValueError, AttributeError) as e:
            logger.warning("Workspace API key config error: %s", e)
        except Exception:
            logger.error("Unexpected error fetching workspace API key", exc_info=True)
            raise

        try:
            from pilot_space.config import get_settings

            settings = get_settings()
            if settings.anthropic_api_key:
                return settings.anthropic_api_key.get_secret_value()
        except (ValueError, AttributeError) as e:
            logger.warning("App-level API key config error: %s", e)
        except Exception:
            logger.error("Unexpected error fetching app-level API key", exc_info=True)
            raise

        return None
