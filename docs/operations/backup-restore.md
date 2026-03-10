# Backup and Restore

Enterprise self-hosted operators can back up all workspace data (PostgreSQL +
Supabase Storage) and restore it without writing custom scripts.

## Prerequisites

### PostgreSQL Client Tools

`pg_dump` and `pg_restore` must be on your PATH.

| Platform | Install Command |
|----------|----------------|
| macOS | `brew install libpq && brew link --force libpq` |
| Ubuntu / Debian | `sudo apt install postgresql-client` |
| RHEL / Amazon Linux | `sudo yum install postgresql` |

Verify: `pg_dump --version`

### CLI Authentication

The `pilot backup` commands read connection details from `~/.pilot/config.toml`.
If you have not authenticated yet:

```bash
pilot login
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `BACKUP_PASSPHRASE` | Only for `--encrypt` / `.enc` archives | AES-256-GCM passphrase |

---

## Create a Backup

### Full backup (all workspaces)

```bash
pilot backup create
```

Produces: `./backups/pilot-space-backup-20240315T143022Z.tar.gz`

### Backup a specific workspace

```bash
pilot backup create --workspace my-workspace-slug
```

Only downloads Storage objects whose paths begin with `my-workspace-slug/`.

### Specify output directory

```bash
pilot backup create --output /var/backups/pilot-space
```

The directory is created automatically if it does not exist.

### Encrypted backup

```bash
pilot backup create --encrypt
```

You will be prompted for a passphrase (confirmed twice). The archive is saved
as `.tar.gz.enc`. To avoid the interactive prompt, set `BACKUP_PASSPHRASE`:

```bash
BACKUP_PASSPHRASE="correct horse battery staple" pilot backup create --encrypt
```

---

## Restore from Backup

### Validate an archive (dry run)

Inspect the manifest and verify the archive is intact without modifying the
database:

```bash
pilot backup restore --dry-run ./backups/pilot-space-backup-20240315T143022Z.tar.gz
```

Example output:

```
Archive manifest:
  Created:         2024-03-15T14:30:22.123456+00:00
  PostgreSQL dump: postgres.dump
  Storage objects: 247
  Checksum:        a3f9b2d1c0e4...

Dry run complete — archive is valid
```

### Full restore

```bash
pilot backup restore ./backups/pilot-space-backup-20240315T143022Z.tar.gz
```

The command displays the manifest, then prompts for confirmation before
overwriting the database. Answer `y` to proceed.

### Restore from encrypted archive

```bash
pilot backup restore ./backups/pilot-space-backup-20240315T143022Z.tar.gz.enc
```

You will be prompted for the decryption passphrase, or set `BACKUP_PASSPHRASE`.

---

## Encrypted Backups

Encryption uses **AES-256-GCM** with **PBKDF2-SHA256** key derivation
(260,000 iterations, 16-byte random salt, 12-byte random nonce).

### Binary format of `.tar.gz.enc` files

```
[0:4]   Magic bytes  PSBC  (Pilot Space Backup Cipher)
[4:20]  16-byte random salt
[20:32] 12-byte random nonce
[32:]   AES-256-GCM ciphertext + 16-byte authentication tag
```

The authentication tag guarantees both confidentiality and integrity — a
tampered file will fail decryption with an `InvalidTag` error.

### Passphrase management

- Store the passphrase in a secrets manager (AWS Secrets Manager, HashiCorp
  Vault, 1Password Teams).
- Do not store the passphrase in the same location as the backup archive.
- Losing the passphrase makes the encrypted backup unrecoverable.

---

## Scheduled Backups (cron)

Daily backup at 02:00, 7-day retention:

```cron
0 2 * * * BACKUP_PASSPHRASE="$(cat /run/secrets/backup_passphrase)" \
  /usr/local/bin/pilot backup create \
  --encrypt \
  --output /var/backups/pilot-space \
  >> /var/log/pilot-backup.log 2>&1

# Prune archives older than 7 days
0 3 * * * find /var/backups/pilot-space -name "*.tar.gz*" -mtime +7 -delete
```

Replace `/run/secrets/backup_passphrase` with your secrets manager's
retrieval command.

---

## Archive Format

Every `.tar.gz` archive contains:

| Path | Description |
|------|-------------|
| `postgres.dump` | pg_dump custom-format database snapshot |
| `manifest.json` | Archive metadata (see below) |
| `storage/<bucket>/<path>` | Supabase Storage objects |

### manifest.json schema

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Archive format version (`"1"`) |
| `created_at` | ISO 8601 | Timestamp when backup was created |
| `pg_dump_file` | string | Name of the dump file inside the archive |
| `storage_objects_count` | integer | Number of storage objects included |
| `checksum_sha256` | string | SHA-256 hex digest of `postgres.dump` |

Example:

```json
{
  "version": "1",
  "created_at": "2024-03-15T14:30:22.123456+00:00",
  "pg_dump_file": "postgres.dump",
  "storage_objects_count": 247,
  "checksum_sha256": "a3f9b2d1c0e4..."
}
```

---

## Troubleshooting

### `pg_dump: command not found`

PostgreSQL client tools are not installed or not on your PATH. Install using
the commands in [Prerequisites](#prerequisites) above.

### `pg_dump failed: connection refused`

The database host is not reachable from the machine running `pilot backup`. Check:

1. The `DATABASE_URL` in `~/.pilot/config.toml` points to a reachable host.
2. Firewall rules allow your IP to connect on port 5432.
3. `pg_isready -d "$DATABASE_URL"` returns "accepting connections".

### `Decryption failed: Not a valid Pilot Space encrypted backup`

The file is not a valid `.tar.gz.enc` archive. Possible causes:

- Wrong file passed (the plain `.tar.gz` was passed instead of `.enc`).
- The file was corrupted in transit. Verify the checksum of the file you
  downloaded.

### `Decryption failed: InvalidTag`

The passphrase is incorrect, or the file was tampered with after encryption.
There is no way to recover data with the wrong passphrase.

### Partial restore / restore interrupted

`pg_restore` uses `--clean --if-exists` which drops and recreates objects.
If interrupted, the database is in a partially restored state. Re-run
`pilot backup restore` with the same archive to complete the restore.

### Out-of-disk space during restore

The restore extracts the full archive to a temporary directory before calling
`pg_restore`. Ensure the system's `/tmp` (or `TMPDIR`) has at least as much
free space as the uncompressed archive size.
