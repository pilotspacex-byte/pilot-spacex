---
phase: 05-pptx-annotations
plan: "01"
subsystem: backend
tags: [fastapi, sqlalchemy, alembic, rls, annotations, pptx]
dependency_graph:
  requires:
    - "04-01: PptxRenderer component (stable prop contract)"
    - "01-01: Artifact upload pipeline (artifacts table exists)"
  provides:
    - "ArtifactAnnotation model + artifact_annotations table"
    - "CRUD API at /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations"
    - "RLS workspace isolation + author-only modify policies"
  affects:
    - "05-02: Frontend annotation panel (consumes this API)"
tech_stack:
  added:
    - "ArtifactAnnotation SQLAlchemy model"
    - "ArtifactAnnotationRepository"
    - "artifact_annotations.py Pydantic schemas"
    - "artifact_annotations.py FastAPI router"
    - "Migration 096 (merge head)"
  patterns:
    - "WorkspaceScopedModel inheritance pattern"
    - "Factory DI provider with Callable session injection"
    - "set_rls_context before all DB ops"
    - "Author ownership guard at router layer (not RLS)"
key_files:
  created:
    - "backend/src/pilot_space/infrastructure/database/models/artifact_annotation.py"
    - "backend/src/pilot_space/infrastructure/database/repositories/artifact_annotation_repository.py"
    - "backend/src/pilot_space/api/v1/schemas/artifact_annotations.py"
    - "backend/src/pilot_space/api/v1/routers/artifact_annotations.py"
    - "backend/alembic/versions/096_create_artifact_annotations_table.py"
  modified:
    - "backend/src/pilot_space/infrastructure/database/models/__init__.py"
    - "backend/src/pilot_space/container/_base.py"
    - "backend/src/pilot_space/container/container.py"
    - "backend/src/pilot_space/api/v1/__init__.py"
decisions:
  - "Hard delete for annotations (no soft-delete): annotations are ephemeral comments, not audited entities"
  - "Author ownership enforced at router layer (404 + 403 checks) rather than solely RLS — RLS provides workspace isolation, router layer enforces per-resource ownership"
  - "slide_index stored as integer (not a FK to a slides table) — slide metadata is computed client-side from PPTX binary"
  - "Migration 096 merges two 095 heads (transcript_cache_rls + workspace_members_rls_index) into single head using tuple down_revision"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-22"
  tasks_completed: 2
  files_created: 5
  files_modified: 4
---

# Phase 05 Plan 01: PPTX Annotation Backend Summary

Full backend for per-slide PPTX annotations: SQLAlchemy model, Alembic migration (merge head) with RLS policies, repository, Pydantic schemas, FastAPI CRUD router, and DI wiring.

## What Was Built

### ArtifactAnnotation Model
`WorkspaceScopedModel` subclass with `artifact_id`, `slide_index`, `content`, `user_id`. Composite index `ix_artifact_annotations_artifact_slide` for efficient per-slide queries.

### Migration 096 (Merge Head)
Merges `095_add_transcript_cache_rls` and `095_add_workspace_members_rls_index` into single head. Creates `artifact_annotations` table with:
- Workspace isolation RLS policy (all workspace members with lowercase roles)
- Author-modify RLS policy (user_id must match `app.current_user_id`)
- Two indexes: `(artifact_id, slide_index)` composite + `workspace_id`

### Repository
`ArtifactAnnotationRepository` with: `create`, `list_by_slide` (ordered ASC), `get_by_id`, `update_content`, `delete` (hard delete returning bool).

### Schemas
- `CreateAnnotationRequest`: `slide_index: int (ge=0)`, `content: str (1-5000 chars)`
- `UpdateAnnotationRequest`: `content: str (1-5000 chars)`
- `ArtifactAnnotationResponse`: full response with all fields + timestamps
- `AnnotationListResponse`: list + total

### Router
4 endpoints at `/workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations`:
- `POST ""` — create annotation (201)
- `GET ""` — list by `slide_index` query param
- `PUT "/{annotation_id}"` — update content (author-only, 403 otherwise)
- `DELETE "/{annotation_id}"` — delete (author-only, 404 then 403 checks)

### DI Wiring
`artifact_annotation_repository = providers.Factory(ArtifactAnnotationRepository, ...)` in `InfraContainer`. Module `pilot_space.api.v1.routers.artifact_annotations` added to `wiring_config.modules`.

## Acceptance Criteria

- [x] `alembic heads` shows single head (096_create_artifact_annotations_table)
- [x] ArtifactAnnotation model imports and `__tablename__ == "artifact_annotations"`
- [x] All 4 schema classes import cleanly
- [x] Repository has all 5 methods
- [x] pyright passes on all new files (0 errors)
- [x] ruff check passes on all new files
- [x] Annotations router registered in api_router.routes
- [x] All 4 endpoints (POST, GET, PUT, DELETE) on router

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- backend/src/pilot_space/infrastructure/database/models/artifact_annotation.py: FOUND
- backend/src/pilot_space/infrastructure/database/repositories/artifact_annotation_repository.py: FOUND
- backend/src/pilot_space/api/v1/schemas/artifact_annotations.py: FOUND
- backend/src/pilot_space/api/v1/routers/artifact_annotations.py: FOUND
- backend/alembic/versions/096_create_artifact_annotations_table.py: FOUND

Commits:
- 1ca7b4d9: feat(05-01): ArtifactAnnotation model, repository, schemas, and migration
- f01962bb: feat(05-01): artifact annotations router, DI wiring, and API registration
