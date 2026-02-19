# Feature Specification: Note Collaboration & Density

**Feature Number**: 016
**Branch**: `016-note-collaboration`
**Created**: 2026-02-18
**Updated**: 2026-02-19 (v1.1 — Applied CRITICAL decision C-5)
**Status**: Draft
**Author**: Tin Dang
**Depends on**: 015-ai-workforce-platform (Agent Loop, Skills, Memory must be operational)
**Blocks**: 017-note-versioning-pm

---

## Overview

Add real-time collaborative editing (CRDT), block-level human/AI ownership enforcement, and density controls to prevent AI output from overwhelming notes.

| Module | Type | Summary |
|--------|------|---------|
| M6a — Collab Engine | New (**conditional** — Sprint 1a gate) | Yjs CRDT via Supabase Realtime |
| M6b — Ownership Engine | New | Block-level human/AI boundary enforcement |
| M8 — Density Engine | New | Collapse, Focus Mode, sidebar panels |

---

## Prerequisite: Sprint 1a Gate (M6a)

**Mandatory load-test gate before proceeding with CRDT**:

- Test: 10 concurrent editors (humans + AI skills), 60 seconds
- Pass: p95 latency < 500ms → proceed with Supabase Realtime
- Fail: p95 ≥ 500ms → switch to y-websocket self-hosted
- Context: Supabase Realtime was removed from 2 existing hooks due to reliability issues

If gate fails and y-websocket is also infeasible, M6a is dropped. Notes remain single-user editable; AI writes sequentially via MCP tools.

---

## System Primitive

### BlockOwnership — The Human-AI Boundary

```typescript
type BlockOwner = 'human' | `ai:${SkillName}` | 'shared';
// Every TipTap block has an `owner` attribute
// human: AI reads only, cannot modify
// ai:{skill}: human approves/rejects only, cannot edit text
// shared: both can read and write
```

**Codebase anchor**: `useBlockEditGuard` already exists at `editor/extensions/pm-blocks/shared/useBlockEditGuard.ts`. M6b extends this to all block types.

---

## Architecture

```
┌────────────────────────────────────────────┐
│  TipTap Editor                              │
│  ├── OwnershipExtension (M6b) — edit guard │
│  ├── YjsExtension (M6a) — CRDT binding    │
│  └── DensityExtension (M8) — collapse/focus│
└──────┬───────────────┬─────────────────────┘
       │               │
  ┌────▼────┐   ┌─────▼──────┐
  │ Collab  │   │ Ownership  │
  │ Engine  │   │  Engine    │
  │  (M6a)  │   │   (M6b)   │
  └────┬────┘   └────────────┘
       │
  ┌────▼──────────────────────┐
  │ Supabase Realtime Channel │
  │ or y-websocket (fallback) │
  └───────────────────────────┘
```

### Module Interfaces

**M6a — Collab Engine**:
```
connect(noteId) → YjsProvider
disconnect(noteId) → void
getPresence(noteId) → (User | AISkill)[]
```

**M6b — Ownership Engine**:
```
setOwner(blockId, owner) → void
checkPermission(blockId, actor) → boolean
filterTransaction(transaction) → transaction | reject
```

**M8 — Density Engine**:
```
collapse(blockGroup) → void
expand(blockGroup) → void
toggleFocusMode() → void
openSidebar(panel:'versions'|'presence'|'conversation') → void
```

---

## Module Specifications

### M6a — Collab Engine

Yjs CRDT for real-time collaborative editing.

```
TipTap Editor ↔ Y.js Document ↔ y-supabase ↔ Supabase Realtime Channel
                                                ↕
                                      PostgreSQL (persistence)
```

**Functional Requirements** (FR-024–033):
- **FR-024**: <200ms sync latency for real-time editing.
- **FR-025**: Concurrent edits resolved without data loss (CRDT).
- **FR-026**: User cursors with name labels and colors.
- **FR-027**: Presence indicator for users AND AI skills.
- **FR-028**: Offline editing with automatic merge on reconnection.
- **FR-029**: At least 50 concurrent editors (humans + AI skills).
- **FR-030**: AI content updates concurrent with human edits without conflict.
- **FR-031**: Presence visually separates humans and AI skills.
- **FR-032**: AI skill presence: avatar, skill name, current intent reference.
- **FR-033**: AI skill presence appears within 2s, disappears within 5s.

---

### M6b — Ownership Engine

Human-AI boundary enforcement at the block level.

#### Backend Ownership Enforcement (C-5)

Ownership is authoritative in the backend, not just the frontend. Block `owner` attribute is stored in the database alongside TipTap block data. MCP tool handlers check ownership before executing write operations.

**Storage**: `owner` field persisted in the block's attrs JSON in the notes table alongside TipTap block content. This is the single source of truth.

**MCP Tool Handler Check**: Before any write operation (`insert_block`, `write_to_note`, `replace_content`, `remove_block`, `update_pm_block`), the handler:
1. Loads block ownership from DB
2. Checks: is the calling actor (skill name or 'human') permitted to write to this block?
3. If violation: raise `OwnershipViolationError` → intent status = "failed", chat error

**Frontend sync**: On page load, frontend fetches block ownership from backend (not from Yjs awareness). Yjs is used for real-time sync of edits, but ownership comes from DB on initial load. This prevents stale frontend state from bypassing ownership.

