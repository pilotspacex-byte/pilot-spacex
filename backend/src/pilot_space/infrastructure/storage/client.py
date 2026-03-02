"""Supabase Storage client for object storage operations.

Wraps the Supabase Storage REST API (S3-compatible) for uploading,
signing, and deleting objects within named buckets.

All requests use the service role key so operations are not subject
to RLS policies — callers are responsible for access-control decisions
before invoking these methods.
"""

from __future__ import annotations

import httpx

from pilot_space.config import get_settings
from pilot_space.infrastructure.logging import get_logger

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
    """Async client for Supabase Storage REST API.

    Uses the service role key so operations bypass RLS.
    Access-control enforcement is the caller's responsibility.

    Attributes:
        _base_url: Supabase project URL.
        _service_key: Service role key used for Authorization header.
        _timeout: HTTP request timeout in seconds.
    """

    _TIMEOUT_SECONDS: float = 30.0

    def __init__(
        self,
        supabase_url: str | None = None,
        service_key: str | None = None,
    ) -> None:
        """Initialize the storage client.

        Args:
            supabase_url: Supabase project URL. Falls back to settings when None.
            service_key: Service role key. Falls back to settings when None.
        """
        settings = get_settings()

        self._base_url = (supabase_url or settings.supabase_url).rstrip("/")
        self._service_key = service_key or settings.supabase_service_key.get_secret_value()

    def _headers(self) -> dict[str, str]:
        """Build common request headers.

        Returns:
            Headers dict with Authorization and content-type for JSON.
        """
        return {
            "Authorization": f"Bearer {self._service_key}",
            "apikey": self._service_key,
        }

    def _storage_url(self, path: str) -> str:
        """Construct a Supabase Storage API URL.

        Args:
            path: Path relative to /storage/v1 (must start with /).

        Returns:
            Full URL string.
        """
        return f"{self._base_url}/storage/v1{path}"

    async def upload_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload bytes to a bucket and return the storage key.

        Uses POST semantics — creates a new object or overwrites an existing one
        (upsert=true).  The caller controls the key and is responsible for
        generating a unique path to avoid unintended overwrites.

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
        url = self._storage_url(f"/object/{bucket}/{key}")
        headers = {
            **self._headers(),
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        logger.debug(
            "storage_upload_start",
            bucket=bucket,
            key=key,
            content_type=content_type,
            size_bytes=len(data),
        )

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS) as client:
                response = await client.post(url, content=data, headers=headers)
        except httpx.TimeoutException as exc:
            logger.exception("storage_upload_timeout", bucket=bucket, key=key)
            raise StorageUploadError(f"Upload timed out for {bucket}/{key}") from exc
        except httpx.HTTPError as exc:
            logger.exception("storage_upload_http_error", bucket=bucket, key=key)
            raise StorageUploadError(f"HTTP error uploading {bucket}/{key}: {exc}") from exc

        if response.status_code not in (200, 201):
            logger.error(
                "storage_upload_failed",
                bucket=bucket,
                key=key,
                status_code=response.status_code,
                response_body=response.text,
            )
            raise StorageUploadError(
                f"Upload failed for {bucket}/{key}: HTTP {response.status_code} — {response.text}"
            )

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
        url = self._storage_url(f"/object/sign/{bucket}/{key}")
        headers = {
            **self._headers(),
            "Content-Type": "application/json",
        }
        payload = {"expiresIn": expires_in}

        logger.debug(
            "storage_sign_url_start",
            bucket=bucket,
            key=key,
            expires_in=expires_in,
        )

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            logger.exception("storage_sign_url_timeout", bucket=bucket, key=key)
            raise StorageSignedUrlError(f"Signed URL request timed out for {bucket}/{key}") from exc
        except httpx.HTTPError as exc:
            logger.exception("storage_sign_url_http_error", bucket=bucket, key=key)
            raise StorageSignedUrlError(
                f"HTTP error generating signed URL for {bucket}/{key}: {exc}"
            ) from exc

        if response.status_code != 200:
            logger.error(
                "storage_sign_url_failed",
                bucket=bucket,
                key=key,
                status_code=response.status_code,
                response_body=response.text,
            )
            raise StorageSignedUrlError(
                f"Signed URL generation failed for {bucket}/{key}: "
                f"HTTP {response.status_code} — {response.text}"
            )

        body = response.json()
        signed_url: str | None = body.get("signedURL") or body.get("signedUrl")

        if not signed_url:
            logger.error(
                "storage_sign_url_missing_field",
                bucket=bucket,
                key=key,
                response_body=body,
            )
            raise StorageSignedUrlError(
                f"Signed URL response missing 'signedURL' field for {bucket}/{key}"
            )

        # Supabase returns a path-only signed URL; prepend base URL when needed.
        if signed_url.startswith("/"):
            signed_url = f"{self._base_url}{signed_url}"

        logger.info("storage_sign_url_success", bucket=bucket, key=key)
        return signed_url

    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from a bucket.

        Args:
            bucket: Bucket name.
            key: Object path within the bucket.

        Raises:
            StorageDeleteError: If the deletion fails.
        """
        url = self._storage_url(f"/object/{bucket}/{key}")
        headers = self._headers()

        logger.debug("storage_delete_start", bucket=bucket, key=key)

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS) as client:
                response = await client.delete(url, headers=headers)
        except httpx.TimeoutException as exc:
            logger.exception("storage_delete_timeout", bucket=bucket, key=key)
            raise StorageDeleteError(f"Delete timed out for {bucket}/{key}") from exc
        except httpx.HTTPError as exc:
            logger.exception("storage_delete_http_error", bucket=bucket, key=key)
            raise StorageDeleteError(f"HTTP error deleting {bucket}/{key}: {exc}") from exc

        # 200 and 404 are both acceptable: 404 means the object is already absent.
        if response.status_code not in (200, 204, 404):
            logger.error(
                "storage_delete_failed",
                bucket=bucket,
                key=key,
                status_code=response.status_code,
                response_body=response.text,
            )
            raise StorageDeleteError(
                f"Delete failed for {bucket}/{key}: HTTP {response.status_code} — {response.text}"
            )

        logger.info(
            "storage_delete_success",
            bucket=bucket,
            key=key,
            was_present=response.status_code != 404,
        )


__all__ = [
    "StorageDeleteError",
    "StorageSignedUrlError",
    "StorageUploadError",
    "SupabaseStorageClient",
    "SupabaseStorageError",
]
