# Roadmap: Pilot Space — v1.2 Office Suite Preview

## Overview

This milestone extends the existing Pilot Space artifact preview pipeline to handle Office binary formats. The work proceeds in five phases: a shared foundation that unblocks all renderers (ArrayBuffer fetch mode, backend allowlist, MIME routing), followed by three renderer phases ordered by risk (Word first to validate the pipeline, then Excel for its additional architectural decisions, then PowerPoint base), and finally the PPTX annotation differentiator which requires a stable renderer and new backend schema before it can be safely implemented.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Unblock all Office renderers with ArrayBuffer fetch mode, backend allowlist extension, and MIME-type routing (completed 2026-03-22)
- [ ] **Phase 2: Word Renderer** - Preview .docx files with preserved formatting; graceful fallback for legacy .doc
- [ ] **Phase 3: Excel Renderer** - Preview .xlsx/.xls files as navigable spreadsheet with multi-sheet tabs and 500-row cap
- [ ] **Phase 4: PowerPoint Base** - Slide-by-slide .pptx preview with navigation controls and fullscreen mode
- [ ] **Phase 5: PPTX Annotations** - Per-slide annotations linked to Pilot Space notes, persisted server-side

## Phase Details

### Phase 1: Foundation
**Goal**: All Office binary file types can be uploaded and routed to the correct renderer without data corruption
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. User can upload .docx, .doc, .pptx, and .ppt files through the artifact upload UI without a "file type not allowed" error
  2. useFileContent returns an ArrayBuffer (not a string) when fetching .xlsx, .docx, and .pptx files — verified by no "Invalid signature" parse errors in renderer phases
  3. mime-type-router routes .xlsx/.xls to 'xlsx', .docx/.doc to 'docx', and .pptx/.ppt to 'pptx' renderer types
  4. User sees a "Download to view" fallback message when opening .doc or .ppt legacy binary files in the artifact modal
**Plans:** 2/2 plans complete
Plans:
- [ ] 01-01-PLAN.md — MIME routing, ArrayBuffer fetch mode, backend allowlist
- [ ] 01-02-PLAN.md — Legacy format fallback and FilePreviewModal wiring

### Phase 2: Word Renderer
**Goal**: Users can read .docx documents inside the artifact modal with formatting preserved; .doc files degrade gracefully to a download prompt
**Depends on**: Phase 1
**Requirements**: DOCX-01, DOCX-02, DOCX-03, DOCX-04
**Success Criteria** (what must be TRUE):
  1. User can open a .docx file in the artifact modal and see rendered text with headings, bold, italic, lists, tables, and inline images — not raw binary
  2. When docx-preview fails on a complex document, user sees the document rendered via mammoth fallback without a blank or error screen
  3. User sees visual page-break dividers in the scrollable document view separating logical pages
  4. User can open a sidebar showing the document's table of contents (extracted from DOCX headings) and click a heading to jump to that section
**Plans:** 2 plans
Plans:
- [ ] 02-01-PLAN.md — DocxRenderer with docx-preview primary, mammoth fallback, DOCX_PURIFY_CONFIG security, page-break indicators
- [ ] 02-02-PLAN.md — Table of contents sidebar with heading extraction and modal toggle

### Phase 3: Excel Renderer
**Goal**: Users can inspect .xlsx and .xls spreadsheet data inside the artifact modal with sheet navigation, without freezing the browser
**Depends on**: Phase 2
**Requirements**: XLSX-01, XLSX-02, XLSX-03, XLSX-04
**Success Criteria** (what must be TRUE):
  1. User can open a .xlsx or .xls file and see data as a scrollable table with column headers aligned — not raw binary or an error
  2. User can switch between sheets in a multi-sheet workbook by clicking tabs in a tab bar below the spreadsheet
  3. User can drag column borders to resize columns and scroll the data while the header row stays frozen at the top
  4. User can type in a search box and see matching cells highlighted in the spreadsheet with the result count shown
  5. Opening a large spreadsheet (up to 10 MB) does not freeze the browser tab; a loading spinner is visible during parse
**Plans:** 2 plans
Plans:
- [ ] 03-01-PLAN.md — Install SheetJS, create XlsxRenderer with sheet tabs and 500-row cap, wire into FilePreviewModal
- [ ] 03-02-PLAN.md — Column resize, frozen header, search with debounced highlight

### Phase 4: PowerPoint Base
**Goal**: Users can view each slide of a .pptx presentation one at a time with navigation controls and fullscreen mode; .ppt files degrade gracefully
**Depends on**: Phase 3
**Requirements**: PPTX-01, PPTX-02, PPTX-04
**Success Criteria** (what must be TRUE):
  1. User can open a .pptx file and view the first slide rendered; "Slide 1 of N" counter is visible and accurate
  2. User can click Prev and Next buttons (or arrow keys in fullscreen) to move between slides — the counter updates with each navigation
  3. User can see a thumbnail strip sidebar showing all slides and click any thumbnail to jump directly to that slide
  4. User can enter fullscreen slideshow mode and use left/right arrow keys to advance and retreat between slides
**Plans:** 2 plans
Plans:
- [ ] 04-01-PLAN.md — PptxRenderer with navigation controls, fullscreen mode, slide state in FilePreviewModal
- [ ] 04-02-PLAN.md — Thumbnail strip sidebar with lazy rendering and toggle

### Phase 5: PPTX Annotations
**Goal**: Users can attach text annotations to individual PPTX slides, linked to the current project context, and see them persist across page reloads
**Depends on**: Phase 4
**Requirements**: PPTX-03
**Success Criteria** (what must be TRUE):
  1. User can open the annotation panel on any slide, type a note, and save it — the annotation is visible the next time they open the same PPTX artifact
  2. Each annotation is stored against a specific slide index so navigating to slide 3 shows only slide 3's annotations
  3. User can edit or delete an existing slide annotation from the annotation panel
**Plans:** 2 plans
Plans:
- [ ] 05-01-PLAN.md — Backend: ArtifactAnnotation model, migration with RLS, repository, CRUD API router, DI wiring
- [ ] 05-02-PLAN.md — Frontend: API client, TanStack Query hooks, PptxAnnotationPanel, FilePreviewModal wiring

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete   | 2026-03-22 |
| 2. Word Renderer | 0/2 | Planning complete | - |
| 3. Excel Renderer | 0/2 | Planning complete | - |
| 4. PowerPoint Base | 0/2 | Planning complete | - |
| 5. PPTX Annotations | 0/2 | Planning complete | - |
