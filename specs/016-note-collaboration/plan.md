# Implementation Plan: Note Collaboration & Density

**Feature Number**: 016
**Spec Version**: v1.0
**Created**: 2026-02-19
**Author**: Tin Dang

---

## Overview

3 sprints delivering M6a (gated) → M6b → M8. Sprint 1a has a mandatory load-test gate that determines CRDT provider. M6b can proceed independently of the M6a gate result.

**Critical path**: M6a gate → M6a Collab Engine → M6b Ownership Engine → M8 Density Engine

**Migration base**: Continues from Feature 015 (migration 039). Feature 016 starts at 040.

**Dependency**: Feature 015 must be complete (Agent Loop, Skills, Memory operational).

---

## Sprint 1a: CRDT Proof-of-Concept + Load-Test Gate (M6a — Gate)

**Goal**: Determine whether Supabase Realtime can handle CRDT sync at acceptable latency. Gate result decides provider for full M6a implementation.

### Phase 1a-POC: Minimal Yjs Integration

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Yjs document binding POC | FE | Minimal TipTap + Yjs binding (y-prosemirror). Single note, no persistence. Verify CRDT merge works with TipTap schema. |
| y-supabase provider POC | FE | Connect Yjs doc to Supabase Realtime channel. Broadcast awareness + doc updates. |
| Load-test harness | QA | Puppeteer/Playwright script: 10 concurrent browser tabs editing same note for 60 seconds. Measure sync latency p50/p95/p99. |
| Fallback: y-websocket server | BE | Dockerized y-websocket server ready to deploy if Supabase Realtime fails gate. |

### Sprint 1a Gate

- [ ] 10 concurrent editors (mix of real browsers + headless), 60 seconds continuous editing
- [ ] **PASS**: p95 sync latency < 500ms → proceed with Supabase Realtime
- [ ] **FAIL**: p95 >= 500ms → retest with y-websocket. If y-websocket also fails → M6a dropped, notes remain single-user
- [ ] Document gate result with metrics in `specs/016-note-collaboration/gate-result.md`

---

## Sprint 1b: Ownership Engine (M6b)

**Goal**: Block-level human/AI ownership enforcement. Can proceed regardless of Sprint 1a gate result.

**Depends on**: Feature 015 complete (AI skills must be operational for AI block creation).

### Phase 1b-1: Ownership Extension

| Deliverable | Layer | Details |
|-------------|-------|---------|
| OwnershipExtension (TipTap) | FE | New TipTap extension adding `owner` attribute to all block nodes. Values: "human", "ai:{skill-name}", "shared". Default: "human" for new blocks. |
| Edit guard (filterTransaction) | FE | Extend existing `useBlockEditGuard` to reject edits violating ownership rules. Human cannot edit AI blocks (approve/reject only). AI cannot modify human blocks. Shared blocks: both can edit. |
| Visual ownership indicators | FE | Left-border color coding: human (none/default), AI (teal accent), shared (dashed). Tooltip showing owner on hover. |
| Legacy block migration | FE | Blocks without `owner` attribute default to "human" on load (FR-009). |

### Phase 1b-2: Backend Ownership Support

| Deliverable | Layer | Details |
|-------------|-------|---------|
| MCP tool ownership integration | AI | AI skills set `owner: "ai:{skill-name}"` when creating blocks via MCP tools (`write_to_note`, `insert_block`). |
| Ownership validation in MCP handlers | BE | MCP tool handlers verify ownership before allowing block modifications. Reject with error if AI tries to modify human-owned block. |
| Approve/reject API for AI blocks | BE | `POST /api/v1/notes/{id}/blocks/{blockId}/approve` → changes owner to "shared". `POST .../reject` → removes block. |

### Sprint 1b Gate

- [ ] New blocks default to "human" owner (unit test)
- [ ] AI-created blocks have "ai:{skill-name}" owner (integration test)
- [ ] Human cannot edit AI block text — edit transaction rejected (unit test)
- [ ] AI MCP tool cannot modify human block — handler rejects (integration test)
- [ ] Legacy blocks without owner default to "human" (unit test)
- [ ] Visual indicators render correctly for all 3 ownership types (Storybook)
- [ ] Approve/reject API changes ownership correctly (integration test)
- [ ] Test coverage >80% for new code

---

## Sprint 2: Collab Engine Full Build (M6a)

**Goal**: Full real-time collaborative editing with persistence, presence, and AI skill integration.

