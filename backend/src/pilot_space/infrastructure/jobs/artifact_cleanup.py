"""artifact_cleanup — deletes stale pending_upload artifact records and their storage objects.

Background job triggered by TASK_ARTIFACT_CLEANUP in MemoryWorker.

Deletes pending_upload artifact records older than 24 hours along with their
corresponding storage objects in the 'note-artifacts' bucket.

Storage cleanup is best-effort: a failure to delete a storage object is logged
but does not prevent the DB record from being counted as cleaned (the DB
delete already completed before storage cleanup is attempted by the caller,
since delete_stale_pending returns the stale records after deleting them).

Feature: v1.1 — Artifacts (ARTF-06)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.repositories.artifact_repository import (
    ArtifactRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

_BUCKET = "note-artifacts"
_STALE_AFTER_HOURS = 24


async def run_artifact_cleanup(
    session: AsyncSession,
    storage_client: SupabaseStorageClient,
) -> int:
    """Delete pending_upload artifact records older than 24h and their storage objects.

    Fetches stale records from the DB, deletes them, then removes each corresponding
    storage object. Storage deletion is non-fatal: a failure logs a warning but does
    not affect the returned count (DB records are already gone).

    Args:
        session: Database session (caller responsible for commit).
        storage_client: Supabase Storage client for object deletion.

    Returns:
        Number of artifact DB records deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=_STALE_AFTER_HOURS)
    repo = ArtifactRepository(session)
    stale = await repo.delete_stale_pending(older_than=cutoff)

    if not stale:
        logger.info("artifact_cleanup_complete", deleted_count=0)
        return 0

    deleted_count = 0
    for artifact in stale:
        try:
            await storage_client.delete_object(bucket=_BUCKET, key=artifact.storage_key)
            logger.info(
                "artifact_cleanup_deleted",
                artifact_id=str(artifact.id),
                storage_key=artifact.storage_key,
            )
        except Exception as exc:  # BLE001: non-fatal storage cleanup; DB record already deleted
            # Non-fatal: storage object may not exist (upload failed before reaching storage).
            # Log and continue to next artifact; DB record is already deleted.
            logger.warning(
                "artifact_cleanup_storage_delete_failed",
                artifact_id=str(artifact.id),
                error=str(exc),
            )
        deleted_count += 1  # Count regardless of storage result — DB record is gone

    logger.info("artifact_cleanup_complete", deleted_count=deleted_count)
    return deleted_count


__all__ = ["run_artifact_cleanup"]
