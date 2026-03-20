# Roadmap: Pilot Space

## Milestones

- ✅ **v1.0 Enterprise** — Phases 1–11 (shipped 2026-03-09)
- ✅ **v1.0-alpha Pre-Production Launch** — Phases 12–23 (shipped 2026-03-12)
- ✅ **v1.0.0-alpha2 Notion-Style Restructure** — Phases 24–29 (shipped 2026-03-12)
- 🚧 **v1.1 Medium Editor & Artifacts** — Phases 30–36 (in progress)

## Phases

<details>
<summary>✅ v1.0 Enterprise (Phases 1–11) — SHIPPED 2026-03-09</summary>

- [x] Phase 1: Identity & Access (9/9 plans) — completed 2026-03-07
- [x] Phase 2: Compliance & Audit (5/5 plans) — completed 2026-03-08
- [x] Phase 3: Multi-Tenant Isolation (8/8 plans) — completed 2026-03-08
- [x] Phase 4: AI Governance (10/10 plans) — completed 2026-03-08
- [x] Phase 5: Operational Readiness (7/7 plans) — completed 2026-03-09
- [x] Phase 6: Wire Rate Limiting + SCIM Token (1/1 plans) — completed 2026-03-09
- [x] Phase 7: Wire Storage Quota Enforcement (2/2 plans) — completed 2026-03-09
- [x] Phase 8: Fix SSO Integration (1/1 plans) — completed 2026-03-09
- [x] Phase 9: Login Audit Events (1/1 plans) — completed 2026-03-09
- [x] Phase 10: Wire Audit Trail (1/1 plans) — completed 2026-03-09
- [x] Phase 11: Fix Rate Limiting Architecture (1/1 plans) — completed 2026-03-09

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0-alpha Pre-Production Launch (Phases 12–23) — SHIPPED 2026-03-12</summary>

