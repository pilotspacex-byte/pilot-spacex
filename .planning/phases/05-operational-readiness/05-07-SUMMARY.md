---
phase: 05-operational-readiness
plan: 07
subsystem: cli
tags: [python, typer, cli, backup, postgresql, supabase, config, pg_dump, pg_restore]

requires:
  - phase: 05-05
    provides: backup CLI sub-package (pg_backup.py, storage_backup.py, archive.py, encryption.py)

provides:
  - PilotConfig with database_url and supabase_url fields (load/save/env fallback)
  - backup.py correctly wired to use config.database_url for pg_dump/pg_restore
  - backup.py uses config.supabase_url for storage download with api_url fallback
  - database_url guard in create_backup and restore_backup (exit 1 with clear error)
  - CLI command layer tests covering create, missing-database_url, and dry-run restore

affects: [operators running pilot backup create/restore in production]

tech-stack:
  added: []
  patterns:
    - "PilotConfig uses dataclass field(default='') for optional fields — graceful degradation without KeyError"
    - "Env var fallback pattern: config.toml value OR env var OR empty string"
    - "CLI command tests use typer.testing.CliRunner with patch() for all external dependencies"
    - "database_url guard at command entry: fail fast with clear message before any subprocess calls"

key-files:
  created: []
  modified:
    - cli/src/pilot_cli/config.py
    - cli/src/pilot_cli/commands/backup.py
    - cli/src/pilot_cli/commands/login.py
    - cli/tests/test_config.py
    - cli/tests/test_backup.py
    - cli/tests/test_login.py

key-decisions:
  - "database_url and supabase_url use empty string default not KeyError — backup command validates at use time with clearer message"
  - "supabase_url or api_url fallback in storage download — safe degradation for single-deployment operators using api_url as Supabase gateway"
  - "database_url guard placed after PilotConfig.load() not inside PilotConfig — keeps config.py a pure data model, command layer owns validation"
  - "Login prompts database_url/supabase_url with empty string default — operators using env vars do not need to enter values at login time"

patterns-established:
  - "Typer CLI tests: use CliRunner.invoke with patch for PilotConfig.load to inject test configs"
  - "Guard pattern: check empty config field, print clear Rich-formatted message, raise typer.Exit(1)"

requirements-completed: [OPS-05]

duration: 4min
completed: 2026-03-09
---

# Phase 05 Plan 07: Backup CLI database_url Wiring Fix Summary

**Fixed runtime wiring bug: backup.py now passes config.database_url (postgresql://) to pg_dump/pg_restore instead of config.api_url (HTTP URL), with database_url guard and full CLI command layer test coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T01:34:19Z
- **Completed:** 2026-03-09T01:38:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- PilotConfig gains `database_url` and `supabase_url` str fields with empty string defaults and env var fallback (DATABASE_URL, SUPABASE_URL)
- `pilot login` now prompts for PostgreSQL database URL and Supabase project URL after api_key
- `backup.py` passes `config.database_url` to `pg_dump` and `pg_restore`; `config.supabase_url or config.api_url` to `download_storage_objects`
- `create_backup` and `restore_backup` both guard against empty `database_url` with exit code 1 and clear error message
- 8 backup tests (5 existing + 3 new CLI command layer), 106 total CLI tests all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add database_url and supabase_url to PilotConfig; update login to capture them** - `80a777ff` (feat)
2. **Task 2: Fix backup.py URL wiring and add CLI command layer tests** - `e3167dcc` (fix)

_Note: TDD tasks — tests written first (RED), then implementation (GREEN)._

## Files Created/Modified

- `cli/src/pilot_cli/config.py` - Added `database_url` and `supabase_url` fields with defaults, env var fallback in load(), save() writes both
- `cli/src/pilot_cli/commands/backup.py` - Added database_url guards, fixed pg_dump/pg_restore/storage URLs
- `cli/src/pilot_cli/commands/login.py` - Added two new Prompt.ask calls for database_url and supabase_url
- `cli/tests/test_config.py` - 4 new tests: field existence, round-trip, env fallback, empty-when-absent
- `cli/tests/test_backup.py` - 3 new CLI command layer tests using CliRunner
- `cli/tests/test_login.py` - Updated 4-prompt side_effects; added test verifying new fields passed to PilotConfig

## Decisions Made

- `database_url` and `supabase_url` default to empty string (not raise KeyError) — backup command fails at use time with a clearer, more actionable error message
- `supabase_url or api_url` fallback in storage download — safe degradation for single-deployment setups where api_url and Supabase gateway are the same host
- Database URL guard placed in the command layer (backup.py), not in PilotConfig — keeps config as a pure data model; commands own validation semantics
- Login prompts for both new fields with `default=""` — operators who use env vars are not forced to enter values during `pilot login`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — test mocking strategy for `typer.testing.CliRunner` with `patch("pilot_cli.commands.backup.pg_dump")` required the `fake_pg_dump` side_effect to write the dump file to `output_path` (because `create_archive` reads it for SHA-256). This was anticipated and handled correctly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- OPS-05 fully satisfied: `pilot backup create` and `pilot backup restore` are correctly wired at runtime
- Operators must re-run `pilot login` or set `DATABASE_URL`/`SUPABASE_URL` env vars to use backup commands
- All 106 CLI tests pass, no regressions

## Self-Check: PASSED

All 7 files verified present. Commits 80a777ff and e3167dcc confirmed in git log.

---
*Phase: 05-operational-readiness*
*Completed: 2026-03-09*
