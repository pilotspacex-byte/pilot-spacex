# Project Research Summary

**Project:** Pilot Space v1.1 — Medium Editor & File Artifacts
**Domain:** Rich text editor enhancement + file artifact management on an existing TipTap + FastAPI + Supabase stack
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

This milestone extends an existing, mature platform (not a greenfield build) with a Medium-style writing experience and file artifact management. The core finding is that the stack already covers ~90% of what is needed: TipTap 3.x is installed with `BubbleMenu`/`FloatingMenu` bundled in `@tiptap/react`, the backend has `storage3`, `python-multipart`, and `supabase` SDKs in place, and TanStack Query's `useMutation` already handles optimistic UI for other features. Only 5 new npm packages are required and zero new Python packages. The recommended approach is additive: extend existing extensions and patterns rather than replacing them.

The key architectural risk is the suite of integration constraints that exist in the current TipTap setup. Four hard rules govern every new editor extension: (1) new block nodes must be registered in Group 3 before `BlockIdExtension`, (2) new node views must NOT be wrapped in MobX `observer()` due to a React 19 + `ReactNodeViewRenderer` + `flushSync` incompatibility, (3) new nodes must register `renderMarkdown` or content silently drops on save, and (4) the existing `SelectionToolbar` must be extended rather than replaced with TipTap's `BubbleMenu` API to avoid conflicts with `GhostTextExtension` and `SlashCommandExtension`. These are non-negotiable constraints, not options — violating any one causes silent data loss, runtime crashes, or plugin conflicts.

Security and storage design require deliberate upfront choices. The upload flow must be DB-first (write a `pending_upload` record, then upload to Supabase Storage, then mark `ready`) to prevent orphaned storage objects on failure. File access must go through backend-generated signed URLs — never public bucket URLs — to enforce workspace isolation. Video iframes require explicit `sandbox` and `allow` attributes, and `frame-src` in `next.config.ts` must be updated to include only `youtube-nocookie.com` and `player.vimeo.com`. All three size enforcement layers (frontend validation, FastAPI body check, Nginx `client_max_body_size 12m`) must be in place before the upload endpoint goes live.

## Key Findings

### Recommended Stack

The project needs exactly 5 new frontend packages and 0 new backend packages. TipTap's `BubbleMenu` and `FloatingMenu` components are already bundled inside the installed `@tiptap/react` package — no separate installs. The backend `storage3`, `python-multipart`, and `supabase` SDKs already cover all storage operations needed.

**Core new technologies:**
- `@tiptap/extension-image` ^3.20.4 — official image node, required foundation for `FigureNode` (image with caption); not in StarterKit
- `@tiptap/extension-youtube` ^3.20.4 — official YouTube embed node; Vimeo requires a custom ~60-line extension (no TipTap 3-compatible Vimeo package exists)
- `react-dropzone` ^15.0.0 — drag-and-drop file upload; React 19 compatible as of Feb 2026
- `papaparse` ^5.5.3 — CSV parsing for preview modal; use directly, not via `react-papaparse` wrapper
- `@e965/xlsx` ^0.20.3 — Excel preview; use this maintained fork, NOT `xlsx` on npm (unmaintained, active CVEs in 2026)

**Critical version notes:**
- Use `@e965/xlsx` not `xlsx` — the npm `xlsx` name is an unmaintained fork with CVEs
- `@fourwaves/tiptap-extension-vimeo` is TipTap 2.x only; build a custom ~60-line Vimeo node instead
- `BubbleMenu`/`FloatingMenu` import from `@tiptap/react/menus` (already installed) — do NOT install separate `@tiptap/extension-bubble-menu`

See `.planning/research/STACK.md` for full installation commands and version compatibility table.

### Expected Features

All features across 4 categories (editor UX, file upload/preview, artifacts management page, video embeds) are well-understood. The feature set is concrete and bounded — this is enhancement work with clear scope, not exploratory product development.

**Must have (table stakes — P1):**
- Pull quote toggle (styled blockquote variant) — low effort, high craft signal
- Focus mode (hide chrome, Cmd+Shift+F) — MobX flag + CSS, no new infrastructure
- Floating toolbar heading toggle H1/H2/H3 — currently missing from `SelectionToolbar`
- Inline image insertion via `/image` slash command + drag-and-drop
- Inline image captions (custom `FigureNode` extending `@tiptap/extension-image`)
- `FileCardNode` with upload, progress indicator, and preview modal (text, JSON, code, Markdown, CSV, images)
- `/file`, `/image`, `/video` slash commands (additive entries to existing `SlashCommandExtension`)
- Per-project artifacts management page: list, preview, download, delete + optimistic UI
- YouTube embed via `@tiptap/extension-youtube`
- Vimeo embed via custom `VimeoNode`

