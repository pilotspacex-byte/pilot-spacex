# Requirements: Pilot Space — Office Suite Preview

**Defined:** 2026-03-21
**Core Value:** Think first, structure later — notes are the entry point, not forms.

## v1.2 Requirements

Requirements for Office Suite Preview milestone. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: System supports ArrayBuffer fetch mode in useFileContent for binary file types (xlsx, docx, pptx)
- [x] **FOUND-02**: User can upload .docx, .doc, .pptx, .ppt files (backend allowlist extension)
- [x] **FOUND-03**: System routes Office MIME types to correct renderer via mime-type-router
- [x] **FOUND-04**: User sees "Download to view" fallback for legacy binary formats (.doc, .xls, .ppt) that cannot be parsed client-side

### Excel Preview

- [x] **XLSX-01**: User can preview .xlsx/.xls files as a scrollable table with headers, rows, and column alignment
- [x] **XLSX-02**: User can switch between sheets via tab bar for multi-sheet workbooks
- [x] **XLSX-03**: User can resize columns by dragging and freeze the header row while scrolling
- [x] **XLSX-04**: User can search within spreadsheet data with highlight matching

### Word Preview

- [x] **DOCX-01**: User can preview .docx files with preserved formatting (fonts, colors, alignment, images) via docx-preview
- [x] **DOCX-02**: System falls back to mammoth.js renderer when docx-preview fails on complex documents
- [x] **DOCX-03**: User sees visual page-break indicators in scrollable document view
- [x] **DOCX-04**: User can navigate document sections via table of contents sidebar extracted from DOCX headings

### PowerPoint Preview

- [x] **PPTX-01**: User can view PPTX slides one at a time with prev/next navigation and "Slide N of M" counter
- [x] **PPTX-02**: User sees slide thumbnail strip sidebar for quick navigation to any slide
- [x] **PPTX-03**: User can add per-slide annotations linked to Pilot Space notes (persisted server-side)
- [x] **PPTX-04**: User can enter fullscreen slideshow mode with keyboard navigation (arrow keys)

## v1.3 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Office Editing

- **EDIT-01**: User can edit Excel cells inline with changes saved back to storage
- **EDIT-02**: User can edit Word document text inline with formatting preserved
- **EDIT-03**: User can collaborate on Office documents in real-time (Google Docs-like)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Formula evaluation in Excel | Requires SheetJS Pro license ($); stored/last-computed values sufficient for preview |
| Live editing of Office documents | Deferred to v1.3; validate preview need first before investing in complex editing |
| Server-side file conversion | Client-side only approach; no server dependency, works with signed URLs |
| File size limit increase | 10 MB limit sufficient per user decision; covers most Office documents |
| PDF preview | Not requested; current download fallback acceptable |
| Video/audio preview | Out of scope; existing download fallback covers these |
| Print from preview | Low priority; users can download and print natively |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| XLSX-01 | Phase 3 | Complete |
| XLSX-02 | Phase 3 | Complete |
| XLSX-03 | Phase 3 | Complete |
| XLSX-04 | Phase 3 | Complete |
| DOCX-01 | Phase 2 | Complete |
| DOCX-02 | Phase 2 | Complete |
| DOCX-03 | Phase 2 | Complete |
| DOCX-04 | Phase 2 | Complete |
| PPTX-01 | Phase 4 | Complete |
| PPTX-02 | Phase 4 | Complete |
| PPTX-03 | Phase 5 | Complete |
| PPTX-04 | Phase 4 | Complete |

**Coverage:**
- v1.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 — traceability filled after roadmap creation*
