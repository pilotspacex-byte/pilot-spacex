# Feature Research

**Domain:** Medium-style editor UX, file artifact upload/preview, per-project artifacts management page, video embeds
**Researched:** 2026-03-18
**Confidence:** HIGH (TipTap v3 docs verified via official sources; Supabase Storage patterns confirmed; all findings cross-referenced with existing codebase)

---

## Context: What Already Exists in the Editor

The editor is TipTap v3 (`@tiptap/core ^3.16`, StarterKit, CharacterCount, Placeholder, Highlight, Mention, Table, TaskList, CodeBlockLowlight). The `SelectionToolbar` is a custom floating component — NOT using TipTap's BubbleMenu extension — using fixed positioning from `editor.view.coordsAtPos()`. `SlashCommandExtension` is a custom ProseMirror plugin with keyboard nav, grouping, and AI commands. No image extension, no file upload node, no video embed node exists yet. The backend has `ai_attachments.py` (multipart upload to Supabase Storage) scoped to chat context — a new artifacts scope is needed for notes. Quota enforcement already exists in `workspace_quota.py`.

---

## Feature Landscape

### Category A: Medium-Style Editor Features

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pull quote (styled blockquote variant) | Medium uses a second click on blockquote icon to promote to pull quote. Long-form writing tools (Medium, Craft, Substack) all support this visual emphasis pattern | LOW | Toggle `data-type="pull-quote"` attribute on existing blockquote node. CSS: larger font, muted accent background, prominent left border. No new TipTap node needed — attribute variant of StarterKit blockquote. Add `/pull-quote` slash command entry. |
| Focus mode (distraction-free writing) | Writers expect a "hide chrome" toggle when doing deep work. Notion, Bear, Craft, iA Writer all have this | MEDIUM | MobX flag `isFocusMode` in UI store. CSS: hide sidebar, top nav, EditorToolbar, inject `.focus-mode` on editor wrapper. Keyboard shortcut Cmd+Shift+F or F11. No new TipTap extension — pure layout toggle. |
| Heading level toggle in floating toolbar | Current `SelectionToolbar` has no heading level switcher. Medium shows H1/H2 options in floating toolbar. Users expect to change heading level without deleting and re-typing slash command | LOW | Add H1/H2/H3 toggle buttons to existing `SelectionToolbar`. `editor.isActive('heading', {level: N})` and `editor.chain().toggleHeading({level: N})`. Extend existing component — no new infrastructure. |
| Inline image insertion | Paste image or `/image` slash command inserts image at cursor position | MEDIUM | Requires `@tiptap/extension-image` (not currently installed, v3 at 3.20.x). Wire `/image` slash command to open file picker. Paste handler: detect image files in clipboard paste event, upload, insert Image node with returned URL. File goes to Supabase Storage via new artifact upload endpoint. |
| Inline image captions | Image with editable caption below — Notion, Medium, and Ghost all support this | MEDIUM | TipTap's built-in Image extension has no caption. Use Figure node pattern: custom `FigureNode` wrapping `<figure>` + `<figcaption>` with nested editable paragraph. TipTap's experimental Figure extension documents this pattern. Community `tiptap-image-plus` (v3 compatible) also provides this. Recommend custom Figure node to avoid third-party fragility. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Drag-and-drop image upload onto canvas | Drop image file anywhere on the note to insert at that cursor position — Natural UX that Medium and Notion support | MEDIUM | `handleDOMEvents.drop` in `editor/config.ts` already blocks file drops (`event.preventDefault()` for any `dataTransfer.files`). Change: accept image files, compute drop position from event coords, upload then insert Image node. Async — show placeholder node during upload. |
| `/image`, `/file`, `/video` slash commands | Block inserter that matches project-level expectations described in PROJECT.md | LOW | Add three new entries to `SlashCommandExtension`. Each opens the appropriate picker or URL input popover. Slash command infrastructure is already in place — these are additive entries only. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Replace SelectionToolbar with TipTap BubbleMenu extension | "Official" floating toolbar approach | `SelectionToolbar` works and avoids the `flushSync` / React 19 bug (documented in MEMORY.md for observer-wrapped components adjacent to TipTap NodeViews). Switching BubbleMenu risks reintroducing that bug. | Extend existing `SelectionToolbar` — add heading toggle and any new formatting buttons to the current component. |
| Add TypeAhead / autocomplete overlay to slash menu | "Modern editors have predictive suggestions" | `SlashCommandExtension` already filters-as-you-type via `filterCommands()`. Adding a second suggestion layer conflicts with `GhostTextExtension` (both use ProseMirror decorations at the cursor position). | The current slash menu already filters by name, label, and keywords — just add new command entries. |
| Full-screen writing mode on mobile | "Writers want focus everywhere" | Mobile is explicitly out of scope per PROJECT.md. Desktop + tablet responsive is the target. | Focus mode for desktop/tablet only. |

