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

- [ ] **Phase 30: TipTap Extension Foundation** - Pull quote, heading toggle, extension registration patterns established
- [ ] **Phase 31: Storage Backend** - Artifact model, upload service, project_artifacts router, size enforcement
- [ ] **Phase 32: Inline Editor Features** - FileCardNode, FigureNode, slash commands, drag-and-drop
- [ ] **Phase 33: Video Embeds** - YouTube/Vimeo iframe players, paste detection, CSP
- [ ] **Phase 34: File Preview Modal** - Shared preview dialog with per-MIME renderers
- [ ] **Phase 35: Artifacts Management Page** - Per-project artifacts page with optimistic CRUD, search, sort
- [ ] **Phase 36: Editor UX Polish** - Focus mode (Cmd+Shift+F), distraction-free writing

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

### Phase 36: Editor UX Polish
**Goal**: Users can enter focus mode to hide all surrounding chrome and write without distraction — triggered by keyboard shortcut or toolbar toggle — with no conflicts with slash commands or other editor overlays.
**Depends on**: Phase 30
**Requirements**: EDIT-03
**Success Criteria** (what must be TRUE):
  1. User pressing Cmd+Shift+F enters focus mode — sidebar, header, and all chrome outside the editor are hidden
  2. User pressing Cmd+Shift+F again (or Escape) exits focus mode and all chrome reappears
  3. Slash command menu, floating toolbar, and file preview modal all remain functional while in focus mode (z-index hierarchy correct)
**Plans**: TBD

## Progress

**Execution Order:** 30 → 31 → 32 → 33 → 34 → 35 → 36

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1–11 | v1.0 | 46/46 | Complete | 2026-03-09 |
| 12–23 | v1.0-alpha | 37/37 | Complete | 2026-03-12 |
| 24–29 | v1.0.0-alpha2 | 14/14 | Complete | 2026-03-12 |
| 30. TipTap Extension Foundation | v1.1 | 0/? | Not started | - |
| 31. Storage Backend | v1.1 | 0/? | Not started | - |
| 32. Inline Editor Features | v1.1 | 0/? | Not started | - |
| 33. Video Embeds | v1.1 | 0/? | Not started | - |
| 34. File Preview Modal | v1.1 | 0/? | Not started | - |
| 35. Artifacts Management Page | v1.1 | 0/? | Not started | - |
| 36. Editor UX Polish | v1.1 | 0/? | Not started | - |

**Total: 29 phases complete, 97 plans, 86 requirements across 3 milestones | v1.1: 7 phases, 22 requirements**

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements*
*v1.0-alpha shipped: 2026-03-12 — 12 phases, 37 plans, 39/39 requirements + 7 gap closure items*
*v1.0.0-alpha2 shipped: 2026-03-12 — 6 phases, 14 plans, 17/17 requirements*
*v1.1 roadmap created: 2026-03-18 — 7 phases, 22 requirements*