**Functional Requirements** (FR-001–009):
- **FR-001**: Every block MUST have `owner`: "human", "ai:{skill-name}", or "shared".
- **FR-002**: Human blocks read-only to AI — enforced at MCP tool handler level (backend). Frontend provides UX guard only.
- **FR-003**: AI blocks non-editable by humans (approve/reject only) — enforced at TipTap extension level (frontend).
- **FR-004**: Shared blocks readable and writable by both.
- **FR-005**: New human blocks default to "human".
- **FR-006**: New AI blocks set to "ai:{skill-name}".
- **FR-007**: Ownership visually indicated.
- **FR-008**: CRDT layer (or app layer if no CRDT) MUST reject ownership violations. Backend is the authoritative enforcement point.
- **FR-009**: Legacy blocks default to "human".

---

### M8 — Density Engine

Prevent AI output from overwhelming the note canvas.

**Functional Requirements** (FR-095–099):
- **FR-095**: Intent blocks collapse to single-line summary.
- **FR-096**: Progress blocks collapse to status summary.
- **FR-097**: Version history, presence, conversations in sidebar panels.
- **FR-098**: Focus Mode hides all AI blocks, shows only human content.
- **FR-099**: AI block groups display summary header with expand/collapse.

**Performance** (FR-076–080):
- **FR-076**: Annotation query <50ms for 200+ annotations.
- **FR-077**: Index migration MUST NOT lock tables (CONCURRENTLY).
- **FR-078**: <100ms keystroke latency at 200 blocks.
- **FR-079**: Dirty detection within 50ms (non-blocking).
- **FR-080**: 60fps scroll at 500 blocks.

**Templates** (FR-063–065):
- **FR-063**: 4 SDLC templates: Sprint Planning, Design Review, Postmortem, Release Planning.
- **FR-064**: Templates create independent copies.
- **FR-065**: Admin custom templates supported.

---

## Key Entities

| Entity | Module | Storage | Purpose |
|--------|--------|---------|---------|
| BlockOwnership | M6b | TipTap block attr | Human-AI boundary (not a DB table) |
| CollaborativeSession | M6a | Yjs awareness | Ephemeral presence (not a DB table) |
| AISkillPresence | M6a | Yjs awareness | Ephemeral skill presence (not a DB table) |

---

## Edge Cases

### M6a — Collab Engine
- WebSocket drops → Local changes buffered, auto-reconnect with CRDT merge
- Character-level conflict → CRDT convergence (last-writer-wins per position)
- AI skill loses connection → Buffer and reconnect (same as human)
- Stale AI presence → 10s heartbeat timeout, auto-removed
- 100+ editors → Soft limit at 50, read-only overflow

### M6b — Ownership Engine
- Human pastes into AI block → Blocked with toast
- Legacy block without owner → Default to "human"
- Multiple AI skills creating blocks → Serialized through CRDT (or queue without CRDT)

### M8 — Density Engine
- 1000+ blocks → Warning recommending split into sub-notes

---

## Success Criteria

| Module | Criteria | Target |
|--------|----------|--------|
| M6a Collab | Sprint 1a gate: p95 latency (10 editors) | <500ms (gate); <200ms (target) |
| M6a Collab | Data loss during concurrent editing | 0 |
| M6a Collab | Skill presence visibility | <2s appear, <5s disappear |
| M6b Ownership | Ownership violations | 0 in integration tests |
| M8 Density | Focus Mode toggle time | <200ms |
| M8 Performance | Keystroke latency at 200 blocks | <100ms |
| M8 Performance | Annotation query at 200+ annotations | <50ms |
| M8 Performance | Contract test catches divergences | 100% |

---

## Risk Register

| ID | Risk | Score | Response |
|----|------|-------|----------|
| R-003 | Block ownership + CRDT complexity | 16 | Ownership at app layer, CRDT handles sync. Phase after CRDT stable. |
| R-004 | CRDT merge unexpected states | 15 | Integration tests, version history as safety net. |
| R-023 | Yjs document state divergence | 15 | Periodic snapshots, server-authoritative merge. |
| R-029 | Supabase Realtime scaling | 12 | Sprint 1a gate. Fallback: y-websocket. |
| R-002 | Block ownership UX confusing | 9 | Clear indicators, tooltips, onboarding. |
| R-005 | CRDT bundle > 100KB | 9 | Lazy-load collab module. |
| R-006 | WebSocket infrastructure complexity | 12 | Use Supabase Realtime, evaluate managed solution. |
| R-007 | AI presence WebSocket noise | 6 | Batch updates, 5s heartbeat. |
| R-009 | Large doc rendering breaks extensions | 16 | Structural hash, virtual rendering separate story. |
| R-017 | Editors exceed 50 limit | 6 | Skills count toward limit, max 5. |
| R-018 | Annotation index migration downtime | 10 | CONCURRENTLY option. |
| R-024 | Note density overwhelming | 9 | Default collapsed, Focus Mode. |

---

## Architectural Decisions

| ID | Decision | Choice | Rationale |
|----|----------|--------|-----------|
| AD-3 | Note Density | Collapsible + sidebar + Focus Mode | Prevents AI output from overwhelming notes. |
| AD-4 | CRDT | Yjs + Supabase Realtime (gated) | TipTap official binding. Existing infrastructure. |

---

## Next Phase

1. **Sprint 1a**: CRDT proof-of-concept + load-test gate
2. **Sprint 1b**: Ownership engine (can proceed regardless of CRDT gate result)
3. **Sprint 2**: Density engine (depends on ownership)
4. **After 016** → Feature 017 (Version Engine + PM Block types)
