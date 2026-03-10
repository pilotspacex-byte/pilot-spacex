---
phase: 05-operational-readiness
plan: "05"
subsystem: cli
tags: [backup, restore, pg_dump, pg_restore, aes-256-gcm, encryption, supabase-storage, typer, rich]

# Dependency graph
requires:
  - phase: 04-ai-governance
    provides: stable platform with working CLI patterns (pilot login, pilot implement)
provides:
  - pilot backup create command: pg_dump + Storage download + .tar.gz archive + AES-256-GCM encryption
  - pilot backup restore command: manifest display + dry-run validation + pg_restore with confirmation guard
  - backup sub-package: pg_backup.py, storage_backup.py, archive.py, encryption.py
  - operator guide: docs/operations/backup-restore.md
affects: [ops-runbooks, disaster-recovery, enterprise-onboarding]

# Tech tracking
tech-stack:
  added: [cryptography>=46.0.5 (AES-256-GCM, PBKDF2HMAC)]
  patterns:
    - TDD (RED/GREEN) — tests written first in test_backup.py, all failed before implementation
    - PGPASSWORD env injection — password stripped from database URL before passing to subprocess
    - PSBC magic bytes — 4-byte header for encrypted file format validation before decryption attempt
    - Pagination loop — offset-based httpx pagination until response.length < page_size

key-files:
  created:
    - cli/src/pilot_cli/backup/__init__.py
    - cli/src/pilot_cli/backup/pg_backup.py
    - cli/src/pilot_cli/backup/storage_backup.py
    - cli/src/pilot_cli/backup/archive.py
    - cli/src/pilot_cli/backup/encryption.py
    - cli/src/pilot_cli/commands/backup.py
    - cli/tests/test_backup.py
    - docs/operations/backup-restore.md
  modified:
    - cli/src/pilot_cli/main.py (add_typer backup_app)
    - cli/pyproject.toml (cryptography dependency)
    - cli/uv.lock

key-decisions:
  - "PGPASSWORD env + URL password-stripping: pg_dump/pg_restore strip the password from the URL before passing it as a CLI arg; password set only via PGPASSWORD env to prevent exposure in ps aux"
  - "PSBC magic bytes header: encrypted files begin with b'PSBC' (Pilot Space Backup Cipher) so decrypt_file() can validate the file type before attempting AESGCM.decrypt()"
  - "AES-256-GCM with PBKDF2-SHA256 (260k iterations): provides authenticated encryption; invalid tag = wrong passphrase or tampering, unambiguous error vs silent corruption"
  - "dry_run=True skips output_dir creation entirely: test asserts output_dir.exists() is False, not just empty"
  - "Pagination fetches buckets first then paginates each bucket: consistent with Supabase Storage REST API shape (/storage/v1/bucket then /storage/v1/object/list/{bucket_id})"

patterns-established:
  - "backup sub-package pattern: pg_backup / storage_backup / archive / encryption as separate pure-function modules with no CLI coupling"
  - "Typer sub-app registration: backup_app = typer.Typer(); app.add_typer(backup_app, name='backup') in main.py"

requirements-completed: [OPS-05]

# Metrics
duration: 28min
completed: 2026-03-08
---

# Phase 05 Plan 05: Backup and Restore CLI Summary

**`pilot backup create` and `pilot backup restore` CLI commands using pg_dump, AES-256-GCM encryption, and Supabase Storage pagination with PGPASSWORD env isolation and dry-run validation**

## Performance

- **Duration:** 28 min
- **Started:** 2026-03-08T16:45:30Z
- **Completed:** 2026-03-08T17:13:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Backup sub-package with four decoupled modules: `pg_backup.py` (subprocess wrappers with PGPASSWORD env), `storage_backup.py` (paginated httpx downloads), `archive.py` (tar.gz packing with manifest.json), `encryption.py` (AES-256-GCM with PBKDF2HMAC-SHA256)
- `pilot backup create`: Rich spinner progress, timestamped archive name, optional `--encrypt` with passphrase prompt, `--workspace` prefix filter
- `pilot backup restore`: manifest display, `--dry-run` validates without DB writes, interactive confirmation guard before `pg_restore`
- 5 unit tests (TDD RED→GREEN): archive creation, dry-run validation, encrypt/decrypt roundtrip, PGPASSWORD env isolation, pagination with 150 total objects across 2 pages
- Operator guide `docs/operations/backup-restore.md` covering prerequisites, create/restore workflows, encryption format spec, cron scheduling, and troubleshooting

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement backup sub-package and unit tests** - `a99f50fb` (feat - TDD)
2. **Task 2: Implement backup CLI commands, register in main.py, write operator guide** - `02dcf38c` (feat)

