"""xfail test stubs for audit router actor_type parameter.

Phase 4 — AI Governance (AIGOV-03):
The audit router must pass actor_type query parameter to AuditLogRepository
for both list and export endpoints.

Implemented in plan 04-05 (AIGOV-03 audit router actor_type param).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-03: audit list passes actor_type to repo — implemented in 04-05",
)
async def test_audit_list_actor_type_param_passed_to_repo() -> None:
    """GET /workspaces/{slug}/audit?actor_type=AI passes actor_type to list_filtered.

    The audit list router must accept actor_type as a query parameter
    and forward it to AuditLogRepository.list_filtered().
    Verify via mock that list_filtered is called with actor_type='AI'.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-03: audit export passes actor_type to repo — implemented in 04-05",
)
async def test_audit_export_actor_type_param_passed_to_repo() -> None:
    """GET /workspaces/{slug}/audit/export?actor_type=AI passes actor_type to list_for_export.

    The audit export router must accept actor_type as a query parameter
    and forward it to AuditLogRepository.list_for_export().
    Verify via mock that list_for_export is called with actor_type='AI'.
    """
