"""Reusable file-upload validation helpers for routers.

MIME type, empty-file, and max-size checks are HTTP-level concerns that belong
in the router layer (per service-pattern rules).  This module centralises the
three guards so every upload endpoint uses the same logic and error format.
"""

from __future__ import annotations

from collections.abc import Collection

from fastapi import HTTPException, UploadFile, status


def sanitize_content_type(file: UploadFile) -> str:
    """Return the base MIME type from an ``UploadFile``, stripping parameters.

    Falls back to ``application/octet-stream`` when the browser sends nothing.
    """
    return (file.content_type or "application/octet-stream").split(";")[0].strip()


async def read_and_validate(
    file: UploadFile,
    *,
    allowed_mime_types: Collection[str],
    max_bytes: int,
    file_label: str = "File",
) -> tuple[bytes, str]:
    """Read *file* bytes and validate MIME type, emptiness, and size.

    Parameters
    ----------
    file:
        The ``UploadFile`` from a multipart form field.
    allowed_mime_types:
        Set/frozenset/list of acceptable MIME base types (e.g. ``"audio/webm"``).
    max_bytes:
        Maximum allowed file size in bytes.
    file_label:
        Human-readable noun used in error messages (e.g. ``"Audio file"``).

    Returns
    -------
    tuple[bytes, str]
        ``(file_bytes, content_type)`` on success.

    Raises
    ------
    HTTPException 400
        On MIME mismatch, empty body, or size overflow.
    """
    content_type = sanitize_content_type(file)

    if content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported type '{content_type}'. "
                f"Allowed: {', '.join(sorted(allowed_mime_types))}"
            ),
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{file_label} is empty",
        )

    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{file_label} exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
        )

    return data, content_type
