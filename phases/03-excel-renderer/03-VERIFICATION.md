---
phase: 03-excel-renderer
verified: 2026-03-22T00:00:00Z
status: gaps_found
score: 11/12 must-haves verified
gaps:
  - truth: "User can open a .xls file in the artifact modal and see data rendered identically to .xlsx"
    status: failed
    reason: "FilePreviewModal.isLegacyOfficeFormat() classifies '.xls' as a legacy format and short-circuits to DownloadFallback with reason='legacy' before the xlsx renderer is reached. mime-type-router.ts correctly routes .xls to 'xlsx' RendererType (line 174), and useFileContent returns ArrayBuffer for 'xlsx' type, but the early-exit guard in renderContent() (lines 264-268 of FilePreviewModal.tsx) catches .xls before the switch statement, blocking the renderer entirely."
    artifacts:
      - path: "frontend/src/features/artifacts/components/FilePreviewModal.tsx"
        issue: "isLegacyOfficeFormat() includes 'xls' (line 252), causing .xls files to show a download fallback instead of the XlsxRenderer. SheetJS 0.20.3 supports .xls (BIFF8) via the same XLSX.read() call, so no parser limitation exists."
    missing:
      - "Remove 'xls' from the isLegacyOfficeFormat check — keep only 'doc' and 'ppt' as legacy formats. .xls is supported by SheetJS CE and should flow through to XlsxRenderer."
human_verification:
  - test: "Open a .xlsx file with multiple sheets in the artifact modal"
    expected: "Table renders with column headers in row 1, data rows below, sheet tabs visible at bottom, spinner shown briefly during parse"
    why_human: "Cannot exercise browser ArrayBuffer fetch + SheetJS DOM rendering programmatically"
  - test: "Open a large .xlsx file (>500 rows)"
    expected: "Spinner shows briefly, then truncation banner 'Showing 500 of N rows. Download for full data.' appears above the table; no browser freeze"
    why_human: "Performance and spinner visibility require live browser interaction"
  - test: "Drag a column border in the spreadsheet table"
    expected: "Column width changes smoothly; adjacent columns are unaffected; no text overflow"
    why_human: "JS drag handler (mousedown/mousemove/mouseup) requires manual UI interaction"
  - test: "Scroll down past 20+ rows"
    expected: "Header row stays pinned at the top of the table while data rows scroll underneath"
    why_human: "sticky positioning within Radix ScrollArea viewport requires visual confirmation"
  - test: "Type a search term in the search box"
    expected: "After 300ms debounce, matching cells are highlighted with a subtle primary-color background; match count (e.g. '3 matches') shown next to input; switching sheets clears the search"
    why_human: "Debounce timing and highlight rendering require live browser interaction"
---

# Phase 3: Excel Renderer Verification Report

