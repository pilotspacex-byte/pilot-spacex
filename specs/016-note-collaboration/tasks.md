# Tasks: Note Collaboration & Density (Feature 016)

**Spec**: v1.0 | **Plan**: v1.0 | **Generated**: 2026-02-19

---

## Legend

- **Status**: `[ ]` pending, `[~]` in progress, `[x]` done, `[-]` blocked
- **Layer**: DB (database/migration), BE (backend service), AI (agent/skill), FE (frontend), QA (test)
- **Deps**: Task IDs that must complete first

---

## Sprint 1a: CRDT Proof-of-Concept + Load-Test Gate (M6a — Gate)

### Phase 1a-POC: Minimal Yjs Integration

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-101 | [ ] Create minimal Yjs + TipTap binding POC | M6a | FE | Feature 015 complete | Yjs Y.Doc bound to TipTap via y-prosemirror. Single note, in-memory only. Two browser tabs can edit same doc via shared Y.Doc. CRDT merge verified: concurrent inserts at same position produce deterministic result. |
| T-102 | [ ] Integrate y-supabase provider | M6a | FE | T-101 | Yjs doc syncs via Supabase Realtime channel. Awareness protocol broadcasts cursor positions. Connection lifecycle: connect on note open, disconnect on close. Auto-reconnect on drop. |
| T-103 | [ ] Create y-websocket fallback server | M6a | BE | — | Dockerized y-websocket server. Dockerfile + docker-compose service. Configurable port. Persistence to LevelDB. Ready to deploy if Supabase Realtime fails gate. |
| T-104 | [ ] Create load-test harness | M6a | QA | T-102 | Playwright script: launches 10 concurrent browser contexts editing same note for 60 seconds. Each context types random text at 2 char/sec. Measures: sync latency (time from keystroke to appearance in other tabs) at p50/p95/p99. Outputs JSON report. |
| T-105 | [ ] Execute Sprint 1a gate test | M6a | QA | T-104 | Run load test against Supabase Realtime. Document results in `gate-result.md`. If p95 >= 500ms: retest with y-websocket (T-103). Final decision recorded with metrics. |

---

## Sprint 1b: Ownership Engine (M6b)

