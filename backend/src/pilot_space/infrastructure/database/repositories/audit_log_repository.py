"""AuditLogRepository — write and query audit_log entries.

Provides:
- create(): inserts an immutable AuditLog row
- list_filtered(): cursor-based pagination with optional filters
- compute_diff(): module-level helper for before/after payload generation

Requirements: AUDIT-01, AUDIT-06
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, delete, or_, select

from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compute a before/after diff containing only changed fields.

    Args:
        before: State of the entity before the mutation.
        after: State of the entity after the mutation.

    Returns:
        Dict with "before" and "after" keys, each containing only the
        fields whose values changed. Keys present in `after` but not in
        `before` are treated as None in the before snapshot.
    """
    changed_fields = {k for k in after if after[k] != before.get(k)}
    return {
        "before": {k: before.get(k) for k in changed_fields},
        "after": {k: after[k] for k in changed_fields},
    }


def _encode_cursor(ts: datetime, row_id: uuid.UUID) -> str:
    """Encode a pagination cursor as base64(JSON).

    Args:
        ts: created_at timestamp of the last row on the current page.
        row_id: UUID of the last row on the current page.

    Returns:
        Base64-encoded JSON string with "ts" and "id" keys.
    """
    payload = json.dumps({"ts": ts.isoformat(), "id": str(row_id)})
    return base64.b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    """Decode a pagination cursor from base64(JSON).

    Args:
        cursor: Base64-encoded cursor string.

    Returns:
        Tuple of (datetime, UUID) or None if decoding fails.
    """
    try:
        payload = json.loads(base64.b64decode(cursor).decode())
        ts = datetime.fromisoformat(payload["ts"])
        row_id = uuid.UUID(payload["id"])
        return ts, row_id
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pagination result
# ---------------------------------------------------------------------------


