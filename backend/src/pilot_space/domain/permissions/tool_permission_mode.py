"""ToolPermissionMode enum — admin-chosen approval mode per AI tool.

Phase 69 — Granular tool permissions. A single enum shared by the
domain, service, and API layers. The underlying DB column is a
``VARCHAR(8)`` with a ``CHECK (mode IN ('auto','ask','deny'))``
constraint — see migration 105 and the WorkspaceToolPermission model.

DD-003: tools classified as ``CRITICAL_REQUIRE_APPROVAL`` in
``permission_handler.ACTION_CLASSIFICATIONS`` MUST NOT be set to
``AUTO``. Enforcement lives in ``PermissionService.set()``.
"""

from __future__ import annotations

from enum import StrEnum


class ToolPermissionMode(StrEnum):
    """Approval mode for a single AI tool in a single workspace.

    Attributes:
        AUTO: Tool executes without human approval.
        ASK: Tool pauses and requests human approval before executing.
        DENY: Tool is blocked; invocations raise ``PermissionDeniedError``.
    """

    AUTO = "auto"
    ASK = "ask"
    DENY = "deny"


__all__ = ["ToolPermissionMode"]