**Depends on**: Sprint 1a gate passed (provider decided). Sprint 1b complete (ownership must be stable before adding CRDT).

**Note**: If Sprint 1a gate failed and M6a was dropped, skip this sprint entirely. Proceed to Sprint 3.

### Phase 2a: CRDT Persistence + Provider

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Yjs provider (final) | FE | Full Yjs provider using gate-selected transport (Supabase Realtime or y-websocket). Connection management, auto-reconnect, error handling. |
| Yjs persistence backend | BE | Store Yjs document state in PostgreSQL. Load on connect, persist on disconnect + periodic snapshots (30s). |
| Migration 040: `note_yjs_states` table | DB | UUID PK, note_id FK (unique), yjs_state bytea, updated_at. For server-side Yjs state persistence. |
| Offline editing support | FE | IndexedDB local Yjs state. On reconnect: CRDT merge with server state. No data loss (FR-028). |

### Phase 2b: Presence System

| Deliverable | Layer | Details |
|-------------|-------|---------|
| User presence via Yjs awareness | FE | Cursor positions with name labels and colors. User avatar in presence bar. <200ms update latency (FR-024). |
| AI skill presence | FE+AI | When AI skill operates on note: set awareness entry with skill name, avatar, current intent reference. Appear within 2s (FR-033), disappear within 5s of completion. |
| Presence indicator UI | FE | Top-right presence bar showing avatars (human) and skill icons (AI). Visual separation between human and AI participants (FR-031). Click to scroll to cursor position. |
| Soft editor limit | FE | Warning at 50 concurrent editors. Read-only overflow beyond limit (FR-029 + edge case). AI skills count toward limit, max 5 AI slots. |

### Phase 2c: CRDT + Ownership Integration

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Ownership in CRDT transactions | FE | CRDT layer rejects transactions that violate ownership (FR-008). Ownership attribute synced via Yjs. |
| AI write serialization | BE | Multiple AI skills creating blocks: serialized through CRDT awareness protocol. Queue if CRDT unavailable. |
| Conflict resolution | FE | Character-level CRDT convergence. Ownership violations → toast notification to violating user. |

### Sprint 2 Gate

- [ ] 10 concurrent editors, real-time sync, 0 data loss (load test)
- [ ] p95 sync latency <200ms (target, not just gate threshold)
- [ ] Offline edit → reconnect → merge without data loss (integration test)
- [ ] User cursors visible with correct colors/names (E2E test)
- [ ] AI skill presence appears within 2s, disappears within 5s (integration test)
- [ ] Ownership violations rejected at CRDT layer (unit test)
- [ ] 50+ editors → soft limit warning, overflow read-only (integration test)
- [ ] Test coverage >80% for new code

---

## Sprint 3: Density Engine (M8)

**Goal**: Prevent AI output from overwhelming notes. Collapsible blocks, Focus Mode, sidebar panels, templates.

**Depends on**: Sprint 1b complete (ownership needed for Focus Mode filtering). Sprint 2 if CRDT was built (presence sidebar panel needs it).

### Phase 3a: Collapse + Focus Mode

| Deliverable | Layer | Details |
|-------------|-------|---------|
| DensityExtension (TipTap) | FE | New TipTap extension managing collapse/expand state per block group. Intent blocks → single-line summary (FR-095). Progress blocks → status summary (FR-096). AI block groups → summary header (FR-099). |
| Focus Mode | FE | Toggle: hides all AI-owned blocks, shows only human content (FR-098). Persisted in localStorage per note. Toggle button in editor toolbar. <200ms toggle time. |
| Collapse persistence | FE | Collapse state stored in note metadata (not in Yjs doc to avoid CRDT overhead). Restored on load. |

### Phase 3b: Sidebar Panels

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Sidebar panel framework | FE | Right-side panel with tabs: Versions, Presence, Conversation. Open via `openSidebar(panel)`. Resizable. |
| Version history panel | FE | Lists note versions (placeholder — full version engine in Feature 017). Shows "Coming soon" with basic auto-save timestamps. |
| Presence panel | FE | Lists all active editors with cursor color, last edit time. AI skills with current intent. Only shown if CRDT active. |
| Conversation panel | FE | Threaded AI discussions per block. Links to existing annotation system. |

### Phase 3c: Templates + Performance

