"""Shared types and constants for role skill services.

Source: 011-role-based-skills, T009
"""

from __future__ import annotations

VALID_ROLE_TYPES = frozenset(
    {
        "business_analyst",
        "product_owner",
        "developer",
        "tester",
        "architect",
        "tech_lead",
        "project_manager",
        "devops",
        "custom",
    }
)

MAX_ROLES_PER_USER_WORKSPACE = 3

__all__ = ["MAX_ROLES_PER_USER_WORKSPACE", "VALID_ROLE_TYPES"]
