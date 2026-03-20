# Architecture Research

**Domain:** Medium-style Editor & File Artifacts — integration with existing TipTap + Supabase Storage
**Researched:** 2026-03-18
**Confidence:** HIGH (direct codebase inspection)

## System Overview

```
Existing Architecture (unchanged layers)
==========================================
Frontend: Next.js 15 App Router + MobX + TanStack Query + shadcn/ui
Backend:  FastAPI 5-layer Clean Architecture + SQLAlchemy async + DI
Database: PostgreSQL 16 + RLS + pgvector + pgmq
Auth:     Supabase Auth + JWT + RLS policies
Storage:  Supabase Storage (S3-compatible) — already used for chat-attachments bucket

New Components (v1.1 milestone)
==========================================

                    ┌─────────────────────────────────────────┐
                    │        Note Editor (TipTap)             │
                    │                                          │
                    │  Existing extensions (unchanged):        │
                    │  GhostText, SlashCommand, BlockId,       │
                    │  CodeBlock, PMBlock, Mention, etc.        │
                    │                                          │
                    │  NEW extensions (Group 3 — block types): │
                    │  ┌──────────────────────────────────┐   │
                    │  │ FileCardExtension (Node)          │   │
                    │  │ VideoEmbedExtension (Node)        │   │
                    │  │ PullQuoteExtension (Node)         │   │
                    │  │ ImageCaptionExtension (mark)      │   │
                    │  └──────────────────────────────────┘   │
                    │                                          │
                    │  NEW overlays (Group 5 — marks):         │
                    │  ┌──────────────────────────────────┐   │
                    │  │ FloatingToolbarExtension (mark)   │   │
                    │  └──────────────────────────────────┘   │
                    └──────────────┬───────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────▼──────┐  ┌─────────▼──────┐  ┌──────────▼──────┐
    │ File Upload    │  │ Preview Modal  │  │ Artifacts Page  │
    │ (new service)  │  │ (new component)│  │ (new page)      │
    └────────┬───────┘  └────────────────┘  └──────────┬──────┘
             │                                          │
             │ POST multipart                 TanStack Query
             ▼                                          │
    ┌────────────────┐                        ┌─────────▼──────┐
    │ Backend        │                        │ Backend        │
    │ artifacts API  │◄───────────────────────│ GET/DELETE     │
    │ (NEW router)   │                        │ artifacts      │
    └────────┬───────┘                        └────────────────┘
             │
             ▼
    ┌────────────────┐     ┌─────────────────────┐
    │ Artifact       │     │ Supabase Storage    │
    │ model (NEW)    │────▶│ note-artifacts/     │
    │ in PostgreSQL  │     │ {ws}/{note}/{id}/   │
    └────────────────┘     │ {filename}          │
                           └─────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status | Integration Point |
|-----------|----------------|--------|-------------------|
| `FileCardExtension` | TipTap node for inline file cards | NEW | Group 3 in `createEditorExtensions.ts` |
| `VideoEmbedExtension` | TipTap node for YouTube/Vimeo embeds | NEW | Group 3 in `createEditorExtensions.ts` |
| `PullQuoteExtension` | TipTap node for pull-quote blocks | NEW | Group 3 in `createEditorExtensions.ts` |
| `FloatingToolbarExtension` | Selection-triggered floating toolbar | NEW | Group 5 in `createEditorExtensions.ts` |
| `FilePreviewModal` | Multi-format preview dialog | NEW | shadcn/ui Dialog, called from FileCardView |
| `ArtifactsPage` | Per-project artifacts management | NEW | `/{ws}/projects/{pid}/artifacts/page.tsx` |
| `ArtifactStore` | MobX store for artifact CRUD + optimistic UI | NEW | `frontend/src/stores/features/artifacts/` |
| `Artifact` model | PostgreSQL model for persistent artifacts | NEW | `backend/.../models/artifact.py` |
| `ArtifactsRouter` | FastAPI endpoints for artifact CRUD | NEW | `backend/.../routers/project_artifacts.py` |
| `ArtifactUploadService` | Upload + Storage key management | NEW | Mirrors `AttachmentUploadService` pattern |
| `SupabaseStorageClient` | S3-compatible object storage | EXISTING | Already handles `chat-attachments` bucket |
| `SlashCommandExtension` | `/` block inserter | MODIFY | Add file-card and video-embed commands |
| `createEditorExtensions` | Extension factory | MODIFY | Register new extensions in correct groups |

## Critical Integration Points with Existing Architecture

### 1. TipTap Extension Registration Order

The existing `createEditorExtensions.ts` has a **mandatory ordering** enforced by comments and the `PRE-002` spec:

- **Group 3 (block-type nodes)**: `FileCardExtension`, `VideoEmbedExtension`, `PullQuoteExtension` MUST go here — after `CodeBlockExtension` and `PMBlockExtension`, before `BlockIdExtension`.
- **Group 5 (inline marks/decorations)**: `FloatingToolbarExtension` goes here — after `GhostTextExtension`.

Violating the order causes `BlockIdExtension` to miss new node types, breaking AI block references and annotation linking (the `PRE-002` constraint).

The `ImageCaptionExtension` is a mark (not a node), so it goes in Group 5 alongside other marks.

### 2. Existing `AttachmentUploadService` Is Not Reusable As-Is

The existing service (`application/services/ai/attachment_upload_service.py`) handles **chat context attachments** (temporary, 24h TTL, stored in `chat-attachments` bucket). Artifacts are **permanent** (no TTL, stored in `note-artifacts` bucket, linked to notes and projects).

The `SupabaseStorageClient` is fully reusable. The upload service pattern is the template — create a new `ArtifactUploadService` with different bucket, no TTL, different size limits (10MB uniform), and different allowed MIME types.

### 3. `ChatAttachment` Model Is Not Reusable

`ChatAttachment` has `expires_at`, `session_id`, and is user-scoped. The new `Artifact` model is note-scoped and project-scoped (permanent). Use `WorkspaceScopedModel` as the base (same as `Note`, `Project`) to get workspace-level RLS automatically.

### 4. Slash Command Integration

The existing `SlashCommandExtension` supports `SlashCommand[]` with an `execute(editor)` function. New commands for file card and video embed are added to `getDefaultCommands()` in `slash-command-items.ts`. The execute function for file-card triggers the file picker via a callback (same pattern as AI commands use `onAICommand`).

The `SlashCommand.group` type is currently `'formatting' | 'blocks' | 'ai'`. Add `'media'` for the new commands to group them correctly in the menu.

### 5. FileCard Node Stores artifact_id in TipTap JSON

The `FileCardExtension` node stores `{ artifact_id, filename, mime_type, size_bytes, uploaded_at }` as node attributes in the TipTap JSON document. The `artifact_id` is a UUID reference to the `artifacts` table. When the note is saved, the TipTap JSON persists in `notes.content` (JSONB), and the artifact metadata is available via the `artifact_id` reference.

This matches how `InlineIssueExtension` stores `issue_id` as an attribute and renders a React component NodeView.

### 6. MobX `ArtifactStore` Follows `NoteStore` Pattern

`NoteStore` uses MobX `makeAutoObservable` with TanStack Query for server sync. The `ArtifactStore` follows the same pattern:
- `artifacts: Map<string, Artifact[]>` keyed by `project_id`
- Optimistic updates on delete (remove from map, rollback on error)
- Optimistic updates on upload (add placeholder with `uploading: true`, replace on success)
- `isSaving`, `isLoading`, `error` state fields

### 7. RLS on `artifacts` Table

`WorkspaceScopedModel` provides `workspace_id` with an index and a FK to `workspaces.id (ondelete=CASCADE)`. Supabase's RLS policies filter by `workspace_id` in the JWT claims — no new RLS policy syntax needed, just follow the same migration pattern as other `WorkspaceScopedModel` tables.

## New Database Model

```python
# backend/src/pilot_space/infrastructure/database/models/artifact.py