@dataclass
class AuditLogPage:
    """Cursor-based pagination result for audit log queries.

    Attributes:
        items: AuditLog rows for the current page.
        has_next: Whether additional rows exist after this page.
        next_cursor: Opaque cursor for the next page, None if no more pages.
    """

    items: list[AuditLog]
    has_next: bool = False
    next_cursor: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class AuditLogRepository:
    """Repository for AuditLog inserts and filtered reads.

    Deliberately standalone (not extending BaseRepository) to avoid:
    - Inheriting soft-delete methods inappropriate for immutable records
    - BaseRepository.get_by_id signature conflicts

    Attributes:
        session: Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        actor_type: ActorType,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
        ai_input: dict[str, Any] | None = None,
        ai_output: dict[str, Any] | None = None,
        ai_model: str | None = None,
        ai_token_cost: int | None = None,
        ai_rationale: str | None = None,
    ) -> AuditLog:
        """Insert a new AuditLog row and return it.

        All keyword arguments are required except those with defaults.

        Args:
            workspace_id: Owning workspace UUID.
            actor_id: UUID of the acting user/system, or None for system actions.
            actor_type: ActorType enum value (USER, SYSTEM, or AI).
            action: Dot-notation action string e.g. "issue.create".
            resource_type: Resource category e.g. "issue", "note".
            resource_id: UUID of the affected resource, or None for workspace-level.
            payload: JSONB diff {"before": {...}, "after": {...}} of changed fields.
            ip_address: Client IP address from request context.
            ai_input: Raw AI input (only for AI actor entries).
            ai_output: Raw AI output (only for AI actor entries).
            ai_model: Model identifier e.g. "claude-sonnet-4-20250514".
            ai_token_cost: Token count consumed.
            ai_rationale: AI's stated rationale for the action.

        Returns:
            The created AuditLog instance with id and created_at populated.
        """
        row = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            ip_address=ip_address,
            ai_input=ai_input,
            ai_output=ai_output,
            ai_model=ai_model,
            ai_token_cost=ai_token_cost,
            ai_rationale=ai_rationale,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id(self, entry_id: uuid.UUID) -> AuditLog | None:
        """Fetch a single AuditLog row by primary key.

        Args:
            entry_id: UUID primary key of the audit log entry.

        Returns:
            AuditLog instance or None if not found.
        """
        result = await self.session.execute(select(AuditLog).where(AuditLog.id == entry_id))
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        actor_type: ActorType | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> AuditLogPage:
        """Return a cursor-paginated list of AuditLog rows for a workspace.

        Ordering: created_at DESC, id DESC (stable sort for ties).
        Cursor encodes the last seen (created_at, id) to enable keyset pagination.

        Args:
            workspace_id: Workspace to query (required — tenant isolation).
            actor_id: Optional filter by actor UUID.
            actor_type: Optional filter by actor type (USER, AI, or SYSTEM).
            action: Optional filter by exact action string e.g. "issue.create".
            resource_type: Optional filter by resource category.
            start_date: Optional inclusive lower bound for created_at.
            end_date: Optional inclusive upper bound for created_at.
            cursor: Opaque cursor from a previous page response.
            page_size: Number of items per page (capped at 500).

        Returns:
            AuditLogPage with items, has_next flag, and next_cursor.
        """
        page_size = min(page_size, 500)

        stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)

        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if actor_type is not None:
            # Use .value to compare the string value directly against the String(10) column,
            # avoiding SQLAlchemy serializing ActorType enum as "ActorType.AI" instead of "AI".
            stmt = stmt.where(AuditLog.actor_type == actor_type.value)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        # Keyset cursor: rows where (created_at, id) comes before the cursor position
        if cursor is not None:
            decoded = _decode_cursor(cursor)
            if decoded is not None:
                cur_ts, cur_id = decoded
                stmt = stmt.where(
                    or_(
                        AuditLog.created_at < cur_ts,
                        and_(
                            AuditLog.created_at == cur_ts,
                            AuditLog.id < cur_id,
                        ),
                    )
                )

        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(page_size + 1)

        result = await self.session.execute(stmt)
        rows: list[AuditLog] = list(result.scalars().all())

        has_next = len(rows) > page_size
        if has_next:
            rows = rows[:page_size]

        next_cursor: str | None = None
        if has_next and rows:
            last = rows[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return AuditLogPage(
            items=rows,
            has_next=has_next,
            next_cursor=next_cursor,
        )

    async def list_for_export(
        self,
        *,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        actor_type: ActorType | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditLog]:
        """Return all AuditLog rows for export, respecting filters.

        Loads rows in batches of 100 via yield_per to avoid OOM on large exports.
        No pagination cursor — returns full result set matching filters.

        Args:
            workspace_id: Workspace to query (required — tenant isolation).
            actor_id: Optional filter by actor UUID.
            actor_type: Optional filter by actor type (USER, AI, or SYSTEM).
            action: Optional filter by exact action string.
            resource_type: Optional filter by resource category.
            start_date: Optional inclusive lower bound for created_at.
            end_date: Optional inclusive upper bound for created_at.

        Returns:
            List of AuditLog rows matching the filters, ordered by created_at DESC.
        """
        stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)

        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if actor_type is not None:
            stmt = stmt.where(AuditLog.actor_type == actor_type.value)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

        result = await self.session.stream_scalars(stmt)
        return [row async for row in result]

    async def purge_expired(
        self,
        *,
        workspace_id: uuid.UUID,
        retention_days: int | None,
        now: datetime | None = None,
    ) -> int:
        """Delete audit log rows older than retention_days for a workspace.

        Used by the pg_cron retention job (or test harness). The SQL trigger
        bypass (app.audit_purge session variable) must be set by the caller
        when running against PostgreSQL.

        Args:
            workspace_id: Workspace whose rows to purge.
            retention_days: Number of days to retain. Defaults to 90 if None.
            now: Reference timestamp (defaults to UTC now). Useful for tests.

        Returns:
            Number of rows deleted.
        """
        from datetime import UTC, timedelta

        effective_days = retention_days if retention_days is not None else 90
        reference_time = now or datetime.now(UTC)
        cutoff = reference_time - timedelta(days=effective_days)

        stmt = delete(AuditLog).where(
            AuditLog.workspace_id == workspace_id,
            AuditLog.created_at < cutoff,
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]


async def write_audit_nonfatal(
    audit_repo: AuditLogRepository | None,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an audit log entry non-fatally (swallows all exceptions).

    Convenience wrapper for service-layer audit writes where the primary
    write path must not be interrupted by audit failures.

    Args:
        audit_repo: AuditLogRepository instance, or None to skip.
        workspace_id: Owning workspace UUID.
        actor_id: Actor UUID (or None for system actions).
        action: Dot-notation action string e.g. "issue.create".
        resource_type: Resource category string.
        resource_id: Affected resource UUID or None.
        payload: JSONB diff payload.
        ip_address: Client IP or None.
    """
    if audit_repo is None:
        return
    try:
        await audit_repo.create(
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=ActorType.USER,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            ip_address=ip_address,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).warning("write_audit_nonfatal: failed to write %s", action)


__all__ = [
    "AuditLogPage",
    "AuditLogRepository",
    "_decode_cursor",
    "_encode_cursor",
    "compute_diff",
    "write_audit_nonfatal",
]
