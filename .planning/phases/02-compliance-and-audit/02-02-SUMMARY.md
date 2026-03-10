---
phase: 02-compliance-and-audit
plan: "02"
subsystem: database
tags: [audit-log, repository, cursor-pagination, sqlalchemy, tdd]

# Dependency graph
requires:
  - phase: 02-compliance-and-audit plan 01
    provides: AuditLog model, ActorType enum, migration 065

provides:
  - AuditLogRepository with create() and list_filtered() (cursor-based pagination)
  - compute_diff() helper for before/after payload generation
  - write_audit_nonfatal() convenience wrapper for non-fatal audit writes
  - Audit instrumentation in all resource-mutating services (issues, notes, cycles, workspace_members, custom_roles)

affects:
  - 02-03 (audit query API — uses AuditLogRepository.list_filtered)
  - 02-04 (AI audit hook — uses AuditLogRepository.create with ActorType.AI)
  - 02-05 (retention/purge — extends AuditLogRepository)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Standalone repository (not extending BaseRepository) for immutable records to avoid inheriting soft-delete methods
    - Keyset cursor pagination using base64(JSON{ts, id}) for stable DESC ordering
    - Non-fatal audit writes — all service-layer audit calls wrapped in try/except, never interrupt primary write path
    - write_audit_nonfatal() module-level helper to reduce audit boilerplate in service layer
    - TDD RED→GREEN cycle with pytest + aiosqlite in-memory SQLite

key-files:
  created:
    - backend/src/pilot_space/infrastructure/database/repositories/audit_log_repository.py
  modified:
    - backend/src/pilot_space/infrastructure/database/repositories/__init__.py
    - backend/src/pilot_space/application/services/issue/create_issue_service.py
    - backend/src/pilot_space/application/services/issue/update_issue_service.py
    - backend/src/pilot_space/application/services/issue/delete_issue_service.py
    - backend/src/pilot_space/application/services/note/create_note_service.py
    - backend/src/pilot_space/application/services/note/update_note_service.py
    - backend/src/pilot_space/application/services/note/delete_note_service.py
    - backend/src/pilot_space/application/services/cycle/create_cycle_service.py
    - backend/src/pilot_space/application/services/cycle/update_cycle_service.py
    - backend/src/pilot_space/application/services/cycle/add_issue_to_cycle_service.py
    - backend/src/pilot_space/application/services/rbac_service.py
    - backend/src/pilot_space/application/services/workspace_member.py
    - backend/tests/audit/test_audit_hook.py

key-decisions:
  - "AuditLogRepository is standalone (not extending BaseRepository) to prevent inheriting soft-delete methods on immutable audit records"
  - "Cursor pagination uses keyset (created_at DESC, id DESC) with base64-encoded JSON cursor for O(1) page seeks"
  - "All service audit writes are non-fatal: wrapped in try/except, failures logged as WARNING only"
  - "write_audit_nonfatal() added as module-level function to reduce boilerplate; accepts AuditLogRepository | None for easy opt-in"
  - "delete_note_service.py drops Activity tracking entirely — Activity.issue_id is a non-nullable FK; notes cannot use the Activity model"

patterns-established:
  - "Non-fatal audit pattern: if self._audit_repo is not None: try: await self._audit_repo.create(...) except Exception as exc: logger.warning(...)"
  - "Cursor encoding: base64(json.dumps({'ts': ts.isoformat(), 'id': str(uuid)})) for opaque pagination tokens"
  - "Service constructor accepts audit_log_repository: AuditLogRepository | None = None for backward-compatible opt-in"

requirements-completed: [AUDIT-01, AUDIT-06]

# Metrics
duration: ~90min
completed: 2026-03-08
---

# Phase 2 Plan 02: AuditLogRepository and Service Instrumentation Summary

**Standalone AuditLogRepository with cursor-paginated reads, plus non-fatal audit instrumentation across all 5 resource-mutating service families (issues, notes, cycles, workspace_members, custom_roles)**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-03-07T (previous session)
- **Completed:** 2026-03-08T02:03:38Z
- **Tasks:** 2 of 2
- **Files modified:** 14

## Accomplishments

- Standalone `AuditLogRepository` with `create()` (all keyword-arg, non-nullable insert) and `list_filtered()` (keyset cursor pagination, 7 filter params, page_size capped at 500)
- `compute_diff()` module-level helper producing `{before: {changed_fields}, after: {changed_fields}}`
- `write_audit_nonfatal()` convenience wrapper; handles `audit_repo=None` gracefully
- 20 tests passing (TDD RED→GREEN) covering repository create, list_filtered edge cases, cursor encoding, and all service-layer audit writes
- All 5 service families instrumented with 11 distinct action strings

## Task Commits

1. **Task 1: AuditLogRepository (TDD RED→GREEN)** - `f2000c86` (feat)
2. **Task 2: Service audit instrumentation** - `666008ae` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified

- `backend/src/pilot_space/infrastructure/database/repositories/audit_log_repository.py` - New standalone repository; `AuditLogRepository`, `AuditLogPage`, `compute_diff`, `write_audit_nonfatal`
- `backend/src/pilot_space/infrastructure/database/repositories/__init__.py` - Added new exports
- `backend/src/pilot_space/application/services/issue/create_issue_service.py` - `issue.create` audit write
- `backend/src/pilot_space/application/services/issue/update_issue_service.py` - `issue.update` audit write (only when fields changed)
- `backend/src/pilot_space/application/services/issue/delete_issue_service.py` - `issue.delete` audit write + Activity constructor bug fix
- `backend/src/pilot_space/application/services/note/create_note_service.py` - `note.create` audit write
- `backend/src/pilot_space/application/services/note/update_note_service.py` - `note.update` audit write; added `actor_id` to payload
- `backend/src/pilot_space/application/services/note/delete_note_service.py` - `note.delete` audit write; removed broken Activity tracking
- `backend/src/pilot_space/application/services/cycle/create_cycle_service.py` - `cycle.create` audit write; added `actor_id` to payload
- `backend/src/pilot_space/application/services/cycle/update_cycle_service.py` - `cycle.update` audit write
- `backend/src/pilot_space/application/services/cycle/add_issue_to_cycle_service.py` - `cycle.issue_added` / `cycle.issue_removed` audit writes
- `backend/src/pilot_space/application/services/rbac_service.py` - `custom_role.create/update/delete` audit writes; added `actor_id` param
- `backend/src/pilot_space/application/services/workspace_member.py` - `member.role_changed` / `member.removed` audit writes; refactored to use `write_audit_nonfatal`

## Decisions Made

- `AuditLogRepository` does not extend `BaseRepository` — avoids inheriting `soft_delete()`, `get_all()` with `is_deleted` filtering, and `update()` which are inappropriate for immutable records
- Cursor uses `(created_at DESC, id DESC)` keyset: when cursor present, query fetches rows where `created_at < ts OR (created_at == ts AND id < cursor_id)` — provides O(1) page seeks vs OFFSET
- `write_audit_nonfatal()` uses `ActorType.USER` as the default; AI-actor writes require direct `create()` call with `actor_type=ActorType.AI`
- `delete_note_service.py` Activity tracking removed: `Activity.issue_id` is a non-nullable FK to the `issues` table, making it structurally incompatible with notes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Activity constructor in delete_issue_service.py**
- **Found during:** Task 2 (service instrumentation)
- **Issue:** `Activity(verb=ActivityType.DELETED, object_type="issue", object_id=..., metadata=...)` — wrong field names; Activity model uses `activity_type`, `issue_id`, `activity_metadata`
- **Fix:** Corrected to `Activity(activity_type=ActivityType.DELETED, issue_id=issue.id, activity_metadata={...})`
- **Files modified:** `backend/src/pilot_space/application/services/issue/delete_issue_service.py`
- **Verification:** Tests pass; Activity row is created with correct FK
- **Committed in:** `666008ae`

**2. [Rule 1 - Bug] Removed broken Activity tracking from delete_note_service.py**
- **Found during:** Task 2 (service instrumentation)
- **Issue:** `delete_note_service.py` attempted to create `Activity(issue_id=...)` but notes don't have an associated issue; `Activity.issue_id` is a non-nullable FK to `issues`, causing IntegrityError on note deletions
- **Fix:** Removed Activity tracking entirely from delete_note_service; replaced with audit_log write only
- **Files modified:** `backend/src/pilot_space/application/services/note/delete_note_service.py`
- **Verification:** Service no longer depends on `activity_repository`; audit log write confirmed in tests
- **Committed in:** `666008ae`

**3. [Rule 3 - Blocking] workspace_member.py exceeded 700-line pre-commit limit**
- **Found during:** Task 2 (commit attempt)
- **Issue:** Audit instrumentation pushed `workspace_member.py` to 757 lines, triggering pre-commit `check-file-size` hook failure
- **Fix:** Moved inline `write_audit_nonfatal` imports to top-level; trimmed 2 verbose multi-line docstrings to one-liners
- **Files modified:** `backend/src/pilot_space/application/services/workspace_member.py`
- **Verification:** 694 lines, pre-commit passes
- **Committed in:** `666008ae`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. Bug fixes were pre-existing and discovered during instrumentation. File size fix was triggered by the new code addition. No scope creep.

## Issues Encountered

- Pre-commit ruff-format loop required re-staging files on first commit attempt (import ordering)
- pyright `reportUnusedImport` for `write_audit_nonfatal` in `__init__.py` — resolved by adding to `__all__`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `AuditLogRepository.list_filtered()` ready for Plan 02-03 (audit query API endpoint)
- `AuditLogRepository.create()` ready for Plan 02-04 (AI audit hook with `actor_type=ActorType.AI`)
- `AuditLogRepository` ready for Plan 02-05 (retention/purge — add `purge_expired()` method)
- All resource mutations now emit audit entries; 29 xfailed tests from plans 02-03 through 02-05 remain as pending work

---
*Phase: 02-compliance-and-audit*
*Completed: 2026-03-08*
