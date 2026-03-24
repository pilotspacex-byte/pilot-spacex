# Phase 42: Command Palette and Breadcrumb Navigation - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-generated from roadmap, Phase 40 context, and VS Code feature comparison

<domain>
## Phase Boundary

Add three VS Code-inspired navigation features to the Monaco editor environment:
1. **Command palette** (Cmd+Shift+P) — searchable action list with fuzzy matching
2. **Breadcrumb navigation** — file path breadcrumbs above the editor with clickable segments
3. **Symbol outline panel** (Cmd+Shift+O) — hierarchical symbol view for navigating within files

All three features augment the existing editor (Phase 40) without modifying core editing behavior.

</domain>

<decisions>
## Implementation Decisions

### Command Palette
- Trigger: Cmd+Shift+P (macOS) / Ctrl+Shift+P (Windows/Linux)
- UI: Full-width overlay at top of editor area (like VS Code), not a modal dialog
- Fuzzy search: Use shadcn Command component (cmdk) — same pattern as QuickOpen from Phase 40
- Action categories: File (new, open, save), Edit (undo, redo, find, replace), View (toggle sidebar, toggle preview, zoom), Navigate (go to file, go to line, go to symbol), Note (insert PM block, toggle focus mode), AI (ghost text toggle, extract issues)
- Each action shows: icon, label, category badge, keyboard shortcut (if any)
- Actions are registered via a central `ActionRegistry` — new actions can be added without modifying the palette component
- Recently used actions appear at top (persist in localStorage, cap at 5)
- Empty state: "No matching actions" with suggestion text

### Breadcrumb Navigation
- Position: horizontal bar above the editor, below the tab bar
- Segments: Workspace name > Project name (if applicable) > File path segments (folder/file)
- Click behavior: clicking a segment opens a dropdown showing siblings at that level (other files in same folder, other projects in workspace)
- Selecting a sibling navigates to it (opens file via FileStore)
- Separator: chevron right icon (Lucide `ChevronRight`)
- Current segment (last) is bold, prior segments are muted text
- For notes: Workspace > Project > Note title
- For code files: Workspace > Project > path/to/file.ts (each path segment clickable)
- Overflow: horizontal scroll with fade-out edges when path is very long

### Symbol Outline Panel
- Trigger: Cmd+Shift+O (macOS) / Ctrl+Shift+O (Windows/Linux) toggles panel visibility
- Position: right sidebar panel, collapsible (like VS Code's outline)
- Width: 240px default, resizable
- For markdown/notes: extract headings (H1-H6) and PM block markers as symbols
- For code files: use Monaco's built-in `DocumentSymbolProvider` (returns functions, classes, variables, etc.)
- Tree view: collapsible hierarchy (headings nest under parent headings, methods nest under classes)
- Click to navigate: clicking a symbol scrolls the editor to that line
- Active symbol highlighted: tracks cursor position and highlights the current symbol
- Icons: Lucide icons per symbol kind (heading → `Hash`, function → `FunctionSquare`, class → `Box`, variable → `Variable`)
- Empty state: "No symbols found" for plain text files

### Keyboard Shortcuts
- Cmd+Shift+P: Command palette
- Cmd+Shift+O: Symbol outline toggle
- Cmd+P: Quick open (already exists from Phase 40)
- Cmd+G: Go to line (new action in palette + direct shortcut)
- Escape: Close palette/outline

### Claude's Discretion
- Action registry implementation details (Map vs array, lazy loading)
- Breadcrumb dropdown animation style
- Symbol outline refresh debounce timing
- Exact icon choices per symbol kind
- Command palette max visible items before scroll

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 40 Editor Foundation
- `frontend/src/features/editor/EditorLayout.tsx` — Three-panel layout (breadcrumbs integrate here)
- `frontend/src/features/editor/EditorToolbar.tsx` — Existing toolbar (palette trigger button goes here)
- `frontend/src/features/editor/MonacoNoteEditor.tsx` — Main editor (symbol extraction integrates here)
- `frontend/src/features/file-browser/components/QuickOpen.tsx` — Existing cmdk pattern (reuse for palette)
- `frontend/src/features/file-browser/components/TabBar.tsx` — Tab bar (breadcrumbs go below this)
- `frontend/src/features/file-browser/stores/FileStore.ts` — File/tab state (breadcrumbs read from this)
- `frontend/src/features/editor/markers/pmBlockMarkers.ts` — PM block parser (symbol outline uses this)

### UI Design System
- `specs/001-pilot-space-mvp/ui-design-spec.md` — UI/UX design spec v4.0
- `.impeccable.md` — Design context, brand personality

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QuickOpen.tsx` + `useQuickOpen.ts` — cmdk-based fuzzy search with Cmd+P trigger. Command palette is structurally identical (overlay + fuzzy search + action list). Reuse the pattern, not the component.
- `Command` shadcn component — Already installed and used by QuickOpen. Palette uses the same component.
- `FileStore` — Provides `activeFile`, `tabs`, `openFile()` for breadcrumb navigation and action dispatch.
- `pmBlockMarkers.ts` — `parsePMBlockMarkers()` extracts PM block positions for symbol outline.
- `EditorLayout.tsx` — Three-panel layout where breadcrumbs and outline panel integrate.

### Established Patterns
- `next/dynamic` with `ssr: false` for heavy components
- MobX `observer()` for components reading store state (breadcrumbs need activeFile)
- Keyboard shortcuts via `useEffect` + `addEventListener('keydown')` (see `useAutoSaveEditor.ts` for Cmd+S pattern)

### Integration Points
- `EditorLayout.tsx` — Breadcrumb bar inserts between TabBar and editor content area
- `EditorToolbar.tsx` — Palette trigger button (magnifying glass or command icon)
- `MonacoNoteEditor.tsx` — Symbol provider registration for outline panel
- Workspace layout — Palette overlay mounts at workspace level (above all panels)

</code_context>

<specifics>
## Specific Ideas

- Command palette should feel like VS Code's — instant open, keyboard-first, fuzzy search
- Breadcrumbs should feel like VS Code's — compact, clickable, contextual dropdowns
- Symbol outline should feel like VS Code's outline panel — tree view, click-to-navigate, active tracking
- All three features share the "keyboard-first navigation" philosophy — power users should never need the mouse

</specifics>

<deferred>
## Deferred Ideas

- Custom keybinding configuration UI — future phase (Phase 46 customization)
- Command palette extensions/plugins — Phase 45 (Editor Plugin API)
- Multi-file symbol search (workspace-wide) — would be its own feature
- Breadcrumb "recent files" dropdown — nice-to-have, not in scope

</deferred>

---

*Phase: 42-command-palette-and-breadcrumb-navigation*
*Context gathered: 2026-03-24 via auto mode*