class Artifact(WorkspaceScopedModel):
    """Permanent file artifact linked to a note and project.

    Storage key format:
        note-artifacts/{workspace_id}/{project_id}/{note_id}/{artifact_id}/{filename}

    Attributes:
        note_id: Note where this artifact was first uploaded.
        project_id: Project owning this artifact (for management page).
        uploader_id: User who uploaded the file.
        filename: Original filename including extension (max 255 chars).
        mime_type: MIME type, e.g. 'text/csv' (max 100 chars).
        size_bytes: File size in bytes; must be > 0 and <= 10MB.
        storage_key: Supabase Storage object path; globally unique.
        description: Optional user-provided description.
    """
    __tablename__ = "artifacts"

    note_id: Mapped[uuid.UUID | None]  # FK to notes.id (SET NULL on delete)
    project_id: Mapped[uuid.UUID]      # FK to projects.id (CASCADE delete)
    uploader_id: Mapped[uuid.UUID]     # FK to users.id (SET NULL on delete)
    filename: Mapped[str]              # String(255)
    mime_type: Mapped[str]             # String(100)
    size_bytes: Mapped[int]            # BigInteger, CHECK > 0
    storage_key: Mapped[str]           # Text, unique
    description: Mapped[str | None]    # Text, nullable

    __table_args__ = (
        Index("ix_artifacts_project_id", "project_id"),
        Index("ix_artifacts_note_id", "note_id"),
        Index("ix_artifacts_uploader_id", "uploader_id"),
        CheckConstraint("size_bytes > 0", name="ck_artifacts_size_positive"),
        CheckConstraint(
            "size_bytes <= 10485760",  # 10MB
            name="ck_artifacts_size_max"
        ),
    )
