# Pitfalls Research

**Domain:** Adding Medium-style editor extensions, file artifact uploads with preview modals, Supabase Storage integration, per-project artifacts management page, and YouTube/Vimeo video embeds to an existing TipTap-based platform (Pilot Space v1.1)
**Researched:** 2026-03-18
**Confidence:** HIGH (direct codebase analysis of existing TipTap extension setup + verified via TipTap GitHub issues and official docs)

## Critical Pitfalls

### Pitfall 1: New Block Extensions Inserted After BlockIdExtension Break UUID Assignment

**What goes wrong:**
Any new TipTap block node extension (FileCardNode, VideoEmbedNode, PullQuoteNode, ImageCaptionNode) inserted into the extension array AFTER `BlockIdExtension` will not receive stable block UUIDs. The `BlockIdExtension` traverses the schema and assigns UUIDs at registration time — nodes registered after it are invisible to that traversal. This means the new nodes lack `blockId` attributes, which breaks: margin annotation linking, AI block references, scroll sync, and the knowledge graph chunker that uses block IDs to identify content segments.

**Why it happens:**
The codebase has a clearly documented ordering rule (PRE-002 in `createEditorExtensions.ts`): new block-type extensions go in Group 3, BEFORE `BlockIdExtension` in Group 4. Developers adding a new extension either miss this comment or append to the end of the array as a convenience. The failure is silent at first — the block renders correctly, but `blockId` is null.

**How to avoid:**
Insert all new block-type extensions (Group 3) in `createEditorExtensions.ts` BEFORE the Group 4 marker comment. The file documents this precisely. No exceptions. Add a dev-time assertion in `BlockIdExtension` that logs a warning if any registered node type has a null `blockId` after assignment.

**Warning signs:**
- `blockId` attribute is `null` on newly inserted nodes (inspect via `editor.getJSON()`)
- Margin annotation clicking does nothing for new block types
- AI block processing indicator never appears on new blocks
- Knowledge graph chunker emits `NOTE_CHUNK` nodes without valid `blockId`

**Phase to address:**
Phase 1 (TipTap Extension Foundation) — establish the extension registration order before any new node is built.

---

### Pitfall 2: Floating Toolbar (BubbleMenu) Conflicts With Ghost Text and Slash Command Decorations

**What goes wrong:**
TipTap's `BubbleMenu` extension uses a separate Tippy.js instance that fires on every editor selection change. The existing `GhostTextExtension` stores a decoration at the cursor position and fires `handleTextInput` to show/hide ghost text. The existing `SlashCommandExtension` tracks its own plugin state via `SLASH_COMMAND_PLUGIN_KEY`. When a new floating Medium-style toolbar is added using `BubbleMenu`, three failure modes emerge: (1) the BubbleMenu appears while ghost text is active and Tab key now has two consumers (accept ghost text vs. dismiss BubbleMenu), (2) the BubbleMenu fires `shouldShow` while the slash command menu is open (because slash command mode does not suppress selection), and (3) Tippy.js destroys or repositions the ghost text decoration widget DOM node when it calculates BubbleMenu placement.

**Why it happens:**
`GhostTextExtension` explicitly checks `SLASH_COMMAND_PLUGIN_KEY.getState(view.state)?.isActive` before triggering AI (line 406 of `GhostTextExtension.ts`). But this coordination is one-directional — the BubbleMenu does not check ghost text or slash command state. BubbleMenu fires on any non-empty selection, regardless of what other extensions are doing. The existing `SelectionToolbar` in this codebase avoids this issue by NOT using `BubbleMenu` — it uses a custom selection listener (`selectionchange` event + `getBoundingClientRect`). Adding a second floating layer using the official `BubbleMenu` API introduces the Tippy conflict.

**How to avoid:**
Do NOT use TipTap's `BubbleMenu` extension. Follow the pattern already established in `SelectionToolbar.tsx`: implement a custom floating toolbar using selection position calculation via `editor.state.selection` and `view.coordsAtPos()`. The `shouldShow` logic must check: `!ghostTextStorage.text && !slashCommandState?.isActive && !selection.empty`. This keeps all three plugins coordinated through explicit state checks rather than relying on Tippy.js layering. The existing `SelectionToolbar` is already the Medium-style floating toolbar — extend it rather than adding a second one.

