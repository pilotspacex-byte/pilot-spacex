# Requirements: Pilot Space v1.1 — Medium Editor & Artifacts

**Defined:** 2026-03-18
**Core Value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## v1.1 Requirements

Requirements for milestone v1.1. Each maps to roadmap phases.

### Editor UX

- [x] **EDIT-01**: User can toggle pull quote styling on blockquotes
- [x] **EDIT-02**: User can toggle H1/H2/H3 headings from floating toolbar on text selection
- [x] **EDIT-03**: User can enter focus mode (Cmd+Shift+F) to hide chrome and focus on writing
- [x] **EDIT-04**: User can insert images via /image slash command and drag-and-drop
- [x] **EDIT-05**: User can add captions to inline images (figure + figcaption)

### File Artifacts

- [x] **ARTF-01**: User can upload files (up to 10MB) into notes as inline card blocks
- [x] **ARTF-02**: User can drag-and-drop files onto the editor canvas to create file cards
- [x] **ARTF-03**: User can insert file cards via /file slash command
- [x] **ARTF-04**: System stores uploaded files in Supabase Storage with workspace isolation
- [x] **ARTF-05**: System enforces 10MB file size limit at client, API, and infrastructure layers
- [x] **ARTF-06**: System validates file types against an extension allowlist before storage

### Artifacts Management

- [x] **MGMT-01**: User can view all project artifacts on a dedicated per-project page
- [x] **MGMT-02**: User can preview artifacts inline on the management page
- [x] **MGMT-03**: User can download artifacts from the management page
- [x] **MGMT-04**: User can delete artifacts with instant optimistic UI feedback
- [x] **MGMT-05**: User can search artifacts by filename
- [x] **MGMT-06**: User can sort artifacts by type, date, or size

### Video Embeds

- [x] **VID-01**: User can embed YouTube videos in notes via /video slash command
- [x] **VID-02**: User can embed Vimeo videos in notes via /video slash command
- [x] **VID-03**: System auto-detects YouTube/Vimeo URLs on paste and offers to embed
- [x] **VID-04**: Video embeds render as inline players with proper iframe sandboxing

### File Preview

- [x] **PREV-01**: User can preview images in a popup modal from file cards
- [x] **PREV-02**: User can preview text, Markdown, and JSON files with proper formatting
- [x] **PREV-03**: User can preview code files with syntax highlighting (Python, JS, HTML, CSS, etc.)
- [x] **PREV-04**: User can preview CSV files as formatted tables
- [x] **PREV-05**: System provides download fallback for unsupported file types

## v1.2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### File Preview (Extended)

- **PREV-06**: User can preview Excel/XLSX files as formatted tables
- **PREV-07**: User can preview PDF files inline

### Artifacts Management (Extended)

- **MGMT-07**: User can toggle grid/list view on artifacts page
- **MGMT-08**: User can reuse artifacts across multiple notes
- **MGMT-09**: User can see "Used in" note deep-links on artifacts page

### Video Embeds (Extended)

- **VID-05**: Video embeds show thumbnail placeholder before iframe activation

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| PDF in-app preview (pdf.js) | ~2MB bundle; browser opens PDFs natively |
| Generic iframe embed for arbitrary URLs | CSP violations cause silent failures; YouTube + Vimeo only |
| Replacing SelectionToolbar with TipTap BubbleMenu | Breaks ghost text/slash command coordination (documented pitfall) |
| Bulk download as ZIP | Requires server-side assembly; low priority |
| Artifact version history | Complexity vs. value for v1.1 |
| Real-time websocket for artifacts page | Optimistic UI sufficient; infra overhead not justified |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EDIT-01 | Phase 30 | Complete |
| EDIT-02 | Phase 30 | Complete |
| EDIT-03 | Phase 36 | Complete |
| EDIT-04 | Phase 32 | Complete |
| EDIT-05 | Phase 32 | Complete |
| ARTF-01 | Phase 32 | Complete |
| ARTF-02 | Phase 32 | Complete |
| ARTF-03 | Phase 32 | Complete |
| ARTF-04 | Phase 31 | Complete |
| ARTF-05 | Phase 31 | Complete |
| ARTF-06 | Phase 31 | Complete |
| MGMT-01 | Phase 35 | Complete |
| MGMT-02 | Phase 35 | Complete |
| MGMT-03 | Phase 35 | Complete |
| MGMT-04 | Phase 35 | Complete |
| MGMT-05 | Phase 35 | Complete |
| MGMT-06 | Phase 35 | Complete |
| VID-01 | Phase 33 | Complete |
| VID-02 | Phase 33 | Complete |
| VID-03 | Phase 33 | Complete |
| VID-04 | Phase 33 | Complete |
| PREV-01 | Phase 34 | Complete |
| PREV-02 | Phase 34 | Complete |
| PREV-03 | Phase 34 | Complete |
| PREV-04 | Phase 34 | Complete |
| PREV-05 | Phase 34 | Complete |

**Coverage:**
- v1.1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation — all 22 requirements mapped*