```

## New TipTap Extensions

### FileCardExtension

A TipTap `Node` (block-level, non-editable) that renders as an inline file card. Follows the same pattern as `InlineIssueExtension` (which uses `ReactNodeViewRenderer`).

**Node schema:**
```typescript
addAttributes() {
  return {
    artifactId: { default: null },
    filename: { default: '' },
    mimeType: { default: '' },
    sizeBytes: { default: 0 },
    uploadedAt: { default: null },
    // 'uploading' is client-only state — NOT persisted in TipTap JSON
    // Managed via editor.storage['fileCard'].pendingUploads Set<string>
  };
}
```

**NodeView component** (`FileCardView.tsx`):
- Displays filename, file type icon, human-readable size
- Click triggers `FilePreviewModal` (signed URL fetched via `GET /artifacts/{id}/signed-url`)
- Upload state: show spinner while `artifactId` is null (placeholder node during upload)
- Only non-`observer()` concern: same constraint as `PropertyBlockView` — `ReactNodeViewRenderer` + MobX `observer()` causes `flushSync` errors in React 19. Use context bridge if MobX reactive state is needed inside the NodeView.

### VideoEmbedExtension

A TipTap `Node` that parses YouTube/Vimeo URLs and renders `<iframe>` embeds. Uses `ReactNodeViewRenderer`.

**URL patterns to detect:**
- YouTube: `https://www.youtube.com/watch?v={id}`, `https://youtu.be/{id}`
- Vimeo: `https://vimeo.com/{id}`

**Node attributes:** `{ url, embedUrl, platform: 'youtube' | 'vimeo', videoId }`

**Paste handler**: Override `addProseMirrorPlugins()` with a paste handler that detects YouTube/Vimeo URLs pasted alone on a new line and auto-converts them to video embed nodes. This matches how Medium handles YouTube URLs pasted at the start of a line.

### FloatingToolbarExtension

A TipTap `Extension` (not a Node or Mark) that renders a floating toolbar when text is selected. Uses a `Decoration.widget` positioned above the selection, similar to how `SlashCommandExtension` renders its menu.

**Toolbar buttons:** Bold, Italic, Underline, Code (inline), Link, Highlight, H1/H2/H3 toggle, Quote block.

**Key constraint**: The toolbar must NOT use `observer()` for the same reasons as `FileCardView`. Use `editor.on('selectionUpdate', ...)` to show/hide the toolbar based on selection state. This avoids MobX entirely for toolbar visibility state.

**Position calculation**: Use `editor.view.coordsAtPos(selection.from)` to get absolute coordinates, then position the toolbar DOM element via `position: fixed` in the `Decoration.widget` callback.

### PullQuoteExtension

A TipTap `Node` for Medium-style pull quotes (large, centered text block). Extends `Blockquote` with a different HTML rendering. Simple extension — no NodeView needed.

