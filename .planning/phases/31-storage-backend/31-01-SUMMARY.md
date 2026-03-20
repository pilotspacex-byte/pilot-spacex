---
phase: 31-storage-backend
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, postgresql, artifacts, supabase-storage, orm]

# Dependency graph
requires:
  - phase: 30-tiptap-extension-foundation
    provides: TipTap extension foundation used in notes where artifacts will be embedded
provides:
  - Alembic migration 090 creating artifacts table with all columns, indexes, and constraints
  - Artifact SQLAlchemy ORM model extending WorkspaceScopedModel
  - Model registered in models/__init__.py for Alembic autogenerate discovery
affects: [32-artifact-tiptap-node, 33-artifact-service-api, 34-file-preview, 35-artifacts-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DB-first upload: create DB record (status=pending_upload) before touching storage, update to ready after success"
    - "WorkspaceScopedModel extension: use # type: ignore[assignment] when overriding __tablename__"
    - "Inline index=True omitted when composite index in __table_args__ already covers the column"

key-files:
  created:
    - backend/alembic/versions/090_add_artifacts_table.py
    - backend/src/pilot_space/infrastructure/database/models/artifact.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/__init__.py

key-decisions:
  - "Removed inline index=True from project_id — composite ix_artifacts_workspace_project already covers project_id; prevents alembic drift from spurious ix_artifacts_project_id"
  - "Added # type: ignore[assignment] to __tablename__ = artifacts — required for all models extending WorkspaceScopedModel/BaseModel due to declared_attr directive type conflict"
  - "Used port 15433 (direct DB) instead of 15432 (pooler) for alembic — Supabase pgBouncer requires tenant format on 15432 which breaks standard migrations"

patterns-established:
  - "Pattern: WorkspaceScopedModel tablename override uses # type: ignore[assignment] (see note.py, issue.py)"
  - "Pattern: Composite indexes in __table_args__ replace per-column index=True to avoid alembic schema drift"

requirements-completed: [ARTF-04, ARTF-05, ARTF-06]

# Metrics
duration: 7min
completed: 2026-03-19
---

# Phase 31 Plan 01: Storage Backend Summary

**Alembic migration 090 + Artifact SQLAlchemy ORM model: artifacts table with DB-first upload status machine, workspace isolation, and Supabase Storage key format enforced at model layer**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-19T12:49:07Z
- **Completed:** 2026-03-19T12:56:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created Alembic migration 090 establishing the artifacts table with all required columns (id, workspace_id, project_id, user_id, filename, mime_type, size_bytes, storage_key, status, is_deleted, deleted_at, created_at, updated_at), CHECK constraints (status, size_bytes), and 3 indexes
- Implemented Artifact SQLAlchemy model extending WorkspaceScopedModel with explicit __tablename__ and matching schema
- Registered Artifact in models/__init__.py making it discoverable by Alembic autogenerate; verified zero schema drift on artifacts table

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Alembic migration 090 for artifacts table** - `4648cbae` (feat)
2. **Task 2: Implement Artifact SQLAlchemy model and register in __init__.py** - `c12466f0` (feat)

## Files Created/Modified

- `backend/alembic/versions/090_add_artifacts_table.py` - Migration 090: creates artifacts table, 3 indexes, 2 CHECK constraints; down_revision = "089_add_role_type_idx"
- `backend/src/pilot_space/infrastructure/database/models/artifact.py` - Artifact ORM model extending WorkspaceScopedModel; status machine (pending_upload/ready); storage_key format documented in docstring
- `backend/src/pilot_space/infrastructure/database/models/__init__.py` - Added Artifact import and "Artifact" to __all__

## Decisions Made

- **Inline index=True removed from project_id:** The composite index `ix_artifacts_workspace_project(workspace_id, project_id)` in `__table_args__` covers project_id queries scoped by workspace. Adding `index=True` would create a redundant standalone `ix_artifacts_project_id` that wasn't in the migration, causing alembic schema drift.
- **`# type: ignore[assignment]` on `__tablename__`:** Required pattern for all models that extend `WorkspaceScopedModel`/`BaseModel` — the `@declared_attr.directive` in BaseModel makes `__tablename__` a `_declared_directive[str]` type, so assigning a plain string literal triggers a pyright type error. Existing models (note.py, issue.py) use the same suppress comment.
- **Direct DB connection (port 15433) for alembic:** The Supabase pgBouncer pooler on port 15432 rejects connections with "Tenant or user not found" in the current local dev setup. Alembic migrations connect directly to the DB on port 15433, bypassing the pooler. This is a dev-environment concern only — production uses proper connection strings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed index=True from project_id to fix alembic schema drift**
- **Found during:** Task 2 (Artifact SQLAlchemy model implementation)
- **Issue:** The plan's model code example included `index=True` on `project_id`, but the migration did not create a standalone `ix_artifacts_project_id` index. Running `alembic check` detected the spurious index as schema drift.
- **Fix:** Removed `index=True` from `project_id` mapped_column. The composite `ix_artifacts_workspace_project(workspace_id, project_id)` in `__table_args__` provides equivalent query performance for workspace-scoped project lookups.
- **Files modified:** `backend/src/pilot_space/infrastructure/database/models/artifact.py`
- **Verification:** `alembic check` output shows zero artifact-specific drift after fix.
- **Committed in:** `c12466f0` (Task 2 commit)

**2. [Rule 1 - Bug] Added # type: ignore[assignment] to __tablename__ to fix pyright error**
- **Found during:** Task 2 (pre-commit pyright hook failure)
- **Issue:** Pyright error: `Type "Literal['artifacts']" is not assignable to declared type "_declared_directive[str]"` — the BaseModel inherited `__tablename__` as a `@declared_attr.directive`.
- **Fix:** Added `# type: ignore[assignment]` comment matching the pattern established by `note.py` and `issue.py`.
- **Files modified:** `backend/src/pilot_space/infrastructure/database/models/artifact.py`
- **Verification:** `uv run pyright src/pilot_space/infrastructure/database/models/artifact.py` exits with 0 errors.
- **Committed in:** `c12466f0` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness — one prevented schema drift, one fixed a type error caught by pre-commit hooks. No scope creep.

## Issues Encountered

- Supabase pgBouncer pooler (port 15432) returned "Tenant or user not found" blocking standard `alembic upgrade head`. Resolved by running alembic with the direct DB URL on port 15433. This is a local dev environment quirk — prior migrations presumably ran with the pooler working correctly. Documented as a dev environment note, not a code issue.

## User Setup Required

None - no external service configuration required. The `note-artifacts` Supabase Storage bucket creation is deferred to Phase 33 (service + API layer) when the upload endpoint will be built.

## Next Phase Readiness

- `artifacts` table is live in the DB at migration 090
- `Artifact` model is importable from `pilot_space.infrastructure.database.models`
- Foundation ready for Phase 31 Plan 02 (ArtifactRepository) and Plan 03 (ArtifactUploadService + router)
- Phase 32 (TipTap ArtifactNode extension) can reference the Artifact model schema

---
*Phase: 31-storage-backend*
*Completed: 2026-03-19*
