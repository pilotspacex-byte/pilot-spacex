# Stack Research

**Domain:** Medium-style editor experience, file artifact uploads with preview modals, Supabase Storage backend, optimistic UI for artifacts CRUD, YouTube/Vimeo video embeds
**Researched:** 2026-03-18
**Confidence:** HIGH

## Scope

Stack additions/changes needed for v1.1 Medium Editor & Artifacts:
1. Medium-style TipTap editor: floating toolbar on selection, / block inserter for images/embeds/file cards, focus mode, inline image captions, pull quotes
2. File artifact uploads as inline cards in notes — preview modals for markdown, CSV, JSON, text, Excel, code, images (10MB limit)
3. Per-project artifacts management page with optimistic UI (CRUD)
4. Artifact persistence via Supabase Storage (S3 protocol) through FastAPI backend
5. YouTube/Vimeo video embed inline players in notes

**Existing stack (DO NOT re-research):** Next.js 16.1, React 19.2, MobX 6, TanStack Query 5, shadcn/ui, TipTap 3.x (StarterKit, Markdown, Table, CodeBlock-lowlight, CharacterCount, Placeholder, Highlight, TaskList, Suggestion, tiptap-markdown), FastAPI, SQLAlchemy async, Supabase (Auth + PostgreSQL 16 + storage3 Python SDK), Redis, python-multipart (already in pyproject.toml), react-markdown (already installed), lowlight (already in use for code highlighting), dompurify (already installed).

## Key Finding: Minimal New Dependencies Required

The TipTap editor already runs at v3.x. `BubbleMenu` and `FloatingMenu` components ship inside `@tiptap/react` (already installed) and do NOT require separate package installs. The backend already has `storage3>=0.8.0`, `python-multipart>=0.0.12`, and `supabase>=2.10.0`, meaning zero new Python dependencies are required. The frontend gaps are: TipTap image extension, TipTap YouTube extension, a CSV parser for preview, and an Excel parser for preview.

---

## Recommended Stack Additions

### New Frontend Libraries (5 packages)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `@tiptap/extension-image` | `^3.20.4` | Image node in editor (upload + display) | Official TipTap image extension. Enables `setImage()` command, resize handles, configurable inline/block rendering. Required foundation for image-with-caption custom node and the file card `/` slash command insertion. Not in starter-kit. |
| `@tiptap/extension-youtube` | `^3.20.4` | YouTube iframe embed node | Official TipTap YouTube extension. Renders sandboxed `<iframe>` with `youtube.com/embed/` URL. Handles URL parsing from `/setYoutubeVideo({ src })` command. Vimeo requires a custom node (see Architecture). Same major version as rest of TipTap 3 stack — no compatibility risk. |
| `react-dropzone` | `^15.0.0` | Drag-and-drop file upload zone | Standard for React file drop UIs. 15.0.0 released Feb 2026, React 19 compatible. Used in the artifact upload area (artifacts management page) and editor image/file insertion dialog. No runtime dependencies. |
| `papaparse` | `^5.5.3` | CSV parsing for preview modal | Fastest in-browser CSV parser. 5.5.3 last published Dec 2024, stable API. Used to parse uploaded CSV artifact content into a 2D array for table rendering in the preview modal. `@types/papaparse` ships in the same package (no separate @types needed). |
| `@e965/xlsx` | `^0.20.3` | Excel (.xlsx/.xls) parsing for preview modal | **Use `@e965/xlsx` not `xlsx`** — the `xlsx` npm name is an unmaintained fork with known CVEs (DoS, prototype pollution). `@e965/xlsx` is the maintained community fork with identical API. Parses XLSX/XLS binary in browser to JSON rows for table preview. Import pattern: `import * as XLSX from '@e965/xlsx'`. |

### No New Backend Libraries Required

The backend already provides everything needed:

| Capability | Existing Asset | How It Covers the Need |
|------------|---------------|----------------------|
| File upload ingestion | `python-multipart>=0.0.12` | FastAPI `UploadFile` + `File(...)` — already in `pyproject.toml` |
| Supabase Storage upload | `storage3>=0.8.0` | `await client.storage.from_(bucket).upload(path, data, file_options)` — Python SDK |
| Signed URL generation | `storage3>=0.8.0` | `create_signed_url(path, expires_in)` — 2-hour default, sufficient for modal preview |
| Auth enforcement | `supabase>=2.10.0` | Service role client for bucket operations; user JWT for RLS-gated reads |
| Request body parsing | `pydantic>=2.10.0` | Artifact metadata model (name, mime_type, size, project_id) |
| DB persistence | `sqlalchemy>=2.0.36` | New `artifacts` table with Alembic migration — no new ORM library |

---

## TipTap Architecture Decisions

