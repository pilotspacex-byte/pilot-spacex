"""Pydantic schemas for workspace session management endpoints (AUTH-06)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    """Response schema for a single workspace session.

    Attributes:
        id: Session UUID.
        user_id: UUID of the authenticated user.
        user_display_name: Display name from user profile (may be None).
        user_avatar_url: Avatar URL from user profile (may be None).
        ip_address: Client IP address (may be None).
        browser: Browser family + major version, e.g. "Chrome 120".
        os: OS family + major version, e.g. "macOS 14".
        device: Device type, e.g. "Desktop" or "iPhone".
        last_seen_at: Timestamp of last request using this session.
        created_at: Timestamp when session was first recorded.
        is_current: True if this session matches the requesting JWT.
    """

    id: UUID
    user_id: UUID
    user_display_name: str | None
    user_avatar_url: str | None
    ip_address: str | None
    browser: str | None
    os: str | None
    device: str | None
    last_seen_at: datetime
    created_at: datetime
    is_current: bool

    model_config = ConfigDict(from_attributes=True)


class TerminateAllResponse(BaseModel):
    """Response after terminating all sessions for a user.

    Attributes:
        terminated: Number of sessions that were revoked.
    """

    terminated: int