```typescript
// Renders as: <blockquote class="pull-quote">...</blockquote>
// CSS handles the large typography treatment
```

## New Frontend Components

### FilePreviewModal

A shadcn/ui `Dialog` that renders different preview UIs based on MIME type. The signed URL is fetched from `GET /workspaces/{wid}/artifacts/{id}/signed-url` when the modal opens.

| MIME Type | Preview Component | Library |
|-----------|-------------------|---------|
| `image/*` | `<img>` with zoom | Browser native |
| `text/plain`, `text/markdown` | Syntax-highlighted text | `shiki` (already used by `CodeBlockExtension`) |
| `text/csv` | Scrollable table | Custom table component |
| `application/json` | Syntax-highlighted JSON | `shiki` |
| `text/x-python`, `text/javascript`, etc. | Syntax-highlighted code | `shiki` |
| `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Table preview | `xlsx` (new dependency) or `SheetJS` |
| Unsupported | Download button + filename | None |

**No PDF viewer**: PDF preview requires a heavy dependency (`react-pdf`). Given the 10MB limit applies to all file types and PDFs are not in the file-card scope (chat attachments support PDF but note artifacts are for code/data/text files), PDF preview can be deferred.

### ArtifactsPage

Route: `/{workspaceSlug}/projects/{projectId}/artifacts`

A grid/list of all artifacts for a project. Each card shows filename, type icon, uploader avatar, upload date, size. Actions: preview (opens `FilePreviewModal`), copy link, delete (with optimistic removal).

**TanStack Query integration**: `useQuery(['artifacts', projectId])` fetches `GET /workspaces/{wid}/projects/{pid}/artifacts`. Mutations use `useMutation` with `onMutate` for optimistic updates — same pattern as issue CRUD.

**ArtifactStore (MobX)**: Manages upload progress state (`uploading`, `progress`) for files being uploaded from the editor. TanStack Query manages the fetched list. ArtifactStore handles the ephemeral upload state. This separation matches how `NoteStore` handles save state (MobX) while TanStack Query handles the note list.

## Data Flow

### File Upload Flow (from Editor)

```
User selects file via /file-card slash command (triggers <input type="file">)
    |
    v
FileCardExtension inserts placeholder node:
  { type: 'fileCard', attrs: { artifactId: null, filename, mimeType, sizeBytes: 0 } }
    |
    v
ArtifactStore.upload(noteId, projectId, file)
  -> POST /workspaces/{wid}/projects/{pid}/artifacts (multipart/form-data)
  -> ArtifactUploadService:
       1. Validate MIME type (whitelist)
       2. Validate size <= 10MB
       3. storage.upload_object('note-artifacts', key, data, content_type)
       4. artifact_repo.create(Artifact(...))
       5. Return { artifact_id, filename, mime_type, size_bytes }
    |
    v
On success: editor.commands.updateFileCard(placeholderId, { artifactId, sizeBytes })
  -> FileCardExtension updates node attrs with real artifact_id
    |
    v
Note auto-save (2s debounce) persists TipTap JSON with artifact_id in node attrs
```

### File Preview Flow (from Editor or Artifacts Page)

```
User clicks FileCard / artifact in ArtifactsPage
    |
    v
FilePreviewModal opens (artifact_id passed as prop)
    |
    v
TanStack Query: GET /workspaces/{wid}/artifacts/{id}/signed-url
  -> Backend: storage.get_signed_url('note-artifacts', artifact.storage_key, expires_in=3600)
  -> Returns { signed_url }
    |
    v
Modal renders preview using signed_url:
  - Images: <img src={signed_url}>
  - Text/code: fetch(signed_url) -> render with shiki
  - CSV: fetch(signed_url) -> parse -> render table
  - Excel: fetch(signed_url) -> parse with xlsx library -> render table
```

### Video Embed Flow

```
User types /video (slash command) or pastes YouTube/Vimeo URL on blank line
    |
    v
VideoEmbedExtension.parseURL(url) -> { platform, videoId, embedUrl }
    |
    v
Insert VideoEmbed node: { url, embedUrl, platform, videoId }
    |
    v
VideoEmbedView renders:
  <iframe src={embedUrl} sandbox="allow-scripts allow-same-origin" />
  with aspect-ratio: 16/9 wrapper
    |
    v
