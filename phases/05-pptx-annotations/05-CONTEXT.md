# Phase 5: PPTX Annotations - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-slide text annotations on PPTX artifacts, linked to the current project. Annotations persist server-side in a new `artifact_annotations` table. Users can create, edit, and delete annotations per slide. Each annotation is scoped to a specific slide index.

</domain>

<decisions>
## Implementation Decisions

### Data model — new `artifact_annotations` table (PPTX-03)
- New SQLAlchemy model: `ArtifactAnnotation` in `infrastructure/database/models/artifact_annotation.py`
- Fields: `id` (UUID PK), `artifact_id` (FK → artifacts.id), `slide_index` (int), `content` (text), `user_id` (FK → users.id), `workspace_id` (FK → workspaces.id), `created_at`, `updated_at`
- Index on `(artifact_id, slide_index)` for efficient per-slide queries
- RLS policies: workspace members can read; only annotation author can update/delete
- [auto] Selected: Do NOT reuse `NoteAnnotation` table — it's coupled to TipTap block IDs and `note_id` FK which don't exist for PPTX artifacts

### API endpoints
- `POST /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations` — Create annotation (body: `{ slide_index, content }`)
- `GET /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations?slide_index=N` — List annotations for a slide
- `PUT /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotation_id}` — Update annotation content
- `DELETE /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotation_id}` — Delete annotation
- All endpoints require workspace membership (same as existing artifact endpoints)
- Follow existing `project_artifacts.py` router patterns — RLS context, `@inject`, `Provide[Container.x]`

### Frontend — annotation panel
- Collapsible panel on the right side of the slide (when annotations exist or user clicks "Add annotation")
- Panel shows annotations for the CURRENT slide only — changes when user navigates slides
- Each annotation card: author avatar, display name, timestamp, content text, edit/delete buttons (for own annotations)
- New annotation: text area + "Save" button at bottom of panel
- [auto] Selected: Panel built as a separate component `PptxAnnotationPanel.tsx`, rendered alongside PptxRenderer in FilePreviewModal

### State management
- TanStack Query for CRUD operations (NOT MobX) — annotations are server state, not UI state
- `useSlideAnnotations(artifactId, slideIndex)` hook — fetches annotations for current slide
- Optimistic updates for create/edit/delete (same pattern as `useDeleteArtifact`)
- Query key: `['artifact-annotations', artifactId, slideIndex]`
- Invalidate on create/edit/delete

### Connection to Phase 4 interface
- PptxAnnotationPanel receives `currentSlide` from FilePreviewModal (same state driving PptxRenderer)
- When slide changes, annotation panel re-queries for new slide's annotations
- No modification to PptxRenderer needed — annotation panel is a sibling component, not a child

### Alembic migration
- New migration file: create `artifact_annotations` table
- Add RLS policies matching existing artifact patterns (workspace isolation, author-only write)
- Add `WITH CHECK` clause (same pattern as migration 094)

### Claude's Discretion
- Exact annotation panel width and layout
- Whether to show annotation count badge on slides in thumbnail strip
- Empty state text when no annotations on current slide
- Maximum annotation content length

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend patterns to follow
- `backend/src/pilot_space/api/v1/routers/project_artifacts.py` — Router pattern: RLS context, @inject, workspace member check
- `backend/src/pilot_space/infrastructure/database/models/artifact.py` — WorkspaceScopedModel base class
- `backend/src/pilot_space/infrastructure/database/repositories/artifact_repository.py` — Repository pattern
- `backend/alembic/versions/091_add_artifacts_table.py` — Migration pattern for artifact-related tables
- `backend/alembic/versions/094_add_artifacts_rls_with_check.py` — RLS policy pattern with WITH CHECK

### Frontend patterns to follow
- `frontend/src/features/artifacts/hooks/use-delete-artifact.ts` — Optimistic update pattern with TanStack Query
- `frontend/src/features/artifacts/hooks/use-project-artifacts.ts` — Query key factory pattern
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Modal layout where annotation panel will be added

### Research
- `.planning/research/ARCHITECTURE.md` — Annotation architecture: separate table, TanStack Query, not MobX
- `.planning/research/PITFALLS.md` — PPTX annotation data loss pitfall (must persist server-side)

### Phase 4 interface contract
- PptxRenderer controlled component: `currentSlide`, `onSlideCountKnown(total)`, `onNavigate(index)`
- Annotation panel is a sibling to PptxRenderer, sharing `currentSlide` state from FilePreviewModal

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useDeleteArtifact`: Optimistic update + rollback + toast pattern — reuse for annotation CRUD
- `Avatar`, `AvatarFallback`: shadcn/ui — for annotation author display
- `Button`, `Textarea`: shadcn/ui — for annotation creation form
- `WorkspaceScopedModel`: Base class with `id`, `workspace_id`, `is_deleted`, timestamps

### Established Patterns
- Repository pattern: `ArtifactRepository` with `create()`, `get_by_id()`, `delete()` — create `ArtifactAnnotationRepository`
- DI wiring: New repository + service must be registered in `container.py` `wiring_config.modules`
- RLS: `set_rls_context(session, user_id, workspace_id)` called before all DB operations

### Integration Points
- `FilePreviewModal.tsx`: Add annotation panel next to PptxRenderer for 'pptx' type
- `container.py`: Register annotation repository and service
- New backend files: model, repository, service, router, migration
- New frontend files: `PptxAnnotationPanel.tsx`, `useSlideAnnotations.ts`

</code_context>

<specifics>
## Specific Ideas

- Annotations should feel like PowerPoint's comment panel — sidebar with author + timestamp + text
- This is the key differentiator: linking slide annotations to the SDLC project context

</specifics>

<deferred>
## Deferred Ideas

- Linking annotations to specific issues or notes (deep integration) — future enhancement
- Annotation position on slide (x,y coordinates) — skip for v1, just per-slide text
- @mention support in annotations — future

</deferred>

---

*Phase: 05-pptx-annotations*
*Context gathered: 2026-03-22*