**Should have (competitive differentiators — P2):**
- URL paste detection → offer to embed (YouTube/Vimeo `PasteRule`)
- Video thumbnail placeholder before iframe activation
- Upload progress indicator on `FileCardNode`
- "Used in" note deep-link on artifacts management page

**Defer (v1.x — after validation):**
- XLSX preview (`@e965/xlsx` dep cost justified only with demand signal)
- Grid/list view toggle on artifacts page
- Artifact reuse across notes

**Defer (v2+):**
- PDF in-app preview (pdf.js too heavy; browser handles natively)
- Bulk download as ZIP (requires server-side assembly)
- Artifact version history

**Anti-features to explicitly avoid:**
- Replacing `SelectionToolbar` with TipTap's `BubbleMenu` extension — breaks ghost text/slash command coordination
- Generic iframe embed for arbitrary URLs — CSP violations cause silent failures; YouTube + Vimeo only
- PDF preview — `react-pdf` adds ~2MB; browser opens PDFs natively

See `.planning/research/FEATURES.md` for full prioritization matrix and competitor analysis.

### Architecture Approach

The architecture is additive to existing Clean Architecture layers. The critical path is storage layer first (DB migration + `ArtifactUploadService` + `project_artifacts` router), then editor extensions and management UI in parallel, then preview modal, then polish. Video embeds, focus mode, and pull quote are fully backend-independent and can be built concurrently with the storage work.

**Major new components:**

Backend:
1. `Artifact` ORM model — extends `WorkspaceScopedModel`; stores file metadata + `storage_key`; uses `note-artifacts` Supabase Storage bucket (separate from `chat-attachments` which has TTL expiry)
2. `ArtifactUploadService` — mirrors `AttachmentUploadService` pattern; DB-first upload flow (write `pending_upload` record → upload to Storage → mark `ready`)
3. `project_artifacts.py` router — CRUD + signed URL endpoints under existing `v1` API surface

Frontend:
4. `FileCardExtension` + `FileCardView` — TipTap block node (Group 3); plain (non-observer) wrapper component with context bridge for reactive state
5. `VideoEmbedExtension` + `VideoEmbedView` — YouTube/Vimeo iframe node; validates URLs against allowlist before inserting
6. `PullQuoteExtension` — ~30-line blockquote variant; no NodeView needed
7. `FloatingToolbarExtension` — extend existing `SelectionToolbar`, not a new BubbleMenu instance
8. `FilePreviewModal` — shadcn `Dialog` with per-MIME-type renderer; shared between `FileCardView` and `ArtifactsPage`
9. `ArtifactStore` (MobX) — ephemeral upload progress state; TanStack Query owns the persistent artifacts list
10. `ArtifactsPage` — `/{ws}/projects/{pid}/artifacts` route; TanStack Query CRUD with optimistic delete

**Key patterns:**
- Extension registration order: new block nodes in Group 3, before `BlockIdExtension` (PRE-002 constraint)
- NodeView components: plain wrapper → context bridge → observer child (never `observer()` on the NodeView directly)
- Markdown serialization: define `renderMarkdown` in the same PR as the node, never deferred
- Storage access: backend service-role upload only; signed URLs for all reads (never public URLs)
- State ownership split: TanStack Query owns server-fetched lists; MobX owns ephemeral client state (upload progress, optimistic placeholders)

See `.planning/research/ARCHITECTURE.md` for full component map, data flows, project structure, and suggested build order.

### Critical Pitfalls

1. **New block extensions registered after `BlockIdExtension`** — `blockId` is null on new nodes; breaks annotation linking, AI block references, KG chunker. Prevention: always insert in Group 3 of `createEditorExtensions.ts` before the Group 4 marker. Verify with `editor.getJSON()` immediately after adding any new block node.

2. **MobX `observer()` on TipTap NodeView components** — causes nested `flushSync` crash in React 19 (`ReactNodeViewRenderer` + MobX `useSyncExternalStore` both call `flushSync`). Prevention: use context bridge pattern (plain NodeView wrapper → observer child via React context), same as `IssueEditorContent`.

3. **Missing `renderMarkdown` on custom nodes** — `tiptap-markdown` silently drops unregistered nodes at save time; `FileCardNode` and video embeds disappear after page reload. Prevention: define `renderMarkdown` in the same commit as the node extension. Test with round-trip: insert → `getMarkdown()` → re-parse → verify node survives.

