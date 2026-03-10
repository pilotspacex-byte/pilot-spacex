"""pilot backup — create and restore workspace backup archives.

Produces .tar.gz archives containing a PostgreSQL custom-format dump and
Supabase Storage objects. Supports AES-256-GCM encryption via --encrypt.
"""

from __future__ import annotations

import datetime
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pilot_cli.backup.archive import create_archive, extract_archive, read_manifest
from pilot_cli.backup.encryption import decrypt_file, encrypt_file
from pilot_cli.backup.pg_backup import pg_dump, pg_restore
from pilot_cli.backup.storage_backup import download_storage_objects
from pilot_cli.config import PilotConfig

backup_app = typer.Typer(name="backup", help="Backup and restore all workspace data.")
console = Console()


@backup_app.command("create")
def create_backup(
    output: Path = typer.Option(
        Path("./backups"),
        "--output",
        "-o",
        help="Output directory for the backup archive.",
    ),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        help="Backup specific workspace slug prefix (default: all).",
    ),
    encrypt: bool = typer.Option(
        False,
        "--encrypt",
        help="Encrypt archive with AES-256-GCM.",
    ),
    passphrase: str | None = typer.Option(
        None,
        "--passphrase",
        envvar="BACKUP_PASSPHRASE",
        help="Encryption passphrase (or set BACKUP_PASSPHRASE env var).",
    ),
) -> None:
    """Create a backup archive of PostgreSQL and Supabase Storage.

    Produces a timestamped .tar.gz (or .tar.gz.enc if --encrypt) archive
    in the output directory containing:

    - postgres.dump — pg_dump custom-format database snapshot
    - manifest.json — metadata with SHA-256 checksum and object count
    - storage/      — Supabase Storage objects
    """
    try:
        config = PilotConfig.load()
    except FileNotFoundError as e:
        console.print("[red]Not logged in.[/red] Run [bold]pilot login[/bold] first.")
        raise typer.Exit(1) from e

    if not config.database_url:
        console.print(
            "[red]database_url not configured.[/red] "
            "Set DATABASE_URL env var or re-run [bold]pilot login[/bold]."
        )
        raise typer.Exit(1)

    output.mkdir(parents=True, exist_ok=True)

    if encrypt and not passphrase:
        passphrase = typer.prompt(
            "Encryption passphrase",
            hide_input=True,
            confirmation_prompt=True,
        )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Dumping PostgreSQL...", total=None)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dump_path = tmp_path / "postgres.dump"

            # Step 1: pg_dump
            try:
                pg_dump(config.database_url, dump_path)
            except Exception as e:
                console.print(f"[red]pg_dump failed:[/red] {e}")
                raise typer.Exit(1) from e
            progress.update(task, description="PostgreSQL dump complete")

            # Step 2: Download storage objects
            progress.update(task, description="Downloading Supabase Storage objects...")
            import asyncio

            try:
                objects = asyncio.run(
                    download_storage_objects(
                        supabase_url=config.supabase_url or config.api_url,
                        service_key=config.api_key,
                        workspace=workspace,
                    )
                )
            except Exception as e:
                console.print(f"[red]Storage download failed:[/red] {e}")
                raise typer.Exit(1) from e
            progress.update(
                task,
                description=f"Downloaded {len(objects)} storage objects",
            )

            # Step 3: Create archive
            progress.update(task, description="Creating archive...")
            timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
            archive_name = f"pilot-space-backup-{timestamp}.tar.gz"
            archive_path = output / archive_name
            create_archive(dump_path, objects, archive_path)

            # Step 4: Encrypt if requested
            if encrypt and passphrase:
                progress.update(task, description="Encrypting archive...")
                encrypted_path = archive_path.with_suffix("").with_suffix(
                    ".tar.gz.enc"
                )
                encrypt_file(archive_path, encrypted_path, passphrase)
                archive_path.unlink()
                archive_path = encrypted_path

    console.print(f"[green]Backup complete:[/green] {archive_path}")


