"""ConstitutionIngestService + ConstitutionVersionGate.

T-033: Ingest RFC 2119 rules → version bump → keyword index (sync) → enqueue vector indexing.
T-034: Version gate — block skill execution until indexed (max 60s).

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.constitution_rule import ConstitutionRule, RuleSeverity
from pilot_space.infrastructure.database.models.memory_entry import (
    ConstitutionRule as ConstitutionRuleModel,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.constitution_repository import (
        ConstitutionRuleRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

_CONSTITUTION_INDEXING_TASK_TYPE = "memory_embedding"
_CONSTITUTION_TABLE = "constitution_rules"

# Version gate constants (T-034)
_VERSION_GATE_POLL_INTERVAL_S = 2.0
_VERSION_GATE_MAX_WAIT_S = 60.0


@dataclass(frozen=True, slots=True)
class ConstitutionRuleInput:
    """A single rule to ingest.

    Attributes:
        content: Rule text (RFC 2119 severity auto-detected).
        severity: Override severity (None = auto-detect from content).
        source_block_id: Optional TipTap block UUID.
    """

    content: str
    severity: RuleSeverity | None = None
    source_block_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ConstitutionIngestPayload:
    """Payload for constitution rule ingestion.

    Attributes:
        workspace_id: Owning workspace.
        rules: List of rules to ingest as new version.
    """

    workspace_id: UUID
    rules: list[ConstitutionRuleInput] = field(default_factory=list)


@dataclass
class ConstitutionIngestResult:
    """Result of rule ingestion.

    Attributes:
        version: New version number created.
        rule_count: Number of rules ingested.
        indexing_enqueued: Whether async vector indexing was enqueued.
    """

    version: int
    rule_count: int
    indexing_enqueued: bool


class ConstitutionIngestService:
    """Service to ingest workspace AI behavior rules.

    Parses RFC 2119 severity, assigns next version number, persists
    synchronously (keyword search works immediately), and enqueues
    async vector indexing.

    Example:
        service = ConstitutionIngestService(constitution_repository, queue_client, session)
        result = await service.execute(ConstitutionIngestPayload(
            workspace_id=workspace_id,
            rules=[ConstitutionRuleInput(content="You must not expose API keys")],
        ))
        # result.version == 2 (next version after current)
    """

    def __init__(
        self,
        constitution_repository: ConstitutionRuleRepository,
        queue: SupabaseQueueClient,
        session: AsyncSession,
    ) -> None:
        """Initialize service.

        Args:
            constitution_repository: Repository for ConstitutionRule access.
            queue: Queue client for async indexing jobs.
            session: Async DB session.
        """
        self._const_repo = constitution_repository
        self._queue = queue
        self._session = session

    async def execute(self, payload: ConstitutionIngestPayload) -> ConstitutionIngestResult:
        """Ingest rules as a new version.

        Args:
            payload: Rules and workspace context.

        Returns:
            ConstitutionIngestResult with new version number.
        """
        if not payload.rules:
            current_version = await self._const_repo.get_latest_version(payload.workspace_id)
            return ConstitutionIngestResult(
                version=current_version,
                rule_count=0,
                indexing_enqueued=False,
            )

        # Compute next version
        current_version = await self._const_repo.get_latest_version(payload.workspace_id)
        new_version = current_version + 1

        # Deactivate all existing rules for this workspace
        existing = await self._const_repo.get_active_rules(payload.workspace_id)
        for rule_model in existing:
            rule_model.active = False  # type: ignore[attr-defined]
            await self._const_repo.update(rule_model)

        # Persist new rules synchronously
        created_ids: list[UUID] = []
        for rule_input in payload.rules:
            severity = rule_input.severity or ConstitutionRule.detect_severity(rule_input.content)
            rule_model = ConstitutionRuleModel(
                id=uuid.uuid4(),
                workspace_id=payload.workspace_id,
                content=rule_input.content,
                severity=severity,
                version=new_version,
                source_block_id=rule_input.source_block_id,
                active=True,
            )
            created = await self._const_repo.create(rule_model)
            created_ids.append(created.id)  # type: ignore[arg-type]

        await self._session.commit()

        # Enqueue async vector indexing for each rule (J-4)
        enqueued = await self._enqueue_indexing(
            rule_ids=created_ids,
            workspace_id=payload.workspace_id,
            version=new_version,
        )

        logger.info(
            "ConstitutionIngestService: ingested %d rules as version %d for workspace %s",
            len(payload.rules),
            new_version,
            payload.workspace_id,
        )

        return ConstitutionIngestResult(
            version=new_version,
            rule_count=len(payload.rules),
            indexing_enqueued=enqueued,
        )

    async def _enqueue_indexing(
        self,
        rule_ids: list[UUID],
        workspace_id: UUID,
        version: int,
    ) -> bool:
        """Enqueue vector indexing jobs for constitution rules (J-4).

        Args:
            rule_ids: List of ConstitutionRule UUIDs to index.
            workspace_id: Workspace context.
            version: New version being indexed.

        Returns:
            True if all jobs enqueued successfully.
        """
        try:
            for rule_id in rule_ids:
                job_payload: dict[str, Any] = {
                    "task_type": _CONSTITUTION_INDEXING_TASK_TYPE,
                    "entry_id": str(rule_id),
                    "workspace_id": str(workspace_id),
                    "table": _CONSTITUTION_TABLE,
                    "indexed_version": version,
                    "enqueued_at": datetime.now(tz=UTC).isoformat(),
                }
                await self._queue.enqueue(QueueName.AI_NORMAL, job_payload)
            return True
        except Exception:
            logger.error(
                "Failed to enqueue constitution indexing for version %d workspace %s",
                version,
                workspace_id,
                exc_info=True,
            )
            return False


class ConstitutionVersionGate:
    """Blocks skill execution until constitution vector index is ready.

    T-034: If current_version > last_indexed_version, polls every 2s.
    After 60s timeout, proceeds with keyword-only search.

    Example:
        gate = ConstitutionVersionGate(constitution_repository)
        await gate.wait_for_version(workspace_id, required_version=3)
    """

    def __init__(
        self,
        constitution_repository: ConstitutionRuleRepository,
    ) -> None:
        """Initialize gate.

        Args:
            constitution_repository: Repository for version checks.
        """
        self._const_repo = constitution_repository

    async def wait_for_version(
        self,
        workspace_id: UUID,
        required_version: int,
    ) -> bool:
        """Wait until the required constitution version is indexed.

        Polls every 2s, times out after 60s. On timeout, returns False
        (caller should proceed with keyword-only behavior).

        Args:
            workspace_id: Workspace to check.
            required_version: Minimum version that must be indexed.

        Returns:
            True if version is indexed within timeout, False if timed out.
        """
        elapsed = 0.0
        while elapsed < _VERSION_GATE_MAX_WAIT_S:
            indexed = await self._get_indexed_version(workspace_id)
            if indexed >= required_version:
                logger.debug(
                    "ConstitutionVersionGate: version %d ready for workspace %s",
                    required_version,
                    workspace_id,
                )
                return True
            await asyncio.sleep(_VERSION_GATE_POLL_INTERVAL_S)
            elapsed += _VERSION_GATE_POLL_INTERVAL_S

        logger.warning(
            "ConstitutionVersionGate: timed out waiting for version %d workspace %s — "
            "proceeding with keyword-only",
            required_version,
            workspace_id,
        )
        return False

    async def _get_indexed_version(self, workspace_id: UUID) -> int:
        """Get the latest indexed (active) version for the workspace.

        Rules are considered indexed when they are active (active=True).
        The indexing worker sets active=True after embedding completes.

        Args:
            workspace_id: Workspace to check.

        Returns:
            Latest version with at least one active rule, or 0.
        """
        active_rules = await self._const_repo.get_active_rules(workspace_id)
        if not active_rules:
            return 0
        return max(getattr(r, "version", 0) for r in active_rules)
