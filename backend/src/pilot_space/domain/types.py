"""Shared domain types and sentinels.

Provides common type utilities used across the domain and application layers.
"""

from __future__ import annotations

from typing import Any

# Sentinel that distinguishes "field omitted" from "field explicitly set to None".
# Use in dataclass fields: `field(default_factory=lambda: UNSET)`
# Check with: `if value is not UNSET`
UNSET: Any = object()