4. **Single-phase upload (storage first, DB second)** — upload failure leaves orphaned Supabase Storage objects with no DB record and no cleanup path. Prevention: DB-first flow in `ArtifactUploadService`: write `status: pending_upload` → upload file → update to `status: ready`. Add 24h cleanup job for stale `pending_upload` records.

5. **Video iframe XSS and missing CSP** — missing `sandbox`/`allow` attributes on iframes allow embedded page to navigate parent; missing `frame-src` in Next.js CSP causes production embed failures. Prevention: always include `sandbox="allow-scripts allow-same-origin allow-presentation allow-fullscreen"` on video iframes; add `frame-src https://www.youtube-nocookie.com https://player.vimeo.com` to `next.config.ts` before shipping video embeds.

**Additional pitfalls (moderate severity):**
- Signed URL expiry with long TanStack Query `staleTime` — set `staleTime` to max 55 minutes on any query embedding signed URLs; handle 403 in preview modal with query invalidation
- Three-layer file size enforcement (client, FastAPI, Nginx) — all three must be in place; missing Nginx `client_max_body_size 12m` returns raw HTML 413 that breaks `ApiError.fromAxiosError`
- MIME type spoofing — backend must validate content via magic bytes / header sniffing, not trust `file.type` from browser

See `.planning/research/PITFALLS.md` for full pitfall-to-phase mapping and recovery strategies.

## Implications for Roadmap

Based on combined research findings, the build order is dependency-driven. The storage layer is the critical path; editor extension foundation must be established before any node UI is built to prevent cascading pitfalls.

### Phase 1: TipTap Extension Foundation
**Rationale:** Three of the five critical pitfalls manifest at the extension layer and must be resolved before any node UI is built. Establishing the correct extension registration order, the NodeView wrapper pattern, and the `renderMarkdown` contract upfront prevents cascading failures in all subsequent phases.
**Delivers:** Extension scaffolding with correct group ordering verified, reusable NodeView context bridge pattern established, `renderMarkdown` contract verified on a simple node, slash command group `'media'` added, pull quote extension (simplest new node — proof-of-concept for all patterns), floating toolbar heading toggle (extend `SelectionToolbar`, not replace it)
**Addresses:** Pull quote, heading toggle in floating toolbar
**Avoids:** Pitfall 1 (BlockIdExtension ordering), Pitfall 2 (observer NodeView flushSync), Pitfall 3 (markdown serialization loss)
**Research flag:** Standard patterns — well-documented in codebase (`createEditorExtensions.ts` PRE-002 comments, existing `PMBlockExtension` pattern)

### Phase 2: Storage Backend
**Rationale:** The upload API must exist before any frontend artifact feature can be completed. The DB-first upload flow must be designed here, not retrofitted later. All three file size enforcement layers belong in this phase.
**Delivers:** Alembic migration for `artifacts` table, `ArtifactUploadService` (DB-first: `pending_upload` → upload → `ready`), `project_artifacts.py` router (upload, list, delete, signed URL), Nginx `client_max_body_size 12m` config, 24h cleanup job for stale `pending_upload` records
**Uses:** Existing `SupabaseStorageClient`, `WorkspaceScopedModel`, `AttachmentUploadService` as template; `note-artifacts` bucket (separate from `chat-attachments`)
**Implements:** `Artifact` ORM model, `ArtifactRepository`, `ArtifactContentService` (signed URL generation)
**Avoids:** Pitfall 4 (orphaned storage objects), Pitfall 7 (three-layer size enforcement), Pitfall 5 (workspace isolation via application-layer checks)
**Research flag:** Standard patterns — mirrors existing `AttachmentUploadService` and `ChatAttachment` model; no new patterns needed

### Phase 3: Inline Editor Features (File Cards + Image)
**Rationale:** Now that the upload API exists, editor extensions that depend on it can be built. Image insertion is a prerequisite for image captions. FileCardNode upload integration connects editor to backend.
**Delivers:** `@tiptap/extension-image` install, custom `FigureNode` (image + caption), `FileCardExtension` + `FileCardView` (with placeholder node pattern during upload), drag-and-drop file/image onto canvas, `/image` and `/file` slash commands, `ArtifactStore` (MobX) for upload progress state
**Uses:** Context bridge pattern from Phase 1; upload API from Phase 2
**Implements:** Placeholder node optimistic pattern (insert with `artifactId: null`, update on upload completion)
**Avoids:** Pitfall 2 (observer NodeView), Pitfall 3 (`renderMarkdown` for FileCardNode serialized as `[filename](artifact://uuid)`)
**Research flag:** Needs care on context bridge — established pattern exists (`issue-note-context.ts`) but each node view requires implementing it correctly

