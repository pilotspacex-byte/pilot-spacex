"""Tests verifying legacy approval_waiter.py is deleted (APPR-04).

Covers:
- APPR-04: approval_waiter.py file does not exist
- APPR-04: No imports of wait_for_approval or approval_waiter in codebase
- APPR-04: UnifiedApprovalBus is importable as replacement
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_approval_waiter_file_does_not_exist() -> None:
    """APPR-04: approval_waiter.py must be deleted."""
    waiter_path = (
        Path(__file__).parents[4]
        / "src"
        / "pilot_space"
        / "ai"
        / "sdk"
        / "approval_waiter.py"
    )
    assert not waiter_path.exists(), f"Legacy file still exists: {waiter_path}"


def test_no_import_of_wait_for_approval() -> None:
    """APPR-04: No module should import wait_for_approval."""
    with pytest.raises(ImportError):
        from pilot_space.ai.sdk.approval_waiter import wait_for_approval  # noqa: F401


def test_no_import_of_approval_waiter_module() -> None:
    """APPR-04: The approval_waiter module itself must not be importable."""
    with pytest.raises(ImportError):
        import pilot_space.ai.sdk.approval_waiter  # noqa: F401


def test_unified_approval_bus_is_importable() -> None:
    """APPR-04: Replacement module is importable."""
    from pilot_space.ai.sdk.approval_bus import (  # noqa: F401
        UnifiedApprovalBus,
        get_approval_bus,
    )


def test_approval_bus_exported_from_sdk_init() -> None:
    """APPR-04: UnifiedApprovalBus and get_approval_bus are re-exported from sdk __init__."""
    from pilot_space.ai.sdk import (  # noqa: F401
        UnifiedApprovalBus,
        get_approval_bus,
    )


def test_no_source_references_to_approval_waiter() -> None:
    """APPR-04: No .py files in backend/src reference approval_waiter (excluding comments in approval_bus)."""
    src_root = Path(__file__).parents[4] / "src" / "pilot_space"
    violations: list[str] = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "approval_bus.py":
            # approval_bus.py has docstring references (migration history) -- skip
            continue
        content = py_file.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if "approval_waiter" in line and not line.strip().startswith("#"):
                violations.append(f"{py_file.relative_to(src_root)}:{i}: {line.strip()}")
    assert not violations, "Files still reference approval_waiter:\n" + "\n".join(violations)