---

### Category B: File Artifact Upload and Inline Preview

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| File upload via `/file` slash command | Notion and Confluence users expect to attach files inline in documents | MEDIUM | New TipTap Node: `FileCardNode` (atom block node). Slash command `/file` opens OS file picker. On select: POST multipart to new `POST /workspaces/{id}/artifacts/upload`. Node stores `artifact_id`, `filename`, `mime_type`, `size_bytes`. Renders as inline card. Mirror `ai_attachments.py` pattern but under a new `artifacts` scope. |
| Inline file card rendering | File block appears as rich card: file type icon, filename, size, preview trigger button | MEDIUM | ReactNodeView for `FileCardNode`. Icon mapped from mime type. Filename truncated. Human-readable size. Click anywhere on card opens preview modal. Uses same card aesthetic as `NotePreviewCard`. |
| Upload progress indicator on card | Show % complete during upload — no dead-looking UI while uploading | LOW | `onUploadProgress` callback from Axios. `FileCardNode` shows progress bar in `uploading` state, replaces with card on success, shows error state with retry on failure. |
| Preview modal: images | Full-size image in lightbox — standard for any image display | LOW | Shadcn `Dialog` already in codebase. `<img>` in dialog. Add zoom controls. Simple. |
| Preview modal: code files (JS, TS, Python, HTML, CSS, JSON) | Developers attach code snippets — syntax highlighting is expected | LOW | `lowlight` already installed and used in `CodeBlockExtension`. Reuse in preview modal. Detect language from file extension or mime type. |
| Preview modal: Markdown | Render markdown as HTML | LOW | `react-markdown` + `remark-gfm` already installed. Wrap in `Dialog`. |
| Preview modal: Plain text | Show text verbatim in scrollable container | LOW | `<pre>` element in dialog. No library needed. |
| Preview modal: CSV (basic) | CSV shown as a sortable/scrollable table | MEDIUM | Parse with `FileReader` + manual split or lightweight `papaparse` (~28KB gzipped). Render as `<table>` with sticky header. Limit rows displayed (500) with "Download to see full file" notice. |
| Client-side file size limit (10MB) | Guard before uploading — instant feedback, no wasted bandwidth | LOW | Check `file.size <= 10 * 1024 * 1024` before POST. Show toast error immediately. Backend also enforces this (mirror `ai_attachments.py` FILE_TOO_LARGE pattern). |
| Supported MIME type validation (client-side) | Users expect clear rejection with list of supported types | LOW | Check MIME against allowlist before POST. Error toast with supported types listed. |
| Delete file card from note | Remove card and its storage object | MEDIUM | Delete button on `FileCardNode`. `DELETE /workspaces/{id}/artifacts/{artifact_id}`. Optimistic: remove node from document immediately, restore on failure with toast. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Preview modal: XLSX (Excel) | Engineers attach data sheets and specs — in-app XLSX preview avoids switching to another app | HIGH | `xlsx` (SheetJS) — ~250KB. Parse first sheet → HTML table. Cap at 500 rows. Lazy-import (`import('xlsx')`) to keep initial bundle unaffected. Only add if explicitly prioritized, due to bundle and implementation cost. |
| Drag-and-drop file onto note canvas | Drop file anywhere to insert `FileCardNode` at that position | MEDIUM | Extend `handleDOMEvents.drop` (currently blocks all file drops). Handle non-image files → upload → insert `FileCardNode` at computed position. Same async-with-placeholder pattern as image drop. |
| Artifact reuse across notes (reference by ID) | Same file, multiple notes — efficient storage | HIGH | Out of scope for v1. Requires artifact-note join table and deduplication. Defer to v1.x. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| In-editor XLSX editing | "Embed spreadsheet like Google Sheets" | Full spreadsheet engine in a note editor is enormous scope. No lightweight React spreadsheet fits the 700-line file constraint without external heavy SDKs. | Read-only XLSX preview with "Download" button. |
| PDF preview in modal | PDFs are common attachments | `pdf.js` adds ~2MB to bundle. Self-hosted PDF rendering is complex and fragile with fonts/forms. | PDF icon card with "Open in new tab" (browser handles PDF natively). |
| File version history | "Track changes to attached files" | Storage management and version UI complexity far exceeds v1 value. | Single version per artifact. Users re-upload if file changed. |