### Phase 4: Video Embeds
**Rationale:** Fully backend-independent — no storage, no DB migration needed. Isolated scope with its own security requirements (CSP, sandbox attributes). Can be built in parallel with Phase 3 but sequenced after to allow Phase 3 patterns to be established first.
**Delivers:** `@tiptap/extension-youtube` install, custom `VimeoNode` (~60 lines), `VideoEmbedView` (with iframe sandbox attributes), URL paste detection `PasteRule`, CSP `frame-src` update in `next.config.ts`, URL validation allowlist rejecting malformed URLs with user-visible toast
**Avoids:** Pitfall 8 (malformed URL validation), Pitfall 9 (iframe XSS and missing CSP)
**Research flag:** Standard patterns — YouTube extension is official TipTap documentation; Vimeo custom node follows identical pattern; URL validation is an allowlist, not regex

### Phase 5: File Preview Modal
**Rationale:** Depends on Phase 2 (signed URL endpoint) and Phase 3 (FileCardNode exists to trigger the modal). Build once, shared between editor and management page. Common MIME types first, Excel deferred to v1.x.
**Delivers:** `FilePreviewModal` shadcn Dialog with renderers for: image, text/Markdown (`react-markdown` + `remark-gfm`), JSON + code (reuse existing `lowlight`/shiki), CSV (`papaparse`); "Download" fallback for unsupported types; 403 error handling triggers TanStack Query invalidation; HTML files previewed as source code (never as live HTML)
**Uses:** `papaparse` (new dep); existing `react-markdown`, `lowlight`, `dompurify`; `@e965/xlsx` deferred (lazy import, P3 only)
**Avoids:** Pitfall 6 (signed URL expiry — handle 403 in modal), security: HTML preview must render escaped source, not `innerHTML`
**Research flag:** Standard patterns for all renderers; CSV table rendering for large files (capped at 500 rows) — decide truncation vs. virtual scrolling upfront

### Phase 6: Artifacts Management Page
**Rationale:** Depends on Phase 2 (all artifact API endpoints) and Phase 5 (`FilePreviewModal` to reuse). The management page reuses both the API layer and the preview component — no new infrastructure needed.
**Delivers:** `ArtifactsPage` route at `/{ws}/projects/{pid}/artifacts`, TanStack Query hooks (`useArtifacts`, `useDeleteArtifact` with optimistic delete, `useArtifactSignedUrl`), `staleTime` set to 55 minutes on artifact list query, `artifact-card` component (filename, type icon, size, uploader avatar, date), client-side filename search filter, sort by type/date/size
**Uses:** `useQuery`/`useMutation` optimistic update pattern (same as issues/cycles in codebase); `FilePreviewModal` from Phase 5
**Avoids:** Pitfall 6 (staleTime constraint — never `Infinity` on queries with signed URLs), optimistic rollback shows "Upload failed, retry?" state not silent disappearance
**Research flag:** Standard patterns — reuses established optimistic update pattern already used in issues and cycles features

### Phase 7: Editor UX Polish
**Rationale:** Focus mode is independent of the storage system and can be deferred until core functionality is complete. Low-risk, high-craft item.
**Delivers:** Focus mode (MobX `isFocusMode` flag + CSS hide-chrome, Cmd+Shift+F shortcut), `z-index` hierarchy ensuring focus mode overlay does not cover slash command menu
**Addresses:** Focus mode — explicitly a "Medium-style editor" requirement from PROJECT.md
**Research flag:** Standard patterns — pure CSS/MobX, no new dependencies, no backend

### Phase Ordering Rationale

- **Phase 1 before all other phases:** The three extension pitfalls (ordering, observer, renderMarkdown) are load-bearing constraints. Building Phases 3 or 4 without Phase 1 foundations guarantees rework.
- **Phase 2 (storage) before Phase 3 (file upload):** FileCardNode cannot complete its upload flow without the API endpoint. The FileCardNode static rendering can start in parallel, but upload integration requires Phase 2.
- **Phases 3 and 4 can be built in parallel:** Video embeds have zero backend dependencies and zero shared state with the file upload work.
- **Phase 5 before Phase 6:** The artifacts management page reuses `FilePreviewModal`. Avoid building the modal twice in two different places.
- **Phase 7 last:** Pure polish with no blocking dependencies; safe to defer if time-constrained without impacting any other phase.

### Research Flags