### Floating Toolbar (BubbleMenu)

**Use `BubbleMenu` from `@tiptap/react/menus`** — NOT the separate `@tiptap/extension-bubble-menu` package.

`@tiptap/react` (already installed at `^3.16.0`) ships `BubbleMenu` and `FloatingMenu` as React components inside the package. Per official TipTap 3 docs: "If you are using React, use the framework-specific BubbleMenu component instead of the extension." The component manages DOM lifecycle, positioning, and React re-renders automatically. No new package install is needed.

```tsx
// Import from @tiptap/react/menus — already bundled with @tiptap/react
import { BubbleMenu } from '@tiptap/react/menus'
```

### Block Inserter (FloatingMenu)

**Use `FloatingMenu` from `@tiptap/react/menus`** — same reasoning as BubbleMenu.

The existing `SlashCommandExtension` already handles the `/` block inserter pattern. For the Medium-style "+" button that appears on an empty line (the alternative to typing `/`), use `FloatingMenu` from `@tiptap/react/menus` with `shouldShow` filtering to empty paragraphs. This triggers the same slash command palette used today.

### Image with Caption

**Build a custom `FigureNode` extension** extending TipTap's `@tiptap/extension-image`.

The official image extension does not support captions. TipTap has an experimental `Figure` extension but it is not published to npm (docs say "copy the source code"). The approach: extend `@tiptap/extension-image` to wrap `<figure>` + `<figcaption>` with an editable caption node. This inserts into Group 3 (block-type extensions) in `createEditorExtensions.ts` at the `PRE-002` insertion point, before `BlockIdExtension`.

Third-party alternatives (`@pentestpad/tiptap-extension-figure`, `tiptap-image-plus`) require TipTap 2.x or lack maintenance. Build custom: ~80 lines, full control, no external package.

### Pull Quotes

**Extend the existing `blockquote` node** (ships in StarterKit) with a `variant` attribute and CSS class `pull-quote`.

Pull quotes are a styled `blockquote` with centered/enlarged typography — not a distinct node type. Adding a `PullQuoteExtension` that extends `Blockquote.extend({ addAttributes() { return { variant: { default: 'standard' } } } })` and maps `variant: 'pull-quote'` to a CSS class is sufficient. No new package needed.

### Video Embeds (YouTube + Vimeo)

**YouTube:** Use `@tiptap/extension-youtube` (official). The `setYoutubeVideo({ src })` command accepts full YouTube URLs and extracts the video ID automatically.

**Vimeo:** Build a custom `VimeoNode` extension (~60 lines). No official TipTap Vimeo extension exists. The `@fourwaves/tiptap-extension-vimeo` package is only compatible with TipTap 2.x (last updated 2022). Custom implementation: iframe node that accepts `https://player.vimeo.com/video/{id}` URLs, same pattern as the YouTube extension. Insert both via the slash command menu as "YouTube" and "Vimeo" entries.

### File Artifact Card Node

**Build a custom `ArtifactCardNode` extension** — a ProseMirror leaf node (no content children) that stores `{ artifactId, fileName, mimeType, fileSize }` as node attributes and renders a `ReactNodeViewRenderer` component. Follows the same pattern as existing `InlineIssueExtension` and `PMBlockExtension` in the codebase. Inserted via slash command or drag-and-drop. Clicking triggers the preview modal.

---

## Supporting Libraries Already Available (No Install Needed)