---

### Category C: Per-Project Artifacts Management Page

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| List all artifacts for a project | Users need a central registry of files attached to any note in a project — Notion "Files & Media" pattern | MEDIUM | New route: `/[workspaceSlug]/projects/[projectId]/artifacts`. TanStack Query: `useProjectArtifacts(projectId)`. New backend endpoint: `GET /workspaces/{id}/projects/{projectId}/artifacts` — returns paginated list of artifacts with metadata. |
| File metadata columns | Name, size, type, uploader, upload date, linked note | LOW | Use existing table/list patterns from issues list view. Avatar + name for uploader. Date formatted with `date-fns` (already installed). Note title as deep-link. |
| Download artifact | Time-limited signed URL for download | LOW | `GET /workspaces/{id}/artifacts/{artifact_id}/download` returns signed URL from Supabase Storage (1hr TTL). Frontend: open URL in new tab. Supabase supports `createSignedUrl` from Python SDK. |
| Delete artifact with confirmation | Remove from storage and orphan any referencing file cards | MEDIUM | Shadcn `AlertDialog` (already used in codebase) for confirmation. Optimistic: remove from list immediately. Rollback on error with toast. Backend: hard-delete Storage object + DB record; `FileCardNode` in documents references `artifact_id` — orphaned cards show "File deleted" state on next load. |
| Client-side filename search/filter | Expected for any file list with more than 10 items | LOW | Filter against TanStack Query cached list client-side. No server search needed at this scale (projects rarely exceed 200 artifacts). |
| Optimistic UI for delete | Modern file management UIs give instant feedback — no spinner | LOW | TanStack Query `useMutation` with `onMutate`/`onError`/`onSettled`. Pattern already used in cycles and issues in this codebase. Snapshot → remove → rollback on error. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Preview from artifacts page | Click any artifact row to open same preview modal as inline card | LOW | Reuse `FilePreviewModal` component from Category B. Single implementation, two entry points. |
| "Used in" note deep-link | Each artifact row shows which note it's embedded in, with a clickable link | MEDIUM | Backend: artifact record stores `note_id`. Return `note_id` + `note_title` in artifact list response. Frontend: link to note page. |
| Grid / list view toggle | Gallery view for images, table view for code/docs | MEDIUM | MobX UI store flag `artifactsViewMode: 'grid' | 'list'`. Grid: image thumbnails in CSS grid. List: tabular data. Persist preference in localStorage. |
| Sort by type, date, size | Expected power-user feature for large artifact libraries | LOW | Client-side sort on the TanStack Query cached list. No server sorting needed. Add column header sort buttons. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Folder organization for artifacts | "Files need hierarchy" | Creates a tree UI with drag-and-drop, rename, and nesting. This is a file explorer app inside an SDLC tool. Enormous v1 scope. | Filter/sort by type, date, linked note. Simple enough for v1. |
| Bulk download as ZIP | Power users want export | Requires server-side ZIP assembly. Supabase Storage has no bulk download API. | Per-file download. Defer bulk export to v1.x. |
| Storage usage widget on page | "How much space am I using?" | Storage quota is tracked in `workspace_quota.py`. Simple summary is feasible but is a workspace settings concern, not per-project artifacts page. | Add to workspace settings/admin dashboard. |

---