**Phase Goal:** Users can inspect .xlsx and .xls spreadsheet data inside the artifact modal with sheet navigation, without freezing the browser
**Verified:** 2026-03-22
**Status:** gaps_found (1 gap blocking full goal achievement)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can open a .xlsx file and see data rendered as a table with column headers | VERIFIED | XlsxRenderer.tsx lines 186–222: Table renders headers via sheetData.headers, rows via sheetData.rows |
| 2 | User can open a .xls file and see data rendered identically to .xlsx | FAILED | FilePreviewModal.tsx line 252: `isLegacyOfficeFormat()` includes `'xls'`, causing .xls files to return DownloadFallback before reaching XlsxRenderer |
| 3 | User can click sheet tabs at the bottom to switch sheets in a multi-sheet workbook | VERIFIED | XlsxRenderer.tsx lines 223–240: sheet tab bar renders when SheetNames.length > 1; onClick sets activeSheet |
| 4 | First sheet is active by default when a workbook is opened | VERIFIED | XlsxRenderer.tsx line 66: `setActiveSheet(wb.SheetNames[0] ?? '')` in the parse useEffect |
| 5 | Large spreadsheets show at most 500 rows with a truncation banner | VERIFIED | XlsxRenderer.tsx line 29: `const MAX_ROWS = 500`; line 101: `truncated = totalRows > MAX_ROWS`; lines 167–170: truncation banner |
| 6 | A loading spinner is visible while the file is being parsed | VERIFIED | XlsxRenderer.tsx lines 149–158: spinner rendered when `isParsing` is true; deferred via `setTimeout(fn, 0)` to allow render before blocking parse |
| 7 | User can drag column borders to resize columns | VERIFIED | XlsxRenderer.tsx lines 126–147: JS drag handler on mousedown; document listeners for mousemove/mouseup; colWidths state map |
| 8 | Header row stays frozen at the top while scrolling through data rows | VERIFIED | XlsxRenderer.tsx line 187: `<TableHeader className="sticky top-0 z-10 bg-background">` |
| 9 | User can type in a search box and see matching cells highlighted | VERIFIED | XlsxRenderer.tsx lines 31–42: highlightCell() wraps match in `<mark className="bg-primary/20 ...">` |
| 10 | Search result count is displayed next to the search input | VERIFIED | XlsxRenderer.tsx lines 179–183: `{matchCount} {matchCount === 1 ? 'match' : 'matches'}` rendered when searchTerm is active |
| 11 | Switching sheets clears the search input and highlights | VERIFIED | XlsxRenderer.tsx lines 78–82: useEffect on `[activeSheet]` resets searchInput, searchTerm, and colWidths |
| 12 | Search input is debounced at 300ms | VERIFIED | XlsxRenderer.tsx lines 84–88: `setTimeout(() => setSearchTerm(searchInput), 300)` with cleanup |

