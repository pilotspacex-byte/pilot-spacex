"""Intent registry + dispatcher for the Edit Proposal pipeline (Phase 89 Plan 03).

Rewire matrix — single source of truth for which tool names map to which
handler module:

    Tool name                | Handler module         | Artifact type | Diff kind
    -------------------------+------------------------+---------------+----------
    create_issue             | intent_handlers.issue  | ISSUE         | fields
    update_issue             | intent_handlers.issue  | ISSUE         | fields
    create_note              | intent_handlers.note   | NOTE          | fields
    create_note_annotation   | intent_handlers.note   | NOTE          | fields

Tools NOT registered here are either:
* Read-only (don't create proposals).
* Internal bookkeeping that sits in the allow-listed
  ``pilot_space.ai.proposals.intent_handlers/`` path if it needs to mutate
  at all (e.g. ownership_server.set_block_owner — allow-listed per
  REV-89-03-C, documented in 89-03-SUMMARY).

The 9-item audit-gate violation inventory from 89-02-SUMMARY is covered by
rewires of the 4 call-site tool functions above (update_issue alone
accounts for 5 violation lines).

## Session threading

``IntentExecutorProtocol.execute`` in ``proposal_bus.py`` does NOT take a
``session`` kwarg — handlers pull the request-scoped session from
``get_current_session()`` (ContextVar populated by SessionDep). This keeps
the Plan 01 protocol contract unchanged.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pilot_space.application.services.proposal_bus import IntentExecutionOutcome
from pilot_space.domain.exceptions import AppError
from pilot_space.domain.proposal import ArtifactType

IntentHandler = Callable[..., Awaitable[IntentExecutionOutcome]]
RevertHandler = Callable[..., Awaitable[IntentExecutionOutcome]]


class IntentNotRegisteredError(AppError):
    """Raised when ``IntentExecutor.execute`` is called with an unknown tool name."""

    error_code = "intent_not_registered"
    http_status = 500


_REGISTRY: dict[str, IntentHandler] = {}

# Revert registry — keyed by ``ArtifactType`` (NOT by tool name). Revert is
# per-artifact (Phase 89 Plan 05): regardless of which tool created the
# proposal, reverting an Issue is the same operation. Handlers accept
# ``workspace_id`` + ``target_artifact_id`` kwargs and pull the DB session via
# ``get_current_session()`` (matching the Plan 03 intent-handler pattern —
# keeps ``IntentExecutorProtocol`` unchanged).
_REVERT_REGISTRY: dict[ArtifactType, RevertHandler] = {}


def register_intent(tool_name: str) -> Callable[[IntentHandler], IntentHandler]:
    """Decorator that registers a handler for ``tool_name``.

    Handlers receive ``intent_args`` as the first positional kwarg plus
    ``workspace_id`` and ``target_artifact_id`` as keyword args. They return
    ``IntentExecutionOutcome(applied_version, lines_changed)``.

    Duplicate registration raises ``RuntimeError`` at import time — failing
    loudly is preferable to silently clobbering a handler.
    """

    def decorator(fn: IntentHandler) -> IntentHandler:
        existing = _REGISTRY.get(tool_name)
        if existing is not None and existing is not fn:
            msg = f"Intent already registered: {tool_name} -> {existing!r}"
            raise RuntimeError(msg)
        _REGISTRY[tool_name] = fn
        return fn

    return decorator


def _registered_tool_names() -> list[str]:
    """Return tool names currently in the registry (test-only helper)."""
    return sorted(_REGISTRY.keys())


def register_revert(
    artifact_type: ArtifactType,
) -> Callable[[RevertHandler], RevertHandler]:
    """Decorator registering a revert handler for ``artifact_type``.

    Revert is per-artifact (not per-tool) — regardless of which tool mutated
    the artifact, reverting is the inverse of the artifact's state change.
    Handlers receive ``workspace_id`` and ``target_artifact_id`` as keyword
    args and return ``IntentExecutionOutcome(applied_version, lines_changed)``
    where ``applied_version`` is the new post-revert version number.

    Duplicate registration raises ``RuntimeError`` at import time (same policy
    as ``register_intent``).
    """

    def decorator(fn: RevertHandler) -> RevertHandler:
        existing = _REVERT_REGISTRY.get(artifact_type)
        if existing is not None and existing is not fn:
            msg = f"Revert handler already registered: {artifact_type} -> {existing!r}"
            raise RuntimeError(msg)
        _REVERT_REGISTRY[artifact_type] = fn
        return fn

    return decorator


class IntentExecutor:
    """Dispatches accepted proposals to the right handler by tool name.

    Wired into ``ProposalBus`` as ``IntentExecutorProtocol``. On
    ``accept_proposal``, the bus calls ``execute(...)``; we look up the
    handler by ``intent_tool`` and delegate. Failures propagate to the bus,
    which catches them, persists status=ERRORED, and raises
    ``ProposalIntentExecutionError`` (Plan 01 contract).
    """

    async def execute(
        self,
        *,
        intent_tool: str,
        intent_args: dict[str, Any],
        workspace_id: UUID,
        target_artifact_type: ArtifactType,
        target_artifact_id: UUID,
    ) -> IntentExecutionOutcome:
        handler = _REGISTRY.get(intent_tool)
        if handler is None:
            msg = (
                f"No intent handler registered for tool {intent_tool!r}. "
                f"Known tools: {_registered_tool_names()}"
            )
            raise IntentNotRegisteredError(msg)
        return await handler(
            intent_args,
            workspace_id=workspace_id,
            target_artifact_id=target_artifact_id,
        )

    async def execute_revert(
        self,
        *,
        target_artifact_type: ArtifactType,
        target_artifact_id: UUID,
        workspace_id: UUID,
    ) -> IntentExecutionOutcome:
        """Dispatch an accepted revert to the per-artifact handler.

        Unlike :py:meth:`execute`, revert is keyed by ``ArtifactType`` — the
        inverse of any mutation on an Issue is the same operation regardless
        of which tool produced the original proposal. Spec + Decision are
        deliberately unregistered (tables deferred per Plan 01 D-89-01-02);
        dispatching those artifact types raises
        :class:`IntentNotRegisteredError` which the global handler maps to
        RFC 7807 500.
        """
        handler = _REVERT_REGISTRY.get(target_artifact_type)
        if handler is None:
            msg = (
                f"No revert handler registered for artifact type "
                f"{target_artifact_type!r}. Known: "
                f"{sorted(t.value for t in _REVERT_REGISTRY)}"
            )
            raise IntentNotRegisteredError(msg)
        return await handler(
            workspace_id=workspace_id,
            target_artifact_id=target_artifact_id,
        )


__all__ = [
    "IntentExecutor",
    "IntentHandler",
    "IntentNotRegisteredError",
    "RevertHandler",
    "register_intent",
    "register_revert",
]
