"""SCIM 2.0 request/response schemas — AUTH-07.

Light wrappers around scim2-models for project-specific schemas.
The scim2-models library handles core SCIM schema validation (User, PatchOp,
ListResponse, ServiceProviderConfig).
"""

from __future__ import annotations

from pydantic import BaseModel


class ScimTokenResponse(BaseModel):
    """Response returned when admin generates a SCIM bearer token.

    The raw token is shown ONCE and never stored. Subsequent calls
    replace the old token hash with a new one.
    """

    token: str
    message: str = "Store this token securely. It will not be shown again."


__all__ = ["ScimTokenResponse"]