**Plan metadata:** (docs commit — see below)

_Note: Task 1 is TDD — tests written first (RED), then implementation (GREEN), committed together._

## Files Created/Modified

- `cli/src/pilot_cli/backup/__init__.py` — package marker
- `cli/src/pilot_cli/backup/pg_backup.py` — pg_dump/pg_restore wrappers, PGPASSWORD env injection, URL password stripping
- `cli/src/pilot_cli/backup/storage_backup.py` — paginated httpx Supabase Storage download/upload
- `cli/src/pilot_cli/backup/archive.py` — tar.gz creation with manifest.json, extract_archive with dry_run, read_manifest
- `cli/src/pilot_cli/backup/encryption.py` — AES-256-GCM encrypt/decrypt, PBKDF2HMAC-SHA256 key derivation, PSBC magic bytes
- `cli/src/pilot_cli/commands/backup.py` — Typer backup_app with create and restore commands
- `cli/src/pilot_cli/main.py` — add_typer(backup_app, name="backup")
- `cli/tests/test_backup.py` — 5 unit tests with mocked subprocess and httpx
- `docs/operations/backup-restore.md` — 238-line operator guide
- `cli/pyproject.toml` — cryptography>=46.0.5 added
- `cli/uv.lock` — updated

## Decisions Made

- **PGPASSWORD env + URL stripping**: Test `test_pg_dump_uses_pgpassword_env` caught the original implementation passing the full database URL (with embedded password) as a CLI argument to pg_dump. Fixed by `_strip_password()` which rebuilds the URL without the password component before passing to subprocess. Password flows only via env.
- **PSBC magic bytes**: Encrypted files start with `b"PSBC"` (4 bytes) so `decrypt_file()` can detect wrong file type immediately rather than failing mid-decryption with an opaque error.
- **260,000 PBKDF2 iterations**: NIST-recommended minimum as of 2023 for HMAC-SHA256.
- **dry_run=True skips directory creation entirely**: `output_dir.mkdir()` is only called when `dry_run=False`, making the test assertion (`not output_dir.exists()`) unambiguous.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pg_backup.py was passing password in CLI args to pg_dump**
- **Found during:** Task 1 (TDD GREEN phase — test `test_pg_dump_uses_pgpassword_env` caught it)
- **Issue:** Original implementation passed the full `database_url` (containing `s3cr3t` in the URL) as a positional arg to `pg_dump`, visible in process listings
- **Fix:** Added `_strip_password(database_url)` that rebuilds the URL with username but no password before passing it to subprocess; password set only via `PGPASSWORD` env var
- **Files modified:** `cli/src/pilot_cli/backup/pg_backup.py`
- **Verification:** `test_pg_dump_uses_pgpassword_env` passes — asserts no CLI arg contains the password string
- **Committed in:** `a99f50fb` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - security bug)
**Impact on plan:** Security fix required for production correctness. Password in CLI args would expose credentials via `ps aux` on any multi-user system. No scope creep.

## Issues Encountered

- Test `test_storage_download_paginates` initial mock used positional args but `httpx.AsyncClient.get()` uses keyword args — fixed mock signature to `*args, **kwargs` and adjusted expected call count from 2 to 3 (1 bucket list + 2 object pages).

## User Setup Required

External services require manual operator setup before using `pilot backup`:

- **PostgreSQL client tools**: `brew install libpq` (macOS) or `apt install postgresql-client` (Ubuntu)
- **BACKUP_PASSPHRASE env var**: Required only for `--encrypt` / `.enc` archives
- See `docs/operations/backup-restore.md` for full prerequisites and verification steps

## Next Phase Readiness

- Backup/restore CLI is production-ready for enterprise self-hosted operators
- `pilot backup restore --dry-run` provides non-destructive archive validation
- Operator guide documents scheduling, encryption, and troubleshooting
- Phase 05 continues with remaining operational readiness plans

---
*Phase: 05-operational-readiness*
*Completed: 2026-03-08*