### Category D: Video Embeds (YouTube / Vimeo)

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| YouTube URL → inline player | Paste or `/video` command inserts embedded YouTube player. Expected by Notion, Confluence, Linear users | MEDIUM | `@tiptap/extension-youtube` (official TipTap extension, v3 compatible). Add to package.json. Configure in editor extensions list. Wire `/video` slash command → URL input popover → validate → insert. Handles YouTube URL normalization. |
| Vimeo URL → inline player | Same expectation as YouTube — Vimeo is common for internal team recordings | MEDIUM | No official TipTap Vimeo extension. Recommend `@fourwaves/tiptap-extension-vimeo` — community fork of extension-youtube modified for Vimeo, maintained, v3-compatible. |
| Responsive 16:9 aspect ratio | Video players must not break layout at different widths | LOW | CSS: `aspect-ratio: 16/9; width: 100%` on iframe wrapper. Tailwind: `aspect-video`. Both extensions support width configuration. |
| Lazy iframe loading | Video iframes must not block page render | LOW | `loading="lazy"` on iframe element. YouTube embed URL: `?autoplay=0`. Both extensions support this configuration. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| URL paste detection → offer to convert | Paste a raw YouTube/Vimeo URL anywhere in text → toast/popover offers to convert to embedded player | MEDIUM | TipTap `PasteRule` on the video node extensions. Regex detect YouTube/Vimeo URL pattern. Offer conversion non-destructively (user can decline, URL stays as text). |
| Video thumbnail placeholder before activation | Show video thumbnail while iframe is not yet activated — better perceived performance | LOW | YouTube thumbnail API: `https://img.youtube.com/vi/{videoId}/hqdefault.jpg`. Show `<img>` placeholder until user clicks "Play". Replace with iframe on click. Reduces iframe count on load. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Generic iframe embed for any URL | "Embed any website" | CSP violations and `X-Frame-Options: SAMEORIGIN` on most sites create blank or broken embeds. Users frustrated with silent failures. | Only YouTube and Vimeo — tested and reliable. Show link preview card for other URLs. |
| Video file upload and hosting | "Upload internal meeting recordings" | Supabase Storage is not a video CDN. No transcoding, no adaptive bitrate streaming. 10MB limit makes real video files impossible. | Embeds only. For internal videos, teams upload to YouTube (unlisted) or Vimeo and embed. |
| Autoplay on load | "More dynamic" | Browser autoplay policies block autoplay without user interaction. Results in inconsistent behavior across browsers. | Never autoplay. Player starts paused. |

---

## Feature Dependencies

```
[Inline Image Insertion]
    └──requires──> [@tiptap/extension-image (new dep)]
    └──requires──> [Artifact Upload API: POST /workspaces/{id}/artifacts/upload (new)]
    └──shares──> [Artifact Upload API with FileCardNode]

[Image Captions]
    └──requires──> [Inline Image Insertion (above)]
    └──requires──> [Custom FigureNode TipTap extension (new)]

[FileCardNode Inline Block]
    └──requires──> [Artifact Upload API (above)]
    └──requires──> [FileCardNode TipTap Node extension (new)]
    └──requires──> [FilePreviewModal component (new)]

[Artifacts Management Page]
    └──requires──> [Artifact Upload API (above)]
    └──requires──> [Artifact List API: GET /workspaces/{id}/projects/{projectId}/artifacts (new)]
    └──requires──> [Artifact Delete API: DELETE /workspaces/{id}/artifacts/{id} (new)]
    └──requires──> [Signed Download URL: GET /workspaces/{id}/artifacts/{id}/download (new)]
    └──reuses──> [FilePreviewModal from FileCardNode]

[Preview Modal: XLSX]
    └──requires──> [xlsx (SheetJS) new dep — lazy import]
    └──note──> [700-line file limit: xlsx parsing logic must be in separate utility module]

[YouTube Embed]
    └──requires──> [@tiptap/extension-youtube (new dep)]

[Vimeo Embed]
    └──requires──> [@fourwaves/tiptap-extension-vimeo (new dep)]

[Focus Mode]
    └──requires──> [MobX UI store flag — trivial, follows existing store patterns]

[Pull Quote]
    └──enhances──> [existing StarterKit blockquote — attribute toggle only, no new node]

[Floating Toolbar Heading Toggle]
    └──enhances──> [existing SelectionToolbar — additive buttons only]
    └──conflicts──> [TipTap BubbleMenu extension — do NOT replace SelectionToolbar]

[Slash Commands: /image, /file, /video, /pull-quote]
    └──enhances──> [existing SlashCommandExtension — additive entries only]
```

### Dependency Notes

- **FileCardNode requires Artifact Upload API to complete before node insertion:** The node cannot be inserted until upload succeeds and `artifact_id` is returned. Use a placeholder node with loading state during upload.
- **Artifacts Management Page requires all four new artifact endpoints:** Plan backend before or alongside frontend.
- **FilePreviewModal is shared:** Build once, used by both inline `FileCardNode` and the artifacts page row click.
- **Floating Toolbar must NOT be replaced with BubbleMenu:** The custom `SelectionToolbar` avoids the `flushSync` + React 19 bug documented in MEMORY.md. Extend it additively.
- **XLSX lazy import:** `import('xlsx')` dynamically when preview modal opens for an XLSX file. Do not statically import or it adds ~250KB to initial bundle.