Note auto-save persists the node attrs (only url/embedUrl stored, no backend record)
```

Video embeds are purely client-rendered — no backend storage needed. The `embedUrl` is derived from the `url` at insertion time. No `artifact_id` involved.

### Artifacts Management Page Flow

```
User navigates to /{ws}/projects/{pid}/artifacts
    |
    v
ArtifactsPage mounts
    |
    v
TanStack Query: GET /workspaces/{wid}/projects/{pid}/artifacts
  -> ArtifactRepository.list_by_project(project_id)
  -> Returns { items: Artifact[], total }
    |
    v
Grid renders artifact cards
    |
    v
User deletes artifact:
  1. Optimistic: remove from local cache (TanStack queryClient.setQueryData)
  2. DELETE /workspaces/{wid}/artifacts/{id}
     -> ArtifactUploadService.delete(artifact_id, user_id)
     -> storage.delete_object('note-artifacts', artifact.storage_key)
     -> artifact_repo.delete(artifact_id)
  3. On error: rollback (invalidate query to refetch)
```

## Recommended Project Structure

```
backend/
  alembic/versions/
    0XX_add_artifacts_table.py              # NEW: artifacts table + RLS migration

  src/pilot_space/
    api/v1/
      routers/
        project_artifacts.py               # NEW: CRUD + signed-url endpoints
      schemas/
        artifact.py                        # NEW: ArtifactResponse, ArtifactUploadResponse

    application/services/
      artifact/
        __init__.py                        # NEW: service exports
        artifact_upload_service.py         # NEW: upload/delete service (mirrors AttachmentUploadService)
        artifact_content_service.py        # NEW: signed URL generation

    infrastructure/database/
      models/
        artifact.py                        # NEW: Artifact ORM model
      repositories/
        artifact_repository.py             # NEW: CRUD repository

    container/
      container.py                         # MODIFY: wire ArtifactUploadService + ArtifactRepository

frontend/
  src/
    stores/features/artifacts/
      ArtifactStore.ts                     # NEW: MobX store (upload progress, optimistic delete)

    features/notes/editor/extensions/
      FileCardExtension.ts                 # NEW: TipTap Node for file cards (Group 3)
      FileCardView.tsx                     # NEW: React NodeView component
      VideoEmbedExtension.ts              # NEW: TipTap Node for video embeds (Group 3)
      VideoEmbedView.tsx                   # NEW: React NodeView with <iframe>
      PullQuoteExtension.ts               # NEW: TipTap Node extending Blockquote (Group 3)
      FloatingToolbarExtension.ts         # NEW: Selection toolbar Extension (Group 5)
      FloatingToolbarView.tsx             # NEW: Toolbar DOM component

    features/notes/editor/extensions/
      slash-command-items.ts              # MODIFY: add file-card, video-embed commands
      createEditorExtensions.ts           # MODIFY: register new extensions in correct groups
      index.ts                            # MODIFY: export new extensions

    features/artifacts/
      components/
        artifact-card.tsx                 # NEW: grid card with icon, name, size, actions
        artifact-grid.tsx                 # NEW: responsive grid layout
        file-preview-modal.tsx            # NEW: multi-format preview Dialog
        file-preview-renderers/
          image-preview.tsx               # NEW
          text-preview.tsx               # NEW (uses shiki)
          csv-preview.tsx                # NEW
          excel-preview.tsx              # NEW (uses xlsx)
          code-preview.tsx               # NEW (uses shiki)
      hooks/
        useArtifacts.ts                   # NEW: TanStack Query hooks
        useUploadArtifact.ts             # NEW: mutation hook
        useDeleteArtifact.ts             # NEW: mutation hook with optimistic update
        useArtifactSignedUrl.ts          # NEW: signed URL fetch hook

    app/(workspace)/[workspaceSlug]/
      projects/[projectId]/
        artifacts/
          page.tsx                        # NEW: ArtifactsPage route

    stores/
      RootStore.ts                        # MODIFY: add artifacts: ArtifactStore