| Deliverable | Layer | Details |
|-------------|-------|---------|
| 4 SDLC templates | FE+BE | Sprint Planning, Design Review, Postmortem, Release Planning (FR-063). Template creates independent copy (FR-064). |
| Template CRUD API | BE | `POST /api/v1/templates`, `GET`, `PUT`, `DELETE`. Admin-only for custom templates (FR-065). RLS enforced. |
| Migration 041: `note_templates` table | DB | UUID PK, workspace_id (RLS), name, description, content JSONB (TipTap doc), is_system boolean, created_by, timestamps. |
| Performance: 200-block keystroke latency | FE | Optimize TipTap rendering for <100ms keystroke at 200 blocks (FR-078). Virtual rendering for off-screen blocks if needed. |
| Performance: 500-block scroll | FE | 60fps scroll at 500 blocks (FR-080). Lazy render off-screen blocks. |
| Performance: annotation query <50ms | BE | Index on `(note_id, block_id)` for annotations. CONCURRENTLY to avoid locks (FR-077). |
| Migration 041: annotation index | DB | `CREATE INDEX CONCURRENTLY idx_annotations_note_block ON annotations(note_id, block_id)`. |
| 1000+ block warning | FE | Show warning banner recommending split into sub-notes (edge case). |

### Sprint 3 Gate

- [ ] Intent blocks collapse to single-line summary (unit test)
- [ ] Focus Mode hides AI blocks, shows human only (unit test + Storybook)
- [ ] Focus Mode toggle <200ms (performance test)
- [ ] Sidebar panels open/close correctly (E2E test)
- [ ] 4 SDLC templates create independent copies (integration test)
- [ ] Admin can create custom templates (integration test)
- [ ] <100ms keystroke latency at 200 blocks (performance test)
- [ ] 60fps scroll at 500 blocks (performance test)
- [ ] Annotation query <50ms at 200+ annotations (load test)
- [ ] Annotation index created CONCURRENTLY (migration test)
- [ ] Test coverage >80% for new code

---

## Cross-Sprint Concerns

### Migration Strategy

| Migration | Sprint | Contents |
|-----------|--------|----------|
| 040 | Sprint 2 | `note_yjs_states` table (CRDT persistence) |
| 041 | Sprint 3 | `note_templates` table + annotation index (CONCURRENTLY) |

**Note**: Sprint 1a (POC) and Sprint 1b (Ownership) require no migrations. Ownership is stored as TipTap block attributes, not database columns.

### Risk Mitigations

| Risk | Mitigation | Sprint |
|------|-----------|--------|
| R-029: Supabase Realtime scaling | Sprint 1a gate with y-websocket fallback | Sprint 1a |
| R-005: CRDT bundle >100KB | Lazy-load collab module, code-split Yjs | Sprint 2 |
| R-003: Ownership + CRDT complexity | Ownership at app layer first (Sprint 1b), CRDT integration after stable (Sprint 2) | Sprint 1b→2 |
| R-004: CRDT merge unexpected states | Integration tests, version history as safety net (Feature 017) | Sprint 2 |
| R-009: Large doc rendering | Virtual rendering, 1000+ block warning | Sprint 3 |
| R-024: Note density overwhelming | Default collapsed AI blocks, Focus Mode | Sprint 3 |
| R-018: Annotation index migration downtime | CREATE INDEX CONCURRENTLY | Sprint 3 |

### Testing Strategy

- **Unit tests**: TipTap extensions (ownership, density, collab), services. >80% coverage per sprint.
- **Integration tests**: CRDT sync, ownership enforcement via MCP tools, template CRUD, annotation queries.
- **Load tests**: Sprint 1a gate (10 editors, p95 <500ms), Sprint 2 (200ms target), Sprint 3 (200 blocks, 500 blocks).
- **E2E tests**: Collaborative editing flow, ownership violation rejection, Focus Mode, template creation.
- **Performance tests**: Keystroke latency, scroll FPS, annotation query time, Focus Mode toggle.

---

## Dependencies

| External | Used By | Fallback |
|----------|---------|----------|
| Supabase Realtime | M6a CRDT sync | y-websocket self-hosted |
| Feature 015 (AI Skills) | M6b AI block creation | M6b can test with mock skill output |
| TipTap/ProseMirror | M6b ownership, M8 density | No fallback — core dependency |
| Yjs | M6a CRDT | No fallback — core dependency for collab |

---

## After Feature 016

1. **Feature 017** (Note Versioning + PM Blocks): M6c Version Engine + M6d PM Block Engine
2. **CRDT monitoring**: Add observability for sync latency, conflict rate, presence accuracy
3. **Ownership analytics**: Track AI vs human content ratio per note
