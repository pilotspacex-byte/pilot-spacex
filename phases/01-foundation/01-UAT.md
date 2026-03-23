---
status: testing
phase: milestone-v1.2-office-suite
source: 01-01-SUMMARY.md, 01-02-SUMMARY.md, 02-01-SUMMARY.md, 02-02-SUMMARY.md, 03-01-SUMMARY.md, 03-02-SUMMARY.md, 04-01-SUMMARY.md, 04-02-SUMMARY.md, 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-03-22T12:00:00Z
updated: 2026-03-22T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Upload Office Files
expected: |
  Upload a .docx, .xlsx, and .pptx file through the artifact upload UI. All three should upload successfully without "file type not allowed" error. They appear in the artifacts list with correct file icons.
awaiting: user response

## Tests

### 1. Upload Office Files
expected: Upload .docx, .xlsx, .pptx files — all accepted, appear in artifact list with correct icons
result: [pending]

### 2. Legacy Format Fallback
expected: Upload or open a .doc or .ppt file — shows "Download to view — this file format requires a desktop application" with download button (not a broken renderer)
result: [pending]

### 3. Word Document Preview
expected: Click a .docx artifact — modal shows rendered document with headings, bold, lists, tables, images preserved (not raw binary). Scrollable continuous view like Google Docs.
result: [pending]

### 4. Word — mammoth Fallback
expected: If a complex .docx fails to render via docx-preview, it seamlessly falls back to mammoth renderer — no error flash, document still readable (may have less formatting)
result: [pending]

### 5. Word — Page Break Indicators
expected: A .docx with page breaks shows visual dashed dividers with "Page break" labels between sections
result: [pending]

### 6. Word — Table of Contents Sidebar
expected: Click the TableOfContents icon in modal header — sidebar appears showing document headings (h1/h2/h3). Click a heading — scrolls to that section smoothly.
result: [pending]

### 7. Excel Spreadsheet Preview
expected: Click a .xlsx artifact — modal shows data as a scrollable table with column headers. Loading spinner visible during parse. Not frozen.
result: [pending]

### 8. Excel — Sheet Tab Navigation
expected: Open a multi-sheet .xlsx — tab bar appears at bottom. Click different tabs to switch sheets. Data updates.
result: [pending]

### 9. Excel — Frozen Header Row
expected: Scroll down in a spreadsheet — header row stays pinned at top (position: sticky)
result: [pending]

### 10. Excel — Column Resize
expected: Drag a column border in the header — column width changes. Resize is interactive.
result: [pending]

### 11. Excel — Search
expected: Type in search box above spreadsheet — matching cells highlight with subtle primary color background. Match count shown (e.g., "5 matches"). Clears when switching sheets.
result: [pending]

### 12. Excel — .xls Support
expected: Open a .xls file (Excel 97-2003) — renders as table just like .xlsx (SheetJS supports BIFF8). Does NOT show "download to view" fallback.
result: [pending]

### 13. PowerPoint Slide Preview
expected: Click a .pptx artifact — first slide renders on canvas. "Slide 1 of N" counter visible and accurate.
result: [pending]

### 14. PowerPoint — Slide Navigation
expected: Click Prev/Next buttons to move between slides — counter updates. Prev disabled on slide 1, Next disabled on last slide. Arrow keys also work.
result: [pending]

### 15. PowerPoint — Thumbnail Strip
expected: Toggle thumbnail sidebar — vertical strip appears on left showing small slide previews. Click any thumbnail to jump to that slide. Active slide has primary color border.
result: [pending]

### 16. PowerPoint — Fullscreen Slideshow
expected: Click Play/fullscreen button — slides fill screen with black background. Left/Right arrows navigate. Escape exits.
result: [pending]

### 17. PPTX — Add Annotation
expected: On a PPTX slide, toggle annotation panel (right side). Type a note and save. Annotation appears with your avatar, name, timestamp.
result: [pending]

### 18. PPTX — Annotation Persistence
expected: Add an annotation, close the modal, reopen the same .pptx on the same slide — annotation is still there (server-persisted).
result: [pending]

### 19. PPTX — Per-Slide Scoping
expected: Add annotations on slide 1 and slide 3. Navigate to slide 2 — no annotations shown. Navigate to slide 3 — only slide 3's annotations appear.
result: [pending]

### 20. PPTX — Edit/Delete Annotation
expected: Edit an existing annotation — text updates. Delete an annotation — removed from panel. Only your own annotations show edit/delete buttons.
result: [pending]

### 21. NoteCanvas — Office Preview via FileCard
expected: In a note with an uploaded .docx/.xlsx/.pptx FileCard, click the card — FilePreviewModal opens with the correct renderer (not download fallback). Same experience as from Artifacts page.
result: [pending]

## Summary

total: 21
passed: 0
issues: 0
pending: 21
skipped: 0

## Gaps

[none yet]