@backup_app.command("restore")
def restore_backup(
    archive: Path = typer.Argument(
        ...,
        help="Path to backup archive (.tar.gz or .tar.gz.enc).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate archive contents without writing to the database.",
    ),
    passphrase: str | None = typer.Option(
        None,
        "--passphrase",
        envvar="BACKUP_PASSPHRASE",
        help="Decryption passphrase for encrypted archives.",
    ),
) -> None:
    """Restore workspace data from a backup archive.

    Displays archive metadata and requires interactive confirmation before
    overwriting the target database. Use --dry-run to validate only.
    """
    if not archive.exists():
        console.print(f"[red]Archive not found:[/red] {archive}")
        raise typer.Exit(1)

    # Decrypt if .enc extension
    actual_archive = archive
    tmp_dir_handle: tempfile.TemporaryDirectory | None = None  # type: ignore[type-arg]

    if archive.suffix == ".enc":
        if not passphrase:
            passphrase = typer.prompt("Decryption passphrase", hide_input=True)
        tmp_dir_handle = tempfile.TemporaryDirectory()
        decrypted_path = Path(tmp_dir_handle.name) / "decrypted.tar.gz"
        try:
            decrypt_file(archive, decrypted_path, passphrase)
        except Exception as e:
            console.print(f"[red]Decryption failed:[/red] {e}")
            tmp_dir_handle.cleanup()
            raise typer.Exit(1) from e
        actual_archive = decrypted_path

    try:
        manifest = read_manifest(actual_archive)
    except (ValueError, KeyError) as e:
        console.print(f"[red]Invalid archive:[/red] {e}")
        if tmp_dir_handle:
            tmp_dir_handle.cleanup()
        raise typer.Exit(1) from e

    console.print("[bold]Archive manifest:[/bold]")
    console.print(f"  Created:         {manifest.get('created_at', 'unknown')}")
    console.print(f"  PostgreSQL dump: {manifest.get('pg_dump_file', 'unknown')}")
    console.print(f"  Storage objects: {manifest.get('storage_objects_count', 0)}")
    checksum = str(manifest.get("checksum_sha256", "unknown"))[:16]
    console.print(f"  Checksum:        {checksum}...")

    if dry_run:
        console.print("\n[green]Dry run complete — archive is valid[/green]")
        if tmp_dir_handle:
            tmp_dir_handle.cleanup()
        return

    try:
        config = PilotConfig.load()
    except FileNotFoundError as e:
        console.print("[red]Not logged in.[/red] Run [bold]pilot login[/bold] first.")
        if tmp_dir_handle:
            tmp_dir_handle.cleanup()
        raise typer.Exit(1) from e

    if not config.database_url:
        console.print(
            "[red]database_url not configured.[/red] "
            "Set DATABASE_URL env var or re-run [bold]pilot login[/bold]."
        )
        if tmp_dir_handle:
            tmp_dir_handle.cleanup()
        raise typer.Exit(1)

    console.print(f"\n[yellow]Target:[/yellow] {config.database_url}")
    confirmed = typer.confirm(
        "\nThis will overwrite the target database. Continue?",
        default=False,
    )
    if not confirmed:
        console.print("[dim]Restore cancelled.[/dim]")
        if tmp_dir_handle:
            tmp_dir_handle.cleanup()
        raise typer.Exit(0)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        extract_archive(actual_archive, tmp_path)
        dump_file = manifest.get("pg_dump_file", "postgres.dump")
        dump_path = tmp_path / dump_file
        try:
            pg_restore(config.database_url, dump_path)
        except Exception as e:
            console.print(f"[red]pg_restore failed:[/red] {e}")
            if tmp_dir_handle:
                tmp_dir_handle.cleanup()
            raise typer.Exit(1) from e

    if tmp_dir_handle:
        tmp_dir_handle.cleanup()

    console.print("[green]Restore complete[/green]")
