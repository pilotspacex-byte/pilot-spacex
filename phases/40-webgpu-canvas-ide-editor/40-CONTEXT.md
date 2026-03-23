# Phase 40: WebGPU Note Canvas + IDE File Editor - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate the note editor from TipTap/ProseMirror (DOM-based) to Monaco Editor (Canvas-based) as the base rendering layer, achieving GPU-accelerated performance. Add full IDE-like file editing capabilities — file tree browser, quick open, syntax-highlighted file editing, and rendered markdown preview. TipTap features (PM blocks, ghost text, slash commands, collab) are rebuilt as Monaco widgets/decorations within Monaco's Canvas viewport.

Two tracks:
1. **Editor migration** — Monaco becomes the base layer. TipTap block model maps onto Monaco view zones/widgets. Yjs collab connects through y-monaco.
2. **IDE file editor** — Full Monaco editor for code files, artifacts, local repo files, and remote repo browsing (read-only). File tree sidebar + Cmd+P quick open.

</domain>

<decisions>
## Implementation Decisions

### Editor Architecture (TipTap → Monaco Migration)
- Monaco Editor is the base rendering layer, replacing TipTap/ProseMirror's DOM rendering
- TipTap's block-based features render INSIDE Monaco's canvas viewport as Monaco widgets/view zones
- Document model: Monaco text model is source of truth. Notes stored as markdown text. PM blocks stored as special markdown markers (e.g., ```pm:decision ... ```) that Monaco detects and renders as view zone widgets
- Yjs collaboration connects through Monaco's text model using y-monaco binding (not y-prosemirror)
- Slash commands (/) and mentions (@) use Monaco's native CompletionItemProvider suggest widget
- Ghost text AI uses Monaco's native inline completions API
- All 10 PM block types (RACI, decision, risk, dependency, etc.) become Monaco view zone widgets with their existing React renderers
- Rich formatting (bold, italic, headings, lists) applied via Monaco decorations on the markdown text

### File Sources & Navigation
- Four file sources: (1) artifact files via S3 signed URLs (web), (2) local repo files via tauri-plugin-fs (Tauri), (3) note content as markdown files, (4) remote repo files via GitHub/GitLab API
- Remote repo files are read-only browsing — no editing or committing back via API
- File navigation: VS Code-style file tree sidebar + Cmd+P fuzzy quick open (both available)
- Tab system for open files — multiple files open simultaneously
- Save model: auto-save with 2s debounce for all file types (notes, code files, artifacts). Modified indicator during debounce window.

### Performance & Animations
- GPU acceleration goal is primarily achieved by Monaco's Canvas rendering (replaces DOM-based TipTap)
- Spring physics scrolling in editor viewport, file tree, and note list sidebar (not modals/settings)
- Crossfade transitions (200-300ms) for mode switches (rich view ↔ source view), panel open/close, file tree expand/collapse
- Target: 60fps scroll, smooth deceleration, no layout jank during transitions

### Markdown Preview
- Toggle mode: switch between edit mode (raw markdown in Monaco) and preview mode (rendered HTML). One at a time, not side-by-side.
- Full extended markdown: GFM + Mermaid diagrams + KaTeX math ($inline$ and $$block$$) + footnotes + definition lists + custom containers (admonitions/callouts)
- Existing Mermaid 11.12.2 dependency reused for diagram rendering

### Platform Strategy
- Web-first: artifact files, notes, remote repo browsing work on web
- Tauri bonus: local repo file browsing/editing added for desktop app
- No collaboration on file editing — single-user only