- [x] Phase 12: Onboarding & First-Run UX (3/3 plans) — completed 2026-03-09
- [x] Phase 13: AI Provider Registry + Model Selection (4/4 plans) — completed 2026-03-10
- [x] Phase 14: Remote MCP Server Management (4/4 plans) — completed 2026-03-10
- [x] Phase 15: Related Issues (3/3 plans) — completed 2026-03-10
- [x] Phase 16: Workspace Role Skills (4/4 plans) — completed 2026-03-10
- [x] Phase 17: Skill Action Buttons (2/2 plans) — completed 2026-03-11
- [x] Phase 18: Tech Debt Closure (3/3 plans) — completed 2026-03-11
- [x] Phase 19: Skill Registry & Plugin System (4/4 plans) — completed 2026-03-11
- [x] Phase 20: Skill Template Catalog (4/4 plans) — completed 2026-03-11
- [x] Phase 21: Documentation & Verification Closure (2/2 plans) — completed 2026-03-12
- [x] Phase 22: Integration Safety — Session & OAuth2 UI (2/2 plans) — completed 2026-03-12
- [x] Phase 23: Tech Debt Sweep (2/2 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0-alpha-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0.0-alpha2 Notion-Style Restructure (Phases 24–29) — SHIPPED 2026-03-12</summary>

- [x] Phase 24: Page Tree Data Model (2/2 plans) — completed 2026-03-12
- [x] Phase 25: Tree API & Page Service (2/2 plans) — completed 2026-03-12
- [x] Phase 26: Sidebar Tree & Navigation (3/3 plans) — completed 2026-03-12
- [x] Phase 27: Project Hub & Issue Views (2/2 plans) — completed 2026-03-12
- [x] Phase 28: Visual Design Refresh (2/2 plans) — completed 2026-03-12
- [x] Phase 29: Responsive Layout & Drag-and-Drop (3/3 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0.0-alpha2-ROADMAP.md`

</details>

### 🚧 v1.1 Medium Editor & Artifacts (In Progress)

**Milestone Goal:** Transform the note editor into a polished Medium-style writing experience with file artifact uploads rendered as inline cards, a per-project artifacts management page with optimistic UI, and inline video embeds for YouTube/Vimeo.

- [x] **Phase 30: TipTap Extension Foundation** - Pull quote, heading toggle, extension registration patterns established (completed 2026-03-19)
- [x] **Phase 31: Storage Backend** - Artifact model, upload service, project_artifacts router, size enforcement (completed 2026-03-19)
- [ ] **Phase 32: Inline Editor Features** - FileCardNode, FigureNode, slash commands, drag-and-drop
- [x] **Phase 33: Video Embeds** - YouTube/Vimeo iframe players, paste detection, CSP (completed 2026-03-19)
- [x] **Phase 34: File Preview Modal** - Shared preview dialog with per-MIME renderers (completed 2026-03-19)
- [x] **Phase 35: Artifacts Management Page** - Per-project artifacts page with optimistic CRUD, search, sort (completed 2026-03-19)
- [x] **Phase 36: Editor UX Polish** - Focus mode (Cmd+Shift+F), distraction-free writing (completed 2026-03-19)

## Phase Details

### Phase 30: TipTap Extension Foundation
**Goal**: Editor extension infrastructure is sound — correct registration order, NodeView context bridge pattern, and markdown serialization contract are all verified on working nodes before any storage-dependent feature is built.
**Depends on**: Phase 29 (existing editor codebase)
**Requirements**: EDIT-01, EDIT-02
**Success Criteria** (what must be TRUE):
  1. User can toggle pull quote styling on any blockquote via floating toolbar, and the pull quote survives a page reload (round-trip serialization verified)
  2. User can toggle H1, H2, and H3 headings from the floating toolbar on a text selection
  3. New extensions appear in the correct Group 3 slot in `createEditorExtensions.ts` (before `BlockIdExtension`), verified by `editor.getJSON()` showing non-null `blockId` on new nodes
  4. NodeView wrapper pattern (plain component + context bridge, no `observer()` on the NodeView directly) is established and documented in a code comment for future nodes
**Plans**: 3 plans
Plans:
- [ ] 30-01-PLAN.md — TDD: Write RED test scaffolding for PullQuoteExtension, SelectionToolbar headings, and node-view-bridge
- [ ] 30-02-PLAN.md — Implement PullQuoteExtension (EDIT-01): attr toggle, markdown serialize, slash command, CSS, export
- [ ] 30-03-PLAN.md — Implement heading dropdown + node-view-bridge utility (EDIT-02 + bridge pattern)

### Phase 31: Storage Backend
**Goal**: Files can be stored and retrieved through a secure backend API — DB-first upload flow prevents orphaned storage objects, all three size enforcement layers are active, and workspace isolation is enforced at the application layer.
**Depends on**: Phase 30
**Requirements**: ARTF-04, ARTF-05, ARTF-06
**Success Criteria** (what must be TRUE):
  1. A file upload via the API is reflected in both the `artifacts` DB table (status: ready) and the `note-artifacts` Supabase Storage bucket with workspace-scoped key
  2. Uploading a file over 10MB is rejected with a 413 response at the FastAPI layer (not an unformatted Nginx HTML error)
  3. A file with a disallowed extension is rejected with a 422 response listing the allowed types
  4. A signed URL fetched from the backend grants time-limited read access to the artifact; a direct public bucket URL does not work
  5. A failed upload mid-stream (simulated) leaves no orphaned storage object — the stale `pending_upload` DB record is cleaned up by the 24h cleanup job
**Plans**: 3 plans
Plans:
- [ ] 31-01-PLAN.md — Alembic migration 090 + Artifact SQLAlchemy model + model registration
- [ ] 31-02-PLAN.md — ArtifactRepository, ArtifactUploadService, Pydantic schemas, cleanup job + MemoryWorker dispatch
- [ ] 31-03-PLAN.md — project_artifacts router (POST/GET/GET-url/DELETE) + DI wiring + human verify checkpoint

### Phase 32: Inline Editor Features
**Goal**: Users can insert images and files directly into notes as rendered inline blocks — images with optional captions, files as interactive cards that upload to the backend and display metadata.
**Depends on**: Phase 30, Phase 31
**Requirements**: ARTF-01, ARTF-02, ARTF-03, EDIT-04, EDIT-05
**Success Criteria** (what must be TRUE):
  1. User can insert an image into a note via the `/image` slash command; the image renders inline and persists after page reload
  2. User can add a caption below an inline image; the caption text is editable and persists after page reload
  3. User can drag and drop an image or file onto the editor canvas and it becomes an inline block
  4. User can insert a file card via the `/file` slash command; the card shows upload progress, then displays the filename, type, and size on completion
  5. File cards and images survive a note save/reload cycle (markdown serialization round-trip verified)
**Plans**: 5 plans
Plans:
- [ ] 32-01-PLAN.md — Infrastructure: ArtifactStore, artifactsApi, RootStore wiring, Wave 0 test scaffolds
- [ ] 32-02-PLAN.md — FileCardExtension: node + context bridge + FileCardNodeView (plain) + FileCardView (observer)
- [ ] 32-03-PLAN.md — FigureExtension: node + FigureNodeView (plain) + editable caption via NodeViewContent
- [ ] 32-04-PLAN.md — Editor wiring: slash commands + drop handler + extension registration + stale node cleanup
- [ ] 32-05-PLAN.md — Visual verification checkpoint: full test suite + human flow verification

### Phase 33: Video Embeds
**Goal**: Users can embed YouTube and Vimeo videos as inline players directly in notes — via slash command, URL paste, or manual URL entry — with proper iframe security controls in place.
**Depends on**: Phase 30
**Requirements**: VID-01, VID-02, VID-03, VID-04
**Success Criteria** (what must be TRUE):
  1. User can embed a YouTube video in a note via the `/video` slash command; the video renders as a playable inline iframe
  2. User can embed a Vimeo video in a note via the `/video` slash command; the video renders as a playable inline iframe
  3. Pasting a YouTube or Vimeo URL into the editor triggers an offer to embed; accepting replaces the plain URL with an inline player
  4. Video iframes render with `sandbox` and `allow` attributes enforced; arbitrary non-video URLs are rejected with a user-visible toast
  5. The Next.js CSP `frame-src` includes `youtube-nocookie.com` and `player.vimeo.com` — video iframes load in production without CSP errors
**Plans**: 3 plans
Plans:
- [ ] 33-01-PLAN.md — Install @tiptap/extension-youtube, implement YoutubeExtension and VimeoNode with tests (TDD RED/GREEN)
- [ ] 33-02-PLAN.md — Wire extensions into editor: Group 3 registration, /video slash command, VideoPasteDetector
- [ ] 33-03-PLAN.md — CSP frame-src headers in next.config.ts + responsive .video-embed CSS

### Phase 34: File Preview Modal
**Goal**: Users can preview uploaded file content directly in a modal — images render visually, text and code files render with formatting, CSV files render as tables, and unsupported types fall back to a download prompt.
**Depends on**: Phase 31
**Requirements**: PREV-01, PREV-02, PREV-03, PREV-04, PREV-05
**Success Criteria** (what must be TRUE):
  1. User can click a file card in the editor to open an image preview modal with the full-resolution image displayed
  2. User can preview Markdown, plain text, and JSON files in the modal with proper formatting (Markdown rendered, JSON syntax-highlighted)
  3. User can preview code files (Python, JS, HTML, CSS, etc.) in the modal with syntax highlighting
  4. User can preview CSV files in the modal rendered as a formatted table (capped at 500 rows with a visible truncation indicator if exceeded)
  5. User clicking a file type with no supported renderer sees a "Download" button as the fallback action
**Plans**: 2 plans
Plans:
- [ ] 34-01-PLAN.md — Install papaparse, create mime-type-router utility, useFileContent hook, test scaffolds
- [ ] 34-02-PLAN.md — Build 7 renderer components and FilePreviewModal shell; complete all tests

### Phase 35: Artifacts Management Page
**Goal**: Users can discover, manage, and act on all project artifacts from a dedicated page — with instant optimistic feedback on deletes, client-side search by filename, and sorting by type, date, or size.
**Depends on**: Phase 31, Phase 34
**Requirements**: MGMT-01, MGMT-02, MGMT-03, MGMT-04, MGMT-05, MGMT-06
**Success Criteria** (what must be TRUE):
  1. User navigating to `/{workspace}/projects/{id}/artifacts` sees all files uploaded to that project listed with filename, type icon, file size, uploader, and upload date
  2. User can click any artifact to open the `FilePreviewModal` inline on the management page (reusing the Phase 34 component)
  3. User can download any artifact directly from the management page
  4. User can delete an artifact and the row disappears immediately (optimistic UI); on server error, the row reappears with a visible error state
  5. User can type in a search box to filter artifacts by filename; results update with each keystroke
  6. User can sort artifacts by type, date, or size and the list reorders accordingly
**Plans**: 2 plans
Plans:
- [ ] 35-01-PLAN.md — Artifact types, API service, and TanStack Query hooks (data layer)
- [ ] 35-02-PLAN.md — ArtifactsPage component + ProjectSidebar nav link (UI layer)

### Phase 36: Editor UX Polish
**Goal**: Users can enter focus mode to hide all surrounding chrome and write without distraction — triggered by keyboard shortcut or toolbar toggle — with no conflicts with slash commands or other editor overlays.
**Depends on**: Phase 30
**Requirements**: EDIT-03
**Success Criteria** (what must be TRUE):
  1. User pressing Cmd+Shift+F enters focus mode — sidebar, header, and all chrome outside the editor are hidden
  2. User pressing Cmd+Shift+F again (or Escape) exits focus mode and all chrome reappears
  3. Slash command menu, floating toolbar, and file preview modal all remain functional while in focus mode (z-index hierarchy correct)
**Plans**: 2 plans
Plans:
- [ ] 36-01-PLAN.md — UIStore isFocusMode observable + AppShell sidebar/hamburger hide
- [ ] 36-02-PLAN.md — NoteCanvasProps threading + chrome hide + keyboard shortcut + focus button + exit affordance

### Phase 37: Artifact Preview Rendering Engine
**Goal**: Users can preview HTML files with a sandboxed live render toggle alongside the existing source code view — HTML defaults to source (safe-by-default) with an opt-in "Preview" mode using a DOMPurify-sanitized iframe with no JavaScript execution.
**Depends on**: Phase 34
**Requirements**: PREV-03
**Success Criteria** (what must be TRUE):
  1. User can open an HTML file in FilePreviewModal and see syntax-highlighted source code by default
  2. User can click a "Preview" tab to render HTML content in a sandboxed iframe (no script execution)
  3. User can toggle between source and preview views freely
  4. The iframe uses DOMPurify sanitization and a sandbox attribute that excludes allow-scripts
**Plans**: 2 plans
Plans:
- [ ] 37-01-PLAN.md — TDD: HtmlRenderer tests + HtmlRenderer component + mime-type-router update
- [ ] 37-02-PLAN.md — Wire HtmlRenderer into FilePreviewModal + update tests + visual verification

## Progress

**Execution Order:** 30 → 31 → 32 → 33 → 34 → 35 → 36

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1–11 | v1.0 | 46/46 | Complete | 2026-03-09 |
| 12–23 | v1.0-alpha | 37/37 | Complete | 2026-03-12 |
| 24–29 | v1.0.0-alpha2 | 14/14 | Complete | 2026-03-12 |
| 30. TipTap Extension Foundation | 3/3 | Complete   | 2026-03-19 | - |
| 31. Storage Backend | 3/3 | Complete   | 2026-03-19 | - |
| 32. Inline Editor Features | 4/5 | In Progress|  | - |
| 33. Video Embeds | 3/3 | Complete   | 2026-03-19 | - |
| 34. File Preview Modal | 2/2 | Complete   | 2026-03-19 | - |
| 35. Artifacts Management Page | 2/2 | Complete   | 2026-03-19 | - |
| 36. Editor UX Polish | 2/2 | Complete   | 2026-03-19 | - |
| 37. Artifact Preview Rendering Engine | 2/2 | Complete    | 2026-03-20 | - |

**Total: 29 phases complete, 97 plans, 86 requirements across 3 milestones | v1.1: 7 phases, 22 requirements**

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements*
*v1.0-alpha shipped: 2026-03-12 — 12 phases, 37 plans, 39/39 requirements + 7 gap closure items*
*v1.0.0-alpha2 shipped: 2026-03-12 — 6 phases, 14 plans, 17/17 requirements*
*v1.1 roadmap created: 2026-03-18 — 7 phases, 22 requirements*
