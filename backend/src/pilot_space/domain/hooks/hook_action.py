"""HookAction enum -- admin-chosen action for workspace hook rules.

Phase 83 -- workspace hooks API. A single StrEnum shared by the domain,
service, and API layers. The underlying DB column is a ``VARCHAR(20)``
with a ``CHECK (action IN ('allow', 'deny', 'require_approval'))``
constraint -- see migration 110 and the WorkspaceHookConfig model.

DD-003: hooks with ``action=allow`` on tools classified as
``CRITICAL_REQUIRE_APPROVAL`` are overridden at evaluation time to
``require_approval``. The evaluator (Plan 02) enforces this guard, not
the creation endpoint -- admins can still see and configure the rule.
"""

from __future__ import annotations

from enum import StrEnum


class HookAction(StrEnum):
    """Action to take when a workspace hook rule matches.

    Attributes:
        ALLOW: Tool executes without human approval.
        DENY: Tool is blocked; invocations are rejected.
        REQUIRE_APPROVAL: Tool pauses and requests human approval.
    """

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


__all__ = ["HookAction"]
