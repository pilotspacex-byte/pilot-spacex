---
phase: 31-storage-backend
plan: 03
subsystem: api
tags: [fastapi, artifacts, dependency-injector, tdd, supabase-storage]

# Dependency graph
requires:
  - phase: 31-02
    provides: ArtifactUploadService, ArtifactRepository, ArtifactResponse schemas — service layer consumed by this router
  - phase: 31-01
    provides: Artifact SQLAlchemy model and Alembic migration 090 — ORM layer consumed by repository
provides:
  - project_artifacts FastAPI router with POST/GET/GET-url/DELETE at /workspaces/{ws_id}/projects/{project_id}/artifacts
  - ArtifactRepository registered in InfraContainer (_base.py) as artifact_repository
  - ArtifactUploadService registered in Container (container.py) as artifact_upload_service
  - pilot_space.api.v1.routers.project_artifacts added to wiring_config.modules
  - 13 router-layer unit tests covering all endpoints and error paths
affects:
  - 32-artifact-editor-extension (frontend consumes these endpoints)
  - 35-artifacts-page (frontend consumes signed URL and list endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD red-green cycle for router layer (tests before implementation)
    - Direct function call tests (no TestClient/HTTP stack) — same pattern as test_ai_attachments.py
    - RFC 7807 error bodies for 413 and 422 responses
    - Dual-layer 10MB enforcement (pre-read size check + post-read byte count)
    - InfraContainer.artifact_repository accessed directly from router via Provide[InfraContainer.artifact_repository]
    - ArtifactResponse.model_validate() used to convert ORM objects to response schemas in list endpoint

key-files:
  created:
    - backend/src/pilot_space/api/v1/routers/project_artifacts.py
    - backend/tests/unit/api/test_project_artifacts.py
  modified:
    - backend/src/pilot_space/api/v1/__init__.py
    - backend/src/pilot_space/container/_base.py
    - backend/src/pilot_space/container/container.py

key-decisions:
  - "CurrentUser resolves to TokenPayload which exposes .user_id not .id — router uses current_user.user_id throughout"
  - "InfraContainer.artifact_repository used directly in list/url endpoints (not proxied through Container) — consistent with how storage_client is accessed"
  - "ArtifactResponse.model_validate() called explicitly in list_artifacts — avoids Pydantic alias confusion when converting ORM objects"
  - "Test helper _make_current_user sets .user_id not .id — matches TokenPayload interface"

patterns-established:
  - "Root routes use empty string '' not '/' (CLAUDE.md Gotcha #1) — confirmed in router.post and router.get decorators"
  - "session: SessionDep declared in every route function (CLAUDE.md Gotcha #3)"
  - "New router module added to wiring_config.modules (CLAUDE.md Gotcha #2)"
  - "RFC 7807 error body: {type, title, status, detail} for 413 and 422; allowed_extensions list in UNSUPPORTED_FILE_TYPE response"

requirements-completed: [ARTF-04, ARTF-05, ARTF-06]

# Metrics
duration: 10min
completed: 2026-03-19
---

# Phase 31 Plan 03: Project Artifacts Router Summary

**FastAPI router for note file uploads — POST/GET/GET-url/DELETE at /api/v1/workspaces/{ws}/projects/{proj}/artifacts with dual-layer 10MB enforcement and RFC 7807 error bodies, wired into DI container**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-19T13:16:22Z
- **Completed:** 2026-03-19T13:26:23Z
- **Tasks:** 2 (+ checkpoint awaiting human verification)
- **Files modified:** 5

## Accomplishments

- project_artifacts router with 4 endpoints (POST, GET list, GET signed URL, DELETE)
- Dual-layer 10MB enforcement: pre-read via `file.size` + post-read via `len(file_data)`
- RFC 7807 error bodies for 413 (too large) and 422 (bad extension with `allowed_extensions` list)
- ArtifactRepository registered in InfraContainer; ArtifactUploadService registered in Container
- 13 router-layer unit tests using direct function call pattern (no HTTP stack)
- All 3823 unit tests pass; pyright + ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Write router-layer tests (TDD red phase)** - `3c7ffeb7` (test)
2. **Task 2: Implement project_artifacts router and wire DI** - `79a42267` (feat)

## Files Created/Modified

- `backend/src/pilot_space/api/v1/routers/project_artifacts.py` — Router with 4 endpoints, size enforcement, error mapping
- `backend/tests/unit/api/test_project_artifacts.py` — 13 router-layer unit tests (TDD)
- `backend/src/pilot_space/api/v1/__init__.py` — Added project_artifacts_router include
- `backend/src/pilot_space/container/_base.py` — Added ArtifactRepository factory
- `backend/src/pilot_space/container/container.py` — Added ArtifactUploadService factory + wiring_config module

## Decisions Made

- `current_user.user_id` not `.id` — CurrentUser resolves to TokenPayload; accessing `.id` would be an attribute error at runtime
- `InfraContainer.artifact_repository` accessed directly in list/url endpoints (not re-exported through Container) — consistent with `storage_client` pattern
- `ArtifactResponse.model_validate()` explicit conversion in list_artifacts endpoint — avoids Pydantic camelCase alias confusion when converting ORM objects in unit tests
- Test `_make_current_user` sets `.user_id` attribute — matches TokenPayload interface exactly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed current_user.id to current_user.user_id**
- **Found during:** Task 2 (pyright type check)
- **Issue:** Plan template used `current_user.id` but CurrentUser is TokenPayload which exposes `.user_id`
- **Fix:** Changed all occurrences to `current_user.user_id`; also updated test helper
- **Files modified:** project_artifacts.py, test_project_artifacts.py
- **Verification:** pyright reports 0 errors; tests pass
- **Committed in:** 79a42267 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed ArtifactResponse.model_validate() for ORM conversion in list endpoint**
- **Found during:** Task 2 (test run revealed Pydantic alias resolution issue)
- **Issue:** `ArtifactListResponse(artifacts=orm_list)` passed raw ORM objects but Pydantic's camelCase alias_generator tried to access `storageKey`, `mimeType` etc. on MagicMock objects
- **Fix:** Explicit `[ArtifactResponse.model_validate(a) for a in orm_artifacts]` call
- **Files modified:** project_artifacts.py
- **Verification:** All 13 tests pass
- **Committed in:** 79a42267 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug fixes)
**Impact on plan:** Both fixes necessary for correctness; no scope creep.

## Issues Encountered

- TDD cycle required one fix to the test helper `_make_current_user` (`.id` → `.user_id`) to align with actual `TokenPayload` interface. Tests then passed on first run after fix.

## User Setup Required

None — router is wired, but the `note-artifacts` Supabase Storage bucket must exist before E2E uploads work. Create via SQL:
```sql
INSERT INTO storage.buckets (id, name, public) VALUES ('note-artifacts', 'note-artifacts', false) ON CONFLICT DO NOTHING;
```
(This is a pre-existing concern documented in Phase 31 RESEARCH.md, not new work.)

## Next Phase Readiness

- Phase 31 storage backend is complete: migration + model (31-01) + service layer (31-02) + router (31-03)
- Ready for Phase 32: artifact editor extension (TipTap FileCard node, frontend upload flow)
- Checkpoint awaiting human verification of quality gates and OpenAPI docs

---
*Phase: 31-storage-backend*
*Completed: 2026-03-19*