| Need | Existing Library | Notes |
|------|-----------------|-------|
| Code syntax highlighting in preview modal | `lowlight` ^3.2.0 + `react-markdown` ^10.1.0 | Already used in `CodeBlockExtension`; reuse for code file preview |
| Markdown rendering in preview modal | `react-markdown` ^10.1.0 + `remark-gfm` ^4.0.1 | Already installed; render `.md` artifact content |
| HTML sanitization in preview modal | `dompurify` ^3.3.1 | Already installed; sanitize any HTML artifacts before preview render |
| Image display in preview modal | Native `<img>` + signed URL from backend | Supabase Storage signed URL is all that's needed |
| Text file display in preview modal | `react-markdown` or `<pre>` | Plain text renders directly; no library needed |
| JSON pretty-print in preview modal | `JSON.stringify(parsed, null, 2)` + `lowlight` | JSON formatted + syntax-highlighted with existing lowlight |
| Optimistic UI for artifacts CRUD | TanStack Query 5's `useMutation` `onMutate`/`onError` | Already used in the codebase for other mutations; same pattern |
| File upload progress tracking | `XMLHttpRequest` or `axios` upload progress event | `axios` is already installed (`^1.7.0`); use `onUploadProgress` callback |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `BubbleMenu` from `@tiptap/react/menus` | `@tiptap/extension-bubble-menu` (separate package) | The React component ships inside `@tiptap/react` already installed; separate package adds nothing for React projects |
| `FloatingMenu` from `@tiptap/react/menus` | `@tiptap/extension-floating-menu` (separate package) | Same: React component already bundled with installed `@tiptap/react` |
| Custom `FigureNode` (~80 lines) | `@pentestpad/tiptap-extension-figure` | Requires TipTap 2.x, not 3.x; unmaintained for over a year |
| Custom `FigureNode` (~80 lines) | `tiptap-image-plus` | Mixed TipTap 2/3 support; adds 2.8kB for functionality achievable in 80 lines with full control |
| Custom `VimeoNode` (~60 lines) | `@fourwaves/tiptap-extension-vimeo` | Last published 2022; TipTap 2.x only; not compatible with project's TipTap 3 stack |
| `@e965/xlsx` | `xlsx` (npm) | `xlsx` on npm is an unmaintained fork with multiple active CVEs (DoS, prototype pollution per 2026 security reports) |
| `papaparse` (core) | `react-papaparse` | `react-papaparse` is a React wrapper around `papaparse`; last published 2 years ago; direct `papaparse` is simpler for parse-only use case in a modal |
| `react-dropzone` | Native HTML `<input type="file">` + `dragover` events | `react-dropzone` handles MIME type filtering, drag state, validation errors, and test utilities. Saves ~200 lines of boilerplate for the artifacts upload page |
| Supabase Storage via backend API | Direct browser upload to Supabase Storage | Backend upload enforces 10MB limit, virus scan hooks, workspace quota (already tracked in storage_quota), and audit log entries. Browser-direct bypasses all these controls |
| TanStack Query `onMutate` rollback | MobX optimistic state | TanStack Query already owns server state; doing optimistic UI in MobX creates a split-ownership problem. Use TanStack for all server state mutations including optimistic updates per DD pattern in the codebase |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@tiptap/extension-bubble-menu` (package) | `@tiptap/react/menus` BubbleMenu component already ships with installed `@tiptap/react` | Import from `@tiptap/react/menus` |
| `@tiptap/extension-floating-menu` (package) | Same: already bundled with `@tiptap/react` | Import from `@tiptap/react/menus` |
| `xlsx` (npm name) | Unmaintained npm package with CVEs; SheetJS stopped publishing to this name years ago | `@e965/xlsx` — identical API, maintained fork |
| `react-papaparse` | 2-year-old wrapper; the raw `papaparse` is simpler for modal-only parsing | `papaparse` directly |
| `@pentestpad/tiptap-extension-figure` | TipTap 2.x only | Custom 80-line `FigureNode` extension |
| `react-syntax-highlighter` | Already have `lowlight` (^3.2.0) used by the CodeBlock extension; adding a second highlighter is redundant weight | Reuse `lowlight` + `react-markdown` for code file preview |
| `prism-react-renderer` | Same reasoning as react-syntax-highlighter; lowlight is already the project's highlighter | Reuse `lowlight` |
| `tiptap-image-plus` | Mixed TipTap v2/v3 support; adds bundle overhead | Custom `FigureNode` extending `@tiptap/extension-image` |
| S3-compatible boto3 in Python backend | `storage3` Python SDK already provides the same operations with better Supabase integration | `storage3` (already installed) |
| Y.js collaborative editing | Explicitly out of scope per PROJECT.md; already in package.json but unused | Not applicable |

---

## Integration Points with Existing TipTap Setup

The critical file is `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts`. New extensions slot into the documented groups:

```
Group 3 — Block-type extensions (PRE-002 insertion point):
  CodeBlockExtension  ← existing
  FigureNode (image with caption)  ← NEW: insert here
  ArtifactCardNode  ← NEW: insert here
  YoutubeNode (@tiptap/extension-youtube)  ← NEW: insert here
  VimeoNode (custom)  ← NEW: insert here
  BlockIdExtension  ← existing (MUST remain last in Group 3)

Group 5 — Inline marks & decorations:
  SlashCommandExtension  ← existing (extend slash-command-items.ts with new commands)
