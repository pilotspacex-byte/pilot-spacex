"""DeviationAnalysisHandler -- AI deviation detection between PR and source spec.

Triggered after a BatchRunIssue completes successfully with a PR URL.
Compares the implementation (PR) against the original spec note using a
cheap Haiku model call. If deviation is detected, appends an annotation
to the source note's spec_annotations JSONB array.

Living Specs feature (Phase 78, Plan 01 — LSP-02).

Message payload:
    {
        "task_type": "deviation_analysis",
        "issue_id": "<uuid>",
        "pr_url": "<github-pr-url>",
        "workspace_id": "<uuid>",
        "actor_user_id": "<uuid>",
        "source_note_id": "<uuid>",
    }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.proxy.llm_gateway import LLMGateway

__all__ = ["TASK_DEVIATION_ANALYSIS", "DeviationAnalysisHandler"]

logger = logging.getLogger(__name__)

TASK_DEVIATION_ANALYSIS = "deviation_analysis"

# Sentinel returned by the model when no deviation is detected.
_NO_DEVIATION_SENTINEL = "NO_DEVIATION"

# Maximum characters of note content to include in the LLM prompt.
_MAX_NOTE_CHARS = 6_000


@dataclass(frozen=True, slots=True)
class _DeviationPayload:
    workspace_id: UUID
    actor_user_id: UUID
    issue_id: UUID
    pr_url: str
    source_note_id: UUID

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _DeviationPayload:
        return cls(
            workspace_id=UUID(str(d["workspace_id"])),
            actor_user_id=UUID(str(d["actor_user_id"])),
            issue_id=UUID(str(d["issue_id"])),
            pr_url=str(d["pr_url"]),
            source_note_id=UUID(str(d["source_note_id"])),
        )


class DeviationAnalysisHandler:
    """Background handler: compare PR vs spec note, append deviation annotation.

    Non-fatal by design — all failure modes are logged and swallowed.
    The handler is registered in MemoryWorker._dispatch for the
    'deviation_analysis' task type.

    Args:
        session: DB session for this job (worker-owned, committed by worker).
        llm_gateway: LLMGateway for cheap model call. May be None if not
            configured — handler short-circuits gracefully.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGateway | None = None,
    ) -> None:
        self._session = session
        self._llm_gateway = llm_gateway

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process one deviation_analysis queue message. Never raises.

        Args:
            payload: Queue message payload dict.

        Returns:
            Result dict with success flag and metadata.
        """
        try:
            p = _DeviationPayload.from_dict(payload)
        except (KeyError, ValueError) as exc:
            logger.warning(
                "DeviationAnalysisHandler: invalid payload %r — %s",
                payload,
                exc,
            )
            return {"success": False, "error": "invalid_payload"}

        if self._llm_gateway is None:
            logger.info(
                "DeviationAnalysisHandler: no LLMGateway wired — skipping "
                "(workspace=%s issue=%s)",
                p.workspace_id,
                p.issue_id,
            )
            return {"success": True, "skipped": "no_llm_gateway"}

        # 1. Load issue details
        try:
            issue_title, issue_description = await self._load_issue(p.issue_id)
        except Exception:
            logger.exception(
                "DeviationAnalysisHandler: failed to load issue %s — abort",
                p.issue_id,
            )
            return {"success": False, "error": "issue_load_failed"}

        # 2. Load note content (plain text)
        try:
            note_text = await self._load_note_text(p.source_note_id)
        except Exception:
            logger.exception(
                "DeviationAnalysisHandler: failed to load note %s — abort",
                p.source_note_id,
            )
            return {"success": False, "error": "note_load_failed"}

        if not note_text.strip():
            logger.info(
                "DeviationAnalysisHandler: note %s has no plain text — skip",
                p.source_note_id,
            )
            return {"success": True, "skipped": "empty_note"}

        # 3. LLM call — cheap Haiku-tier model, non-fatal
        deviation_text = await self._detect_deviation(
            workspace_id=p.workspace_id,
            actor_user_id=p.actor_user_id,
            pr_url=p.pr_url,
            note_text=note_text,
            issue_title=issue_title,
            issue_description=issue_description or "",
        )

        if deviation_text is None:
            return {"success": False, "error": "llm_failed"}

        if deviation_text == _NO_DEVIATION_SENTINEL:
            logger.info(
                "DeviationAnalysisHandler: no deviation detected "
                "(workspace=%s issue=%s pr=%s)",
                p.workspace_id,
                p.issue_id,
                p.pr_url,
            )
            return {"success": True, "deviation_detected": False}

        # 4. Append annotation to source note — non-fatal
        try:
            appended = await self._append_annotation(
                note_id=p.source_note_id,
                issue_id=p.issue_id,
                pr_url=p.pr_url,
                deviation_text=deviation_text,
            )
        except Exception:
            logger.exception(
                "DeviationAnalysisHandler: failed to append annotation "
                "(note=%s issue=%s) — non-fatal",
                p.source_note_id,
                p.issue_id,
            )
            return {"success": False, "error": "annotation_write_failed"}

        if not appended:
            logger.warning(
                "DeviationAnalysisHandler: note %s not found — annotation skipped",
                p.source_note_id,
            )
            return {"success": False, "error": "note_not_found"}

        logger.info(
            "DeviationAnalysisHandler: deviation annotation appended "
            "(workspace=%s note=%s issue=%s)",
            p.workspace_id,
            p.source_note_id,
            p.issue_id,
        )
        return {
            "success": True,
            "deviation_detected": True,
            "note_id": str(p.source_note_id),
            "issue_id": str(p.issue_id),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_issue(self, issue_id: UUID) -> tuple[str, str | None]:
        """Load issue title and description.

        Returns:
            (title, description) tuple.
        """
        from sqlalchemy import select

        from pilot_space.infrastructure.database.models.issue import Issue

        stmt = select(Issue.name, Issue.description).where(Issue.id == issue_id)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise ValueError(f"Issue {issue_id} not found")
        return row[0], row[1]

    async def _load_note_text(self, note_id: UUID) -> str:
        """Load note and extract plain text from TipTap JSON content.

        Returns:
            Plain text string (may be empty).
        """
        from sqlalchemy import select

        from pilot_space.api.v1.schemas.note import extract_text_from_tiptap
        from pilot_space.infrastructure.database.models.note import Note

        stmt = select(Note.content).where(Note.id == note_id, Note.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise ValueError(f"Note {note_id} not found")

        content = row[0]
        text = extract_text_from_tiptap(content)
        return text[:_MAX_NOTE_CHARS]

    async def _detect_deviation(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        pr_url: str,
        note_text: str,
        issue_title: str,
        issue_description: str,
    ) -> str | None:
        """Call LLM to detect deviation. Returns None on failure.

        Returns:
            'NO_DEVIATION' if implementation matches spec,
            deviation description string if mismatch found,
            None if LLM call failed.
        """
        from pilot_space.ai.providers.provider_selector import TaskType

        prompt = (
            f"Compare the PR at {pr_url} against the original spec.\n\n"
            f"SPEC NOTE:\n{note_text}\n\n"
            f"ISSUE: {issue_title}\n{issue_description}\n\n"
            "If the implementation deviates from what the spec describes, "
            "explain the deviation concisely in 1-2 sentences. "
            f"If no deviation is found, respond with exactly '{_NO_DEVIATION_SENTINEL}'."
        )

        try:
            response = await self._llm_gateway.complete(  # type: ignore[union-attr]
                workspace_id=workspace_id,
                user_id=actor_user_id,
                task_type=TaskType.GRAPH_EXTRACTION,  # cheap Haiku-tier task
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.1,
                agent_name="deviation_analysis_handler",
            )
        except Exception:
            logger.exception(
                "DeviationAnalysisHandler: LLM call failed (workspace=%s)",
                workspace_id,
            )
            return None

        text = (response.text or "").strip()
        if not text:
            return None
        return text

    async def _append_annotation(
        self,
        *,
        note_id: UUID,
        issue_id: UUID,
        pr_url: str,
        deviation_text: str,
    ) -> bool:
        """Append deviation annotation to note's spec_annotations.

        Returns:
            True if annotation was appended, False if note not found.
        """
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        note_repo = NoteRepository(self._session)
        annotation: dict[str, Any] = {
            "type": "deviation",
            "content": deviation_text,
            "issue_id": str(issue_id),
            "pr_url": pr_url,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        return await note_repo.append_spec_annotation(note_id, annotation)
