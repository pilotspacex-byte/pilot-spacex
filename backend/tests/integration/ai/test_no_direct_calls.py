"""Grep-based audit: no direct AsyncAnthropic instantiations in migrated services.

This test scans all service and job files to ensure they use LLMGateway
instead of direct AsyncAnthropic() calls. It will FAIL until Plan 03/04
complete the full migration -- that is intentional.

Exclusions:
- key_storage.py: uses AsyncAnthropic for key validation (not LLM calls)
- ai_configuration.py: uses AsyncAnthropic for test_configuration endpoint
- ghost_text.py: uses AnthropicClientPool (separate streaming path)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Root of the backend source tree
_BACKEND_SRC = Path(__file__).resolve().parents[2] / "src" / "pilot_space"

# Files that legitimately use AsyncAnthropic directly (not via gateway)
_EXCLUDED_FILES = frozenset(
    {
        "key_storage.py",  # Validation call, not LLM completion
        "ai_configuration.py",  # Test configuration endpoint
        "ghost_text.py",  # AnthropicClientPool streaming path
    }
)

# Directories to scan for direct AsyncAnthropic usage
_SCAN_DIRS = [
    _BACKEND_SRC / "application" / "services",
    _BACKEND_SRC / "ai" / "jobs",
]

_PATTERN = re.compile(r"AsyncAnthropic\(")


@pytest.mark.skip(reason="Fails until Plan 03/04 migration complete")
def test_no_direct_async_anthropic_in_services() -> None:
    """Assert no service or job file directly instantiates AsyncAnthropic.

    All LLM calls should go through LLMGateway which handles:
    - BYOK key resolution
    - Resilient execution (retry + circuit breaking)
    - Cost tracking
    - Langfuse tracing
    """
    violations: list[str] = []

    for scan_dir in _SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            if py_file.name in _EXCLUDED_FILES:
                continue
            content = py_file.read_text(encoding="utf-8")
            if _PATTERN.search(content):
                rel_path = py_file.relative_to(_BACKEND_SRC)
                violations.append(str(rel_path))

    assert not violations, (
        f"Direct AsyncAnthropic() found in {len(violations)} file(s). "
        f"Use LLMGateway instead:\n  " + "\n  ".join(sorted(violations))
    )
