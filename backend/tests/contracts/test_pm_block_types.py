"""Contract test: PM Block Type Parity (T-228, 017-M6d).

Validates that the backend's _VALID_PM_BLOCK_TYPES matches the canonical set
defined in specs/contracts/pm-block-types.json.

Both backend and frontend must agree on the complete set; divergence breaks
the AI tool/editor contract (FR-043, FR-044).

Current expected set:
  Original 6: decision, form, raci, risk, timeline, dashboard
  New 4 (017): sprint-board, dependency-map, capacity-plan, release-notes
"""

from __future__ import annotations

import json
from pathlib import Path

from pilot_space.ai.mcp.note_content_server import _VALID_PM_BLOCK_TYPES

# ---------------------------------------------------------------------------
# Contract source of truth
# ---------------------------------------------------------------------------

_CONTRACT_PATH = Path(__file__).parents[3] / "specs" / "contracts" / "pm-block-types.json"


def _load_contract() -> set[str]:
    """Load canonical PM block types from the shared contract file."""
    with _CONTRACT_PATH.open() as fh:
        data = json.load(fh)
    return set(data["block_types"])


class TestPMBlockTypeContract:
    """Backend side of the PM block type contract test.

    Failures here mean the backend has added, removed, or renamed a PM block
    type without updating the shared contract — or vice versa.
    """

    def test_contract_file_exists(self) -> None:
        """Sanity: contract JSON must be present."""
        assert _CONTRACT_PATH.exists(), (
            f"Contract file missing: {_CONTRACT_PATH}. "
            "Create specs/contracts/pm-block-types.json first."
        )

    def test_backend_matches_contract(self) -> None:
        """Backend _VALID_PM_BLOCK_TYPES must exactly equal the contract set."""
        contract = _load_contract()
        backend = set(_VALID_PM_BLOCK_TYPES)

        missing_from_backend = contract - backend
        extra_in_backend = backend - contract

        assert not missing_from_backend, (
            f"PM block types missing from backend (FR-043, FR-044): {sorted(missing_from_backend)}\n"
            f"  Contract requires: {sorted(contract)}\n"
            "Add them to backend/src/pilot_space/ai/mcp/note_content_server.py"
        )
        assert not extra_in_backend, (
            f"Extra PM block types in backend (FR-043, FR-044): {sorted(extra_in_backend)}\n"
            f"  Backend has: {sorted(backend)}\n"
            "Add them to specs/contracts/pm-block-types.json to synchronize."
        )

    def test_original_six_present(self) -> None:
        """Original 6 PM block types must always be present."""
        original = {"decision", "form", "raci", "risk", "timeline", "dashboard"}
        backend = set(_VALID_PM_BLOCK_TYPES)
        missing = original - backend
        assert not missing, f"Original PM block types removed from backend: {sorted(missing)}"

    def test_new_four_from_017_present(self) -> None:
        """4 new PM block types from Feature 017 must be present post-migration."""
        new_types = {"sprint-board", "dependency-map", "capacity-plan", "release-notes"}
        contract = _load_contract()
        # Contract must include the new types; backend must too once 017 lands.
        assert new_types <= contract, (
            f"Feature 017 PM block types missing from contract: {sorted(new_types - contract)}"
        )

    def test_no_duplicate_block_types(self) -> None:
        """_VALID_PM_BLOCK_TYPES must not contain duplicates (frozenset implies this)."""
        all_types = list(_VALID_PM_BLOCK_TYPES)
        assert len(all_types) == len(set(all_types)), (
            "Duplicate PM block types detected in backend definition"
        )

    def test_block_types_are_strings(self) -> None:
        """All block type values must be non-empty strings."""
        for bt in _VALID_PM_BLOCK_TYPES:
            assert isinstance(bt, str), f"Block type {bt!r} is not a string"
            assert bt.strip(), f"Block type {bt!r} is empty or whitespace"
