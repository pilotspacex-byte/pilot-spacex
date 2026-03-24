"""SkillExecutionService: orchestrates skill execution with approval lifecycle.

T-044: Execute a skill for a confirmed WorkIntent.
T-045: Validate skill output against TipTap block schema.

Approval modes (DD-003):
  auto    — output persists immediately (no user gate).
  suggest — output stored for preview; user must accept.
  require — output stored; MUST NOT auto-persist (destructive guard, C-7).

Concurrency: SkillConcurrencyManager (T-047) limits to MAX_CONCURRENT=5 per workspace.
Role gate (C-7): required_approval_role enforced at approval time.

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.application.services.skill.concurrency_manager import (
    SkillConcurrencyManager,
)
from pilot_space.application.services.skill.skill_definition import (
    ApprovalMode,
    SkillDefinition,
    SkillDefinitionParser,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.skill_execution import (
    SkillApprovalRole,
    SkillApprovalStatus,
    SkillExecution,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.domain.work_intent import WorkIntent
    from pilot_space.infrastructure.database.repositories.intent_repository import (
        WorkIntentRepository,
    )
    from pilot_space.infrastructure.database.repositories.skill_execution_repository import (
        SkillExecutionRepository,
    )

logger = get_logger(__name__)

# TipTap block types that require a `content` array
_BLOCK_TYPES_REQUIRING_CONTENT = frozenset(
    {
        "doc",
        "paragraph",
        "heading",
        "blockquote",
        "bulletList",
        "orderedList",
        "listItem",
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
        "codeBlock",
        "taskList",
        "taskItem",
    }
)

# Leaf node types (do NOT require content array)
_LEAF_BLOCK_TYPES = frozenset({"text", "image", "horizontalRule", "hardBreak"})


class SkillOutputValidationError(ValueError):
    """Raised when skill output fails TipTap schema validation (T-045)."""


@dataclass(frozen=True, slots=True)
class ExecuteSkillPayload:
    """Input payload for SkillExecutionService.

    Attributes:
        intent: Confirmed WorkIntent driving the skill.
        skill_name: Name matching a SKILL.md directory (e.g. 'generate-code').
        output: TipTap JSON output produced by the skill.
        workspace_id: Workspace context for RLS + concurrency.
        user_id: Requesting user for audit.
    """

    intent: WorkIntent
    skill_name: str
    output: Any  # Must be a dict; validated by SkillExecutionService._validate_tiptap_output
    workspace_id: UUID
    user_id: UUID


class SkillExecutionService:
    """Orchestrates a single skill execution lifecycle.

    Steps:
      1. Load SkillDefinition from SKILL.md (parse YAML frontmatter).
      2. Validate output against TipTap block schema (T-045).
      3. Acquire concurrency slot (Redis semaphore, max 5 per workspace).
      4. Persist SkillExecution with approval_status derived from approval mode:
         - auto    → AUTO_APPROVED
         - suggest → PENDING_APPROVAL
         - require → PENDING_APPROVAL
      5. Release concurrency slot.
      6. Return SkillExecution ORM model.

    Args:
        session: SQLAlchemy async session.
        skill_exec_repo: Repository for SkillExecution records.
        intent_repo: Repository for WorkIntent records (workspace validation).
        concurrency_manager: Redis-backed slot limiter.
        definition_parser: SKILL.md parser (injectable for testing).
    """

    def __init__(
        self,
        session: AsyncSession,
        skill_exec_repo: SkillExecutionRepository,
        intent_repo: WorkIntentRepository,
        concurrency_manager: SkillConcurrencyManager,
        definition_parser: SkillDefinitionParser | None = None,
    ) -> None:
        self._session = session
        self._exec_repo = skill_exec_repo
        self._intent_repo = intent_repo
        self._concurrency = concurrency_manager
        self._parser = definition_parser or SkillDefinitionParser()

    async def execute(self, payload: ExecuteSkillPayload) -> SkillExecution:
        """Execute a skill and persist the result with appropriate approval status.

        Args:
            payload: Validated execution input.

        Returns:
            Persisted SkillExecution ORM record.

        Raises:
            ValueError: If intent not found or workspace mismatch.
            SkillDefinitionError: If SKILL.md is missing or malformed.
            SkillOutputValidationError: If output fails TipTap schema check.
            RuntimeError: If concurrency slot cannot be acquired.
        """
        # 1. Validate intent ownership
        intent = await self._intent_repo.get_by_id(payload.intent.id)  # type: ignore[arg-type]
        if intent is None:
            msg = f"WorkIntent {payload.intent.id} not found"
            raise NotFoundError(msg)
        if intent.workspace_id != payload.workspace_id:
            msg = "Intent does not belong to workspace"
            raise ForbiddenError(msg)

        # 2. Load skill definition
        skill_def = await self._load_skill_definition(payload.skill_name)

        # 3. Validate TipTap output
        self._validate_tiptap_output(payload.output, payload.skill_name)

        # 4. Acquire concurrency slot
        acquired = await self._concurrency.acquire_slot(payload.workspace_id)
        if not acquired:
            msg = (
                f"Workspace {payload.workspace_id} has reached the maximum "
                "concurrent skill execution limit"
            )
            raise RuntimeError(msg)

        try:
            execution = await self._persist_execution(
                intent_id=payload.intent.id,  # type: ignore[arg-type]
                skill_def=skill_def,
                output=payload.output,
            )
        finally:
            await self._concurrency.release_slot(payload.workspace_id)

        logger.info(
            "SkillExecution created",
            extra={
                "skill": payload.skill_name,
                "execution_id": str(execution.id),
                "approval_status": execution.approval_status.value,
                "workspace_id": str(payload.workspace_id),
            },
        )
        return execution

    async def _persist_execution(
        self,
        intent_id: UUID,
        skill_def: SkillDefinition,
        output: Any,
    ) -> SkillExecution:
        """Create and persist a SkillExecution record.

        Args:
            intent_id: Parent intent UUID.
            skill_def: Parsed skill definition.
            output: Validated TipTap output.

        Returns:
            Persisted SkillExecution model.
        """
        approval_status = (
            SkillApprovalStatus.AUTO_APPROVED
            if skill_def.approval == ApprovalMode.AUTO
            else SkillApprovalStatus.PENDING_APPROVAL
        )

        required_role: SkillApprovalRole | None = None
        if skill_def.required_approval_role is not None:
            required_role = SkillApprovalRole(skill_def.required_approval_role.value)

        execution = SkillExecution(
            intent_id=intent_id,
            skill_name=skill_def.name,
            approval_status=approval_status,
            required_approval_role=required_role,
            output=output,
        )
        created = await self._exec_repo.create(execution)
        await self._session.flush()
        return created

    async def _load_skill_definition(self, skill_name: str) -> SkillDefinition:
        """Load and parse the SkillDefinition from the SKILL.md file.

        Args:
            skill_name: Skill directory name.

        Returns:
            Parsed SkillDefinition.

        Raises:
            SkillDefinitionError: If file is missing or frontmatter is invalid.
        """
        return await self._parser.parse(skill_name)

    def _validate_tiptap_output(self, output: Any, skill_name: str) -> None:
        """Validate that output is a well-formed TipTap block structure (T-045).

        Rules:
          - Output must be a dict with a 'type' key.
          - For block types in _BLOCK_TYPES_REQUIRING_CONTENT, 'content' must be a list.
          - 'content' items are recursively validated.

        Args:
            output: Output JSON to validate.
            skill_name: For error context.

        Raises:
            SkillOutputValidationError: If validation fails.
        """
        if not isinstance(output, dict):  # type: ignore[arg-type]
            msg = f"Skill {skill_name!r}: output must be a JSON object, got {type(output).__name__}"
            raise SkillOutputValidationError(msg)
        if "type" not in output:
            msg = f"Skill {skill_name!r}: output must have a 'type' field"
            raise SkillOutputValidationError(msg)

        self._validate_tiptap_node(output, skill_name, path="root")

    def _validate_tiptap_node(
        self,
        node: dict[str, Any],
        skill_name: str,
        path: str,
    ) -> None:
        """Recursively validate a single TipTap node.

        Args:
            node: Node dict to validate.
            skill_name: Skill name for error context.
            path: JSON path for error messages.

        Raises:
            SkillOutputValidationError: If node is invalid.
        """
        node_type = node.get("type")
        if not isinstance(node_type, str) or not node_type:
            msg = f"Skill {skill_name!r}: node at {path!r} has missing/invalid 'type'"
            raise SkillOutputValidationError(msg)

        # Block types that MUST have a content array
        if node_type in _BLOCK_TYPES_REQUIRING_CONTENT:
            content = node.get("content")
            if content is not None and not isinstance(content, list):
                msg = (
                    f"Skill {skill_name!r}: node at {path!r} (type={node_type!r}) "
                    "has invalid 'content' — expected list"
                )
                raise SkillOutputValidationError(msg)
            # Recurse into children
            for idx, child in enumerate(content or []):
                if not isinstance(child, dict):
                    msg = f"Skill {skill_name!r}: content[{idx}] at {path!r} must be a JSON object"
                    raise SkillOutputValidationError(msg)
                self._validate_tiptap_node(child, skill_name, path=f"{path}.content[{idx}]")


__all__ = [
    "ExecuteSkillPayload",
    "SkillExecutionService",
    "SkillOutputValidationError",
]
