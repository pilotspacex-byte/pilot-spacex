---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Medium Editor & Artifacts
status: planning
stopped_at: Completed 37-artifact-preview-rendering-engine/37-02-PLAN.md
last_updated: "2026-03-20T03:11:11.830Z"
last_activity: 2026-03-18 — v1.1 roadmap created, 22/22 requirements mapped across 7 phases
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 9
  completed_plans: 21
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** Phase 30 — TipTap Extension Foundation

## Current Position

Phase: 30 of 36 (TipTap Extension Foundation)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-18 — v1.1 roadmap created, 22/22 requirements mapped across 7 phases

Progress: [░░░░░░░░░░] 0% (0/7 phases complete)

## Milestone History

| Milestone | Phases | Plans | Requirements | Shipped |
|-----------|--------|-------|-------------|---------|
| v1.0 Enterprise | 1–11 | 46 | 30/30 | 2026-03-09 |
| v1.0-alpha Pre-Production Launch | 12–23 | 37 | 39/39 + 7 gap items | 2026-03-12 |
| v1.0.0-alpha2 Notion-Style Restructure | 24–29 | 14 | 17/17 | 2026-03-12 |

## Accumulated Context

### Roadmap Evolution

- Phase 37 added: Artifact Preview Rendering Engine — HTML live preview, code highlighting, markdown rendering in notes and ChatView

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.1 research]: Use `@e965/xlsx` not `xlsx` npm — unmaintained fork with active CVEs
- [v1.1 research]: Build custom VimeoNode (~60 lines) — no TipTap 3-compatible Vimeo package exists
- [v1.1 research]: DB-first upload flow (pending_upload → upload → ready) — prevents orphaned storage objects
- [v1.1 research]: Never wrap TipTap NodeView in MobX `observer()` — React 19 flushSync crash (same as IssueEditorContent constraint)
- [v1.1 research]: `FilePreviewModal` built once in Phase 34, reused in both FileCardView (Phase 32) and ArtifactsPage (Phase 35)
- [v1.1 research]: CSV preview capped at 500 rows — decision on truncation vs. virtual scrolling deferred to Phase 34 planning
- [Phase 30-tiptap-extension-foundation]: SelectionToolbar tests: capture selectionUpdate listener in mock editor to make toolbar visible without ProseMirror
- [Phase 30-tiptap-extension-foundation]: TDD RED tests committed before production code: 5 PullQuote, 6 SelectionToolbar, 4 node-view-bridge tests
- [Phase 30-tiptap-extension-foundation]: createNodeViewBridgeContext<T>() factory pattern: each NodeView gets its own typed context via null-initialized createContext + useBridgeContext guard
- [Phase 30-tiptap-extension-foundation]: headingLabel computed in SelectionToolbar render body from synchronous editor.isActive() — no useState required since component re-renders on every selectionUpdate
- [Phase 30-tiptap-extension-foundation]: Used parse.updateDOM hook for pull quote round-trip — detects [!quote] marker in rendered HTML, stamps data-pull-quote attr before TipTap parseHTML runs
- [Phase 30-tiptap-extension-foundation]: PullQuoteExtension placed in Group 1 (not Group 3) — same schema name 'blockquote', BlockIdExtension already covers it; StarterKit blockquote: false disables original
- [Phase 31-storage-backend]: Removed inline index=True from Artifact.project_id — composite ix_artifacts_workspace_project covers it; prevents alembic drift from spurious ix_artifacts_project_id
- [Phase 31-storage-backend]: WorkspaceScopedModel tablename override requires # type: ignore[assignment] — BaseModel declared_attr.directive creates type conflict with plain string literal (pattern: note.py, issue.py)
- [Phase 31-storage-backend]: ArtifactUploadService reads persisted.created_at (not local artifact.created_at) to avoid ValidationError when server default not populated in unit tests
- [Phase 31-storage-backend]: MemoryWorker storage_client is optional parameter — TASK_ARTIFACT_CLEANUP logs warning and skips if not configured, enabling gradual rollout without breaking existing worker deployments
- [Phase 31-storage-backend]: CurrentUser resolves to TokenPayload which exposes .user_id not .id — router uses current_user.user_id
- [Phase 31-storage-backend]: ArtifactResponse.model_validate() called explicitly in list endpoint to avoid Pydantic camelCase alias confusion
- [Phase 32-inline-editor-features]: ArtifactStore.reset() aborts all in-flight uploads before clearing the Map — prevents dangling XHRs on sign-out
- [Phase 32-inline-editor-features]: Use getAuthProviderSync().getToken() in artifactsApi — consistent with apiClient.ts, supports Supabase and AuthCore providers
- [Phase 32-inline-editor-features]: @ts-expect-error on Wave 0 test scaffold imports — allows pnpm type-check to pass while vitest fails at runtime (correct RED state)
- [Phase 32-inline-editor-features]: FileCardExtension.addExtensions() includes StarterKit + Markdown for isolated test support — TipTap deduplicates by name in full editor
- [Phase 32-inline-editor-features]: tiptap-markdown serialize() is ProseMirror-style: must call state.write() + state.closeBlock(), not return a string value
- [Phase 32-inline-editor-features]: FigureNodeView uses NodeViewContent for caption slot — no MobX observer needed since attrs come from node.attrs
- [Phase 32-inline-editor-features]: state.write() in FigureExtension serialize() — tiptap-markdown 0.9 requires state mutation, return value is ignored
- [Phase 32-inline-editor-features]: editorRef closure captures Editor in onCreate so drop handler avoids EditorView.editor type cast
- [Phase 32-inline-editor-features]: pilot:upload-artifact CustomEvent decouples slash command execute from API — slash-command-items.ts fires event, config.ts listens
- [Phase 32-inline-editor-features]: SlashCommand.group 'media' added in both slash-command-items.ts AND types.ts — types.ts has parallel interface
- [Phase 33-video-embeds]: CSP directive is frame-src only (not full CSP policy) — minimal surface, additive pattern
- [Phase 33-video-embeds]: frame-src 'self' preserves any same-origin iframes; only 1 iframe found in codebase (test file)
- [Phase 33-video-embeds]: extractVimeoId uses URL hostname check not regex — prevents notvimeo.com false positive
- [Phase 33-video-embeds]: addPasteRules in VimeoNode is no-op — real paste offer UI (VideoPasteDetector) lives in Plan 02
- [Phase 33-video-embeds]: VideoPasteDetector registered in Group 5 after SlashCommandExtension — decoration/interaction layer, not a block-type node
- [Phase 33-video-embeds]: showVideoUrlPrompt appends to document.body not editor DOM — avoids ProseMirror focus conflicts
- [Phase 33-video-embeds]: PasteRule only fires on standalone URLs (anchored regex); empty paragraph guard prevents offer on non-empty lines
- [Phase 34-file-preview-modal]: fetch() directly for signed URL content (not apiClient) — avoids Authorization header that Supabase Storage rejects
- [Phase 34-file-preview-modal]: HTML always routes to 'code' renderer (text/html, .html, .htm) — never live render HTML from storage, XSS prevention
- [Phase 34-file-preview-modal]: useFileContent staleTime 55 min (URLs expire at 60 min), retry:false (403 = expired not transient), isExpired flag for UI
- [Phase 34-file-preview-modal]: LinkOff → Link2Off: lucide-react in project exports Link2Off not LinkOff
- [Phase 34-file-preview-modal]: ImageRenderer uses native <img> not next/image: signed Supabase URLs are external, zoom requires raw dimensions
- [Phase 35-artifacts-management-page]: getSignedUrl uses apiClient (not raw fetch) — backend proxy route /api/v1/workspaces/.../artifacts/{id}/url; raw fetch only for external Supabase storage content URLs
- [Phase 35-artifacts-management-page]: artifactsKeys.list(ws,proj) is the precise invalidation key for useDeleteArtifact — avoids over-invalidation of other project artifact lists
- [Phase 35-artifacts-management-page]: FilePreviewModal gated by selectedArtifact + signedUrlData — avoids empty modal flash while signed URL fetches
- [Phase 35-artifacts-management-page]: handleDownload uses artifactsApi.getSignedUrl directly — one-shot action, no TanStack cache needed
- [Phase 36-editor-ux-polish]: isFocusMode is session-only — excluded from PersistedUIState and setupPersistence reaction; focus mode resets on page reload
- [Phase 36-editor-ux-polish]: AppShell desktop sidebar uses conditional render (not width:0 animation) — removes DOM node so main content fills full viewport
- [Phase 36-editor-ux-polish]: NoteCanvasLayout is NOT observer() — isFocusMode flows as prop from observer NoteDetailPage; prevents React 19 flushSync crash with TipTap NodeViews
- [Phase 36-editor-ux-polish]: Escape guard in keyboard shortcut: e.key === 'Escape' && isFocusMode without e.preventDefault() — lets slash command ProseMirror-level Escape run first
- [Phase 37]: HtmlRenderer defaults to source mode with opt-in sandboxed iframe preview; sandbox='allow-same-origin' only, never allow-scripts
- [Phase 37-artifact-preview-rendering-engine]: FilePreviewModal html-preview case was already wired in Plan 01; Plan 02 only updated test assertions from markdown-content to html-renderer testid