**Warning signs:**
- Tab key accepts ghost text AND dismisses BubbleMenu simultaneously (double-trigger)
- BubbleMenu appears while slash command dropdown is open
- Ghost text decoration flickers or disappears when user makes a text selection
- Two floating elements overlap on the screen

**Phase to address:**
Phase 2 (Medium-Style Editor UX) — before building any floating toolbar UI, decide to extend `SelectionToolbar` not add `BubbleMenu`.

---

### Pitfall 3: FileCardNode Markdown Serialization Breaks Auto-Save and Knowledge Graph

**What goes wrong:**
The existing editor saves content via `tiptap-markdown`'s serialization (the `Markdown` extension is in Group 1 of `createEditorExtensions.ts`). New custom node types — `FileCardNode`, `VideoEmbedNode`, `PullQuoteNode` — have no `renderMarkdown` serializer defined. The `tiptap-markdown` extension silently drops nodes it cannot serialize, producing incomplete saved content. Additionally, the `markdown_chunker.py` background job in the knowledge graph pipeline uses heading-based text extraction. Custom nodes that serialize to nothing or to opaque JSON blobs become invisible to the chunker, breaking AI recall.

**Why it happens:**
TipTap's Markdown extension requires each custom node to register a `renderMarkdown` function. The existing `PMBlockExtension` already documents this: it explicitly states "NOT markdown — complex PM structures have no markdown representation." Developers building new nodes copy PMBlock's pattern without realizing that omitting `renderMarkdown` means silently discarded content at save time.

**How to avoid:**
For each new node type, decide the serialization strategy explicitly before building: (1) Simple nodes like `PullQuoteNode` and `VideoEmbedNode` should serialize to a readable Markdown comment or fenced block (e.g., `:::video{src="..."}`) so content survives round-trips. (2) `FileCardNode` should serialize to a Markdown link with artifact metadata (e.g., `[filename.csv](artifact://uuid)`). (3) Register `renderMarkdown` in each extension's `addExtensions` or via the Markdown extension's `types` configuration. Test round-trip: insert node → get markdown → re-parse → verify node survives.

**Warning signs:**
- File card blocks disappear after page reload (serialized to empty string, saved, parsed back as nothing)
- Auto-save strips video embed blocks silently
- Knowledge graph shows empty chunks for notes that contain only artifact cards
- `editor.storage.markdown.getMarkdown()` returns content shorter than the rendered document

**Phase to address:**
Phase 1 (TipTap Extension Foundation) — define serialization contract for each new node BEFORE building node views.

---

### Pitfall 4: ReactNodeViewRenderer on New Nodes Triggers Nested flushSync in React 19

**What goes wrong:**
The `PMBlockNodeView` and `PropertyBlockView` both use `ReactNodeViewRenderer`. The project memory explicitly documents that `IssueEditorContent` must NOT be wrapped in `observer()` because MobX's `useSyncExternalStore` calls `flushSync` when observables change, which conflicts with TipTap's `ReactNodeViewRenderer` calling `flushSync` during React's rendering lifecycle (React 19 strict mode error: "Cannot update a component from inside the function body of a different component").

New node views for `FileCardNode` (shows upload progress, filename, icon) and `VideoEmbedNode` (shows embedded iframe or placeholder) are natural candidates for MobX `observer()` wrapping since they need reactive updates (upload progress, artifact metadata). Wrapping them in `observer()` reproduces the flushSync crash.

**Why it happens:**
TipTap's `ReactRenderer` calls `flushSync` when `editor.isInitialized` (tracked in `ReactRenderer.tsx:188-191`). MobX `observer()` uses React 18/19's `useSyncExternalStore` which also triggers synchronous rendering. When TipTap updates the node view (e.g., after upload completes), flushSync from TipTap and flushSync from MobX nest, causing the React invariant violation.

**How to avoid:**
Apply the same pattern documented for `PropertyBlockView`: use `ReactNodeViewRenderer` with a plain (non-observer) wrapper component that bridges to an observer child via React context. The pattern: `FileCardNodeView` (plain wrapper, receives TipTap `NodeViewProps`) → provides context → `FileCardContent` (observer, reads artifact store and file upload state). The context bridge decouples TipTap's rendering cycle from MobX's. See `issue-note-context.ts` and `issue-editor-content.tsx` for the established pattern.

