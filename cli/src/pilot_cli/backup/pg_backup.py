"""PostgreSQL backup and restore wrappers using pg_dump / pg_restore.

Password is passed via PGPASSWORD environment variable — never in CLI args —
to avoid the password appearing in process listings (ps aux).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def _extract_password(database_url: str) -> str:
    """Extract the password component from a PostgreSQL connection URL."""
    return urlparse(database_url).password or ""


def _strip_password(database_url: str) -> str:
    """Return the database URL with the password removed.

    The password is passed via PGPASSWORD env var instead, so the URL passed
    to pg_dump / pg_restore must not contain it (prevents exposure in ps aux).
    """
    parsed = urlparse(database_url)
    if parsed.password:
        # Rebuild netloc without the password: user@host:port
        userinfo = parsed.username or ""
        host = parsed.hostname or ""
        port_part = f":{parsed.port}" if parsed.port else ""
        netloc = f"{userinfo}@{host}{port_part}" if userinfo else f"{host}{port_part}"
        sanitized = parsed._replace(netloc=netloc)
        return urlunparse(sanitized)
    return database_url


def pg_dump(database_url: str, output_path: Path) -> None:
    """Run pg_dump in custom format, writing output to output_path.

    Password is injected via PGPASSWORD env var, not in the command args,
    to keep credentials out of process listings.

    Args:
        database_url: Full PostgreSQL connection URL including credentials.
        output_path: Destination path for the .dump file (custom format).

    Raises:
        subprocess.CalledProcessError: If pg_dump exits with non-zero status.
    """
    env = {**os.environ, "PGPASSWORD": _extract_password(database_url)}
    subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-password",
            "--file",
            str(output_path),
            _strip_password(database_url),
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def pg_restore(database_url: str, dump_path: Path) -> None:
    """Run pg_restore with --clean --if-exists for idempotent restores.

    Using --clean --if-exists drops and recreates objects, making this
    safe to run against an existing (possibly partial) database.

    Args:
        database_url: Full PostgreSQL connection URL for the target database.
        dump_path: Path to the .dump file produced by pg_dump.

    Raises:
        subprocess.CalledProcessError: If pg_restore exits with non-zero status.
    """
    env = {**os.environ, "PGPASSWORD": _extract_password(database_url)}
    subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-password",
            "--dbname",
            _strip_password(database_url),
            str(dump_path),
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
