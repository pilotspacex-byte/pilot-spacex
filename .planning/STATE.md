---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Medium Editor & Artifacts
status: planning
stopped_at: Completed 30-tiptap-extension-foundation/30-01-PLAN.md
last_updated: "2026-03-19T12:18:50.397Z"
last_activity: 2026-03-18 — v1.1 roadmap created, 22/22 requirements mapped across 7 phases
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 20
  completed_plans: 1
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

### Pending Todos

None.

### Blockers/Concerns

- [Phase 31]: Verify actual Nginx `client_max_body_size` in `infra/` before assuming 1MB default — may already be set higher
- [Phase 31]: RESOLVED — extension-allowlist approach chosen over python-magic (simpler, no new dep)
- [Phase 32]: Stale `artifactId: null` placeholder nodes from failed uploads need explicit removal strategy on editor mount
- [Phase 34]: RESOLVED — 500-row truncation with download fallback chosen over virtual scrolling

## Session Continuity

Last session: 2026-03-19T12:18:50.394Z
Stopped at: Completed 30-tiptap-extension-foundation/30-01-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 30`