**Warning signs:**
- Console error: "Cannot update a component from inside the function body of a different component" on file card insertion
- React Error Boundary catching "flushSync was called from inside a lifecycle method"
- Upload progress bar never updates (observer wrapped incorrectly, update cycle blocked)
- Node view appears static but console shows continuous render errors

**Phase to address:**
Phase 1 (TipTap Extension Foundation) — establish the node view wrapper pattern before building any node view UI.

---

### Pitfall 5: Supabase Storage Service-Role Bypass Means No RLS on Artifact Objects

**What goes wrong:**
The existing `SupabaseStorageClient` uses the service role key for ALL operations (documented in `backend/src/pilot_space/infrastructure/storage/client.py`: "All requests use the service role key so operations are not subject to RLS policies"). This is correct for the current AI attachment use case (backend-initiated uploads), but for user-uploaded artifacts that must be scoped per-project and per-workspace, using service role means there is no DB-level enforcement preventing one workspace from reading another workspace's artifact files if they can construct the storage key.

**Why it happens:**
The service role client was built for a different use case (AI attachments managed entirely by the backend). Reusing it for user artifacts inherits the "bypass RLS" characteristic without enforcing workspace isolation at the storage layer. The bucket key format (e.g., `{workspace_id}/{project_id}/{artifact_id}/{filename}`) provides logical isolation but only at the application layer — any code with the service key (or any future bug that leaks a key) can read across workspaces.

**How to avoid:**
Two layers of enforcement: (1) Backend API: every artifact endpoint must verify `workspace_id` and `project_id` ownership via the existing `get_current_session()` auth context before issuing any storage operation. This is the primary enforcement layer. (2) Bucket-level policies: configure the `artifacts` bucket as private (not public); use service-role only for the backend FastAPI process; never expose storage keys or presigned URLs to the frontend directly. (3) Key naming: always prefix keys with `{workspace_id}/{project_id}/` and validate this in `ArtifactService.upload()` before calling `SupabaseStorageClient.upload_object()`. This adds defense-in-depth even if a bug bypasses the auth check.

**Warning signs:**
- Artifact API endpoint does not check `project.workspace_id == current_workspace_id` before calling storage
- Presigned URLs embed no workspace context (raw UUID paths allow enumeration)
- Storage bucket is set to Public instead of Private

**Phase to address:**
Phase 3 (Storage Backend) — write RLS-equivalent application-layer checks as part of `ArtifactService` before the endpoint goes live.

---

### Pitfall 6: Signed URL Expiry Creates Stale Previews in Preview Modals

**What goes wrong:**
The existing `SupabaseStorageClient.get_signed_url()` defaults to 1-hour expiry. When the artifacts management page loads, it requests signed URLs for all visible artifacts. If the user keeps the page open for >1 hour, all preview modal URLs are stale — the modal opens a broken image or a 403 response. More critically, if the artifact list is cached in TanStack Query with a long `staleTime`, the signed URLs cached in the query data expire while the cache entry is still considered fresh, producing preview failures without any network error visible to the user.

**Why it happens:**
TanStack Query caches the entire API response including signed URLs. The query `staleTime` controls when the query re-fetches, but this is unrelated to URL expiry. A query with `staleTime: 5 * 60 * 1000` (5 minutes) re-fetches every 5 minutes, but signed URLs valid for 1 hour stay in cache for up to 5 minutes between refreshes — this is fine. The failure happens if `staleTime` is set to `Infinity` (common for artifact lists that "don't change often") or if the user is on a slow connection where the initial fetch took long and then the page sits open.

**How to avoid:**
(1) Set artifact list query `staleTime` to at most 55 minutes — well under the signed URL expiry. (2) Set signed URL expiry to 2 hours, not 1 hour, to give a safety buffer. (3) In the preview modal, detect 403/expired errors and trigger a `queryClient.invalidateQueries(['artifacts', projectId])` to force a re-fetch with fresh signed URLs. (4) Never set `staleTime: Infinity` on any query that embeds signed URLs. Document this constraint in the artifact query file.

**Warning signs:**
- Preview modal shows broken image icon after the page has been open for ~1 hour
- Network tab shows 403 response for preview URLs with no corresponding error in the UI
- `staleTime: Infinity` or no `staleTime` on artifact queries