---

## MVP Definition

### Launch With (v1 — this milestone)

- [ ] Focus mode — pure CSS/MobX flag, directly delivers "Medium-style writing experience"
- [ ] Pull quote toggle — low effort, high craft signal
- [ ] Floating toolbar: heading level toggle H1/H2/H3 — currently missing, users re-type to change headings
- [ ] Inline image insertion via `/image` slash command — "Medium-style editor" without images is incomplete
- [ ] Inline image captions — explicitly required in PROJECT.md milestone spec
- [ ] `FileCardNode` with upload, progress indicator, inline preview modal (text, JSON, code, markdown, CSV, images) — explicitly required
- [ ] `/file` slash command — primary insertion path for file cards
- [ ] Drag-and-drop file onto canvas (images → Image node, other files → FileCardNode) — second insertion path
- [ ] Per-project artifacts management page: list, preview, download, delete + optimistic UI — explicitly required
- [ ] YouTube embed via `@tiptap/extension-youtube` — explicitly required
- [ ] Vimeo embed via `@fourwaves/tiptap-extension-vimeo` — explicitly required
- [ ] URL paste detection for YouTube/Vimeo → offer to embed — primary user discovery path

### Add After Validation (v1.x)

- [ ] XLSX preview — trigger: user feedback requests it; SheetJS dep cost worth it only with demand signal
- [ ] Grid/list view toggle on artifacts page — trigger: artifact count per project routinely exceeds 20
- [ ] Artifact reuse across notes (reference by ID) — trigger: users request deduplication
- [ ] Bulk file operations on artifacts page — trigger: power users managing large artifact sets

### Future Consideration (v2+)

- [ ] Artifact version history — storage and UI complexity out of proportion with v1 value
- [ ] PDF in-app preview — pdf.js bundle weight; browser opens PDFs natively in new tab
- [ ] Bulk download as ZIP — requires server-side ZIP assembly
- [ ] Video upload/hosting — requires CDN and transcoding infrastructure

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Focus mode | HIGH | LOW | P1 |
| Pull quote | MEDIUM | LOW | P1 |
| Heading toggle in floating toolbar | HIGH | LOW | P1 |
| Inline image insertion | HIGH | MEDIUM | P1 |
| Inline image captions | HIGH | MEDIUM | P1 |
| FileCardNode + upload + progress | HIGH | MEDIUM | P1 |
| FilePreviewModal (text/JSON/code/markdown/CSV/image) | HIGH | MEDIUM | P1 |
| `/file`, `/image`, `/video` slash commands | HIGH | LOW | P1 |
| Artifacts management page (list + download + delete + optimistic) | HIGH | MEDIUM | P1 |
| YouTube embed | HIGH | LOW | P1 |
| Vimeo embed | HIGH | LOW | P1 |
| Drag-and-drop file/image upload | MEDIUM | MEDIUM | P1 |
| URL paste → embed offer | MEDIUM | MEDIUM | P2 |
| Upload progress indicator on card | MEDIUM | LOW | P2 |
| "Used in" note link on artifacts page | MEDIUM | MEDIUM | P2 |
| Video thumbnail placeholder | LOW | LOW | P2 |
| Grid view toggle on artifacts page | LOW | MEDIUM | P2 |
| XLSX preview | MEDIUM | HIGH | P3 |
| PDF preview | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch — milestone is incomplete without these
- P2: Should have, add in follow-up phases
- P3: Nice to have, defer

---

## Competitor Feature Analysis

| Feature | Notion | Linear | Pilot Space Approach |
|---------|--------|--------|---------------------|
| Floating toolbar on selection | Yes — appears on text select, includes heading toggles, color, link, AI actions | Limited — issue-focused formatting | Extend existing `SelectionToolbar` with heading toggle; already has Bold/Italic/Link/AI actions |
| Focus/distraction-free mode | No native focus mode | No | MobX flag + CSS hide-chrome; Cmd+Shift+F shortcut |
| Pull quotes | No (blockquote only) | No | Attribute toggle on existing blockquote: blockquote → pull-quote via second click or `/pull-quote` command |
| Inline file cards | Yes — file blocks with icon, download, preview | No | Custom `FileCardNode` ReactNodeView + preview modal |
| Artifacts management page | Yes — "Files & Media" database view | No | Per-project page, flat list, optimistic CRUD, preview reuse |
| YouTube/Vimeo embeds | Yes — `/video` command supports YouTube, Vimeo, and more | No | `@tiptap/extension-youtube` + `@fourwaves/tiptap-extension-vimeo` |
| Image captions | Yes — click below image to add caption | No | Custom FigureNode or `tiptap-image-plus` |

