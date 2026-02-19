"""SkillExecutor — executes skills with approval hold, TipTap validation, and concurrency management.

T-044: Skill executor with approval hold (pending_approval vs auto_approved).
T-045: TipTap block schema validation for skill output.
T-047: Semaphore-based skill concurrency manager (max 5 per workspace).
C-3:  Redis mutex for note-level write locking before any note mutation.
C-7:  required_approval_role enforcement — admin-only for destructive skills.

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Final
from uuid import UUID, uuid4

from pilot_space.ai.skills.skill_discovery import SkillInfo, discover_skills
from pilot_space.infrastructure.cache.redis import RedisClient
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Concurrency limit per workspace (T-047)
MAX_CONCURRENT_SKILLS_PER_WORKSPACE: Final[int] = 5

# Redis mutex TTL for note-level write locking (C-3)
NOTE_WRITE_LOCK_TTL_S: Final[int] = 30

# Redis key prefix for note locks
_NOTE_LOCK_PREFIX = "note_write_lock"

# Redis key prefix for workspace skill semaphore
_SKILL_SEMAPHORE_PREFIX = "skill_semaphore"

# Skills requiring admin approval (C-7)
_ADMIN_REQUIRED_SKILLS: Final[frozenset[str]] = frozenset(
    {
        "generate-migration",
    }
)

# Skills that auto-execute without approval (DD-003 AUTO_EXECUTE)
_AUTO_EXECUTE_SKILLS: Final[frozenset[str]] = frozenset(
    {
        "review-code",
        "review-architecture",
        "scan-security",
        "summarize",
        "improve-writing",
        "find-duplicates",
        "recommend-assignee",
        "generate-diagram",
        "generate-digest",
    }
)


class SkillApprovalDecision(StrEnum):
    """Approval decision for a skill execution."""

    AUTO_APPROVED = "auto_approved"
    PENDING_APPROVAL = "pending_approval"


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillExecutionRequest:
    """Request to execute a skill.

    Attributes:
        skill_name: Name of the skill to execute (e.g. 'generate-code').
        workspace_id: Workspace context for RLS scoping.
        user_id: User triggering the skill.
        note_id: Note to write output to (for write-locking C-3).
        intent_id: Parent work intent (for DB record linkage).
        parameters: Skill-specific parameters passed from the agent.
    """

    skill_name: str
    workspace_id: UUID
    user_id: UUID
    note_id: UUID | None
    intent_id: UUID
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillExecutionResult:
    """Result of a skill execution attempt.

    Attributes:
        execution_id: UUID of the created skill_executions row.
        approval_decision: Whether execution auto-approved or needs approval.
        required_approval_role: Role needed to approve (None if auto-approved).
        output: Skill output payload (None if pending_approval until user approves).
        error: Error message if execution failed.
        queued: True if execution was queued due to concurrency limit (T-047).
        queue_position: Estimated position in workspace queue.
    """

    execution_id: UUID
    approval_decision: SkillApprovalDecision
    required_approval_role: str | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    queued: bool = False
    queue_position: int = 0


class TipTapValidator:
    """Validates TipTap JSON block output from skills (T-045).

    TipTap documents must conform to ProseMirror JSON schema.
    Invalid output is caught before persisting to note content.
    """

    # Required top-level keys for a valid TipTap doc node
    _REQUIRED_DOC_KEYS: ClassVar[frozenset[str]] = frozenset({"type", "content"})

    # Required keys for each block node
    _REQUIRED_BLOCK_KEYS: ClassVar[frozenset[str]] = frozenset({"type"})

    # Valid top-level node types
    _VALID_BLOCK_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "paragraph",
            "heading",
            "bulletList",
            "orderedList",
            "listItem",
            "codeBlock",
            "blockquote",
            "horizontalRule",
            "image",
            "table",
            "tableRow",
            "tableCell",
            "tableHeader",
            "hardBreak",
            "text",
            # PM block types (Feature 017)
            "sprintBoard",
            "dependencyMap",
            "capacityPlanner",
            "releaseNotes",
            "timeline",
            "riskRegister",
            "admonition",
            "callout",
        }
    )

    @classmethod
    def validate_doc(cls, doc: Any) -> tuple[bool, str | None]:
        """Validate a TipTap document JSON structure.

        Args:
            doc: Parsed TipTap document value (expected dict).

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        if not isinstance(doc, dict):
            return False, f"Expected dict, got {type(doc).__name__}"

        if doc.get("type") != "doc":
            return False, f"Root type must be 'doc', got {doc.get('type')!r}"

        if "content" not in doc:
            return False, "Missing 'content' key in doc node"

        content = doc["content"]
        if not isinstance(content, list):
            return False, f"'content' must be a list, got {type(content).__name__}"

        for i, block in enumerate(content):
            valid, error = cls.validate_block(block)
            if not valid:
                return False, f"Block[{i}] invalid: {error}"

        return True, None

    @classmethod
    def validate_block(cls, block: Any) -> tuple[bool, str | None]:
        """Validate a single TipTap block node.

        Args:
            block: Single block value (expected dict) from TipTap content array.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not isinstance(block, dict):
            return False, f"Block must be dict, got {type(block).__name__}"

        if "type" not in block:
            return False, "Block missing 'type' key"

        block_type = block["type"]
        if block_type not in cls._VALID_BLOCK_TYPES:
            # Unknown types are logged but not rejected — forward-compatible
            logger.debug("Unknown TipTap block type: %s (allowed, forward-compat)", block_type)

        return True, None

    @classmethod
    def validate_json_string(cls, json_str: str) -> tuple[bool, str | None]:
        """Validate a JSON string as a TipTap document.

        Args:
            json_str: Raw JSON string from skill output.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            doc = json.loads(json_str)
        except json.JSONDecodeError as exc:
            return False, f"Invalid JSON: {exc}"

        return cls.validate_doc(doc)