**Phase to address:**
Phase 4 (Artifacts Management UI) — set staleTime correctly when writing TanStack Query hooks for artifacts.

---

### Pitfall 7: File Size Enforcement in Three Layers — Missing Any One Causes Silent Overruns

**What goes wrong:**
The 10MB limit must be enforced at: (1) the browser before upload starts, (2) the FastAPI endpoint before reading the body, and (3) the Nginx/proxy layer as `client_max_body_size`. Missing any one layer creates a gap: missing (1) means the user wastes bandwidth uploading a 50MB file only to get a 413 at the server; missing (2) means the FastAPI endpoint reads the full body into memory before rejecting, risking OOM on the container; missing (3) means Nginx will return a raw 413 without the standard RFC 7807 error format the frontend expects, breaking `ApiError.fromAxiosError`.

**Why it happens:**
Developers implement the "obvious" frontend check (file.size > 10MB → show error) and the "obvious" backend check (UploadFile size validation). The Nginx config is forgotten because it lives in `infra/` and is rarely touched. FastAPI defaults to no size limit, and Uvicorn's own limit is very high. When deployed behind Nginx, Nginx's `client_max_body_size` defaults to 1MB — which would reject files above 1MB before FastAPI even sees them, returning a plain 413 HTML page that the frontend cannot parse as `application/problem+json`.

**How to avoid:**
(1) Frontend: validate `file.size` before calling upload mutation, show user-visible error immediately. (2) FastAPI endpoint: validate file size using `UploadFile.size` or read content in chunks, raising `HTTP 413` with `application/problem+json` body. (3) Nginx `infra/` config: set `client_max_body_size 12m` (slightly above 10MB to let FastAPI handle the enforcement and return the correct error format). Document all three enforcement points in the artifact upload endpoint's docstring.

**Warning signs:**
- Large file upload returns a plain HTML 413 page instead of JSON error (Nginx intercepting before FastAPI)
- Uploading a 9.9MB file causes the FastAPI container to spike in memory (body read into memory before size check)
- Frontend shows upload progress to 100% then displays an opaque error (no size check before upload)

**Phase to address:**
Phase 3 (Storage Backend) — enforce all three layers when writing the upload endpoint.

---

### Pitfall 8: Video URL Validation Accepts Malformed YouTube URLs That Produce Empty Iframes

**What goes wrong:**
TipTap's official YouTube extension has a documented bug: pasting `https://youtube.com` (without a video ID) matches the paste rule but `getEmbedUrlFromYoutubeUrl` returns `null`, producing an iframe with no `src`. More broadly, any regex-based YouTube/Vimeo URL parser has edge cases: channel URLs, playlist URLs, shortened `youtu.be` links with extra query params, or `youtube-nocookie.com` variants. A broken embed node is inserted into the document, saved to the DB, and surfaced as a broken iframe to all users who open the note.

