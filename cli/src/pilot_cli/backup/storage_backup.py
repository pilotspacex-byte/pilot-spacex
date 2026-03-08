"""Supabase Storage object download and upload with pagination.

Uses the Supabase Storage REST API directly via httpx.
Pagination: fetch page_size=100 objects per request until response < page_size.
"""

from __future__ import annotations

from typing import Any

import httpx

_PAGE_SIZE = 100


async def download_storage_objects(
    supabase_url: str,
    service_key: str,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    """Download all storage objects from Supabase Storage with pagination.

    Iterates through all buckets visible to the service key. If workspace is
    specified, only downloads objects whose paths begin with that workspace prefix.

    Args:
        supabase_url: Base Supabase URL (e.g., https://xxx.supabase.co).
        service_key: Supabase service_role key for unrestricted access.
        workspace: Optional workspace slug to filter objects by path prefix.

    Returns:
        List of object metadata dicts (name, metadata, etc.) from the Storage API.
    """
    base_url = supabase_url.rstrip("/")
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    all_objects: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        # List all buckets first
        buckets_resp = await client.get(
            f"{base_url}/storage/v1/bucket",
            headers=headers,
        )
        buckets_resp.raise_for_status()
        buckets: list[dict[str, Any]] = buckets_resp.json()

        for bucket in buckets:
            bucket_id: str = bucket["id"]
            offset = 0

            while True:
                params: dict[str, Any] = {
                    "limit": _PAGE_SIZE,
                    "offset": offset,
                }
                if workspace:
                    params["prefix"] = workspace

                resp = await client.get(
                    f"{base_url}/storage/v1/object/list/{bucket_id}",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                page: list[dict[str, Any]] = resp.json()

                for obj in page:
                    obj["_bucket"] = bucket_id
                all_objects.extend(page)

                if len(page) < _PAGE_SIZE:
                    break
                offset += _PAGE_SIZE

    return all_objects


async def upload_storage_objects(
    supabase_url: str,
    service_key: str,
    objects: list[dict[str, Any]],
) -> None:
    """Upload storage objects to Supabase Storage.

    Args:
        supabase_url: Base Supabase URL.
        service_key: Supabase service_role key.
        objects: List of object dicts with 'path', 'content', and '_bucket' keys.
    """
    base_url = supabase_url.rstrip("/")
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        for obj in objects:
            bucket_id: str = obj.get("_bucket", "public")
            path: str = obj["path"]
            content: bytes = obj.get("content", b"")

            resp = await client.post(
                f"{base_url}/storage/v1/object/{bucket_id}/{path}",
                headers={**headers, "Content-Type": "application/octet-stream"},
                content=content,
            )
            resp.raise_for_status()