### Phase 1b-1: Ownership Extension

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-106 | [ ] Create OwnershipExtension for TipTap | M6b | FE | Feature 015 complete | TipTap extension adding `owner` attribute to all block-level nodes. Type: `"human" \| "ai:{skill-name}" \| "shared"`. New human-created blocks default to "human" (FR-005). Extension registered in editor setup. |
| T-107 | [ ] Implement ownership edit guard (filterTransaction) | M6b | FE | T-106 | Extend `useBlockEditGuard.ts` to check `owner` attribute. Rules: human actor + AI block → reject with toast "This block is AI-generated. Use Approve/Reject.". AI actor + human block → reject silently (logged). Shared blocks → allow both. Returns filtered transaction. |
| T-108 | [ ] Create ownership visual indicators | M6b | FE | T-106 | Left-border styling: human blocks (none/default), AI blocks (2px solid teal #29A386), shared blocks (2px dashed gray). Hover tooltip: "Owned by {owner}". Accessible: `aria-label` on block wrapper. |
| T-109 | [ ] Implement legacy block migration | M6b | FE | T-106 | On TipTap doc load: blocks without `owner` attribute get `owner: "human"` (FR-009). Migration runs once per doc load, idempotent. No DB migration needed — attribute-level only. |
| T-110 | [ ] Unit tests for OwnershipExtension | M6b | QA | T-107, T-108, T-109 | Tests: new block gets "human" owner, AI block rejects human edit, human block rejects AI edit, shared block allows both, legacy block defaults to "human", visual indicators render. >80% coverage. |

### Phase 1b-2: Backend Ownership Support

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-111 | [ ] Add ownership to MCP tool block creation | M6b | AI | T-106 | MCP tools `write_to_note`, `insert_block` set `owner: "ai:{skill-name}"` on created blocks (FR-006). Skill name extracted from current execution context. |
| T-112 | [ ] Add ownership validation to MCP tool handlers | M6b | BE | T-111 | MCP tool handlers for `replace_content`, `update_block` check block ownership before allowing modification. AI modifying human block → return error: "Cannot modify human-owned block". |
| T-113 | [ ] Create block approve/reject API | M6b | BE | T-112 | `POST /api/v1/notes/{noteId}/blocks/{blockId}/approve` → sets block owner to "shared", returns updated block. `POST .../reject` → removes block from note content. Auth: workspace member. Pydantic v2 schemas. |
| T-114 | [ ] Create block approve/reject UI | M6b | FE | T-113, T-108 | AI-owned blocks show [Approve] [Reject] buttons in block toolbar. Approve → PATCH to API → border changes to shared style. Reject → DELETE to API → block removed with undo toast (5s). |
| T-115 | [ ] Integration tests for ownership backend | M6b | QA | T-113 | Tests: AI creates block with correct owner, AI rejected when modifying human block, approve changes owner, reject removes block. >80% coverage. |

---

## Sprint 2: Collab Engine Full Build (M6a)

**Note**: Skip this sprint entirely if Sprint 1a gate failed and M6a was dropped.

### Phase 2a: CRDT Persistence + Provider

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-116 | [ ] Create migration 040: `note_yjs_states` table | M6a | DB | Sprint 1a gate passed | Table: UUID PK, note_id FK (unique constraint), yjs_state bytea (Yjs encoded state), updated_at timestamp. RLS policy on workspace_id via notes join. Index on note_id. |
| T-117 | [ ] Create Yjs persistence backend | M6a | BE | T-116 | FastAPI endpoints: `GET /api/v1/notes/{id}/yjs-state` → returns Yjs state bytes. `PUT /api/v1/notes/{id}/yjs-state` → upserts state. Called by provider on connect (load) and periodically (save every 30s). Auth required. |
| T-118 | [ ] Create full Yjs provider | M6a | FE | T-105, T-117 | Production Yjs provider using gate-selected transport. Features: auto-reconnect (exponential backoff 1-30s), connection status indicator, error boundary. Loads state from backend on connect, persists on disconnect. |
| T-119 | [ ] Implement offline editing support | M6a | FE | T-118 | IndexedDB storage for local Yjs state (via y-indexeddb). On reconnect: CRDT merge with server state. Indicator: "Offline — changes will sync" banner. No data loss verified (FR-028). |
| T-120 | [ ] Unit tests for Yjs provider | M6a | QA | T-118, T-119 | Tests: connect/disconnect lifecycle, auto-reconnect, offline→online merge, state persistence. >80% coverage. |

### Phase 2b: Presence System

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-121 | [ ] Implement user presence via Yjs awareness | M6a | FE | T-118 | Each user broadcasts: cursor position, selection range, user name, color (assigned from palette). Renders remote cursors with name labels. Update latency <200ms (FR-024). |
| T-122 | [ ] Implement AI skill presence | M6a | FE+AI | T-121 | When AI skill operates on note: PilotSpaceAgent sets Yjs awareness entry with `{ type: "ai_skill", name: skillName, intentRef: intentId, avatar: skillIcon }`. Appears within 2s of skill start (FR-033). Removed within 5s of completion. 10s heartbeat timeout for stale entries. |
| T-123 | [ ] Create presence indicator UI | M6a | FE | T-121 | Top-right presence bar: user avatars (circle) + AI skill icons (square with teal border). Visual separation between humans and AI (FR-031). Click avatar → scroll to their cursor. Max 8 shown, "+N" overflow. |
| T-124 | [ ] Implement soft editor limit | M6a | FE | T-121 | At 50 concurrent awareness entries → show warning "Note at capacity". Beyond 50 → new connections are read-only. AI skills count toward limit, max 5 AI slots (R-017). |
| T-125 | [ ] Integration tests for presence | M6a | QA | T-122, T-123, T-124 | Tests: user cursor visible to others, AI presence appears/disappears on time, soft limit triggers at 50, AI limit at 5. |

### Phase 2c: CRDT + Ownership Integration

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-126 | [ ] Integrate ownership with CRDT transactions | M6a+M6b | FE | T-118, T-107 | Ownership `owner` attribute synced via Yjs. CRDT layer rejects transactions violating ownership (FR-008). Rejection emits Yjs awareness event → toast on violating client. |
| T-127 | [ ] Implement AI write serialization via CRDT | M6a | BE+AI | T-126 | Multiple AI skills writing to same note: serialized through CRDT awareness lock protocol. Skill acquires write lock (awareness field), other skills wait. Max hold: 30s. Timeout → force release. |
| T-128 | [ ] Integration tests for CRDT + ownership | M6a+M6b | QA | T-126, T-127 | Tests: ownership violation rejected via CRDT, AI write serialized (2 skills → sequential), CRDT merge preserves ownership attributes. |

---

## Sprint 3: Density Engine (M8)

### Phase 3a: Collapse + Focus Mode

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-129 | [ ] Create DensityExtension for TipTap | M8 | FE | T-106 | TipTap extension managing `collapsed` boolean attribute on block groups. Collapse/expand toggle icon on block group headers. Collapsed state renders single-line summary (block type + first 80 chars). |
| T-130 | [ ] Implement intent block collapse (FR-095) | M8 | FE | T-129 | Intent blocks (from Feature 015) collapse to: `[Intent] {what} — {status}`. Single line. Expand shows full intent with why/constraints/acceptance. |
| T-131 | [ ] Implement progress block collapse (FR-096) | M8 | FE | T-129 | Progress blocks collapse to: `[{skill-name}] {status-emoji} {summary}`. Expand shows full execution details. |
| T-132 | [ ] Implement AI block group summary (FR-099) | M8 | FE | T-129 | Consecutive AI-owned blocks grouped. Group header: `AI: {skill-name} — {N blocks}` with expand/collapse. Default: collapsed for groups >3 blocks. |
| T-133 | [ ] Implement Focus Mode (FR-098) | M8 | FE | T-106 | Toggle button in editor toolbar: "Focus Mode". Active: hides all blocks where `owner` starts with "ai:". Shows only "human" and "shared" blocks. State persisted in localStorage keyed by noteId. Toggle time <200ms. |
| T-134 | [ ] Implement collapse persistence | M8 | FE | T-129 | Collapse state stored in localStorage per note (not in Yjs doc). On load: restore collapse state. On new AI output: default collapsed if group >3 blocks. |
| T-135 | [ ] Unit tests for density features | M8 | QA | T-130, T-131, T-132, T-133 | Tests: intent collapse renders summary, progress collapse renders status, AI groups collapse, Focus Mode hides AI blocks, toggle time <200ms. >80% coverage. Storybook stories for each state. |

### Phase 3b: Sidebar Panels

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-136 | [ ] Create sidebar panel framework | M8 | FE | — | Right-side panel component. Tab navigation: Versions, Presence, Conversation. Open/close via `openSidebar(panel)`. Resizable (drag handle). Default width: 320px. Responsive: full overlay on mobile. |
| T-137 | [ ] Create version history panel (placeholder) | M8 | FE | T-136 | Lists auto-save timestamps for current note. "Full version history coming in Feature 017" banner. Shows last 10 save times. Read-only. |
| T-138 | [ ] Create presence panel | M8 | FE | T-136, T-123 | Lists all active editors. Human: avatar, name, last edit relative time. AI: skill icon, skill name, current intent reference. Only enabled if CRDT active. Disabled state: "Single-user mode" message. |
| T-139 | [ ] Create conversation panel | M8 | FE | T-136 | Threaded AI discussions scoped to note. Links to existing annotation/discussion system. New thread button. Thread list with unread count. |
| T-140 | [ ] Unit tests for sidebar panels | M8 | QA | T-137, T-138, T-139 | Tests: panel opens/closes, tabs switch, version list renders, presence list renders, conversation threads render. >80% coverage. |

### Phase 3c: Templates + Performance

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-141 | [ ] Create migration 041: `note_templates` table | M8 | DB | — | UUID PK, workspace_id (RLS), name varchar(255), description text, content JSONB (TipTap document), is_system boolean (default false), created_by UUID FK, created_at, updated_at. RLS policy on workspace_id. |
| T-142 | [ ] Create migration 041: annotation index | M8 | DB | — | `CREATE INDEX CONCURRENTLY idx_annotations_note_block ON annotations(note_id, block_id)`. Non-blocking (FR-077). |
| T-143 | [ ] Create 4 SDLC templates | M8 | FE+BE | T-141 | Seed migration for system templates: Sprint Planning, Design Review, Postmortem, Release Planning (FR-063). Each template: name, description, TipTap content JSONB with appropriate PM block types. `is_system: true`. |
| T-144 | [ ] Create Template CRUD API | M8 | BE | T-141 | `POST /api/v1/templates` (admin), `GET /api/v1/templates` (member), `GET .../templates/{id}`, `PUT .../templates/{id}` (admin+owner), `DELETE .../templates/{id}` (admin+owner). System templates read-only. Pydantic v2 schemas. RLS enforced. |
| T-145 | [ ] Create template picker UI | M8 | FE | T-144 | Template selection modal on "New Note". Grid of cards: name, description, preview thumbnail. "Blank" option always first. Creates independent copy of template content (FR-064). Custom template creation for admins (FR-065). |
| T-146 | [ ] Optimize 200-block keystroke latency | M8 | FE | T-129 | Profile and optimize TipTap rendering for <100ms keystroke at 200 blocks (FR-078). Strategies: debounce decoration updates, lazy block rendering, memoize node views. Performance test in CI. |
| T-147 | [ ] Optimize 500-block scroll performance | M8 | FE | T-146 | 60fps scroll at 500 blocks (FR-080). Virtual rendering for off-screen blocks using intersection observer. Placeholder nodes for collapsed blocks. Performance test in CI. |
| T-148 | [ ] Implement 1000+ block warning | M8 | FE | — | At 1000 blocks: show warning banner "This note is very large. Consider splitting into sub-notes." Dismissable per session. |
| T-149 | [ ] Annotation query performance test | M8 | QA | T-142 | Seed 200+ annotations. Query by note_id + block_id <50ms (FR-076). Load test with 10 concurrent queries. |
| T-150 | [ ] Integration tests for templates | M8 | QA | T-144, T-145 | Tests: CRUD operations, system template read-only, template creates copy, admin-only custom templates. >80% coverage. |
| T-151 | [ ] E2E test: full density workflow | M8 | QA | T-135, T-140, T-150 | Flow: open note with AI content → AI blocks grouped and collapsed → expand group → Focus Mode hides AI → create note from template → sidebar panels open. |

---

## Summary

| Sprint | Tasks | New Tables | New Migrations | New Endpoints | Key Deliverables |
|--------|-------|------------|----------------|---------------|------------------|
| Sprint 1a | T-101 → T-105 (5) | — | — | — | CRDT POC + load-test gate |
| Sprint 1b | T-106 → T-115 (10) | — | — | 2 (block approve/reject) | Ownership extension + edit guard |
| Sprint 2 | T-116 → T-128 (13) | note_yjs_states | 040 | 2 (Yjs state CRUD) | Full CRDT + presence + offline |
| Sprint 3 | T-129 → T-151 (23) | note_templates | 041 | 5 (template CRUD) | Density + sidebar + templates + perf |
| **Total** | **51 tasks** | **2 new tables** | **2 migrations** | **9 new endpoints** | |

### Dependency Graph (Critical Path)

```
Sprint 1a (parallel with Sprint 1b):
T-101 → T-102 → T-104 → T-105 (gate decision)
T-103 (fallback, parallel)

Sprint 1b (parallel with Sprint 1a):
T-106 → T-107 → T-110
T-106 → T-108 → T-110
T-106 → T-109 → T-110
T-111 → T-112 → T-113 → T-114 → T-115

Sprint 2 (depends on Sprint 1a gate + Sprint 1b):
T-116 → T-117 → T-118 → T-119 → T-120
T-118 → T-121 → T-122 → T-125
T-121 → T-123 → T-124 → T-125
T-118 + T-107 → T-126 → T-127 → T-128

Sprint 3 (depends on Sprint 1b, optionally Sprint 2):
T-129 → T-130, T-131, T-132 → T-135
T-106 → T-133 → T-135
T-129 → T-134
T-136 → T-137, T-138, T-139 → T-140
T-141 → T-143 → T-145 → T-150
T-141 → T-144 → T-145
T-129 → T-146 → T-147
T-142 → T-149
T-135 + T-140 + T-150 → T-151
```