**Why it happens:**
The custom `VideoEmbedNode` will need its own URL parser (TipTap's extension is a pro feature). URL validation via regex is error-prone. The failure mode is silent: the node is created with `src: null` or `src: ""`, which renders as a blank iframe element rather than an error state.

**How to avoid:**
Validate YouTube/Vimeo URLs through an allowlist-based extractor, not a blacklist-based regex: (1) Parse with `URL` constructor to get hostname and path safely. (2) Accept only `youtube.com/watch?v=...`, `youtu.be/...`, `youtube-nocookie.com/embed/...`, `vimeo.com/...` patterns. (3) Extract the video ID and construct the embed URL explicitly — never pass raw user-supplied URL as the iframe `src`. (4) If extraction returns `null`, refuse to insert the node and show a toast: "Invalid video URL — only YouTube and Vimeo links are supported." (5) The `VideoEmbedNode.parseHTML()` must validate the stored `src` attribute before rendering — a null src should render as a "broken embed" UI, not a blank iframe.

**Warning signs:**
- Video block inserted but shows blank white space (null src iframe)
- Paste of a YouTube channel page creates an embed node instead of being rejected
- Direct DOM inspection shows `<iframe src="">` in the rendered document

**Phase to address:**
Phase 2 (Medium-Style Editor UX) — implement URL validation before the VideoEmbedNode is used in production.

---

### Pitfall 9: Video Iframe XSS — Missing CSP and sandbox Attributes

**What goes wrong:**
Rendering an iframe with user-controlled `src` is an XSS vector if the `src` URL is not validated to an allowlist (see Pitfall 8) AND the iframe lacks `sandbox` and `allow` attributes. Even with validated YouTube/Vimeo URLs, a misconfigured Next.js CSP header can either (a) block the iframe entirely with a cryptic "refused to frame" error in production or (b) be too permissive and allow the embed to navigate the parent frame. The Next.js CSP documentation notes that nonce-based CSP requires dynamic rendering — static pages cannot use nonces. If the page with video embeds is statically generated, the CSP nonce approach breaks.

**Why it happens:**
The TipTap `VideoEmbedNode` renders to DOM with `ReactNodeViewRenderer`. The iframe HTML is injected into the editor's rendered output. Without explicit `sandbox` and `allow` attributes on the iframe element, the browser's default allows the embedded page to navigate the parent (same-origin frames) or execute scripts. The Next.js CSP header is set in `next.config.ts` headers — adding `frame-src https://www.youtube-nocookie.com https://player.vimeo.com` without verifying it does not break existing `frame-src` directives requires careful audit.

**How to avoid:**
(1) Always render video iframes with: `sandbox="allow-scripts allow-same-origin allow-presentation allow-fullscreen"` — this blocks navigation, form submission, and top-level navigation from the embed. (2) Add `allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"` for YouTube autoplay support. (3) Use the `youtube-nocookie.com` embed domain (not `youtube.com`) for YouTube. (4) Update `next.config.ts` `frame-src` to include only the two allowed embed domains. (5) Test CSP in the browser's Network tab with "Block mixed content" enabled — broken embeds are caught immediately in development.

**Warning signs:**
- Console: "Refused to frame 'https://www.youtube-nocookie.com/' because it violates the following Content Security Policy directive"
- iframe renders in local dev but not in production (CSP header not set locally)
- Embedded video can navigate the parent window (missing sandbox attribute)

**Phase to address:**
Phase 2 (Medium-Style Editor UX) — security attributes are part of the VideoEmbedNode implementation, not a post-launch fix.

---

### Pitfall 10: Optimistic UI Rollback on Upload Failure Leaves Orphaned Storage Objects

**What goes wrong:**
The artifacts management page will use TanStack Query optimistic updates: the artifact card appears immediately in the UI with a pending state, and the actual API call completes asynchronously. If the API call fails (network error, server error, storage quota exceeded), TanStack Query's `onError` rolls back the client-side optimistic entry. However, the Supabase Storage object may have already been uploaded before the database record creation failed. The result is an orphaned storage object: it exists in the `artifacts` bucket but has no DB record referencing it, and no cleanup job removes it.

**Why it happens:**
The upload flow has two steps: (1) PUT file to Supabase Storage → (2) POST artifact metadata to the API (which writes the DB record). If step 2 fails, step 1 already committed. The `SupabaseStorageClient` has no transaction semantics across these two operations. TanStack Query's optimistic rollback only affects the client cache — it cannot roll back a storage write.

**How to avoid:**
(1) Reverse the flow: write the DB record FIRST (with status `pending_upload`), then upload the file, then update the DB record to `ready`. If the upload fails, mark the DB record as `upload_failed` and clean it up via a scheduled job. (2) The `ArtifactService` in the backend is responsible for orchestrating this; the frontend mutation only calls one endpoint. (3) Add a background cleanup job (scheduled every 24 hours) that deletes storage objects whose DB records are in `upload_failed` or `pending_upload` for more than 1 hour. (4) The optimistic UI shows a `pending` card — on error, the card transitions to a "Upload failed, retry?" state rather than disappearing, so users understand what happened.

**Warning signs:**
- Supabase Storage bucket accumulates objects without corresponding DB records
- Upload failure shows no error state to the user (card disappears without explanation)
- Retry upload creates a duplicate storage object with a different key

**Phase to address:**
Phase 3 (Storage Backend) — design the two-phase upload flow before building any frontend optimistic UI.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use TipTap's `BubbleMenu` extension instead of custom positioning | Faster floating toolbar | Conflicts with ghost text and slash command plugins; Tab key ambiguity | Never — existing SelectionToolbar pattern must be extended |
| Skip `renderMarkdown` for FileCardNode | Faster node development | File card blocks silently drop from saved content on markdown round-trip | Never — serialization contract must be defined before building node views |
| Single-phase upload (storage first, DB second) | Simpler upload code | Orphaned storage objects on failure; no reliable rollback | Never — DB-first with pending status is the correct flow |
| Set `staleTime: Infinity` on artifact list query | Fewer API calls | Signed URLs expire while cached data is still "fresh"; stale previews | Never for queries containing signed URLs |
| Validate file MIME type in frontend only | Faster validation | Backend receives wrong content types; allows MIME-type juggling attacks | Never — server must validate content type independently |
| Omit `sandbox` attribute on video iframes | Simpler iframe element | Embedded page can navigate parent; missing required permissions for fullscreen | Never — always include both `sandbox` and `allow` attributes |
| Store full file content in memory during upload | Simpler byte handling | OOM risk on 10MB files; FastAPI container can spike to 3x file size in memory | Never — use streaming reads or chunked processing |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `tiptap-markdown` Markdown extension | Adding new node without `renderMarkdown` causes silent content loss on save | Register `renderMarkdown` in the same PR that introduces the node type |
| `BlockIdExtension` | New block node registered after Group 4 in extension array | Always insert new block nodes in Group 3 per PRE-002 documentation in `createEditorExtensions.ts` |
| `GhostTextExtension` + `SlashCommandExtension` | New floating UI does not check existing plugin states before showing | Check `GHOST_TEXT_PLUGIN_KEY` and `SLASH_COMMAND_PLUGIN_KEY` states in `shouldShow` logic |
| Supabase Storage + TanStack Query | Caching artifact list with embedded signed URLs using `staleTime: Infinity` | Set `staleTime` to 55 minutes max; invalidate on 403 errors from preview modal |
| FastAPI `UploadFile` + Nginx | Nginx `client_max_body_size` defaults to 1MB; rejects files before FastAPI with unparseable HTML 413 | Set `client_max_body_size 12m` in Nginx config; let FastAPI return RFC 7807 error |
| `ReactNodeViewRenderer` + MobX | Wrapping node view component in `observer()` causes nested flushSync in React 19 | Use context bridge pattern: plain NodeView wrapper → observer child component |
| YouTube/Vimeo embeds + Next.js CSP | `frame-src` not updated causes "refused to frame" error in production | Add `frame-src https://www.youtube-nocookie.com https://player.vimeo.com` to `next.config.ts` headers |
| Supabase Storage delete + DB record | Deleting artifact deletes storage object but leaves orphaned DB record on partial failure | Wrap delete in transaction: mark DB record deleted first, then delete storage; dead records are recoverable |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching signed URLs for all artifacts on page load | Artifacts page takes 3-5s with 50 artifacts (50 serial signed URL requests) | Backend generates signed URLs in the list response (batch signing in `ArtifactService.list()`) | >20 artifacts per project |
| Loading full file content into browser memory for preview | Browser tab freezes or crashes for 10MB CSV/Excel | Use streaming reads or chunked rendering; for Excel use `xlsx` with streaming mode | Any file >5MB |
| Re-rendering file card list on every MobX state change | Artifacts page jank when ghost text fires in adjacent editor | Artifact list component must NOT be observer on editor-related stores | Any editor auto-save event |
| Reading full file buffer in FastAPI before size check | Container OOM spike on malicious large upload | Read size from `UploadFile.size` header first; reject before reading body | Any upload >50MB to an unprotected endpoint |
| Generating fresh signed URL on every preview modal open | Each open triggers a backend round-trip adding 200-500ms latency | Cache signed URL in component state for the modal session duration; re-fetch only on 403 | Any preview modal opened repeatedly |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Trusting MIME type from `file.type` browser API | Attacker renames `.exe` to `.csv` and browser reports `text/csv` | Backend must validate content using `python-magic` or header sniffing, not trust client-reported content type |
| Public bucket for artifacts | Any user who constructs the storage key URL can access any file | Set bucket to private; all access via backend-generated signed URLs only |
| Embedding raw user-supplied URL in video iframe `src` | XSS: attacker injects `javascript:` URL or data URI into iframe | Only use reconstructed embed URLs from validated video IDs; never pass raw URLs to iframe |
| Artifact storage key without workspace prefix | Key enumeration allows cross-workspace access if service key is leaked | Always prefix keys with `{workspace_id}/{project_id}/`; validate prefix in `ArtifactService` |
| Missing `X-Content-Type-Options: nosniff` on artifact downloads | Browser executes downloaded HTML file as a script | Backend must set `X-Content-Type-Options: nosniff` and `Content-Disposition: attachment` on file download endpoints |
| File preview rendering unsanitized HTML files | User uploads `malicious.html`; preview modal renders it inline, executing scripts | HTML files must be rendered as source code (escaped) in the preview modal, never as `innerHTML`; use code syntax highlighter, not a raw renderer |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No upload progress indicator for 10MB files | User sees nothing for 5-10 seconds and assumes the upload failed | Show upload progress bar inside the FileCardNode during upload; use `XMLHttpRequest.upload.onprogress` or streaming fetch |
| File preview modal opens with loading spinner but no timeout | User waits indefinitely if signed URL expired or storage is slow | Add 10s timeout to preview fetch; on timeout show "Preview unavailable — download instead" with a direct download button |
| Deleting artifact from management page with no undo | User accidentally deletes a file attached to a note; note shows broken card | Show 5s undo toast after delete; use soft-delete (mark as deleted, clean up after 24 hours) |
| Inserting a file card mid-paragraph breaks text flow | Inline file card disrupts reading; common with drag-and-drop insertions | File cards must be block-level nodes (not inline marks); enforce block insertion in the SlashCommand execute function |
| Video embed showing only URL text in notes list/search | Users cannot identify which notes have video content from search results | Serialize video embeds to a readable Markdown comment like `<!-- video: YouTube https://... -->` so search index includes them |
| Focus mode hides slash command menu behind overlay | User activates focus mode then tries to insert a block; slash command invisible | Focus mode overlay must not cover the slash command dropdown; use `z-index` hierarchy: focus overlay < slash command menu |

## "Looks Done But Isn't" Checklist

- [ ] **FileCardNode:** Often missing round-trip test — verify insert → save → reload shows the same card with correct filename and artifact ID
- [ ] **VideoEmbedNode:** Often missing YouTube-nocookie domain — verify production CSP allows `youtube-nocookie.com` not just `youtube.com`
- [ ] **File upload:** Often missing Nginx config — verify `client_max_body_size` is set to at least 12m in `infra/` before testing with files >1MB
- [ ] **Signed URLs:** Often stale after 1 hour — verify preview modal handles 403 by triggering query invalidation, not showing a broken image
- [ ] **ReactNodeViewRenderer:** Often wrapped in observer — verify new node view components are NOT observer; use context bridge
- [ ] **BlockIdExtension order:** Often new nodes appended to end — verify `editor.getJSON()` shows `blockId` attribute on every FileCardNode and VideoEmbedNode
- [ ] **MIME validation:** Often frontend-only — verify backend rejects `.exe` renamed to `.csv` by checking magic bytes, not just content-type header
- [ ] **Orphaned storage objects:** Often untested — verify upload failure (kill network mid-upload) leaves DB record in `upload_failed` state, not an orphaned storage object
- [ ] **Pull quote / callout Markdown:** Often missing serializer — verify `editor.storage.markdown.getMarkdown()` includes pull quote text, not an empty string
- [ ] **HTML file preview:** Often rendered directly — verify `.html` file previewed as source code (escaped), never as live HTML in preview modal

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| New block node inserted after BlockIdExtension | LOW | Move extension registration to correct position in Group 3; existing persisted content with null blockId needs a one-time migration to assign block IDs |
| BubbleMenu conflicts with ghost text | MEDIUM | Remove BubbleMenu extension; extend existing SelectionToolbar component; requires replacing the toolbar trigger logic |
| FileCardNode serialization drops content | HIGH | Content already saved without the block is gone; going forward add renderMarkdown; inform users to re-attach lost artifacts |
| Orphaned storage objects accumulate | LOW | Write a one-time cleanup script querying DB for valid artifact keys; delete all bucket objects not in that set |
| Signed URLs cached past expiry | LOW | Set correct staleTime on queries; add 403-triggered invalidation in preview modal error handler |
| Nginx rejects files >1MB | LOW | Update `client_max_body_size` in infra config; redeploy proxy; no code changes required |
| Video XSS via unvalidated URL | HIGH | Emergency: add iframe `sandbox` attribute via hotfix; audit all stored VideoEmbedNode src values for non-YouTube/Vimeo domains |
| flushSync crash from observer NodeView | MEDIUM | Remove observer from NodeView component; implement context bridge pattern; requires refactoring the node view and its data consumers |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| BlockIdExtension ordering | Phase 1: TipTap Extension Foundation | `editor.getJSON()` shows `blockId` on every new node type |
| Markdown serialization loss | Phase 1: TipTap Extension Foundation | Round-trip test: insert → get markdown → re-parse → verify node survives |
| ReactNodeViewRenderer + observer flushSync | Phase 1: TipTap Extension Foundation | Open note with FileCardNode; verify no React console errors |
| BubbleMenu conflicts with ghost text/slash command | Phase 2: Medium Editor UX | Tab key with ghost text active does only one thing; slash command open does not show toolbar |
| Video URL validation accepts malformed URLs | Phase 2: Medium Editor UX | Paste `https://youtube.com` → verify rejected with toast; paste valid link → verify embed node |
| Video iframe XSS / missing CSP | Phase 2: Medium Editor UX | Network tab shows no CSP violations; iframe has `sandbox` attribute in DOM |
| Supabase Storage service-role access control | Phase 3: Storage Backend | Cross-workspace artifact access attempt returns 403 from API before storage is called |
| File size enforcement at all three layers | Phase 3: Storage Backend | 11MB file rejected with RFC 7807 error; Nginx config audit |
| Orphaned storage objects on upload failure | Phase 3: Storage Backend | Simulate upload failure; verify DB record is `upload_failed`; verify cleanup job removes orphan |
| Signed URL expiry with TanStack Query | Phase 4: Artifacts Management UI | Keep page open 65 minutes; open preview modal; verify no broken image (query re-fetched) |
| MIME type spoofing | Phase 3: Storage Backend | Upload `.exe` renamed `.csv`; verify backend rejects by content inspection |
| HTML preview XSS | Phase 5: File Preview Modal | Preview `.html` file; verify source code rendered, not live HTML |

## Sources

- Direct codebase analysis: `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` (PRE-002 ordering rule, Groups 1-6)
- Direct codebase analysis: `frontend/src/features/notes/editor/extensions/GhostTextExtension.ts` (SLASH_COMMAND_PLUGIN_KEY check at line 406, Tab key handler)
- Direct codebase analysis: `frontend/src/features/notes/editor/extensions/SlashCommandExtension.ts` (plugin key, isActive state)
- Direct codebase analysis: `frontend/src/components/editor/SelectionToolbar.tsx` (custom selection-based toolbar pattern, NOT observer)
- Direct codebase analysis: `backend/src/pilot_space/infrastructure/storage/client.py` (service role bypass comment)
- Direct codebase analysis: `frontend/src/features/issues/editor/property-block-extension.ts` (ReactNodeViewRenderer, atom node pattern)
- Project memory: `MEMORY.md` (IssueEditorContent must NOT be observer, flushSync constraint)
- TipTap GitHub issue #3764: `flushSync gets called on render when the Editor gets updated with content that uses an extension with addNodeView`
- TipTap GitHub issue #6148: `DragHandle extension conflicts with BubbleMenu`
- TipTap GitHub issue #4560: `Youtube Extension: pasting "https://youtube.com" is considered a valid youtube link`
- TipTap Docs: [Custom Markdown Serializing](https://tiptap.dev/docs/editor/markdown/advanced-usage/custom-serializing)
- TipTap Docs: [BubbleMenu shouldShow](https://tiptap.dev/docs/editor/extensions/functionality/bubble-menu)
- Supabase Docs: [Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)
- Supabase Discussion #21926: `cache-control header missing in Signed URL provided by Supabase storage`
- Next.js Docs: [Content Security Policy](https://nextjs.org/docs/pages/guides/content-security-policy)
- FastAPI Discussion #8167: `Strategies for limiting upload file size`
- PortSwigger: [File upload vulnerabilities](https://portswigger.net/web-security/file-upload)
- MDN: [MIME type verification](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/MIME_types)

---
*Pitfalls research for: Pilot Space v1.1 Medium Editor & Artifacts*
*Researched: 2026-03-18*