```

**Slash command additions** (edit `slash-command-items.ts`):
- `image` — triggers file picker → uploads → inserts `FigureNode`
- `file` — triggers file picker → uploads → inserts `ArtifactCardNode`
- `youtube` — prompts URL → inserts `YoutubeNode`
- `vimeo` — prompts URL → inserts `VimeoNode`
- `divider` — already exists (horizontal rule)

**BubbleMenu placement**: wrap the `<EditorContent>` component with `<BubbleMenu editor={editor}>` in `NoteCanvasEditor.tsx` or the issue note editor. Contains Bold/Italic/Strike/Link/Highlight/PullQuote buttons.

---

## Backend: New Artifacts API Surface

No new Python packages. New router + service + model under the existing Clean Architecture:

```
backend/src/pilot_space/
  api/routers/artifacts.py         — POST /artifacts (upload), GET /artifacts, DELETE /artifacts/:id
  application/
    commands/create_artifact.py    — upload to Supabase Storage, persist metadata
    queries/list_artifacts.py      — query artifacts by project_id
  domain/artifact.py               — Artifact entity
  infrastructure/
    repositories/artifact_repo.py  — SQLAlchemy CRUD
    storage/supabase_storage.py    — Thin wrapper over storage3 SDK (create_signed_url, upload, delete)
```

Supabase Storage bucket strategy: single `artifacts` bucket, path pattern `{workspace_id}/{project_id}/{artifact_id}/{filename}`. Workspace isolation via RLS policy on `storage.objects` checking `workspace_id` prefix against the JWT's workspace claim.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `@tiptap/extension-image` ^3.20.4 | `@tiptap/core` ^3.16.0 (installed) | Same TipTap 3 major version; minor version difference is fine (npm ^ range covers it) |
| `@tiptap/extension-youtube` ^3.20.4 | `@tiptap/core` ^3.16.0 (installed) | Same TipTap 3 major version |
| `react-dropzone` ^15.0.0 | React 19.2.3 | React 19 compatible per 15.0.0 release notes (Feb 2026) |
| `papaparse` ^5.5.3 | No React peer dep | Pure JS parser, framework-agnostic |
| `@e965/xlsx` ^0.20.3 | No React peer dep | Pure JS workbook parser, framework-agnostic |
| `BubbleMenu` from `@tiptap/react/menus` | `@tiptap/react` ^3.16.0 (installed) | Bundled inside installed package; no separate install |
| `FloatingMenu` from `@tiptap/react/menus` | `@tiptap/react` ^3.16.0 (installed) | Bundled inside installed package; no separate install |

---

## Installation

```bash
# Frontend: 5 new packages
cd frontend && pnpm add @tiptap/extension-image @tiptap/extension-youtube react-dropzone papaparse @e965/xlsx

# Frontend type definitions (papaparse ships its own types; others do not need @types)
# @tiptap packages include TypeScript types; react-dropzone includes types; @e965/xlsx includes types

# Backend: NO new packages
# python-multipart, storage3, supabase are already in pyproject.toml
# Only needs: new Alembic migration for artifacts table
cd backend && alembic revision --autogenerate -m "add_artifacts_table"
```

---

## Sources

- [TipTap BubbleMenu docs](https://tiptap.dev/docs/editor/extensions/functionality/bubble-menu) — confirmed `@tiptap/react/menus` import path, no separate package needed for React
- [TipTap FloatingMenu docs](https://tiptap.dev/docs/editor/extensions/functionality/floatingmenu) — confirmed `@tiptap/react/menus` import path
- [TipTap Image extension docs](https://tiptap.dev/docs/editor/extensions/nodes/image) — confirmed capabilities: resize, inline/block, no built-in caption, no upload
- [TipTap YouTube extension docs](https://tiptap.dev/docs/editor/extensions/nodes/youtube) — confirmed YouTube-only (Vimeo not supported), configuration options
- [TipTap Figure experiment](https://tiptap.dev/docs/examples/experiments/figure) — confirmed not published to npm; must copy/build custom
- `npm view @tiptap/extension-image version` → 3.20.4 (verified live)
- `npm view @tiptap/extension-youtube version` → 3.20.4 (verified live)
- `npm view @tiptap/extension-bubble-menu version` → 3.20.4 (verified live)
- `npm view react-dropzone version` → 15.0.0 (verified live)
- `npm view papaparse version` → 5.5.3 (verified live)
- `npm view @e965/xlsx version` → 0.20.3 (verified live)
- [Supabase Storage Python SDK docs](https://supabase.com/docs/reference/python/storage-from-upload) — confirmed `storage3` upload + signed URL API
- [SheetJS security guidance 2026](https://thelinuxcode.com/npm-sheetjs-xlsx-in-2026-safe-installation-secure-parsing-and-real-world-nodejs-patterns/) — confirmed `xlsx` npm CVEs; `@e965/xlsx` as maintained alternative
- [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control) — RLS on `storage.objects` for workspace isolation
- Codebase analysis: `createEditorExtensions.ts`, `slash-command-items.ts`, `PMBlockExtension.ts`, `pyproject.toml`, `package.json` — verified existing capabilities and extension group insertion points

---
*Stack research for: Medium-style TipTap editor, file artifact uploads, Supabase Storage, optimistic UI artifacts, YouTube/Vimeo embeds*
*Researched: 2026-03-18*
