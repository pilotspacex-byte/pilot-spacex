---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Medium Editor & Artifacts
status: planning
stopped_at: Completed 33-video-embeds/33-01-PLAN.md
last_updated: "2026-03-19T14:32:36.676Z"
last_activity: 2026-03-18 — v1.1 roadmap created, 22/22 requirements mapped across 7 phases
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 20
  completed_plans: 12
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

### Pending Todos

None.

### Blockers/Concerns

- [Phase 31]: Verify actual Nginx `client_max_body_size` in `infra/` before assuming 1MB default — may already be set higher
- [Phase 31]: RESOLVED — extension-allowlist approach chosen over python-magic (simpler, no new dep)
- [Phase 32]: Stale `artifactId: null` placeholder nodes from failed uploads need explicit removal strategy on editor mount
- [Phase 34]: RESOLVED — 500-row truncation with download fallback chosen over virtual scrolling

## Session Continuity

Last session: 2026-03-19T14:32:36.674Z
Stopped at: Completed 33-video-embeds/33-01-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 30`
