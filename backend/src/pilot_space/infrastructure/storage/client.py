"""Supabase Storage client for object storage operations.

Wraps the Supabase Storage SDK (storage3 async API) for uploading,
signing, and deleting objects within named buckets.

All requests use the service role key so operations are not subject
to RLS policies — callers are responsible for access-control decisions
before invoking these methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from storage3.exceptions import StorageApiError
from storage3.utils import StorageException

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from supabase import AsyncClient

logger = get_logger(__name__)


class SupabaseStorageError(Exception):
    """Base exception for Supabase Storage errors."""


class StorageUploadError(SupabaseStorageError):
    """Failed to upload an object."""


class StorageSignedUrlError(SupabaseStorageError):
    """Failed to generate a signed URL."""


class StorageDeleteError(SupabaseStorageError):
    """Failed to delete an object."""


class SupabaseStorageClient:
    """Async client for Supabase Storage using the supabase-py SDK.

    Uses the service role key so operations bypass RLS.
    Access-control enforcement is the caller's responsibility.

    A shared ``AsyncClient`` is lazily obtained from
    ``get_supabase_client()`` on first use, ensuring the same SDK
    connection pool is reused across all calls.
    """

    def __init__(
        self,
        client: AsyncClient | None = None,
    ) -> None:
        """Initialise the storage client.

        Args:
            client: Optional pre-constructed ``AsyncClient``.  When *None*
                the shared singleton is obtained lazily on the first
                operation via ``get_supabase_client()``.
        """
        self._client: AsyncClient | None = client

    async def _get_client(self) -> AsyncClient:
        """Return the SDK client, initialising lazily if needed."""
        if self._client is None:
            from pilot_space.infrastructure.supabase_client import get_supabase_client

            self._client = await get_supabase_client()
        return self._client

    async def upload_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload bytes to a bucket and return the storage key.

        Uses upsert semantics — creates a new object or overwrites an
        existing one.  The caller controls the key and is responsible
        for generating a unique path to avoid unintended overwrites.

        Args:
            bucket: Bucket name (e.g. "attachments").
            key: Object path within the bucket (e.g. "workspace-id/file.pdf").
            data: Raw bytes to store.
            content_type: MIME type of the payload (e.g. "application/pdf").

        Returns:
            The storage key (same as ``key``), usable for subsequent operations.

        Raises:
            StorageUploadError: If the upload fails for any reason.
        """
        logger.debug(
            "storage_upload_start",
            bucket=bucket,
            key=key,
            content_type=content_type,
            size_bytes=len(data),
        )

        try:
            client = await self._get_client()
            await client.storage.from_(bucket).upload(
                key,
                data,
                {
                    "content-type": content_type,
                    "x-upsert": "true",
                },
            )
        except (StorageApiError, StorageException) as exc:
            logger.exception("storage_upload_failed", bucket=bucket, key=key)
            raise StorageUploadError(f"Upload failed for {bucket}/{key}: {exc}") from exc
        except Exception as exc:
            logger.exception("storage_upload_error", bucket=bucket, key=key)
            raise StorageUploadError(f"Unexpected error uploading {bucket}/{key}: {exc}") from exc

        logger.info("storage_upload_success", bucket=bucket, key=key)
        return key

    async def get_signed_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a time-limited signed download URL.

        Args:
            bucket: Bucket name.
            key: Object path within the bucket.
            expires_in: URL validity duration in seconds (default 3600 = 1 hour).

        Returns:
            Signed URL string valid for ``expires_in`` seconds.

        Raises:
            StorageSignedUrlError: If URL generation fails.
        """
        logger.debug(
            "storage_sign_url_start",
            bucket=bucket,
            key=key,
            expires_in=expires_in,
        )

        try:
            client = await self._get_client()
            response = await client.storage.from_(bucket).create_signed_url(key, expires_in)
        except (StorageApiError, StorageException) as exc:
            logger.exception("storage_sign_url_failed", bucket=bucket, key=key)
            raise StorageSignedUrlError(
                f"Signed URL generation failed for {bucket}/{key}: {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("storage_sign_url_error", bucket=bucket, key=key)
            raise StorageSignedUrlError(
                f"Unexpected error generating signed URL for {bucket}/{key}: {exc}"
            ) from exc

        # SDK returns {"signedURL": full_url, "signedUrl": full_url}
        signed_url: str | None = response.get("signedURL") or response.get("signedUrl")

        if not signed_url:
            logger.error(
                "storage_sign_url_missing_field",
                bucket=bucket,
                key=key,
                response_keys=list(response.keys()),
            )
            raise StorageSignedUrlError(
                f"Signed URL response missing 'signedURL' field for {bucket}/{key}"
            )

        logger.info("storage_sign_url_success", bucket=bucket, key=key)
        return signed_url

    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from a bucket.

        A 404-equivalent (object already absent) is treated as a success.

        Args:
            bucket: Bucket name.
            key: Object path within the bucket.

        Raises:
            StorageDeleteError: If the deletion fails.
        """
        logger.debug("storage_delete_start", bucket=bucket, key=key)

        try:
            client = await self._get_client()
            await client.storage.from_(bucket).remove([key])
        except StorageApiError as exc:
            # Treat "not found" as success — object already absent.
            is_not_found = (hasattr(exc, "status") and exc.status == 404) or any(
                p in str(exc).lower() for p in ("not found", "does not exist")
            )
            if is_not_found:
                logger.info("storage_delete_not_found", bucket=bucket, key=key)
                return
            logger.exception("storage_delete_failed", bucket=bucket, key=key)
            raise StorageDeleteError(f"Delete failed for {bucket}/{key}: {exc}") from exc
        except (StorageException, Exception) as exc:
            logger.exception("storage_delete_error", bucket=bucket, key=key)
            raise StorageDeleteError(f"Delete failed for {bucket}/{key}: {exc}") from exc

        logger.info("storage_delete_success", bucket=bucket, key=key)


__all__ = [
    "StorageDeleteError",
    "StorageSignedUrlError",
    "StorageUploadError",
    "SupabaseStorageClient",
    "SupabaseStorageError",
]
