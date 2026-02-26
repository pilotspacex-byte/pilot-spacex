"""Storage infrastructure for Pilot Space.

Backend: Supabase Storage (S3-compatible)

Buckets:
- attachments: Issue and note attachments
- avatars: User and workspace avatars
- exports: Workspace export archives
"""

from pilot_space.infrastructure.storage.client import (
    StorageDeleteError,
    StorageSignedUrlError,
    StorageUploadError,
    SupabaseStorageClient,
    SupabaseStorageError,
)

__all__ = [
    "StorageDeleteError",
    "StorageSignedUrlError",
    "StorageUploadError",
    "SupabaseStorageClient",
    "SupabaseStorageError",
]
