"""Domain exceptions for the workspace hook rule service."""

from __future__ import annotations

from pilot_space.domain.exceptions import NotFoundError, ValidationError


class HookRuleError(ValidationError):
    """Generic hook rule validation failure (422).

    Raised when a hook rule violates a business constraint that doesn't
    fit a more specific exception subclass.
    """

    error_code = "hook_rule_error"


class InvalidHookPatternError(ValidationError):
    """Invalid tool pattern in a hook rule (422).

    Raised when the ``tool_pattern`` field contains an invalid regex,
    exceeds the 200-character ReDoS mitigation limit, or is otherwise
    malformed.
    """

    error_code = "invalid_hook_pattern"


class HookRuleNotFoundError(NotFoundError):
    """Hook rule not found (404).

    Raised when a hook rule lookup by ID returns no result.
    """

    error_code = "hook_rule_not_found"


class HookRuleLimitError(ValidationError):
    """Maximum hook rules per workspace exceeded (422).

    Raised when a workspace has reached the 50-rule limit and a new
    rule creation is attempted.
    """

    error_code = "hook_rule_limit_exceeded"


__all__ = [
    "HookRuleError",
    "HookRuleLimitError",
    "HookRuleNotFoundError",
    "InvalidHookPatternError",
]
