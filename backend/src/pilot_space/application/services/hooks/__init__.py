"""Workspace hook rule service layer.

Phase 83 -- declarative workspace hook rules (HOOK-02, HOOK-05).
Provides CRUD operations with pattern validation, rule limits,
Redis cache invalidation, and DD-003 defense-in-depth guard.
"""

from pilot_space.application.services.hooks.exceptions import (
    HookRuleError,
    HookRuleLimitError,
    HookRuleNotFoundError,
    InvalidHookPatternError,
)
from pilot_space.application.services.hooks.hook_rule_service import HookRuleService

__all__ = [
    "HookRuleError",
    "HookRuleLimitError",
    "HookRuleNotFoundError",
    "HookRuleService",
    "InvalidHookPatternError",
]
