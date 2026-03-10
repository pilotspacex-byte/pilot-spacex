"""Backup archive creation and extraction.

Archive format: .tar.gz containing:
  - postgres.dump        — pg_dump custom-format output
  - manifest.json        — metadata: version, created_at, checksum, object count
  - storage/             — directory tree of downloaded storage objects
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

_MANIFEST_FILENAME = "manifest.json"
_DUMP_FILENAME = "postgres.dump"
_ARCHIVE_VERSION = "1"


def _sha256_file(path: Path) -> str:
    """Compute hex SHA-256 of file at path."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create_archive(
    dump_path: Path,
    storage_objects: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    """Pack postgres.dump and storage objects into a .tar.gz archive.

    Adds a manifest.json with metadata including SHA-256 checksum of the dump.

    Args:
        dump_path: Path to the pg_dump output file.
        storage_objects: List of object dicts with 'path' and 'content' keys.
        output_path: Destination path for the .tar.gz archive.

    Returns:
        The manifest dict written into manifest.json.
    """
    checksum = _sha256_file(dump_path)
    created_at = datetime.datetime.now(datetime.UTC).isoformat()

    manifest: dict[str, Any] = {
        "version": _ARCHIVE_VERSION,
        "created_at": created_at,
        "pg_dump_file": _DUMP_FILENAME,
        "storage_objects_count": len(storage_objects),
        "checksum_sha256": checksum,
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()

    with tarfile.open(output_path, "w:gz") as tf:
        # Add postgres.dump
        tf.add(dump_path, arcname=_DUMP_FILENAME)

        # Add manifest.json
        info = tarfile.TarInfo(name=_MANIFEST_FILENAME)
        info.size = len(manifest_bytes)
        tf.addfile(info, io.BytesIO(manifest_bytes))

        # Add storage objects under storage/ prefix
        for obj in storage_objects:
            obj_path: str = obj.get("path", obj.get("name", "unknown"))
            content: bytes = obj.get("content", b"")
            arcname = f"storage/{obj_path}"
            info = tarfile.TarInfo(name=arcname)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))

    return manifest


def extract_archive(
    archive_path: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Extract a backup archive, returning the manifest dict.

    In dry_run mode, reads and validates the manifest without writing any
    files to output_dir.

    Args:
        archive_path: Path to the .tar.gz archive.
        output_dir: Directory to extract files into (not used in dry_run).
        dry_run: If True, validate only — do not extract files.

    Returns:
        The manifest dict from manifest.json inside the archive.

    Raises:
        ValueError: If manifest.json is missing from the archive.
    """
    manifest = read_manifest(archive_path)

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tf:
            resolved_output = output_dir.resolve()
            for member in tf.getmembers():
                member_path = (output_dir / member.name).resolve()
                if not str(member_path).startswith(str(resolved_output) + "/"):
                    raise ValueError(
                        "Archive member would extract outside target directory"
                    )
                tf.extract(member, output_dir)

    return manifest


def read_manifest(archive_path: Path) -> dict[str, Any]:
    """Read and parse manifest.json from a backup archive without full extraction.

    Args:
        archive_path: Path to the .tar.gz archive.

    Returns:
        Parsed manifest dict.

    Raises:
        ValueError: If manifest.json is not found in the archive.
        KeyError: If the archive does not contain manifest.json.
    """
    with tarfile.open(archive_path, "r:gz") as tf:
        try:
            member = tf.getmember(_MANIFEST_FILENAME)
        except KeyError as exc:
            raise ValueError(
                f"Invalid backup archive — {_MANIFEST_FILENAME} not found "
                f"in {archive_path}"
            ) from exc
        f = tf.extractfile(member)
        if f is None:
            raise ValueError(
                f"{_MANIFEST_FILENAME} is not a regular file in the archive"
            )
        return json.loads(f.read())