### Pending Todos

None.

### Blockers/Concerns

- [Phase 31]: Verify actual Nginx `client_max_body_size` in `infra/` before assuming 1MB default — may already be set higher
- [Phase 31]: RESOLVED — extension-allowlist approach chosen over python-magic (simpler, no new dep)
- [Phase 32]: Stale `artifactId: null` placeholder nodes from failed uploads need explicit removal strategy on editor mount
- [Phase 34]: RESOLVED — 500-row truncation with download fallback chosen over virtual scrolling

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 1 | Fix 8 code issues from PR #32 CodeRabbit review | 2026-03-13 | ebeaa9db | | [1-review-all-comments-of-pr-32-then-fix-an](./quick/1-review-all-comments-of-pr-32-then-fix-an/) |
| 2 | Fix remaining 5 CodeRabbit issues from PR #32 | 2026-03-13 | 4d9b7b7a | | [2-review-all-comments-of-pr-32-then-fix-an](./quick/2-review-all-comments-of-pr-32-then-fix-an/) |
| 3 | Review and merge PR #31, #32, #33 | 2026-03-13 | 4e50a10c | | [3-review-carefully-opening-pr-31-32-33-the](./quick/3-review-carefully-opening-pr-31-32-33-the/) |
| 4 | Fix all preexisting pytest failures | 2026-03-13 | 1bd09554 | | [4-checkout-new-branch-from-main-then-fix-a](./quick/4-checkout-new-branch-from-main-then-fix-a/) |
| 5 | Per-user AI model defaults and base_url overrides | 2026-03-13 | bd06487e | | [5-allow-user-to-setup-default-claude-agent](./quick/5-allow-user-to-setup-default-claude-agent/) |
| 6 | Phase 1 UI/UX quick wins (fonts, tokens, hover) | 2026-03-13 | 04ad972d | | [6-implement-phase-1-ui-ux-quick-wins-from-](./quick/6-implement-phase-1-ui-ux-quick-wins-from-/) |
| 8 | Unified AI Providers settings UI with expandable rows | 2026-03-14 | ca12777e | | [8-enhance-ai-providers-settings-ui-unified](./quick/8-enhance-ai-providers-settings-ui-unified/) |
| 10 | Investigate Note-to-Issue pipeline: 5 pathways traced, 28 tests run | 2026-03-15 | n/a (investigation only) | Verified | [10-investigate-into-codebase-of-pilotspace-](./quick/10-investigate-into-codebase-of-pilotspace-/) |
| 11 | Fix AI config POST 500, NoteIssueLink creation, linkType enum alignment | 2026-03-15 | d4a62dd5 | Done | [11-fix-all-issues-found-in-browser-testing-](./quick/11-fix-all-issues-found-in-browser-testing-/) |
| 12 | Validate 3 AI flows + fix LLMProvider enum case mismatch | 2026-03-15 | 4e47d6d4 | Done | [12-validate-3-ai-issue-flows-via-browser-ex](./quick/12-validate-3-ai-issue-flows-via-browser-ex/) |
| 260316-kaf | Remove note emoji selector | 2026-03-16 | 636933f8 | Done | [260316-kaf-remove-note-emoji-selector-in-new-branch](./quick/260316-kaf-remove-note-emoji-selector-in-new-branch/) |
| 260316-phe | Investigate & fix skill features (7 issues fixed) | 2026-03-16 | f01d76a0 | Verified | [260316-phe-investigate-into-current-pilot-space-ski](./quick/260316-phe-investigate-into-current-pilot-space-ski/) |
| 260316-v8c | Improve provider setup UI/UX with dropdown selection | 2026-03-16 | 34d7e3cd | Done | [260316-v8c-improve-provider-setup-ui-ux-with-llm-em](./quick/260316-v8c-improve-provider-setup-ui-ux-with-llm-em/) |
| 260317-0ce | Fix skill editing: AI parser, skill_name, expandable cards, editable preview | 2026-03-17 | c234324c | Verified | [260317-0ce-fix-skill-editing-allow-edit-skill-conte](./quick/260317-0ce-fix-skill-editing-allow-edit-skill-conte/) |
| 260317-bch | User skills in agent system prompt (layer 4.5, TDD) | 2026-03-17 | a743eb3f | Verified | [260317-bch-check-change-of-feat-provider-setup-enha](./quick/260317-bch-check-change-of-feat-provider-setup-enha/) |
| 260317-hms | Migrate provider settings to workspace level (shared resolver, workspace_override) | 2026-03-17 | da3c5101 | Done | [260317-hms-migrate-provider-settings-to-workspace-l](./quick/260317-hms-migrate-provider-settings-to-workspace-l/) |
| 260317-v27 | Enhance Chat AI Issue Extraction Card | 2026-03-17 | 96381ec4 | Done | [260317-v27-enhance-chat-ai-issue-extraction-card](./quick/260317-v27-enhance-chat-ai-issue-extraction-card/) |
| 260318-naw | Settings modal migration investigation: 14 pages catalogued, 4-phase 9-plan migration plan, feat/settings-modal branch | 2026-03-18 | 74dac5cc | Verified | [260318-naw-checkout-new-branch-then-investigate-to-](./quick/260318-naw-checkout-new-branch-then-investigate-to-/) |
| 260318-wqj | Add tags+usage to skill system, extract prompt module, redesign modal with chip tags+usage textarea | 2026-03-18 | d854919c | Needs Review | [260318-wqj-improve-generate-skill-modal-redesign-fo](./quick/260318-wqj-improve-generate-skill-modal-redesign-fo/) |

## Session Continuity

Last session: 2026-03-20T03:07:18.794Z
Stopped at: Completed 37-artifact-preview-rendering-engine/37-02-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 30`
