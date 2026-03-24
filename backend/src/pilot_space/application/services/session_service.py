"""Session management service for workspace session tracking and force-termination.

Provides AUTH-06 session management:
- record_session: throttled upsert via Redis LASTSEEN_KEY
- list_sessions: active sessions with UA parsing
- force_terminate: revoke single session + set REVOKED_KEY in Redis
- terminate_all_for_user: revoke all sessions + Supabase global sign_out
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.database.repositories.workspace_session_repository import (
        WorkspaceSessionRepository,
    )

logger = logging.getLogger(__name__)

# Redis key templates
LASTSEEN_KEY_TEMPLATE = "session:lastseen:{token_hash}"
REVOKED_KEY_TEMPLATE = "session:revoked:{workspace_id}:{token_hash}"

# Throttle window: 60 seconds between last_seen_at DB writes
LASTSEEN_TTL_SECONDS = 60

# Revocation key TTL: 30 minutes (matches JWT expiry)
REVOKED_TTL_SECONDS = 1800


@dataclass
class SessionDisplay:
    """Display object for a workspace session (returned to admin UI)."""

    session_id: UUID
    user_id: UUID
    user_display_name: str | None
    user_avatar_url: str | None
    ip_address: str | None
    browser: str | None
    os: str | None
    device: str | None
    last_seen_at: datetime
    created_at: datetime


def _parse_user_agent(ua_string: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse browser, OS, and device from a User-Agent string.

    Args:
        ua_string: Raw User-Agent header.

    Returns:
        Tuple of (browser, os, device) — each may be None.
    """
    if not ua_string:
        return None, None, None

    try:
        from ua_parser import user_agent_parser

        result = user_agent_parser.Parse(ua_string)
        browser_family = result["user_agent"]["family"]
        browser_version = result["user_agent"].get("major", "")
        os_family = result["os"]["family"]
        os_version = result["os"].get("major", "")
        device_family = result["device"]["family"]

        browser = browser_family if browser_family != "Other" else None
        if browser and browser_version:
            browser = f"{browser} {browser_version}"

        os_name = os_family if os_family != "Other" else None
        if os_name and os_version:
            os_name = f"{os_name} {os_version}"

        device = device_family if device_family != "Other" else "Desktop"

        return browser, os_name, device
    except Exception:
        logger.debug("Failed to parse user agent: %s", ua_string[:100] if ua_string else "")
        return None, None, None


class SessionService:
    """Application service for workspace session management (AUTH-06).

    Coordinates between WorkspaceSessionRepository, Redis, and Supabase admin
    to provide throttled session recording, listing, and force-termination.

    Args:
        session_repo: Repository for workspace session CRUD.
        redis: Redis client for throttle and revocation keys.
        supabase_admin_client: Supabase admin client for global sign_out.
    """

    def __init__(
        self,
        session_repo: WorkspaceSessionRepository,
        redis: RedisClient,
        supabase_admin_client: Any,
    ) -> None:
        """Initialize SessionService."""
        self._repo = session_repo
        self._redis = redis
        self._admin_client = supabase_admin_client

    async def record_session(
        self,
        *,
        token_hash: str,
        user_id: UUID,
        workspace_id: UUID,
        ip_address: str | None,
        user_agent: str | None,
        db: AsyncSession,
    ) -> None:
        """Record or update a workspace session with throttling.

        Checks LASTSEEN_KEY in Redis. If present (within 60s window), skips
        the DB upsert to avoid write storms. Otherwise, upserts the session
        row and refreshes the throttle key.

        Args:
            token_hash: SHA-256 hex digest of the session token.
            user_id: Authenticated user UUID.
            workspace_id: Workspace UUID.
            ip_address: Client IP address.
            user_agent: Raw User-Agent header.
            db: Database session for writes.
        """
        lastseen_key = LASTSEEN_KEY_TEMPLATE.format(token_hash=token_hash)
        throttled = await self._redis.get_raw(lastseen_key)
        if throttled is not None:
            # Within throttle window — skip DB write
            return

        # Upsert session row in DB
        await self._repo.upsert_session(
            user_id=user_id,
            workspace_id=workspace_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            db=db,
        )

        # Set throttle key — prevents writes for the next 60s
        await self._redis.setex(lastseen_key, LASTSEEN_TTL_SECONDS, "1")

    async def list_sessions(
        self,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> list[SessionDisplay]:
        """List active sessions for a workspace with parsed UA info.

        Args:
            workspace_id: Workspace UUID.
            db: Database session.

        Returns:
            List of SessionDisplay objects sorted by last_seen_at DESC.
        """
        sessions = await self._repo.list_active_for_workspace(
            workspace_id=workspace_id,
            db=db,
        )

        displays: list[SessionDisplay] = []
        for session in sessions:
            browser, os_name, device = _parse_user_agent(session.user_agent)
            user = getattr(session, "user", None)
            displays.append(
                SessionDisplay(
                    session_id=session.id,
                    user_id=session.user_id,
                    user_display_name=getattr(user, "display_name", None) if user else None,
                    user_avatar_url=getattr(user, "avatar_url", None) if user else None,
                    ip_address=session.ip_address,
                    browser=browser,
                    os=os_name,
                    device=device,
                    last_seen_at=session.last_seen_at,  # type: ignore[arg-type]
                    created_at=session.created_at,
                )
            )
        return displays

    async def force_terminate(
        self,
        *,
        session_id: UUID,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Force-terminate a single workspace session.

        Sets revoked_at in the DB and writes a REVOKED_KEY to Redis so that
        subsequent requests using the same token receive a 401 immediately.

        Args:
            session_id: Session UUID to terminate.
            workspace_id: Workspace scope (prevents cross-workspace action).
            db: Database session for writes.

        Raises:
            NotFoundError: If session not found or already revoked.
        """
        session = await self._repo.get_session_by_id(session_id, workspace_id)
        if session is None:
            msg = f"Session {session_id} not found in workspace {workspace_id}"
            raise NotFoundError(msg)

        token_hash = session.session_token_hash

        # Revoke in DB
        await self._repo.revoke(
            session_id=session_id,
            workspace_id=workspace_id,
            db=db,
        )

        # Set revocation key so middleware blocks future requests immediately
        revoked_key = REVOKED_KEY_TEMPLATE.format(
            workspace_id=workspace_id,
            token_hash=token_hash,
        )
        await self._redis.setex(revoked_key, REVOKED_TTL_SECONDS, "1")

    async def terminate_all_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> int:
        """Revoke all active sessions for a user and hard-invalidate via Supabase.

        Revokes all active sessions in the DB, then calls Supabase
        auth.admin.sign_out with global scope for hard token invalidation.

        Args:
            user_id: User UUID whose sessions to terminate.
            workspace_id: Workspace UUID scope.
            db: Database session for writes.

        Returns:
            Number of sessions revoked.
        """
        count = await self._repo.revoke_all_for_user(
            user_id=user_id,
            workspace_id=workspace_id,
            db=db,
        )

        # Hard invalidate all Supabase tokens for this user
        try:
            self._admin_client.auth.admin.sign_out(str(user_id), scope="global")
        except Exception:
            logger.warning("Supabase sign_out failed — sessions revoked in DB")

        return count
