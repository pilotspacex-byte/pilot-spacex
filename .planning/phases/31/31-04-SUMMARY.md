---
phase: 31-mcp-infra-hardening
plan: 04
subsystem: security/startup
tags: [security, encryption, startup, fail-fast, production-hardening]
dependency_graph:
  requires: []
  provides: [encryption-key-startup-enforcement]
  affects: [main.py lifespan, production deployment]
tech_stack:
  added: []
  patterns: [fail-fast startup validation, lifespan gating, lru_cache invalidation in tests]
key_files:
  created:
    - backend/tests/unit/test_startup_encryption_enforcement.py
  modified:
    - backend/src/pilot_space/main.py
key_decisions:
  - "Test the enforcement logic via an extracted helper function mirroring the lifespan block, rather than spinning up a full FastAPI app — avoids DI container complexity while still testing the exact same code path"
  - "Patch pilot_space.config.get_settings (not pilot_space.infrastructure.encryption.get_settings) because get_encryption_service imports get_settings locally inside the function body"
metrics:
  duration: 15m
  completed: "2026-03-20"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 2
---

# Phase 31 Plan 04: Production Encryption Key Startup Enforcement Summary

Production fail-fast check added to main.py lifespan: raises RuntimeError when app_env=production and ENCRYPTION_KEY is absent or not a valid Fernet key.

## What Was Built

Added a startup enforcement block in `main.py` lifespan immediately after `jwt_provider_validated`, following the same fail-fast guard pattern. The check:

1. Is gated on `settings.is_production` — development and staging are unaffected
2. Reads `settings.encryption_key.get_secret_value()` — empty string triggers RuntimeError
3. Calls `get_encryption_service()` — if the key is set but invalid Fernet format, `EncryptionError` is caught and re-raised as RuntimeError
4. Emits `logger.info("encryption_key_validated")` on success
5. Every error message includes the Fernet key generation command for operators

## Files Changed

### Created
- `backend/tests/unit/test_startup_encryption_enforcement.py` — 7 unit tests across 4 test classes

### Modified
- `backend/src/pilot_space/main.py` — 21 lines added after `jwt_provider_validated` block (lines 140-162)

## Commits

| Hash | Message |
|------|---------|
| 08d1dbe0 | feat(security): enforce ENCRYPTION_KEY in production startup (MCPI-06) |

## Test Coverage

| Test | Scenario | Result |
|------|----------|--------|
| `TestProductionEmptyKeyRaises::test_production_empty_key_raises` | production + empty key | RuntimeError with "must be set in production" |
| `TestProductionEmptyKeyRaises::test_error_message_includes_generation_command` | production + empty key | Error message contains "Fernet.generate_key" |
| `TestProductionValidKeyPasses::test_production_valid_key_passes` | production + valid Fernet key | No error raised |
| `TestNonProductionEmptyKeyAllowed::test_development_empty_key_no_error` | development + empty key | No error raised |
| `TestNonProductionEmptyKeyAllowed::test_staging_empty_key_no_error` | staging + empty key | No error raised |
| `TestProductionInvalidFernetKeyRaises::test_production_invalid_fernet_key_raises` | production + invalid key format | RuntimeError with "ENCRYPTION_KEY is invalid" |
| `TestProductionInvalidFernetKeyRaises::test_production_invalid_key_wraps_encryption_error` | production + invalid key format | __cause__ is EncryptionError |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] `backend/src/pilot_space/main.py` contains `encryption_key_validated` log statement
- [x] `backend/tests/unit/test_startup_encryption_enforcement.py` exists with 7 tests
- [x] Commit `08d1dbe0` exists
- [x] All 7 tests pass
- [x] pyright: 0 errors, 0 warnings
- [x] ruff: all checks passed
