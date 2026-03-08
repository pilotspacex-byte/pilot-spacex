"""TENANT-02: Workspace encryption API endpoint tests.

Router-level tests for the encryption management API:
- POST /workspaces/{slug}/encryption/verify — validate a Fernet key
- GET /workspaces/{slug}/encryption — get encryption status (key version, enabled)
- Verify encrypted_workspace_key is never exposed in responses

All tests are xfail stubs pending Phase 3 plan 03-03 implementation:
- Encryption router (backend/src/pilot_space/api/v1/routers/workspace_encryption.py)
- WorkspaceEncryptionKey model and service
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(strict=False, reason="TENANT-02: encryption router not yet created")
async def test_verify_endpoint_returns_verified_true_for_valid_key(client: object) -> None:
    """POST /workspaces/{slug}/encryption/verify with valid key returns {"verified": true, "key_version": 1}.

    A valid Fernet key (URL-safe base64, 32 bytes decoded) must:
    1. Be accepted by the verify endpoint.
    2. Return JSON body: {"verified": true, "key_version": <int>}.
    3. Return HTTP 200.
    """
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="TENANT-02: encryption router not yet created")
async def test_verify_endpoint_returns_422_for_invalid_key(client: object) -> None:
    """POST /workspaces/{slug}/encryption/verify with invalid key returns 422.

    Invalid key examples: "not-a-key", random hex string, empty string.
    Expected: HTTP 422 with problem+json body containing "invalid_key_format" detail.
    """
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="TENANT-02: encryption router not yet created")
async def test_encrypted_workspace_key_not_exposed_in_api_response(client: object) -> None:
    """GET /workspaces/{slug}/encryption does not return encrypted_workspace_key field.

    The encrypted_workspace_key column stores sensitive material (master-key-wrapped
    workspace Fernet key). It must never appear in any API response, even to OWNER.

    Assert: response JSON does not contain "encrypted_workspace_key" key at any depth.
    """
    raise NotImplementedError
