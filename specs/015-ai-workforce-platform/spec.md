# Feature Specification: AI Workforce Core

**Feature Number**: 015
**Branch**: `feat/ai-note`
**Created**: 2026-02-17
**Updated**: 2026-02-19 (v5.0 — split into independent module specs)
**Status**: Sprint 1+2 complete, Sprint 3 pending
**Author**: Tin Dang
**Depends on**: None
**Blocks**: 016-note-collaboration, 017-note-versioning-pm

---

## Paradigm Shift

**Before**: Human = Worker, AI = Assistant.
**After**: Human = Validator + Architect, AI = Worker + Builder.

Human commands via chat → AI produces specs, plans, tasks, code, tests into notes. Human reviews → approves, corrects, or redirects.

**Chat is the command center. Notes are the artifact store.**

---

## Module Index

Each module has an independent spec. Read the module spec for complete details.

| Module | Spec | Status | Summary |
|--------|------|--------|---------|
| M1 — Agent Loop | [spec-m1-agent-loop.md](spec-m1-agent-loop.md) | Done | Pipeline: recall → detect → execute → save → respond |
| M2 — Intent Engine | [spec-m2-intent-engine.md](spec-m2-intent-engine.md) | Done | WorkIntent detection, confirmation, dedup, expiry |
| M3 — Skill Fleet | [spec-m3-skill-fleet.md](spec-m3-skill-fleet.md) | Done | 23 skills, approval hold, TipTap validation, concurrency |
| M4 — Memory Engine | [spec-m4-memory-engine.md](spec-m4-memory-engine.md) | Done | Hybrid vector+keyword search, constitution rules |
| M7 — Chat Engine | [spec-m7-chat-engine.md](spec-m7-chat-engine.md) | Pending | Intent cards, approval UI, queue indicator |

> M5 is unused. M6a–M6d are in Feature 016 (Note Collaboration) and Feature 017 (Versioning + PM).

---

## System Primitives

Three types flow through the entire system:

```
WorkIntent   — what the human wants done (M2 produces, M1 routes, M3 executes)
SkillResult  — what the AI produced (M3 produces, M4 stores as MemoryEntry)
MemoryEntry  — what the system learned (M4 stores, M1 recalls)
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   AGENT LOOP (M1)                     │
│  msg → recall(M4) → analyze → skill(M3) → save(M4)  │
│  → present in chat(M7) → approval → respond           │
└──────┬───────────┬───────────┬───────────────────────┘
       │           │           │
  ┌────▼────┐ ┌───▼─────┐ ┌──▼────┐
  │ INTENT  │ │  SKILL  │ │MEMORY │
  │ ENGINE  │ │  FLEET  │ │ENGINE │
  │  (M2)   │ │  (M3)   │ │ (M4)  │
  └─────────┘ └─────────┘ └───────┘
                   │
  ┌────────────────▼───────────────────────────┐
  │   CHAT ENGINE (M7) — frontend SSE consumer  │
  │   Intent cards, progress, approval actions  │
  └────────────────────────────────────────────┘
```

M7 has no backend services. It consumes SSE events M1 already emits.

---

## Implementation Status

| Sprint | Scope | Status |
|--------|-------|--------|
| Sprint 1 | M1 + M2 (Agent Loop + Intent Engine) | Done |
| Sprint 2 | M3 + M4 (Skill Fleet + Memory Engine) | Done |
| Sprint 3 | M7 (Chat Engine frontend) | Pending |

**Migrations completed**: 038 (work_intents), 039 (skill_executions), 040 (memory_engine), 041 (skill_approval_expiry)

---

## Cross-Module Constraints

| ID | Constraint | Modules |
|----|------------|---------|
| C-1 | skill_executions is a full CREATE (no prior table) | M3 |
| C-3 | Redis mutex `note_write_lock:{note_id}` before any note mutation | M3 |
| C-7 | `required_approval_role` in SKILL.md enforced at API layer | M3 |
| C-8 | ConfirmAll must skip intents with dedup_status=pending | M2 |

---

## Key Architectural Decisions

| ID | Decision |
|----|----------|
| AD-1 | SDK subagents within FastAPI (no CLI subprocess) |
| AD-2 | Backend hold + UI release for destructive skill approval |
| AD-6 | deploy/hotfix/generate-migration always require admin approval |
| AD-8 | Chat = command interface, Notes = artifact store |
| AD-10 | Agent loop: recall → analyze → skill → save → respond |
| AD-11 | Memory: pgvector + PostgreSQL FTS hybrid (0.7/0.3 fusion) |

---

## After Feature 015

1. **Feature 016** — Note Collaboration: CRDT, Ownership Engine, Density Engine
2. **Skill audit** — Reconcile 17 existing + 6 new skills, remove overlaps
3. **Ghost text + memory** — Integrate M4 context into GhostTextAgent
4. **Monitoring** — Intent detection accuracy, skill execution latency, memory search p95