```

### Structure Rationale

- **`features/artifacts/` separate from `features/notes/`**: Artifacts have their own management page and are not exclusive to the editor. The editor imports from `features/artifacts/` for the preview modal.
- **`FileCardExtension.ts` stays in `features/notes/editor/extensions/`**: All TipTap extensions live here by convention. The NodeView (`FileCardView.tsx`) is co-located.
- **`ArtifactStore` in global stores**: Upload progress state must be accessible from both the editor (while uploading) and the artifacts page (showing recent uploads). Global store, not feature-local.
- **`project_artifacts.py` router**: Named to avoid collision with the existing `ai_attachments.py` (chat context) and `_chat_attachments.py` (internal) routers.

## Architectural Patterns

### Pattern 1: Extension Group Ordering for New Nodes

**What:** Register new TipTap node extensions in Group 3 of `createEditorExtensions.ts`, before `BlockIdExtension`.
**When to use:** Every new node type extension.
**Trade-offs:** Requires discipline about ordering. Reward: all new block nodes get stable `blockId` attributes automatically, enabling AI block references, annotation linking, and scroll sync without additional work.

```typescript
// In createEditorExtensions.ts, Group 3:
// ... existing: CodeBlockExtension, PMBlockExtension ...
extensions.push(FileCardExtension.configure({ ... }));
extensions.push(VideoEmbedExtension.configure({ ... }));
extensions.push(PullQuoteExtension);
// ── Group 4: Block IDs (MUST remain last) ────
extensions.push(BlockIdExtension.configure({ ... }));
```

### Pattern 2: Placeholder Node for Optimistic Upload

**What:** Insert a placeholder TipTap node with `artifactId: null` immediately on file selection, then update attrs with real `artifactId` after upload completes.
**When to use:** File card uploads.
**Trade-offs:** The placeholder node persists in TipTap JSON if the upload fails. Need cleanup: detect `artifactId: null` nodes on editor mount and remove them (stale upload artifacts from failed sessions).

```typescript
// On file select:
editor.commands.insertContent({
  type: 'fileCard',
  attrs: { artifactId: null, filename, mimeType, sizeBytes: 0, uploading: true }
});

