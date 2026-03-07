"""Test scaffolds for SCIM 2.0 provisioning router — AUTH-07.

These tests define the expected HTTP contract for the /scim/v2 endpoints
before implementation begins. All tests are marked xfail(strict=False) so
they are collected by pytest and run, but do not block the suite.

Requirements covered:
  AUTH-07: SCIM 2.0 user provisioning (create, deactivate, update, auth)
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AUTH-07: SCIM user provisioning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SCIM POST /Users endpoint not yet implemented (AUTH-07)",
)
async def test_scim_provision_user_creates_workspace_member() -> None:
    """POST /scim/v2/Users creates a workspace_member row for the provisioned user.

    Scenario:
        Given a valid SCIM bearer token for a workspace
        When POST /scim/v2/Users is called with a SCIM User resource (userName, emails)
        Then the response status is 201
        And a WorkspaceMember row exists with is_active=True
        And the response body is a valid SCIM User resource with an id
    """
    raise NotImplementedError("AUTH-07: SCIM POST /Users provisioning not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SCIM DELETE /Users deprovisioning not yet implemented (AUTH-07)",
)
async def test_scim_deprovision_deactivates_not_deletes() -> None:
    """DELETE /scim/v2/Users/{id} sets is_active=False, does not hard-delete.

    Scenario:
        Given an existing workspace member with is_active=True
        When DELETE /scim/v2/Users/{scim_id} is called
        Then the response status is 204
        And workspace_member.is_active is False
        And workspace_member row still exists (soft deactivation, not deletion)
    """
    raise NotImplementedError("AUTH-07: SCIM DELETE /Users soft-deactivation not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SCIM PATCH /Users update not yet implemented (AUTH-07)",
)
async def test_scim_patch_user_updates_fields() -> None:
    """PATCH /scim/v2/Users/{id} applies SCIM patch operations to the member.

    Scenario:
        Given an existing workspace member
        When PATCH /scim/v2/Users/{scim_id} is called with
          {"Operations": [{"op": "replace", "path": "active", "value": false}]}
        Then the response status is 200
        And workspace_member.is_active is updated accordingly
        And the response body reflects the updated resource
    """
    raise NotImplementedError("AUTH-07: SCIM PATCH /Users update not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SCIM bearer token authentication not yet implemented (AUTH-07)",
)
async def test_scim_invalid_bearer_token_returns_401() -> None:
    """SCIM requests with an invalid or missing bearer token return 401.

    Scenario:
        Given an invalid or expired SCIM bearer token
        When any SCIM endpoint is called (e.g. GET /scim/v2/Users)
        Then the response status is 401
        And the body contains a SCIM-compliant error schema
    """
    raise NotImplementedError(
        "AUTH-07: SCIM bearer token authentication enforcement not implemented"
    )
