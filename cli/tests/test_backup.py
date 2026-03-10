"""Unit tests for pilot backup sub-package.

Tests use mocked subprocess (pg_dump), mocked httpx (storage download),
and tmp_path for file-based operations.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

# ── test_create_produces_archive ─────────────────────────────────────────────


def test_create_produces_archive(tmp_path: Path) -> None:
    """create_archive() must produce a .tar.gz containing postgres.dump and
    manifest.json when given a dump file and a list of storage objects."""
    from pilot_cli.backup.archive import create_archive

    # Create a stub dump file
    dump_file = tmp_path / "postgres.dump"
    dump_file.write_bytes(b"fake pg_dump content")

    # Two storage objects: each is a dict with path + content bytes
    storage_objects = [
        {"path": "workspace/file1.png", "content": b"\x89PNG\r\n"},
        {"path": "workspace/file2.pdf", "content": b"%PDF-1.4"},
    ]

    archive_path = tmp_path / "test-backup.tar.gz"
    manifest = create_archive(dump_file, storage_objects, archive_path)

    assert archive_path.exists(), "archive file must be created"

    with tarfile.open(archive_path, "r:gz") as tf:
        members = tf.getnames()
        assert "postgres.dump" in members, "archive must contain postgres.dump"
        assert "manifest.json" in members, "archive must contain manifest.json"

        manifest_bytes = tf.extractfile("manifest.json")
        assert manifest_bytes is not None
        manifest_data = json.loads(manifest_bytes.read())

    assert manifest_data["pg_dump_file"] == "postgres.dump"
    assert manifest_data["storage_objects_count"] == 2
    assert "created_at" in manifest_data
    assert "checksum_sha256" in manifest_data
    assert manifest_data["version"] == "1"

    # Return value must match manifest.json content
    assert manifest == manifest_data


# ── test_dry_run_validates ────────────────────────────────────────────────────


def test_dry_run_validates(tmp_path: Path) -> None:
    """extract_archive(dry_run=True) returns manifest dict without extracting
    files to a directory."""
    from pilot_cli.backup.archive import create_archive, extract_archive

    dump_file = tmp_path / "postgres.dump"
    dump_file.write_bytes(b"fake content")
    archive_path = tmp_path / "backup.tar.gz"
    create_archive(dump_file, [], archive_path)

    output_dir = tmp_path / "extracted"
    manifest = extract_archive(archive_path, output_dir, dry_run=True)

    assert isinstance(manifest, dict), "must return dict"
    assert "pg_dump_file" in manifest
    # dry_run must NOT create output directory
    assert not output_dir.exists(), "output_dir must NOT exist after dry_run"


# ── test_encrypt_decrypt_roundtrip ────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip(tmp_path: Path) -> None:
    """encrypt_file + decrypt_file with same passphrase must produce identical
    content to the original."""
    from pilot_cli.backup.encryption import decrypt_file, encrypt_file

    original_content = b"sensitive backup data \x00\xff\xfe" * 100
    input_path = tmp_path / "original.tar.gz"
    input_path.write_bytes(original_content)

    encrypted_path = tmp_path / "backup.tar.gz.enc"
    decrypted_path = tmp_path / "restored.tar.gz"

    encrypt_file(input_path, encrypted_path, "passphrase123")
    assert encrypted_path.exists()
    # Encrypted must differ from original
    assert encrypted_path.read_bytes() != original_content

    decrypt_file(encrypted_path, decrypted_path, "passphrase123")
    assert decrypted_path.read_bytes() == original_content


# ── test_pg_dump_uses_pgpassword_env ─────────────────────────────────────────


def test_pg_dump_uses_pgpassword_env(tmp_path: Path) -> None:
    """pg_dump() must pass PGPASSWORD in env and must NOT include the password
    in the command arguments."""
    from pilot_cli.backup.pg_backup import pg_dump

    database_url = "postgresql://admin:s3cr3t@localhost:5432/pilotdb"
    output_path = tmp_path / "postgres.dump"

    with patch("pilot_cli.backup.pg_backup.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        pg_dump(database_url, output_path)

    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args

    # env must contain PGPASSWORD (passed as keyword argument)
    env = call_kwargs.kwargs.get("env")
    assert env is not None, "env kwarg must be passed"
    assert env["PGPASSWORD"] == "s3cr3t", "PGPASSWORD must equal the password from URL"

    # Command args must NOT contain the password as a plain argument
    cmd_args = call_kwargs.args[0]
    for arg in cmd_args:
        assert "s3cr3t" not in str(arg), f"password must not appear in CLI arg: {arg!r}"


# ── test_storage_download_paginates ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_download_paginates(tmp_path: Path) -> None:
    """download_storage_objects() must paginate: loop until response length <
    page_size. 100 objects on page 1, 50 on page 2 → 150 total objects."""
    from pilot_cli.backup.storage_backup import download_storage_objects

    page1 = [{"name": f"file_{i}.png", "metadata": {}} for i in range(100)]
    page2 = [{"name": f"file_{i}.png", "metadata": {}} for i in range(100, 150)]

    call_count = 0

    async def fake_list(*args: object, **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        response = MagicMock()
        response.raise_for_status = MagicMock()
        if call_count == 1:
            # First call: list buckets endpoint → return one bucket
            response.json.return_value = [{"id": "public", "name": "public"}]
        elif call_count == 2:
            # Second call: list objects page 1 → 100 objects
            response.json.return_value = page1
        else:
            # Third call: list objects page 2 → 50 objects
            response.json.return_value = page2
        return response

    with patch("pilot_cli.backup.storage_backup.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=fake_list)

        objects = await download_storage_objects(
            supabase_url="https://supabase.example.com",
            service_key="test-service-key",
            workspace=None,
        )

    assert len(objects) == 150, f"expected 150 objects, got {len(objects)}"
    # 1 call for bucket listing + 2 paginated object calls = 3 total
    # 1 bucket list + 2 paginated object calls = 3 total HTTP calls
    assert call_count == 3, (
        f"expected 3 HTTP calls (1 bucket list + 2 pages), got {call_count}"
    )


# ── CLI command layer tests ───────────────────────────────────────────────────

runner = CliRunner()

_MOCK_CONFIG = MagicMock(
    database_url="postgresql://localhost/test",
    supabase_url="https://sb.example.com",
    api_url="https://api.example.com",
    api_key="key",
    workspace_slug="ws",
)


def _make_mock_config() -> MagicMock:
    """Return a fresh MagicMock with all PilotConfig fields set."""
    return MagicMock(
        database_url="postgresql://localhost/test",
        supabase_url="https://sb.example.com",
        api_url="https://api.example.com",
        api_key="key",
        workspace_slug="ws",
    )


def test_create_backup_command(tmp_path: Path) -> None:
    """create_backup command: mocked config with valid database_url → exit 0.

    Mocks pg_dump, download_storage_objects, and create_archive so the command
    completes without hitting any real external systems.
    """
    from pilot_cli.commands.backup import backup_app

    dump_path_holder: list[Path] = []

    def fake_pg_dump(url: str, output_path: Path) -> None:
        output_path.write_bytes(b"fake pg_dump content")
        dump_path_holder.append(output_path)

    def fake_create_archive(
        dump_path: Path,
        objects: list,  # type: ignore[type-arg]
        archive_path: Path,
    ) -> dict:  # type: ignore[type-arg]
        archive_path.write_bytes(b"fake archive content")
        import json as _json
        return {"pg_dump_file": "postgres.dump", "version": "1", "created_at": "now",
                "storage_objects_count": 0, "checksum_sha256": "abc123"}

    with (
        patch("pilot_cli.commands.backup.PilotConfig.load", return_value=_make_mock_config()),
        patch("pilot_cli.commands.backup.pg_dump", side_effect=fake_pg_dump),
        patch(
            "pilot_cli.commands.backup.download_storage_objects",
            new=AsyncMock(return_value=[]),
        ),
        patch("pilot_cli.commands.backup.create_archive", side_effect=fake_create_archive),
    ):
        result = runner.invoke(backup_app, ["create", "--output", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Backup complete" in result.output


def test_create_backup_missing_database_url(tmp_path: Path) -> None:
    """create_backup command exits 1 with clear error when database_url is empty."""
    from pilot_cli.commands.backup import backup_app

    empty_db_config = _make_mock_config()
    empty_db_config.database_url = ""

    with patch("pilot_cli.commands.backup.PilotConfig.load", return_value=empty_db_config):
        result = runner.invoke(backup_app, ["create", "--output", str(tmp_path)])

    assert result.exit_code == 1
    assert "database_url not configured" in result.output


def test_restore_backup_dry_run_command(tmp_path: Path) -> None:
    """restore_backup --dry-run validates archive without loading config → exit 0.

    Creates a real archive, then invokes restore with --dry-run.
    No PilotConfig mock needed because dry_run returns before loading config.
    """
    from pilot_cli.backup.archive import create_archive
    from pilot_cli.commands.backup import backup_app

    # Create a real archive so the command can validate it
    dump_file = tmp_path / "postgres.dump"
    dump_file.write_bytes(b"fake pg_dump content")
    archive_path = tmp_path / "test-backup.tar.gz"
    create_archive(dump_file, [], archive_path)

    result = runner.invoke(backup_app, ["restore", str(archive_path), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Dry run complete" in result.output