// After upload:
editor.commands.command(({ tr, state }) => {
  state.doc.descendants((node, pos) => {
    if (node.type.name === 'fileCard' && node.attrs.filename === filename && !node.attrs.artifactId) {
      tr.setNodeMarkup(pos, null, { ...node.attrs, artifactId, sizeBytes, uploading: false });
      return false;
    }
  });
  return true;
});
```

### Pattern 3: Service Role Storage — No Direct Frontend Uploads

**What:** All file uploads go through the FastAPI backend (not directly to Supabase Storage from the browser).
**When to use:** All artifact operations.
**Trade-offs:** One extra network hop vs. direct browser-to-storage upload. Reward: backend enforces MIME whitelist, size limits, quota checks, and creates the DB record atomically. Direct browser uploads would bypass all server-side validation.

This matches the existing `AttachmentUploadService` pattern — the backend uses the service role key to bypass RLS for the storage write, then creates the DB record which IS subject to RLS for subsequent reads.

### Pattern 4: Signed URLs for Preview Downloads

**What:** Never expose the service role key to the frontend. Instead, generate signed URLs server-side with short TTL (1 hour), return to frontend, let browser fetch directly from Supabase Storage.
**When to use:** All file preview operations.
**Trade-offs:** Extra round-trip to generate signed URL before preview. Reward: the service role key never leaves the backend; preview URLs expire after 1 hour.

The `SupabaseStorageClient.get_signed_url()` method is already implemented and tested. No new client code needed.

### Pattern 5: TanStack Query for Artifact List + MobX for Upload Progress

**What:** Separate the concerns: TanStack Query owns the persistent server state (list of artifacts), MobX `ArtifactStore` owns ephemeral client state (current upload progress, placeholder nodes).
**When to use:** Any feature that combines server-fetched lists with client-side ephemeral state.
**Trade-offs:** Two state systems to reason about. This is already the established pattern in this codebase (NoteStore + TanStack Query notes list, IssueStore + TanStack Query).

## Anti-Patterns

### Anti-Pattern 1: Observer on TipTap NodeView

**What people do:** Wrap `FileCardView` or `VideoEmbedView` with `observer()` from MobX.
**Why it is wrong:** `ReactNodeViewRenderer` + MobX `observer()` causes nested `flushSync` errors in React 19. This is the documented constraint from `IssueEditorContent` in the memory notes (`feat/issue-note`).
**Do this instead:** Keep NodeViews as plain React components. Pass reactive data via React context (same context bridge pattern as `IssueNoteContext`). For upload progress state, pass it as a prop from the Extension's `onUploadProgress` callback.

### Anti-Pattern 2: Storing Video Embed Content in the Backend

**What people do:** Create a backend model for video embeds, store the URL in the database separately from the note content.
**Why it is wrong:** The video embed node attributes (url, embedUrl, videoId) are already stored inside `notes.content` JSONB. Creating a separate table duplicates data and adds an unnecessary join.
**Do this instead:** Video embeds are purely editor content. The TipTap JSON in `notes.content` is the single source of truth. No backend record needed beyond the note itself.

### Anti-Pattern 3: Reusing `chat-attachments` Bucket for Artifacts

**What people do:** Store artifacts in the existing `chat-attachments` bucket since the upload service already exists.
**Why it is wrong:** `chat-attachments` has TTL-based expiry (24h) enforced by a `pg_cron` job. Artifacts are permanent. Using the same bucket would either delete artifacts or require disabling TTL cleanup for the entire bucket.
**Do this instead:** Use a separate `note-artifacts` bucket with no TTL. Create `ArtifactUploadService` as a sibling of `AttachmentUploadService` — same pattern, different bucket, no `expires_at`.

### Anti-Pattern 4: Inline File Preview Without Signed URLs

**What people do:** Return a public download URL from the upload endpoint and store it in the node attrs.
**Why it is wrong:** Public URLs mean anyone with the URL can access the file — even after workspace membership is revoked. The file is sensitive (code, CSVs, etc.).
**Do this instead:** Store only `storage_key` in the backend and `artifact_id` in the TipTap node. Generate signed URLs on-demand via `GET /artifacts/{id}/signed-url` with 1-hour TTL.

### Anti-Pattern 5: Loading All Artifact Metadata Into the Editor on Page Load

**What people do:** Eagerly fetch all artifact metadata for a note when the editor loads, to hydrate the FileCard nodes.
**Why it is wrong:** Notes can have many file cards. Fetching all artifact records upfront adds latency to note load. Most cards may not be viewed.
**Do this instead:** The TipTap JSON node already contains `filename`, `mimeType`, `sizeBytes` as display attributes. The card renders immediately from these. Only when the user clicks "preview" does the frontend fetch the signed URL for that single artifact. Lazy loading per-artifact.

### Anti-Pattern 6: `onAICommand`-style Callback for File Upload in Slash Command

**What people do:** Extend the `onAICommand` callback to handle file uploads.
**Why it is wrong:** `onAICommand` is specifically for AI operations. File upload is a different concern.
**Do this instead:** Add a new `onFileCommand` callback option to `SlashCommandOptions`, and pass it through the same way `onAICommand` is passed. Keeps the interface clean and semantically correct.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Supabase Storage | Backend `SupabaseStorageClient` (existing) | Use `note-artifacts` bucket; client already handles upload/sign/delete |
| Supabase RLS | `WorkspaceScopedModel` base class | Automatic workspace filtering on `artifacts` table |
| `shiki` | Already used by `CodeBlockExtension` | Reuse the same `lowlight`/`shiki` instance for preview |
| `xlsx` (SheetJS) | New frontend dependency | Only loaded in `ExcelPreview` component (lazy import) |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `FileCardExtension` <-> `ArtifactStore` | Extension callback (`onUpload`) → Store action | Extension calls `onUpload(file)`, store handles API call, returns `artifactId` |
| `FileCardView` <-> `FilePreviewModal` | React state (local `useState`) | Modal is local to `FileCardView`; signed URL fetched in modal `onOpen` |
| `ArtifactsPage` <-> `ArtifactStore` | TanStack Query hooks | Page uses `useArtifacts(projectId)` hook; delete uses `useDeleteArtifact()` |
| `createEditorExtensions` <-> new extensions | Import + configure | New extensions must be imported and inserted at the correct group position |
| `SlashCommandExtension` <-> `FileCardExtension` | Slash command `execute` callback | `/file-card` command triggers file picker, calls `onFileCommand` callback |
| `project_artifacts` router <-> `ArtifactUploadService` | FastAPI DI (`AttachmentUploadServiceDep` pattern) | New DI provider `ArtifactUploadServiceDep` wired in `container.py` |

## Suggested Build Order

Build order is dependency-driven. Each phase has a testable output.

| Order | Component | Depends On | Rationale |
|-------|-----------|------------|-----------|
| 1 | DB migration + `Artifact` model | Nothing | Foundation for all artifact features |
| 2 | `ArtifactUploadService` + `project_artifacts` router | Migration + `SupabaseStorageClient` (existing) | Backend must exist before frontend upload |
| 3 | `FileCardExtension` + `FileCardView` (no upload, static data) | Nothing | Unblocked; test with hardcoded attrs first |
| 4 | File upload integration (slash command → upload → update node) | Steps 2 + 3 | Connects editor to backend |
| 5 | `FilePreviewModal` (image + text/code types) | Step 2 (signed URL endpoint) | Common file types first |
| 6 | `ArtifactStore` + `ArtifactsPage` | Steps 1-2 | Management page can be built after storage layer |
| 7 | `FilePreviewModal` (CSV + Excel types) | Step 5 | Depends on `xlsx` dependency; do after common types |
| 8 | `VideoEmbedExtension` + `VideoEmbedView` | Nothing | Fully self-contained; no backend required |
| 9 | `FloatingToolbarExtension` | Nothing | Self-contained editor UX; no backend |
| 10 | `PullQuoteExtension` | Nothing | Simple node extension, 30 min effort |
| 11 | Focus mode (fullscreen editor) | Steps 9-10 | Final editor UX polish; needs toolbar complete |

**Critical path:** 1 → 2 → 4 (storage layer and upload flow before the rest).

**Parallelizable:** Steps 3, 8, 9, 10 are fully independent of the backend and can be built in parallel with steps 1-2. Step 6 (ArtifactsPage) can start once step 2 is done.

**Deferred:** Focus mode (step 11) and Excel preview (step 7) are the lowest-priority items and can slip if time-constrained.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-500 artifacts per project | Current approach fine. Single list query with pagination. |
| 500-5000 artifacts per project | Add cursor-based pagination to `GET /projects/{pid}/artifacts`. |
| Large files (close to 10MB) | S3 multipart upload via backend presigned URL. Current httpx approach (full file in memory) is a memory spike risk. Not needed for 10MB limit at current scale. |
| High concurrent uploads | `SupabaseStorageClient` creates a new `httpx.AsyncClient` per call (already async). No pooling issue at current scale. |

## Sources

- Direct codebase inspection (HIGH confidence):
  - `backend/src/pilot_space/application/services/ai/attachment_upload_service.py` — template for `ArtifactUploadService`
  - `backend/src/pilot_space/infrastructure/storage/client.py` — existing `SupabaseStorageClient`
  - `backend/src/pilot_space/infrastructure/database/models/chat_attachment.py` — template for `Artifact` model design (with differences noted)
  - `backend/src/pilot_space/api/v1/routers/ai_attachments.py` — template for `project_artifacts.py` router
  - `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` — extension ordering constraints (PRE-002)
  - `frontend/src/features/notes/editor/extensions/slash-command-items.ts` — slash command extension pattern
  - `frontend/src/features/notes/editor/extensions/SlashCommandExtension.ts` — plugin key/state pattern
  - `frontend/src/stores/features/notes/NoteStore.ts` — MobX store pattern template
  - `frontend/src/stores/RootStore.ts` — store registration pattern
  - `backend/src/pilot_space/infrastructure/database/base.py` — `WorkspaceScopedModel` base
  - `backend/src/pilot_space/container/container.py` — DI wiring pattern
  - `.planning/PROJECT.md` — v1.1 milestone requirements and constraints
  - Memory notes (`feat/issue-note`) — `observer()` + `ReactNodeViewRenderer` constraint

---
*Architecture research for: v1.1 Medium Editor & Artifacts integration with existing Pilot Space*
*Researched: 2026-03-18*
