# Phase 1: Foundation - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Unblock all Office renderers with ArrayBuffer fetch mode in `useFileContent`, backend allowlist extension for `.docx/.doc/.pptx/.ppt`, MIME-type routing additions in `mime-type-router.ts`, and legacy format download fallback. No renderer UI in this phase — only infrastructure.

</domain>

<decisions>
## Implementation Decisions

### ArrayBuffer fetch mode (FOUND-01)
- Extend `useFileContent` to return `ArrayBuffer` instead of `string` for binary renderer types
- Detect binary mode via a `Set<RendererType>` containing `'xlsx'`, `'docx'`, `'pptx'`
- Use `res.arrayBuffer()` for binary types, keep `res.text()` for existing text-based types
- Return type becomes `string | ArrayBuffer | undefined` — renderers cast as needed
- Keep existing `fetch()` pattern (NOT `apiClient`) — signed URLs include auth in query string

### Backend allowlist (FOUND-02)
- Add `.docx`, `.doc`, `.pptx`, `.ppt` to `_ALLOWED_EXTENSIONS` frozenset in `artifact_upload_service.py`
- Add same extensions to `_ALLOWED_EXTENSIONS_DISPLAY` list in `project_artifacts.py`
- No MIME cross-check for Office formats (unlike image extensions) — browser-reported MIME for Office files is unreliable

### MIME type routing (FOUND-03)
- Add three new `RendererType` values: `'xlsx' | 'docx' | 'pptx'`
- Routing rules in `resolveRenderer()`:
  - `.xlsx` / `.xls` + MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` or `application/vnd.ms-excel` → `'xlsx'`
  - `.docx` / `.doc` + MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document` or `application/msword` → `'docx'`
  - `.pptx` / `.ppt` + MIME `application/vnd.openxmlformats-officedocument.presentationml.presentation` or `application/vnd.ms-powerpoint` → `'pptx'`
- Extension-based detection takes priority over MIME (some servers send `application/octet-stream` for Office files)

### Legacy format fallback (FOUND-04)
- `.doc` (Word 97-2003), `.xls` (Excel 97-2003), `.ppt` (PowerPoint 97-2003) route to the same RendererType as their modern counterparts
- The renderer components themselves detect legacy format and show "Download to view — [format] files require a desktop application" message
- Detection: check file extension; `.doc`/`.xls`/`.ppt` without the `x` suffix = legacy
- Reuse existing `DownloadFallback` component with a new `reason: 'legacy'` variant

### Claude's Discretion
- Exact placement of routing rules relative to existing cases in `resolveRenderer()`
- Whether to add MIME type constants or inline them
- Test file generation approach for unit tests

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Artifact pipeline (existing code to modify)
- `frontend/src/features/artifacts/utils/mime-type-router.ts` — Current routing table; add new RendererType values and rules
- `frontend/src/features/artifacts/utils/__tests__/mime-type-router.test.ts` — Existing test patterns to extend
- `frontend/src/features/artifacts/hooks/useFileContent.ts` — Current text-only fetch; extend to ArrayBuffer
- `frontend/src/features/artifacts/components/renderers/DownloadFallback.tsx` — Extend with 'legacy' reason
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Register new renderer types (placeholder for Phase 2+)
- `frontend/src/types/artifact.ts` — Artifact type definition

### Backend allowlist (existing code to modify)
- `backend/src/pilot_space/application/services/artifact/artifact_upload_service.py` — `_ALLOWED_EXTENSIONS` frozenset
- `backend/src/pilot_space/api/v1/routers/project_artifacts.py` — `_ALLOWED_EXTENSIONS_DISPLAY` list

### Research findings
- `.planning/research/SUMMARY.md` — Full research synthesis
- `.planning/research/PITFALLS.md` — Pitfall 1 (binary corruption) and Pitfall 8 (missing allowlist)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DownloadFallback` component: Already handles 'unsupported', 'expired', 'error' reasons — add 'legacy' variant
- `resolveRenderer()`: Pure function with clear priority waterfall — new Office rules slot in before the `text/*` catch-all
- `artifactKeys` in useFileContent: Query key factory already exported — ArrayBuffer queries use same key structure

### Established Patterns
- `useFileContent` uses `useQuery` with `enabled` guard, `staleTime: 55min`, `retry: false` — binary mode follows same pattern
- Renderers are lazy-loaded via `next/dynamic` in `FilePreviewModal` — Office renderers follow same pattern
- Backend `_validate_file_type()` uses `pathlib.Path(filename).suffix.lower()` — no MIME cross-check needed for Office types

### Integration Points
- `RendererType` union in `mime-type-router.ts` — add `'xlsx' | 'docx' | 'pptx'`
- `renderContent()` switch in `FilePreviewModal.tsx` — add placeholder cases (actual renderer components come in Phase 2+)
- `_ALLOWED_EXTENSIONS` in `artifact_upload_service.py` — add 4 extensions
- `_ALLOWED_EXTENSIONS_DISPLAY` in `project_artifacts.py` — add 4 extensions (sorted)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard infrastructure changes. Follow existing patterns exactly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-22*
