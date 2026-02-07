"""Digest job handler for generating workspace digest suggestions.

Orchestrates the full digest generation pipeline:
1. Deduplication check (skip if recently generated)
2. Build workspace context via DigestContextBuilder
3. Call Claude Sonnet with generate-digest skill prompt
4. Parse structured suggestions
5. Store in workspace_digests table

References:
- specs/012-homepage-note/spec.md Background Job Specification
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Cooldown: skip if a digest was generated within this window
DIGEST_COOLDOWN_MINUTES = 30
# Max suggestions per digest
MAX_SUGGESTIONS = 20
# Timeout for the LLM call (seconds)
LLM_TIMEOUT_SECONDS = 60


class DigestJobHandler:
    """Handler for the generate_workspace_digest background job.

    Called by the queue worker when a digest generation message is
    dequeued from the `ai_low` queue.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DigestJobHandler.

        Args:
            session: The async database session.
        """
        self._session = session

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a digest generation job.

        Args:
            payload: Job payload containing workspace_id and trigger.

        Returns:
            Result dict with status and suggestion_count.
        """
        workspace_id = uuid.UUID(payload["workspace_id"])
        trigger = payload.get("trigger", "scheduled")

        logger.info(
            "Starting digest generation",
            extra={"workspace_id": str(workspace_id), "trigger": trigger},
        )

        # Step 1: Deduplication check
        if await self._recently_generated(workspace_id):
            logger.info(
                "Skipping digest generation: recent digest exists",
                extra={"workspace_id": str(workspace_id)},
            )
            return {"status": "skipped", "reason": "cooldown"}

        # Step 2: Build context
        from pilot_space.ai.jobs.digest_context import DigestContextBuilder

        builder = DigestContextBuilder(self._session)
        context = await builder.build(workspace_id)

        if context.total_chars == 0:
            logger.info(
                "Skipping digest generation: no workspace activity",
                extra={"workspace_id": str(workspace_id)},
            )
            return {"status": "skipped", "reason": "no_activity"}

        # Step 3: Generate suggestions via LLM
        suggestions = await self._generate_suggestions(workspace_id, context.to_prompt_text())

        # Step 4: Store digest
        await self._store_digest(
            workspace_id=workspace_id,
            trigger=trigger,
            suggestions=suggestions,
        )

        logger.info(
            "Digest generation complete",
            extra={
                "workspace_id": str(workspace_id),
                "suggestion_count": len(suggestions),
            },
        )

        return {"status": "completed", "suggestion_count": len(suggestions)}

    async def _recently_generated(self, workspace_id: uuid.UUID) -> bool:
        """Check if a digest was generated recently (cooldown guard).

        Args:
            workspace_id: Workspace to check.

        Returns:
            True if a recent digest exists.
        """
        from pilot_space.infrastructure.database.repositories.digest_repository import (
            DigestRepository,
        )

        repo = DigestRepository(self._session)
        since = datetime.now(tz=UTC) - timedelta(minutes=DIGEST_COOLDOWN_MINUTES)
        return await repo.check_recent_digest_exists(workspace_id, since=since)

    async def _generate_suggestions(
        self, workspace_id: uuid.UUID, context_text: str
    ) -> list[dict[str, Any]]:
        """Call LLM to generate digest suggestions.

        Uses Claude Sonnet via direct Anthropic API call with workspace
        BYOK key. Falls back to empty suggestions on failure.

        Args:
            workspace_id: Workspace for API key lookup.
            context_text: Formatted workspace context.

        Returns:
            List of suggestion dicts.
        """
        prompt = self._build_prompt(context_text)

        try:
            from anthropic import AsyncAnthropic

            from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
            from pilot_space.ai.sdk.config import MODEL_SONNET
            from pilot_space.config import get_settings

            settings = get_settings()
            encryption_key = settings.encryption_key.get_secret_value()
            if not encryption_key:
                logger.warning("Encryption key not configured, using fallback")
                return self._fallback_suggestions()

            key_storage = SecureKeyStorage(db=self._session, master_secret=encryption_key)
            api_key = await key_storage.get_api_key(workspace_id, "anthropic")
            if not api_key:
                logger.warning(
                    "Anthropic API key not configured for workspace %s",
                    workspace_id,
                )
                return self._fallback_suggestions()

            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=MODEL_SONNET,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                timeout=LLM_TIMEOUT_SECONDS,
            )

            # Extract text content from response
            content = ""
            for block in response.content:
                if block.type == "text":
                    content = block.text
                    break

            return self._parse_suggestions(content)

        except Exception:
            logger.exception("Digest LLM call failed, using fallback")
            return self._fallback_suggestions()

    @staticmethod
    def _build_prompt(context_text: str) -> str:
        """Build the generate-digest prompt.

        Args:
            context_text: Workspace context summary.

        Returns:
            Full prompt string for LLM.
        """
        return f"""You are an AI assistant analyzing a software workspace.
Based on the following workspace context, generate actionable digest suggestions.

{context_text}

Generate a JSON array of suggestions. Each suggestion must have:
- "id": a new UUID string
- "category": one of (stale_issues, unlinked_notes, review_needed, blocked_dependencies, cycle_risk, overdue_items, unassigned_priority, annotation_pending)
- "title": short actionable title (max 80 chars)
- "description": detailed explanation (max 200 chars)
- "entity_type": "issue", "note", or "cycle"
- "relevance_score": float 0.0-1.0

Return ONLY valid JSON array, no other text. Maximum {MAX_SUGGESTIONS} suggestions."""

    @staticmethod
    def _parse_suggestions(content: str) -> list[dict[str, Any]]:
        """Parse LLM response into suggestion dicts.

        Args:
            content: Raw LLM response text.

        Returns:
            Parsed list of suggestion dicts.
        """
        try:
            # Try to extract JSON from response
            # Handle cases where LLM wraps in markdown code blocks
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first and last lines (code block markers)
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

            suggestions = json.loads(text)
            if not isinstance(suggestions, list):
                return []

            # Validate and ensure UUIDs
            valid: list[dict[str, Any]] = []
            for s in suggestions[:MAX_SUGGESTIONS]:
                if not isinstance(s, dict):
                    continue
                if "id" not in s:
                    s["id"] = str(uuid.uuid4())
                valid.append(s)

            return valid

        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse digest suggestions from LLM response")
            return []

    @staticmethod
    def _fallback_suggestions() -> list[dict[str, Any]]:
        """Generate basic fallback suggestions without LLM.

        Used when LLM is unavailable. Returns generic workspace
        health check suggestions.

        Returns:
            List of basic suggestion dicts.
        """
        return []

    async def _store_digest(
        self,
        workspace_id: uuid.UUID,
        trigger: str,
        suggestions: list[dict[str, Any]],
    ) -> None:
        """Store generated digest in the database.

        Args:
            workspace_id: Workspace the digest belongs to.
            trigger: Generation trigger ('scheduled' or 'manual').
            suggestions: List of suggestion dicts.
        """
        from pilot_space.infrastructure.database.models.workspace_digest import (
            WorkspaceDigest,
        )
        from pilot_space.infrastructure.database.repositories.digest_repository import (
            DigestRepository,
        )

        digest = WorkspaceDigest(
            workspace_id=workspace_id,
            generated_by=trigger,
            suggestions=suggestions,
        )

        repo = DigestRepository(self._session)
        await repo.save_digest(digest)
        await self._session.flush()


__all__ = ["DigestJobHandler"]
