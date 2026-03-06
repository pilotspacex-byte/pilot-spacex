"""Add pg_cron job to purge expired chat attachments hourly.

Revision ID: 050_add_chat_cleanup_cron
Revises: 049_create_drive_credentials
Create Date: 2026-02-26

Creates:
- pg_cron job 'cleanup-expired-chat-attachments' (runs every hour)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "050_add_chat_cleanup_cron"
down_revision: str | None = "049_create_drive_credentials"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Register hourly cron job to delete expired chat_attachments rows."""
    op.execute(
        """
        SELECT cron.schedule(
            'cleanup-expired-chat-attachments',
            '0 * * * *',
            $$DELETE FROM chat_attachments WHERE expires_at < NOW()$$
        );
    """
    )


def downgrade() -> None:
    """Unregister the cleanup cron job."""
    op.execute("SELECT cron.unschedule('cleanup-expired-chat-attachments');")