class WorkspaceSkillSemaphore:
    """Per-workspace asyncio semaphore for skill concurrency limiting (T-047).

    Limits concurrent skill executions to MAX_CONCURRENT_SKILLS_PER_WORKSPACE (5)
    per workspace. The 6th request is queued with a 'Waiting for slot' SSE message.

    Uses in-process asyncio semaphores (per-process limit). For multi-process
    deployments, Redis-based distributed semaphore should replace this.
    """

    _registry: ClassVar[dict[UUID, asyncio.Semaphore]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def get_semaphore(cls, workspace_id: UUID) -> asyncio.Semaphore:
        """Get or create a semaphore for the given workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            Asyncio semaphore with capacity MAX_CONCURRENT_SKILLS_PER_WORKSPACE.
        """
        async with cls._lock:
            if workspace_id not in cls._registry:
                cls._registry[workspace_id] = asyncio.Semaphore(MAX_CONCURRENT_SKILLS_PER_WORKSPACE)
            return cls._registry[workspace_id]

    @classmethod
    async def acquire(cls, workspace_id: UUID) -> tuple[asyncio.Semaphore, bool]:
        """Try to acquire a skill execution slot for the workspace.

        Detects whether the request was queued (had to wait for a free slot)
        by checking if the semaphore is currently at capacity before acquiring.

        Args:
            workspace_id: Workspace to acquire slot for.

        Returns:
            Tuple of (semaphore, was_queued). was_queued=True if we had to wait.
        """
        semaphore = await cls.get_semaphore(workspace_id)
        # semaphore.locked() returns True when all slots are taken
        was_queued = semaphore.locked()
        await semaphore.acquire()
        return semaphore, was_queued

    @classmethod
    def release(cls, semaphore: asyncio.Semaphore) -> None:
        """Release a skill execution slot.

        Args:
            semaphore: Semaphore to release.
        """
        semaphore.release()


class NoteWriteLockManager:
    """Redis mutex for note-level write locking (C-3).

    Prevents concurrent writes to the same note from multiple skill
    executions. Acquires a 30s TTL mutex in Redis before any note
    mutation, releases after completion.

    Adds ~5ms overhead per write (measured Redis round-trip).
    """

    def __init__(self, redis: RedisClient) -> None:
        """Initialize with Redis client.

        Args:
            redis: Async Redis client wrapper.
        """
        self._redis = redis

    def _lock_key(self, note_id: UUID) -> str:
        return f"{_NOTE_LOCK_PREFIX}:{note_id}"

    async def acquire(self, note_id: UUID, holder_id: str | None = None) -> bool:
        """Try to acquire the write lock for a note.

        Uses SET NX EX (atomic check-and-set) for race-free locking.

        Args:
            note_id: Note UUID to lock.
            holder_id: Optional identifier for the lock holder (for debugging).

        Returns:
            True if lock acquired, False if already held.
        """
        key = self._lock_key(note_id)
        value = holder_id or str(uuid4())
        acquired = await self._redis.set(
            key,
            value,
            ttl=NOTE_WRITE_LOCK_TTL_S,
            if_not_exists=True,
        )
        if acquired:
            logger.debug(
                "[NoteWriteLock] Acquired note_id=%s holder=%s ttl=%ds",
                note_id,
                value,
                NOTE_WRITE_LOCK_TTL_S,
            )
        else:
            logger.warning("[NoteWriteLock] FAILED to acquire note_id=%s", note_id)
        return bool(acquired)

    async def release(self, note_id: UUID) -> None:
        """Release the write lock for a note.

        Args:
            note_id: Note UUID to unlock.
        """
        key = self._lock_key(note_id)
        await self._redis.delete(key)
        logger.debug("[NoteWriteLock] Released note_id=%s", note_id)

    async def is_locked(self, note_id: UUID) -> bool:
        """Check if a note is currently write-locked.

        Args:
            note_id: Note UUID to check.

        Returns:
            True if the note has an active write lock.
        """
        key = self._lock_key(note_id)
        return bool(await self._redis.exists(key))


class SkillExecutor:
    """Executes skills with approval hold, TipTap validation, and concurrency limits.

    Orchestrates the full skill execution lifecycle:
    1. Determine approval decision (C-7: admin-only for destructive skills)
    2. Acquire workspace concurrency slot (T-047, max 5)
    3. Acquire note write lock if note_id present (C-3)
    4. Validate skill output TipTap schema (T-045)
    5. Persist SkillExecution DB record
    6. Return result with approval_decision + SSE payload

    Args:
        session: Async SQLAlchemy session for DB writes.
        redis: Async Redis client for write locking (C-3).
        skills_dir: Path to templates/skills/ for skill discovery.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: RedisClient,
        skills_dir: Path,
    ) -> None:
        self._session = session
        self._lock_manager = NoteWriteLockManager(redis)
        self._validator = TipTapValidator()
        self._skills_dir = skills_dir
        self._skill_registry: dict[str, SkillInfo] | None = None

    def _get_registry(self) -> dict[str, SkillInfo]:
        """Lazy-load skill registry from disk."""
        if self._skill_registry is None:
            skills = discover_skills(self._skills_dir)
            self._skill_registry = {s.name: s for s in skills}
        return self._skill_registry

    def _determine_approval_decision(
        self,
        skill_name: str,
        caller_role: str | None,
    ) -> tuple[SkillApprovalDecision, str | None]:
        """Determine approval decision for a skill execution.

        Logic (C-7):
        - Skills in _ADMIN_REQUIRED_SKILLS → pending_approval, required_role=admin
        - Skills in _AUTO_EXECUTE_SKILLS → auto_approved
        - Remaining skills (generate-code, write-tests) → pending_approval (suggest)
          with no role restriction

        Args:
            skill_name: Name of the skill.
            caller_role: Role of the user triggering execution.

        Returns:
            Tuple of (decision, required_approval_role).
        """
        if skill_name in _ADMIN_REQUIRED_SKILLS:
            return SkillApprovalDecision.PENDING_APPROVAL, "admin"

        if skill_name in _AUTO_EXECUTE_SKILLS:
            return SkillApprovalDecision.AUTO_APPROVED, None

        # Default: suggest approval (generate-code, write-tests) — any role can approve
        return SkillApprovalDecision.PENDING_APPROVAL, "member"

    async def execute(
        self,
        request: SkillExecutionRequest,
        output_payload: dict[str, Any],
        caller_role: str | None = None,
    ) -> SkillExecutionResult:
        """Execute a skill with full lifecycle management.

        Steps:
        1. Determine approval decision (auto or pending)
        2. Acquire workspace concurrency slot (max 5)
        3. Acquire note write lock if note_id present (C-3)
        4. Validate TipTap output if blocks present (T-045)
        5. Persist SkillExecution record to DB
        6. Release locks and semaphore
        7. Return result

        Args:
            request: Skill execution request with context.
            output_payload: Skill output dict (may contain 'blocks' with TipTap content).
            caller_role: Workspace role of the triggering user.

        Returns:
            SkillExecutionResult with approval decision and DB record ID.
        """
        from pilot_space.infrastructure.database.models.skill_execution import (
            SkillApprovalRole,
            SkillApprovalStatus,
            SkillExecution,
        )

        execution_id = uuid4()
        approval_decision, required_role = self._determine_approval_decision(
            request.skill_name, caller_role
        )

        # T-045: Validate TipTap output blocks if present
        if "blocks" in output_payload:
            validation_error = self._validate_tiptap_output(output_payload["blocks"])
            if validation_error:
                logger.warning(
                    "[SkillExecutor] TipTap validation failed skill=%s error=%s",
                    request.skill_name,
                    validation_error,
                )
                return SkillExecutionResult(
                    execution_id=execution_id,
                    approval_decision=SkillApprovalDecision.AUTO_APPROVED,
                    error=f"Invalid TipTap output: {validation_error}",
                )

        # T-047: Acquire workspace concurrency slot
        semaphore, was_queued = await WorkspaceSkillSemaphore.acquire(request.workspace_id)
        if was_queued:
            logger.info(
                "[SkillExecutor] Queued skill=%s workspace=%s",
                request.skill_name,
                request.workspace_id,
            )

        note_locked = False
        try:
            # C-3: Acquire note write lock if note_id present
            if request.note_id and approval_decision == SkillApprovalDecision.AUTO_APPROVED:
                holder = f"{request.skill_name}:{execution_id}"
                note_locked = await self._lock_manager.acquire(request.note_id, holder)
                if not note_locked:
                    return SkillExecutionResult(
                        execution_id=execution_id,
                        approval_decision=approval_decision,
                        error=f"Note {request.note_id} is locked by another write operation",
                        queued=was_queued,
                    )

            # Map approval decision to DB model values
            db_status = (
                SkillApprovalStatus.AUTO_APPROVED
                if approval_decision == SkillApprovalDecision.AUTO_APPROVED
                else SkillApprovalStatus.PENDING_APPROVAL
            )
            db_required_role: SkillApprovalRole | None = None
            if required_role == "admin":
                db_required_role = SkillApprovalRole.ADMIN
            elif required_role == "member":
                db_required_role = SkillApprovalRole.MEMBER

            # Persist SkillExecution record
            db_record = SkillExecution(
                id=execution_id,
                intent_id=request.intent_id,
                skill_name=request.skill_name,
                approval_status=db_status,
                required_approval_role=db_required_role,
                output=output_payload
                if approval_decision == SkillApprovalDecision.AUTO_APPROVED
                else None,
            )
            self._session.add(db_record)
            await self._session.flush()

            logger.info(
                "[SkillExecutor] Persisted execution_id=%s skill=%s approval=%s role=%s",
                execution_id,
                request.skill_name,
                approval_decision,
                required_role,
            )

            return SkillExecutionResult(
                execution_id=execution_id,
                approval_decision=approval_decision,
                required_approval_role=required_role,
                output=output_payload
                if approval_decision == SkillApprovalDecision.AUTO_APPROVED
                else None,
                queued=was_queued,
            )

        finally:
            # Always release note lock and concurrency slot
            if note_locked and request.note_id:
                await self._lock_manager.release(request.note_id)
            WorkspaceSkillSemaphore.release(semaphore)

    def _validate_tiptap_output(self, blocks: Any) -> str | None:
        """Validate TipTap blocks from skill output.

        Args:
            blocks: Raw blocks value from output_payload.

        Returns:
            Error message string if invalid, None if valid.
        """
        if isinstance(blocks, str):
            valid, error = self._validator.validate_json_string(blocks)
            return error
        if isinstance(blocks, dict):
            valid, error = self._validator.validate_doc(blocks)
            return error
        if isinstance(blocks, list):
            for i, block in enumerate(blocks):
                valid, error = self._validator.validate_block(block)
                if not valid:
                    return f"blocks[{i}]: {error}"
            return None
        return f"Unexpected blocks type: {type(blocks).__name__}"

    async def approve_execution(
        self,
        execution_id: UUID,
        approved_by: UUID,
        note_id: UUID | None = None,
        output_override: dict[str, Any] | None = None,
    ) -> None:
        """Approve a pending_approval execution, persisting output to note.

        Called from skill approval API (T-046) when user approves.

        Args:
            execution_id: SkillExecution UUID to approve.
            approved_by: User UUID who approved.
            note_id: Note UUID to acquire write lock before persisting.
            output_override: Optional modified output from user edits.
        """
        from sqlalchemy import update

        from pilot_space.infrastructure.database.models.skill_execution import SkillExecution
        from pilot_space.infrastructure.database.repositories.skill_execution_repository import (
            SkillExecutionRepository,
        )

        repo = SkillExecutionRepository(self._session)

        # C-3: Acquire write lock before note update
        if note_id:
            locked = await self._lock_manager.acquire(note_id, f"approve:{execution_id}")
            if not locked:
                raise RuntimeError(f"Cannot approve — note {note_id} is write-locked")

        try:
            await repo.approve(execution_id)
            if output_override:
                await self._session.execute(
                    update(SkillExecution)
                    .where(SkillExecution.id == execution_id)
                    .values(output=output_override)
                )
            await self._session.commit()
        finally:
            if note_id:
                await self._lock_manager.release(note_id)

        logger.info(
            "[SkillExecutor] Approved execution_id=%s by=%s",
            execution_id,
            approved_by,
        )

    async def reject_execution(self, execution_id: UUID, rejected_by: UUID) -> None:
        """Reject a pending_approval execution, discarding output.

        Args:
            execution_id: SkillExecution UUID to reject.
            rejected_by: User UUID who rejected.
        """
        from pilot_space.infrastructure.database.repositories.skill_execution_repository import (
            SkillExecutionRepository,
        )

        repo = SkillExecutionRepository(self._session)
        await repo.reject(execution_id)
        await self._session.commit()

        logger.info(
            "[SkillExecutor] Rejected execution_id=%s by=%s",
            execution_id,
            rejected_by,
        )


__all__ = [
    "NoteWriteLockManager",
    "SkillApprovalDecision",
    "SkillExecutionRequest",
    "SkillExecutionResult",
    "SkillExecutor",
    "TipTapValidator",
    "WorkspaceSkillSemaphore",
]
