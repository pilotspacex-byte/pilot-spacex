# Phase 43: LSP Integration and Code Intelligence - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-generated from roadmap, Phase 40/42 context, and VS Code comparison

<domain>
## Phase Boundary

Integrate Language Server Protocol capabilities into the Monaco editor for code intelligence: autocomplete, hover info, go-to-definition, find references, signature help, and diagnostics. Target TypeScript/JavaScript (primary), Python (secondary), and leverage Monaco's built-in language support for JSON/CSS/HTML. All language services run in the browser via Web Workers — no backend language server dependency.

</domain>

<decisions>
## Implementation Decisions

### Language Coverage
- **TypeScript/JavaScript** (primary) — Monaco's built-in TypeScript language service (already bundled with `monaco-editor`). Full IntelliSense: autocomplete, hover types, go-to-definition, find references, signature help, diagnostics with inline squiggles.
- **Python** (secondary) — Pyright WASM build running in a Web Worker. Provides type checking, autocomplete, hover info, go-to-definition within file. Limited cross-file resolution (no full project analysis in browser).
- **JSON/CSS/HTML** — Monaco's built-in language services (already working out of the box). No additional work needed beyond ensuring they're not disabled.
- **Markdown** — No LSP (notes use custom decorations from Phase 40). Ghost text AI serves as the "intelligence" layer for notes.

### LSP Hosting Model
- Browser-hosted via Web Workers — no backend language server processes
- TypeScript: `monaco.languages.typescript.getTypeScriptWorker()` — built-in, zero config
- Python: Pyright WASM (`pyright-browser` or similar) loaded as a Web Worker
- No socket-based LSP protocol — use Monaco's native language registration APIs (`registerCompletionItemProvider`, `registerHoverProvider`, etc.)
- Workers loaded lazily per language on first file open of that type

### Code Intelligence Features
- **Autocomplete** — Monaco's native suggest widget with type-aware completions. Trigger on `.` (dot) and explicit invoke (Ctrl+Space). Show type info and documentation in suggest detail pane.
- **Hover info** — Type information + documentation on mouse hover. Uses Monaco's `registerHoverProvider`. Show parameter types, return types, JSDoc/docstrings.
- **Go-to-definition (F12)** — Within-file navigation (jump to symbol definition). For Tauri desktop with local files: cross-file navigation within the repo. For web: within-file only.
- **Find references (Shift+F12)** — Within-file references. Shows peek view (inline reference list like VS Code). Cross-file deferred to future.
- **Signature help** — Function parameter hints on `(` trigger. Shows parameter names, types, and optional markers.
- **Diagnostics** — Inline squiggly underlines (errors red, warnings yellow, info blue). Plus a collapsible Problems panel below the editor showing all diagnostics with file, line, message. Click to navigate.

### Diagnostics Panel
- Position: collapsible panel below the editor area (like VS Code's PROBLEMS tab)
- Shows: icon (error/warning/info) + file name + line number + message
- Click to navigate: opens the file and scrolls to the line
- Badge count on panel header: "3 errors, 2 warnings"
- Auto-refreshes on file save and language worker response
- Filters: All / Errors / Warnings toggle

### Platform Differences
- **Web app**: TypeScript + JSON/CSS/HTML intelligence (Monaco built-in). Python limited to Pyright WASM (if bundle size acceptable).
- **Tauri desktop**: Same as web + cross-file go-to-definition via `tauri-plugin-fs` file reading.
- **Bundle size budget**: Pyright WASM is ~5-8MB. Must be lazy-loaded and only fetched when a `.py` file is opened. Show loading indicator while worker initializes.

### Claude's Discretion
- Pyright WASM bundle strategy (CDN vs bundled vs on-demand)
- TypeScript lib definitions loading (which lib.d.ts files to include)
- Diagnostics panel exact layout and animation
- Hover tooltip max width and content truncation
- Auto-import suggestion strategy
- Debounce timing for diagnostics refresh

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 40 Editor Foundation
- `frontend/src/features/editor/MonacoNoteEditor.tsx` — Main editor (register language providers here)
- `frontend/src/features/editor/MonacoFileEditor.tsx` — File editor (language providers apply here)
- `frontend/src/features/editor/hooks/useMonacoNote.ts` — Composite hook (extend with language features)
- `frontend/src/features/editor/themes/pilotSpaceTheme.ts` — Theme (diagnostic colors must match)

### Phase 42 Navigation
- `frontend/src/features/command-palette/registry/ActionRegistry.ts` — Register "Go to Definition", "Find References" as actions
- `frontend/src/features/symbol-outline/hooks/useSymbolOutline.ts` — Symbol extraction (LSP symbols are richer)

### Design System
- `specs/001-pilot-space-mvp/ui-design-spec.md` — UI/UX design spec
- `.impeccable.md` — Brand personality

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Monaco's built-in TypeScript language service — already bundled, just needs configuration
- `@monaco-editor/react` 4.7.0 — handles worker setup via CDN loader
- `pilotSpaceTheme.ts` — Theme tokens that diagnostic colors should reference
- `useSymbolOutline.ts` — Can be enhanced to use LSP symbols instead of regex parsing for code files

### Established Patterns
- Monaco hooks in `frontend/src/features/editor/hooks/` — new language hooks follow same pattern
- `useEffect` for provider registration with cleanup via `IDisposable.dispose()`
- Dynamic imports for heavy features (`next/dynamic` with `ssr: false`)

### Integration Points
- `MonacoFileEditor.tsx` — Primary integration point for code file intelligence
- `MonacoNoteEditor.tsx` — Only for markdown (no LSP, but diagnostics for embedded code blocks could be future)
- `EditorLayout.tsx` — Problems panel mounts below the editor content area
- `ActionRegistry` — Register go-to-definition, find-references, etc. as palette actions

</code_context>

<specifics>
## Specific Ideas

- TypeScript intelligence should feel identical to VS Code — same autocomplete, same hover info, same go-to-definition
- Python intelligence should feel like a lightweight PyCharm — type hints, autocomplete, but not full project analysis
- The Problems panel should feel like VS Code's PROBLEMS tab — same icon language, same click-to-navigate
- Loading states for language workers should be smooth — skeleton or spinner in suggest widget while worker initializes

</specifics>

<deferred>
## Deferred Ideas

- Cross-file go-to-definition on web (requires indexing strategy) — future enhancement
- Full Python project analysis (requires server-side Pyright) — future
- Go, Rust, Java, C# language support — add per-language as demand warrants
- Auto-import suggestions — complex, defer
- Code actions / quick fixes — VS Code-level feature, defer
- Linting integration (ESLint, Ruff) — separate from LSP, defer

</deferred>

---

*Phase: 43-lsp-integration-and-code-intelligence*
*Context gathered: 2026-03-24 via auto mode*
