"""MemoryLifecycleService — pin, forget, decay sweep, GDPR forget.

Phase 69 Wave 2: manages the lifecycle of memory nodes living on
``graph_nodes``. All writes go through the SQLAlchemy session owned by the
caller — the service does NOT commit (workers / request handlers own the
transaction boundary).

Security notes
--------------
* ``pin`` / ``forget`` verify ``workspace_id`` on the target node and
  raise ``ForbiddenError`` on cross-workspace access.
* ``gdpr_forget_user`` is a privileged hard-delete and MUST only be
  invoked from service-role contexts (admin flows).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, delete, select, text, update

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.domain.memory.memory_type import MEMORY_TYPE_TO_NODE_TYPE
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PinPayload:
    workspace_id: UUID
    node_id: UUID
    actor_user_id: UUID


@dataclass(frozen=True, slots=True)
class ForgetPayload:
    workspace_id: UUID
    node_id: UUID
    actor_user_id: UUID


@dataclass(frozen=True, slots=True)
class GDPRForgetPayload:
    user_id: UUID
    workspace_id: UUID
    actor_user_id: UUID


class MemoryLifecycleService:
    """Pin / forget / decay-sweep / GDPR-forget for memory nodes.

    Operates directly on ``graph_nodes`` via SQLAlchemy — the
    knowledge graph repository does not yet expose mutation helpers
    for these flows, and we deliberately keep the service thin so the
    audit trail stays in one place.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Pin
    # ------------------------------------------------------------------

    async def pin(self, payload: PinPayload) -> None:
        """Set ``properties.pinned = true`` on the target node.

        Raises:
            NotFoundError: Node does not exist or was deleted concurrently.
            ForbiddenError: Node belongs to a different workspace.
        """
        node = await self._load_node(payload.node_id)
        self._assert_workspace(node, payload.workspace_id)

        props = dict(node.properties or {})
        props["pinned"] = True
        props["pinned_by"] = str(payload.actor_user_id)
        props["pinned_at"] = datetime.now(tz=UTC).isoformat()

        # C3: guard against a concurrent ``forget`` landing between _load_node
        # and this UPDATE — without ``is_deleted == False`` in the WHERE clause
        # the pin would silently resurrect a tombstoned node's ``properties``
        # while leaving ``is_deleted=true``, producing a contradictory row.
        result = await self._session.execute(
            update(GraphNodeModel)
            .where(
                GraphNodeModel.id == payload.node_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
            .values(properties=props, updated_at=datetime.now(tz=UTC))
        )
        if (getattr(result, "rowcount", 0) or 0) == 0:
            raise NotFoundError(
                f"memory node {payload.node_id} was deleted before pin could commit"
            )
        await self._write_audit(
            action="pin",
            workspace_id=payload.workspace_id,
            actor_user_id=payload.actor_user_id,
            node_id=payload.node_id,
        )
        logger.info(
            "memory_lifecycle: pinned node %s by %s",
            payload.node_id,
            payload.actor_user_id,
        )

    # ------------------------------------------------------------------
    # Forget (soft delete)
    # ------------------------------------------------------------------

    async def forget(self, payload: ForgetPayload) -> None:
        """Soft-delete the target node (``is_deleted = true``).

        Raises:
            NotFoundError: Node does not exist.
            ForbiddenError: Node belongs to a different workspace.
        """
        node = await self._load_node(payload.node_id)
        self._assert_workspace(node, payload.workspace_id)

        now = datetime.now(tz=UTC)
        await self._session.execute(
            update(GraphNodeModel)
            .where(GraphNodeModel.id == payload.node_id)
            .values(is_deleted=True, deleted_at=now, updated_at=now)
        )
        await self._write_audit(
            action="forget",
            workspace_id=payload.workspace_id,
            actor_user_id=payload.actor_user_id,
            node_id=payload.node_id,
        )
        logger.info(
            "memory_lifecycle: forgot node %s by %s",
            payload.node_id,
            payload.actor_user_id,
        )

    # ------------------------------------------------------------------
    # GDPR forget (privileged hard delete)
    # ------------------------------------------------------------------

    async def gdpr_forget_user(self, payload: GDPRForgetPayload) -> int:
        """Hard-delete memory nodes owned by ``user_id`` within a workspace.

        Scoped to (workspace_id, user_id) and restricted to Phase 69 memory
        node types — a workspace admin cannot purge another workspace's data,
        and non-memory nodes (issues, notes, etc.) are untouched. Returns the
        number of nodes deleted.
        """
        memory_node_types = {nt.value for nt in MEMORY_TYPE_TO_NODE_TYPE.values()}
        result = await self._session.execute(
            delete(GraphNodeModel).where(
                and_(
                    GraphNodeModel.user_id == payload.user_id,
                    GraphNodeModel.workspace_id == payload.workspace_id,
                    GraphNodeModel.node_type.in_(memory_node_types),
                )
            )
        )
        deleted = getattr(result, "rowcount", 0) or 0
        await self._write_audit(
            action="gdpr_forget",
            workspace_id=payload.workspace_id,
            actor_user_id=payload.actor_user_id,
            target_user_id=payload.user_id,
            deleted_count=deleted,
        )
        logger.info(
            "memory_lifecycle: gdpr_forget workspace=%s user=%s actor=%s deleted=%d",
            payload.workspace_id,
            payload.user_id,
            payload.actor_user_id,
            deleted,
        )
        return deleted

    # ------------------------------------------------------------------
    # Decay sweep
    # ------------------------------------------------------------------

    async def decay_sweep(self, workspace_id: UUID) -> int:
        """Soft-delete nodes whose ``properties.expires_at`` is in the past.

        Returns the number of nodes soft-deleted.
        """
        now = datetime.now(tz=UTC)
        now_iso = now.isoformat()

        # Fetch candidates: we cannot express `properties->>expires_at < now`
        # portably because SQLite test DB lacks JSONB operators, so fall back
        # to a Python-side filter over active nodes with an expires_at key.
        stmt = select(GraphNodeModel).where(
            and_(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        rows = (await self._session.execute(stmt)).scalars().all()

        expired_ids: list[UUID] = []
        for row in rows:
            props = row.properties or {}
            expires_at = props.get("expires_at")
            if isinstance(expires_at, str) and expires_at < now_iso:
                expired_ids.append(row.id)

        if not expired_ids:
            return 0

        await self._session.execute(
            update(GraphNodeModel)
            .where(GraphNodeModel.id.in_(expired_ids))
            .values(is_deleted=True, deleted_at=now, updated_at=now)
        )
        logger.info(
            "memory_lifecycle: decay_sweep workspace=%s expired=%d",
            workspace_id,
            len(expired_ids),
        )
        return len(expired_ids)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_node(self, node_id: UUID) -> GraphNodeModel:
        stmt = select(GraphNodeModel).where(
            GraphNodeModel.id == node_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        node = (await self._session.execute(stmt)).scalar_one_or_none()
        if node is None:
            raise NotFoundError(f"memory node {node_id} not found")
        return node

    @staticmethod
    def _assert_workspace(node: GraphNodeModel, workspace_id: UUID) -> None:
        if node.workspace_id != workspace_id:
            raise ForbiddenError(
                f"memory node {node.id} does not belong to workspace {workspace_id}"
            )

    async def _write_audit(
        self,
        *,
        action: str,
        workspace_id: UUID,
        actor_user_id: UUID,
        node_id: UUID | None = None,
        target_user_id: UUID | None = None,
        deleted_count: int | None = None,
    ) -> None:
        """Insert a durable audit row for pin / forget / gdpr_forget.

        Writes to ``memory_lifecycle_audit`` (migration 107) via raw SQL so
        the service does not take a dependency on an ORM model that exists
        only for this one write path. Best-effort: logs and continues on
        failure so audit writes cannot mask the primary mutation's success.
        """
        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO memory_lifecycle_audit
                        (workspace_id, actor_user_id, action,
                         node_id, target_user_id, deleted_count)
                    VALUES
                        (:workspace_id, :actor_user_id, :action,
                         :node_id, :target_user_id, :deleted_count)
                    """
                ),
                {
                    "workspace_id": str(workspace_id),
                    "actor_user_id": str(actor_user_id),
                    "action": action,
                    "node_id": str(node_id) if node_id else None,
                    "target_user_id": str(target_user_id) if target_user_id else None,
                    "deleted_count": deleted_count,
                },
            )
        except Exception:
            logger.warning(
                "memory_lifecycle: audit write failed action=%s workspace=%s",
                action,
                workspace_id,
                exc_info=True,
            )


__all__ = [
    "ForgetPayload",
    "GDPRForgetPayload",
    "MemoryLifecycleService",
    "PinPayload",
]
