"""Phase 70-06 — workspace memory producer opt-out toggles.

Thin helper module that stores the four Phase 70 memory producer flags
inside ``workspaces.settings["memory_producers"]`` (JSONB). This side-
steps the broken Wave 0 migration 107 which tried to add columns to a
non-existent ``workspace_ai_settings`` table. The existing
``WorkspaceAISettingsService`` already uses ``workspaces.settings`` for
every other AI feature toggle, so this is consistent with the codebase
pattern.

Flags
-----

``agent_turn``             — default ``True``  (opt-out)
``user_correction``        — default ``True``  (opt-out)
``pr_review_finding``      — default ``True``  (opt-out)
``summarizer``             — default ``False`` (opt-in)

Producer hook sites read these via ``get_producer_toggles(session,
workspace_id)`` on every call — cheap (single SELECT on the workspaces
row which is already hot in the session cache). No per-request caching
is layered on top; if this ever becomes a hot path we can add an LRU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.domain.exceptions import ValidationError
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_SETTINGS_KEY = "memory_producers"

ProducerName = Literal[
    "agent_turn",
    "user_correction",
    "pr_review_finding",
    "summarizer",
]

_VALID_PRODUCERS: frozenset[str] = frozenset(
    {"agent_turn", "user_correction", "pr_review_finding", "summarizer"}
)


@dataclass(frozen=True, slots=True)
class ProducerToggles:
    """Opt-in / opt-out state of the four Phase 70 memory producers."""

    agent_turn: bool = True
    user_correction: bool = True
    pr_review_finding: bool = True
    summarizer: bool = False  # opt-in by default

    @classmethod
    def defaults(cls) -> ProducerToggles:
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProducerToggles:
        if not data:
            return cls.defaults()
        return cls(
            agent_turn=bool(data.get("agent_turn", True)),
            user_correction=bool(data.get("user_correction", True)),
            pr_review_finding=bool(data.get("pr_review_finding", True)),
            summarizer=bool(data.get("summarizer", False)),
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "agent_turn": self.agent_turn,
            "user_correction": self.user_correction,
            "pr_review_finding": self.pr_review_finding,
            "summarizer": self.summarizer,
        }


async def get_producer_toggles(
    session: AsyncSession,
    workspace_id: UUID,
) -> ProducerToggles:
    """Read the producer toggles for a workspace.

    Returns defaults (3x True, summarizer False) for any workspace that
    has never been explicitly configured. Swallows read failures — the
    producer hooks MUST never fail on a settings read, they default
    safely (agent_turn/user_correction/pr_review_finding ON, summarizer
    OFF).
    """
    try:
        stmt = select(Workspace.settings).where(Workspace.id == workspace_id)
        row = (await session.execute(stmt)).scalar_one_or_none()
    except Exception:
        logger.exception(
            "workspace_ai_settings_toggles: read failed (workspace=%s) — returning defaults",
            workspace_id,
        )
        return ProducerToggles.defaults()

    if not row:
        return ProducerToggles.defaults()
    if not row or not hasattr(row, "get"):
        return ProducerToggles.defaults()
    return ProducerToggles.from_dict(row.get(_SETTINGS_KEY))  # type: ignore[union-attr]


async def set_producer_toggle(
    session: AsyncSession,
    workspace_id: UUID,
    producer: str,
    enabled: bool,
) -> ProducerToggles:
    """Persist a single producer toggle and return the resulting state.

    Raises ``ValidationError`` if ``producer`` is not one of the four
    known flag names. The write is committed by the caller — this
    helper only flushes so the next read in the same session sees the
    new value.
    """
    if producer not in _VALID_PRODUCERS:
        raise ValidationError(
            f"unknown memory producer: {producer!r}; "
            f"expected one of {sorted(_VALID_PRODUCERS)}"
        )

    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise ValidationError(f"workspace {workspace_id} not found")

    current = dict(workspace.settings or {})
    producers = dict(current.get(_SETTINGS_KEY) or {})
    producers[producer] = bool(enabled)
    current[_SETTINGS_KEY] = producers
    workspace.settings = current
    flag_modified(workspace, "settings")
    await session.flush()

    return ProducerToggles.from_dict(producers)


__all__ = [
    "ProducerName",
    "ProducerToggles",
    "get_producer_toggles",
    "set_producer_toggle",
]