---

## TipTap-Specific Implementation Notes

### What already exists — do NOT duplicate

- `StarterKit`: heading (H1/H2/H3), bold, italic, strike, code, blockquote, bulletList, orderedList, horizontalRule
- `SlashCommandExtension`: custom ProseMirror plugin — extend by adding new command entries only
- `SelectionToolbar`: custom floating toolbar at `frontend/src/components/editor/SelectionToolbar.tsx` — extend, do not replace
- `GhostTextExtension`: ghost text — ensure new InputRules and PasteRules do not conflict with ghost text decoration positions
- `CodeBlockExtension` with lowlight — reuse `lowlight` instance in `FilePreviewModal` for code file syntax highlighting
- `@tiptap/extension-highlight`, `@tiptap/extension-mention`, `@tiptap/extension-table`, task lists
- Existing `handleDOMEvents.drop` blocks file drops — change to route image files to Image node, other files to FileCardNode

### New TipTap dependencies needed

```
@tiptap/extension-image       — official, v3.20.x
@tiptap/extension-youtube     — official, v3.x
@fourwaves/tiptap-extension-vimeo — community, v3-compatible
```

Optional (P3 only, lazy-loaded):
```
xlsx  — SheetJS, ~250KB, dynamically imported only for XLSX preview
```

### New slash command entries to add to `slash-command-items.ts`

- `/image` → open image file picker, upload to Storage, insert Image node
- `/file` → open file picker (all supported types), upload, insert FileCardNode
- `/video` → open URL input popover, validate YouTube/Vimeo URL regex, insert video node
- `/pull-quote` → toggle blockquote with `data-type="pull-quote"` attribute

---

## Sources

- [TipTap BubbleMenu extension](https://tiptap.dev/docs/editor/extensions/functionality/bubble-menu) — confirmed React component API, Floating UI under the hood, stable per-instance plugin keys in 2025 update
- [TipTap Image extension](https://tiptap.dev/docs/editor/extensions/nodes/image) — confirmed v3 compatible, latest 3.20.2
- [TipTap Image Upload Node UI component](https://tiptap.dev/docs/ui-components/node-components/image-upload-node) — upload integration pattern reference
- [TipTap Figure extension experiment](https://tiptap.dev/docs/examples/experiments/figure) — caption pattern reference
- [TipTap YouTube extension](https://tiptap.dev/docs/editor/extensions/nodes/youtube) — official, confirmed v3
- [tiptap-image-plus (v3 compatible)](https://github.com/RomikMakavana/tiptap-image-plus) — third-party caption + resize alternative
- [@fourwaves/tiptap-extension-vimeo](https://github.com/fourwaves/tiptap-extension-vimeo) — Vimeo community extension, fork of official youtube extension
- [TanStack Query Optimistic Updates v5](https://tanstack.com/query/v5/docs/framework/angular/guides/optimistic-updates) — onMutate/onError/onSettled rollback pattern
- [Supabase Storage Signed URLs](https://supabase.com/docs/reference/javascript/storage-from-createsignedurl) — time-limited download URLs
- [Supabase Signed Upload URLs](https://supabase.com/docs/reference/javascript/storage-from-createsigneduploadurl) — secure upload token pattern
- [Supabase Resumable Uploads](https://supabase.com/docs/guides/storage/uploads/resumable-uploads) — large file handling reference
- Medium editor UX: floating toolbar on text selection; pull quote via second click on blockquote icon; focus mode hides all chrome
- Existing codebase reviewed: `SelectionToolbar.tsx`, `SlashCommandExtension.ts`, `slash-command-items.ts`, `config.ts`, `ai_attachments.py`, `workspace_quota.py`

---

*Feature research for: Medium-style editor, file artifact upload/preview, artifacts management page, video embeds*
*Researched: 2026-03-18*