Phases needing deeper research or careful attention during planning:
- **Phase 3 (File Cards + Image):** The context bridge pattern is established but each new NodeView requires careful implementation. Review `issue-note-context.ts` and `property-block-view.tsx` before writing `FileCardView`. The placeholder node cleanup (stale `artifactId: null` nodes from failed uploads) needs a concrete removal strategy on editor mount.
- **Phase 5 (Preview Modal):** CSV table rendering for large files (capped at 500 rows) needs an explicit decision on truncation vs. `@tanstack/react-virtual` virtual scrolling. Decide before implementation to avoid refactoring later.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Fully documented in `createEditorExtensions.ts` PRE-002 comments and existing `PMBlockExtension` pattern
- **Phase 2:** Direct template in `AttachmentUploadService` and `ChatAttachment` model; no novel patterns
- **Phase 4:** YouTube extension is official TipTap documentation; Vimeo is a 60-line mirror of the same pattern
- **Phase 6:** Optimistic update pattern already used in issues and cycles — same `onMutate`/`onError`/`onSettled` shape
- **Phase 7:** Pure MobX flag + CSS, zero infrastructure

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 5 packages verified live via `npm view`; existing stack audited from `package.json` and `pyproject.toml`; zero new Python deps confirmed |
| Features | HIGH | Cross-referenced with existing codebase components, competitor analysis (Notion/Linear), and PROJECT.md milestone requirements; anti-features explicitly identified |
| Architecture | HIGH | Based on direct codebase inspection of all referenced files; build order derived from actual dependency graph, not speculation; integration constraints confirmed from live code |
| Pitfalls | HIGH | Critical pitfalls 1-4 confirmed from codebase analysis and project memory (MEMORY.md flushSync constraint); pitfalls 5-10 confirmed from TipTap GitHub issues and Supabase docs |

**Overall confidence:** HIGH

### Gaps to Address

- **XLSX preview in v1 vs. v1.x:** Research recommends deferring `@e965/xlsx` until after launch validation, but PROJECT.md may require it in v1. Verify against PROJECT.md milestone spec before Phase 5 planning.
- **Cleanup job for `pending_upload` artifacts:** The DB-first upload flow requires a background cleanup job (24h sweep of stale `pending_upload` records). This is not in the current `memory_worker.py` task list. Add it explicitly during Phase 2 planning.
- **`python-magic` for server-side MIME validation:** PITFALLS.md recommends magic bytes validation in the backend to prevent MIME spoofing. This library is not currently in `pyproject.toml` and would be a new Python dependency. Validate whether it's worth the dependency vs. a simpler extension-allowlist approach during Phase 2.
- **Nginx `client_max_body_size` current value:** Pitfalls research describes the default as 1MB which would break files >1MB before FastAPI. Verify the actual current value in `infra/` before assuming it needs changing.
- **CSV virtual scrolling threshold:** Phase 5 needs a decision on truncating large CSV previews at 500 rows vs. implementing virtual scrolling. Research `@tanstack/react-virtual` during Phase 5 planning if CSVs in the target workflow regularly exceed 500 rows.

## Sources

### Primary (HIGH confidence)
- TipTap official docs: BubbleMenu, FloatingMenu, Image extension, YouTube extension, Figure experiment, Markdown custom serializing — confirmed API contracts and version compatibility
- Supabase docs: Storage access control, signed URLs, Python SDK upload API — confirmed backend operation signatures
- Direct codebase inspection: `createEditorExtensions.ts`, `GhostTextExtension.ts`, `SlashCommandExtension.ts`, `SelectionToolbar.tsx`, `attachment_upload_service.py`, `storage/client.py`, `WorkspaceScopedModel`, `container.py`, `NoteStore.ts`, `RootStore.ts`, `issue-note-context.ts` — all integration constraints verified from live code
- `npm view` on all 5 new packages — version numbers and React 19 compatibility confirmed live

### Secondary (MEDIUM confidence)
- TipTap GitHub issues: #3764 (flushSync NodeView crash), #6148 (BubbleMenu + DragHandle conflict), #4560 (YouTube URL edge case — valid-looking URL with no video ID accepted) — confirm pitfalls are real and community-documented
- SheetJS/xlsx security reports 2026 — confirm `xlsx` npm CVEs; `@e965/xlsx` as the maintained fork with identical API

### Tertiary (needs validation during implementation)
- Nginx `client_max_body_size` default behavior — described in FastAPI community; verify against actual `infra/` Nginx config before assuming 1MB default applies
- `python-magic` as MIME validation approach — mentioned in pitfalls research; validate whether it fits the project's dependency philosophy vs. a simpler extension-based allowlist

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