**Score:** 11/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/features/artifacts/components/renderers/XlsxRenderer.tsx` | Excel renderer with sheet tabs, 500-row cap, frozen header, column resize, search | VERIFIED | 243 lines, exports `XlsxRenderer`; all features implemented and substantive |
| `frontend/package.json` | SheetJS dependency | VERIFIED | Line 103: `"xlsx": "https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz"` |
| `frontend/src/features/artifacts/components/FilePreviewModal.tsx` | Dynamic import + case 'xlsx' | PARTIAL | XlsxRenderer dynamically imported (ssr:false, lines 47–50); case 'xlsx' wired in switch (lines 310–312); BUT isLegacyOfficeFormat blocks .xls files (line 252) |
| `frontend/src/features/artifacts/utils/mime-type-router.ts` | 'xlsx' RendererType, routes .xls and .xlsx | VERIFIED | Lines 26–28: 'xlsx' in RendererType union; line 174: `ext === 'xlsx' || ext === 'xls'` → 'xlsx' |
| `frontend/src/features/artifacts/hooks/useFileContent.ts` | ArrayBuffer mode for xlsx renderer type | VERIFIED | Line 24: `BINARY_RENDERER_TYPES = new Set(['xlsx', 'docx', 'pptx'])`; lines 79–81: `res.arrayBuffer()` for binary types |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `FilePreviewModal.tsx` | `XlsxRenderer.tsx` | dynamic import + case 'xlsx' | WIRED (with gap) | Import at lines 47–50 (`ssr: false`); case 'xlsx' at lines 310–312 returns `<XlsxRenderer content={content as ArrayBuffer} />`; .xls files intercepted before this path |
| `XlsxRenderer.tsx` | `xlsx` (SheetJS) | `XLSX.read(content, { dense: true })` | VERIFIED | Line 64: `XLSX.read(content, { dense: true })` inside setTimeout(fn, 0); `XLSX.utils.sheet_to_json` at line 94 |
| `XlsxRenderer search input` | `XlsxRenderer table cells` | debounced searchTerm + bg-primary/20 highlight | VERIFIED | searchInput → 300ms debounce → searchTerm → matchCount useMemo → highlightCell() called in TableHead (line 195) and TableCell (line 215) |
| `XlsxRenderer thead` | ScrollArea viewport | `sticky top-0` on TableHeader | VERIFIED | Line 187: `className="sticky top-0 z-10 bg-background"` on `<TableHeader>` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| XLSX-01 | 03-01 | User can preview .xlsx/.xls files as a scrollable table with headers, rows, and column alignment | PARTIAL | .xlsx: fully working. .xls: blocked by isLegacyOfficeFormat() in FilePreviewModal — degrades to download fallback instead of table |
| XLSX-02 | 03-01 | User can switch between sheets via tab bar for multi-sheet workbooks | SATISFIED | Sheet tab bar renders when SheetNames.length > 1; clicking tabs calls setActiveSheet; first sheet active by default |
| XLSX-03 | 03-02 | User can resize columns by dragging and freeze the header row while scrolling | SATISFIED | JS drag handler with mousedown/mousemove/mouseup on document; sticky top-0 z-10 bg-background on TableHeader |
| XLSX-04 | 03-02 | User can search within spreadsheet data with highlight matching | SATISFIED | 300ms debounce; bg-primary/20 mark highlight on matching cells; match count display; search resets on sheet switch |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `FilePreviewModal.tsx` | 252 | `return ext === 'doc' \|\| ext === 'xls' \|\| ext === 'ppt'` — includes 'xls' in legacy gate | Blocker | .xls files never reach XlsxRenderer; silently falls back to DownloadFallback with reason="legacy". XLSX-01 requirement half-satisfied. |

No TODO/FIXME/placeholder comments found in modified files. No empty return statements. No console.log-only handlers.

---

## Human Verification Required

### 1. .xlsx table rendering

**Test:** Open a multi-sheet .xlsx file in the artifact modal
**Expected:** Brief spinner, then table with column headers, data rows with alternating bg-muted/30, sheet tabs at bottom
**Why human:** Browser ArrayBuffer fetch + SheetJS DOM rendering cannot be exercised programmatically

### 2. Large file truncation

**Test:** Open a .xlsx file with more than 500 rows
**Expected:** Spinner briefly appears, then "Showing 500 of N rows. Download for full data." banner displays above the table; browser does not freeze
**Why human:** Performance and spinner timing require live browser interaction

### 3. Column resize drag

**Test:** Hover over the right edge of a column header; drag left or right
**Expected:** Column width changes smoothly; colWidths state persists while on the same sheet; switching sheets resets widths
**Why human:** Drag handler (mousedown/mousemove/mouseup) requires manual UI interaction

### 4. Frozen header scroll

**Test:** Open a spreadsheet with 20+ rows; scroll vertically
**Expected:** Header row remains pinned at top of the scroll container; data rows scroll underneath
**Why human:** sticky positioning within Radix ScrollArea viewport requires visual verification

### 5. Search debounce and highlight

**Test:** Type a search term in the "Search in sheet..." input; observe timing and highlight
**Expected:** Cells highlight with a subtle primary-color background after ~300ms; match count appears; switching sheets clears the input
**Why human:** Debounce timing and highlight style correctness require live browser interaction

---

## Gaps Summary

One gap blocks XLSX-01 (and therefore the phase goal for .xls files):

**`.xls` files fall back to download instead of rendering as a table.**

The gap exists because `FilePreviewModal.isLegacyOfficeFormat()` includes `'xls'` alongside `'doc'` and `'ppt'` as legacy formats that cannot be parsed client-side. However:
- `mime-type-router.ts` correctly routes `.xls` → RendererType `'xlsx'`
- `useFileContent.ts` correctly returns `ArrayBuffer` for the `'xlsx'` renderer type
- `XlsxRenderer.tsx` uses `XLSX.read()` which supports `.xls` (BIFF8 format) in SheetJS CE 0.20.3

The fix is minimal: remove `'xls'` from `isLegacyOfficeFormat()` so that `.xls` files follow the same code path as `.xlsx` files. The `.doc` and `.ppt` entries in the guard are still correct (Word binary format and PowerPoint binary format are not supported by mammoth.js or the current pptx renderer).

All other phase deliverables — SheetJS install, deferred parse with spinner, 500-row cap, truncation banner, multi-sheet tabs, frozen header, column resize drag handler, and search with debounced highlight — are fully implemented and wired.

---

_Verified: 2026-03-22_
_Verifier: Claude (gsd-verifier)_