### Claude's Discretion
- Markdown preview engine choice (react-markdown stack vs Monaco-native vs other)
- Spring physics scroll implementation (custom vs library)
- PM block markdown marker format (exact syntax for encoding blocks in text)
- Monaco theme and color scheme (should match Pilot Space design system)
- File tree component implementation (custom vs existing library)
- Tab management UX details (max tabs, tab overflow, close behavior)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Editor Architecture
- `frontend/src/components/editor/NoteCanvasEditor.tsx` — Current TipTap editor initialization and hooks (being replaced)
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` — Extension factory with load order (25+ extensions to migrate)
- `frontend/src/features/notes/editor/extensions/pm-blocks/` — PM block extension + 10 type-specific renderers (must become Monaco view zones)
- `frontend/src/features/notes/editor/extensions/GhostTextExtension.ts` — Ghost text AI (migrate to Monaco inline completions)
- `frontend/src/features/notes/editor/extensions/SlashCommandExtension.ts` — Slash commands (migrate to Monaco CompletionItemProvider)

### Collaboration
- `frontend/src/features/notes/collab/SupabaseYjsProvider.ts` — Supabase Realtime Yjs transport (keep, rebind to y-monaco)
- `frontend/src/features/notes/editor/extensions/YjsCollabExtension.ts` — Current y-prosemirror binding (replace with y-monaco)

### File Preview (Existing Renderers)
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Current file preview modal
- `frontend/src/features/artifacts/components/renderers/` — 6 lazy-loaded renderers (MarkdownRenderer, CodeRenderer, etc.)
- `frontend/src/lib/mime-type-router.ts` — MIME type → renderer routing

### Tauri Desktop File Operations
- `tauri-app/tauri-app/src-tauri/src/commands/git.rs` — Git operations (1096 lines, git2-rs)
- `tauri-app/tauri-app/frontend/src/lib/tauri.ts` — TypeScript IPC bindings (587 lines)
- `tauri-app/tauri-app/frontend/src/stores/features/git/GitStore.ts` — MobX git state (451 lines)
- `tauri-app/tauri-app/frontend/src/features/git/components/diff-viewer.tsx` — Current diff viewer

### Design System
- `specs/001-pilot-space-mvp/ui-design-spec.md` — UI/UX design specification v4.0
- `.impeccable.md` — Design context, brand personality, aesthetic direction

### AI Integration
- `backend/src/pilot_space/ai/README.md` — AI layer architecture, agents, skills, MCP tools
- `backend/src/pilot_space/ai/mcp/note_server.py` — 9 note mutation tools (must work with Monaco model)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lowlight` 3.2.0 — Syntax highlighting (190+ languages). Monaco has built-in highlighting but lowlight patterns may inform language coverage.
- `react-markdown` 10.1.0 + `remark-gfm` 4.0.1 + `rehype-highlight` 7.0.2 — Markdown rendering pipeline (candidate for preview mode)
- `mermaid` 11.12.2 — Diagram rendering with MermaidPreview.tsx component
- `@xyflow/react` 12.10.1 + `d3-force` — Knowledge graph (unaffected, stays SVG-based)
- `react-virtuoso` 4.18.1 — Virtualized lists (reusable for file tree)
- `yjs` 13.6.29 + `y-indexeddb` 9.0.12 — CRDT + local persistence (keep, rebind to Monaco)
- `dompurify` 3.3.1 — HTML sanitization (reuse for markdown preview)

### Established Patterns
- MobX stores + TanStack Query for state management — file editor will need a FileStore
- Dynamic imports via `next/dynamic` for heavy components — Monaco MUST be lazy-loaded (~3MB)
- `isTauri()` guard for platform-conditional features — file tree shows local files only in Tauri
- Observer pattern: components consuming MobX state must be wrapped in `observer()` (but NOT TipTap NodeView renderers — React 19 flushSync issue still applies to Monaco view zone renderers)

### Integration Points
- `NoteCanvas.tsx` → `NoteCanvasEditor.tsx` — Entry point being replaced by Monaco-based editor
- `RootStore.ts` — New FileStore/EditorStore needs to register here
- `workspace-slug-layout.tsx` — Where file tree sidebar and tab bar would mount
- `useAutoSave()` hook — Auto-save pattern to reuse/extend for file editing
- `pilot:preview-artifact` custom event — Current file preview trigger (may evolve into "open in editor")

</code_context>

<specifics>
## Specific Ideas

- Notes are the main interface for user workflow — Monaco enhances notes, doesn't replace the concept
- TipTap features (PM blocks, ghost text, slash commands, collab) must have full feature parity within Monaco
- The editor should feel like a premium IDE (VS Code-quality) with Pilot Space's warm, calm aesthetic
- Spring physics scrolling and crossfade transitions give a polished, native-app feel
- File tree + quick open mirrors VS Code's navigation model — familiar to developers

</specifics>

<deferred>
## Deferred Ideas

- Collaborative file editing (Yjs on code files) — separate phase if needed
- Remote repo file editing + commit via API — Phase 40 is read-only for remote
- Split-pane markdown preview (side-by-side) — toggle mode for now, split pane later if requested
- LSP/IntelliSense/autocomplete for code files — would be its own phase
- Git blame/annotate in the editor — would extend git integration phase
- Multiple terminal tabs/splits (DESK-03) — separate phase

</deferred>

---

*Phase: 40-webgpu-canvas-ide-editor*
*Context gathered: 2026-03-23*
