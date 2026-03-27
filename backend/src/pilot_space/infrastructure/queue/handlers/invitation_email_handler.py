"""Handler for sending invitation emails via Supabase Admin API.

Dispatched by MemoryWorker when a `send_invitation_email` job is dequeued.
The job is enqueued transactionally with the invitation record, so it only
runs after the DB commit — preventing emails for rolled-back invitations.
"""

from __future__ import annotations

from typing import Any

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def send_invitation_email(payload: dict[str, Any]) -> None:
    """Send invitation email via Supabase Admin API.

    Args:
        payload: Queue message with 'email' and 'invitation_id'.
    """
    email = payload.get("email", "")
    invitation_id = payload.get("invitation_id", "")

    if not email or not invitation_id:
        msg = f"send_invitation_email: missing required fields (email={bool(email)}, invitation_id={bool(invitation_id)})"
        raise ValueError(msg)

    from pilot_space.config import get_settings
    from pilot_space.infrastructure.supabase_client import get_supabase_client

    settings = get_settings()
    redirect_url = f"{settings.frontend_url}/accept-invite?invitation_id={invitation_id}"

    client = await get_supabase_client()
    await client.auth.admin.invite_user_by_email(
        email,
        options={
            "redirect_to": redirect_url,
            "data": {"invitation_id": str(invitation_id)},
        },
    )

    logger.info(
        "Invitation email sent via Supabase",
        extra={"invitation_id": invitation_id},
    )
