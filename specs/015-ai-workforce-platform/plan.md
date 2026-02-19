# Implementation Plan: AI Workforce Core

**Feature Number**: 015
**Spec Version**: v4.1
**Created**: 2026-02-18
**Author**: Tin Dang

---

## Overview

3 sprints delivering M1→M2→M3+M4→M7. Each sprint has a gate that must pass before proceeding.

**Critical path**: M1 (Agent Loop) → M2 (Intent Engine) → M3 (Skill Fleet) + M4 (Memory Engine) → M7 (Chat Engine)

**Migration base**: Alembic 037 → Feature 015 starts at 038.

---

## Sprint 1: Foundation — Agent Loop + Intent Engine (M1 + M2)

**Goal**: User types in chat → intents detected, presented, confirmed → agent loop orchestrates.

### Phase 1a: Database + Domain (M2 entities)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Migration 038: `work_intents` table | Infrastructure | UUID PK, workspace_id (RLS), what, why, constraints (JSONB), acceptance (JSONB), status enum, owner, confidence float, parent_intent_id FK, source_block_id, created_at, updated_at |
| Migration 038: `intent_artifacts` table | Infrastructure | UUID PK, intent_id FK, artifact_type, reference_id, reference_type, created_at |
| WorkIntent domain entity | Domain | Rich entity with status transitions, validation (confidence 0-1), dedup logic |
| WorkIntentRepository | Infrastructure | CRUD + RLS enforcement + query by workspace + status filters |
| RLS policies for work_intents | Infrastructure | workspace_id-scoped, member+ access |

### Phase 1b: Intent Engine Service (M2)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| IntentDetectionService | Application | `detect(text, source)` → calls LLM (Sonnet) to extract WorkIntents from text |
| Intent LLM prompt | AI | Structured output: what/why/constraints/acceptance/confidence. Few-shot examples. |
| Chat-priority window | Application | Redis key `intent_lock:{workspace_id}` with 3s TTL. Chat detection sets lock; note detection checks lock before proceeding (FR-020-I) |
| ConfirmAll with cap | Application | Top-10 by confidence, FR-113 |
| Dedup by semantic similarity | Application | Embed intent `what` field, cosine >0.9 → merge. Async post-detection. |
| IntentRouter (API) | Presentation | `POST /api/v1/ai/intents/detect`, `POST .../confirm`, `POST .../reject`, `POST .../edit`, `POST .../confirm-all` |

### Phase 1c: Agent Loop Upgrade (M1)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| PilotSpaceAgent pipeline refactor | AI | Replace single-shot `agent.query()` with: recall → analyze → detect intents → select skill → execute → save → respond |
| Intent hook in agent loop | AI | After LLM analysis, check for WorkIntents. If detected, present in chat before skill execution. |
| SSE event types | AI | New events: `intent_detected`, `intent_confirmed`, `intent_executing`, `intent_completed` |
| Event-driven resume | AI | FR-084: Agent loop subscribes to approval events, resumes blocked work within 5s |

### Sprint 1 Gate

- [ ] WorkIntent CRUD via API (integration test)
- [ ] Intent detection from chat text with >70% accuracy on 20 test cases
- [ ] Chat-priority window suppresses note detection (unit test)
- [ ] ConfirmAll respects cap=10 (unit test)
- [ ] Agent loop recall→analyze→detect pipeline runs end-to-end (integration test)
- [ ] SSE events for intent lifecycle (integration test)
- [ ] Test coverage >80% for new code

---

## Sprint 2: Execution + Knowledge — Skill Fleet + Memory Engine (M3 + M4)

**Goal**: Confirmed intents execute via skills. Workspace knowledge persists and informs future executions.

**Depends on**: Sprint 1 gate passed.

### Phase 2a: Database + Domain (M4 entities)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Migration 039: Embedding dimension migration | Infrastructure | ALTER `embeddings.embedding` from vector(1536) to vector(768). Re-embed existing data with Gemini `gemini-embedding-001`. **Reversible**: keep 1536 backup column during migration. |
| Migration 039: `memory_entries` table | Infrastructure | UUID PK, workspace_id (RLS), content text, embedding vector(768), keywords tsvector, source_type enum, source_id UUID, pinned boolean, created_at, expires_at |
| Migration 039: `constitution_rules` table | Infrastructure | UUID PK, workspace_id, content, severity enum (MUST/SHOULD/MAY), version integer, source_block_id, active boolean |
| Migration 039: `memory_dlq` table | Infrastructure | UUID PK, workspace_id, payload JSONB, error text, attempts integer, created_at, next_retry_at |
| Migration 039: `skill_executions` update | Infrastructure | Add `approval_status` enum (auto_approved, pending_approval, approved, rejected, expired) column |
| MemoryEntry domain entity | Domain | With embedding, keyword extraction, TTL |
| ConstitutionRule domain entity | Domain | With version tracking, severity parsing |
| MemoryEntryRepository | Infrastructure | Hybrid search (0.7 vector + 0.3 keyword fusion), RLS |
| ConstitutionRuleRepository | Infrastructure | Version-gated queries |
| RLS policies | Infrastructure | All new tables workspace-scoped |

### Phase 2b: Memory Engine Service (M4)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| MemorySearchService | Application | `search(query, workspace_id)` → hybrid fusion, <200ms SLA |
| MemorySaveService | Application | `save(entry)` → embed via Gemini API → persist. Retry with backoff (FR-112). DLQ on 3x failure. |
| ConstitutionIngestService | Application | `ingest(rules)` → parse RFC 2119 severity → version bump → keyword index (10s) → vector index (30s) |
| Constitution version gate | Application | `getConstitutionVersion()` + skill pre-check: if version > last_indexed, block up to 60s (FR-073) |
| Embedding provider switch | AI | Update provider config: Gemini `gemini-embedding-001` (768-dim) replaces OpenAI `text-embedding-3-large` (1536-dim) |
| DLQ reconciliation job | Infrastructure | Hourly cron via pgmq: retry DLQ entries, detect orphaned skill executions |
| MemoryRouter (API) | Presentation | `POST /api/v1/ai/memory/search`, `GET .../constitution/version` |

### Phase 2c: Skill Fleet Upgrade (M3)

| Deliverable | Layer | Details |
|-------------|-------|---------|
| 6 net-new SKILL.md files | AI | generate-code, write-tests, generate-migration, review-code, review-architecture, scan-security |
| Skill executor with approval hold | AI | Destructive skills → output held as `pending_approval` in `skill_executions`. Approval API releases persistence. |
| TipTap output validation | AI | FR-114: Validate skill output against TipTap block schema before persistence |
| Approval API endpoints | Presentation | `POST /api/v1/ai/approvals/{id}/approve`, `POST .../reject` |
| Skill concurrency manager | AI | Semaphore: max 5 per workspace (FR-109). 6th → queued with "Waiting for slot" SSE event. |
| Agent loop integration | AI | Wire M4 recall into M1 pipeline. Wire M3 execution into M1 skill step. |

### Sprint 2 Gate

- [ ] Memory search <200ms at 1000 entries (load test)
- [ ] Embedding migration 1536→768 reversible and data preserved (migration test)
- [ ] Constitution version gate blocks stale execution (integration test)
- [ ] DLQ reconciliation recovers >95% of failed entries (integration test)
- [ ] 6 net-new skills execute via SDK subagent (integration test per skill)
- [ ] Destructive skill output held until approval API call (integration test)
- [ ] TipTap schema validation rejects malformed output (unit test)
- [ ] Skill concurrency capped at 5 (integration test)
- [ ] Full agent loop: recall → analyze → skill → save → respond (E2E test)
- [ ] Test coverage >80% for new code

---

## Sprint 3: UX — Chat Engine Upgrade (M7)

**Goal**: Chat renders intent cards, skill progress, approval actions. Full paradigm visible to user.

**Depends on**: Sprint 2 gate passed.

### Phase 3a: Chat Message Types

| Deliverable | Layer | Details |
|-------------|-------|---------|
| IntentCard component | Frontend | Renders WorkIntent with confidence bar, [Confirm] [Edit] [Dismiss] actions |
| SkillProgressCard component | Frontend | Shows: intent summary, skill name, status (executing/completed/failed), artifacts |
| ApprovalCard component | Frontend | For destructive skills: preview output, [Approve] [Reject] actions. Calls approval API. |
| ConversationBlock component | Frontend | Threaded Q&A for AI clarification (FR-066-068) |
| Message type renderer | Frontend | Polymorphic: text → TextMessage, intent → IntentCard, progress → SkillProgressCard, approval → ApprovalCard |

### Phase 3b: Chat Interaction Model

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Intent lifecycle SSE handlers | Frontend | Handle `intent_detected`, `intent_confirmed`, `intent_executing`, `intent_completed` events → update ChatHistoryStore |
| Approval store integration | Frontend | Wire ApprovalCard → ApprovalStore → approval API calls |
| ConfirmAll UI | Frontend | Button in chat header when pending intents exist. Shows count. Calls confirmAll API (max 10). |
| Queue depth indicator | Frontend | When >5 skills running, show "N skills queued" in chat |
| Skill output preview | Frontend | For `suggest` approval: show TipTap block preview in chat before [Approve] writes to note |

### Phase 3c: Ghost Text + Conversation Blocks

| Deliverable | Layer | Details |
|-------------|-------|---------|
| Ghost text — no changes | Frontend | Stays memory-unaware per spec. Document in component README. |
| Conversation block rendering | Frontend | AI-created blocks for clarification. Threaded replies. 5s processing SLA (FR-068). |
| Chat session persistence | Frontend | Ensure intent cards and approval state survive page refresh (rehydrate from API) |

### Sprint 3 Gate

- [ ] IntentCard renders with correct actions (Storybook + unit test)
- [ ] ApprovalCard calls approval API and handles success/error (integration test)
- [ ] SSE intent lifecycle events render correctly in chat (E2E test)
- [ ] ConfirmAll UI respects cap and shows queue depth (unit test)
- [ ] Full user flow: type command → intent card → confirm → skill progress → approve → note updated (E2E test)
- [ ] Chat state rehydrates on page refresh (integration test)
- [ ] Test coverage >80% for new frontend code
- [ ] Lighthouse accessibility >95 for new components

---

## Cross-Sprint Concerns

### Migration Strategy

| Migration | Sprint | Contents |
|-----------|--------|----------|
| 038 | Sprint 1 | `work_intents`, `intent_artifacts` tables + RLS |
| 039 | Sprint 2 | `memory_entries`, `constitution_rules`, `memory_dlq` tables + embedding 1536→768 migration + `skill_executions.approval_status` column + RLS |

### Risk Mitigations

| Risk | Mitigation | Sprint |
|------|-----------|--------|
| Intent detection accuracy <70% | 20 labeled test cases, confidence threshold, structured prompts | Sprint 1 |
| Embedding migration data loss | Backup 1536 column, reversible migration, re-embed with Gemini | Sprint 2 |
| Memory search >200ms | HNSW index, connection pooling, query plan analysis | Sprint 2 |
| Destructive skill bypass | Backend hold enforcement, approval API auth check | Sprint 2 |
| Chat UX confusion | Intent card design review, user testing with 3 team members | Sprint 3 |

### Testing Strategy

- **Unit tests**: Domain entities, services, validators. >80% coverage per sprint.
- **Integration tests**: API endpoints, DB queries with RLS, SSE events, skill execution.
- **E2E tests**: Full user flows (chat → intent → skill → approve → note). 3 critical paths.
- **Load tests**: Memory search at 1000+ entries (Sprint 2 gate).
- **Migration tests**: 1536→768 embedding migration reversibility (Sprint 2).

---

## Dependencies

| External | Used By | Fallback |
|----------|---------|----------|
| Anthropic Claude API (Sonnet) | M2 intent detection, M3 skill execution | Retry 3x, circuit breaker, degrade to cached responses |
| Google Gemini API (Flash) | M4 embeddings, ghost text, writing skills | Keyword-only search fallback for M4 |
| Supabase Queues (pgmq) | M4 DLQ reconciliation job | Manual reconciliation via admin API |
| Redis | Chat-priority window lock, session cache | PostgreSQL fallback for locks (advisory locks) |

---

## After Feature 015

1. **Feature 016** (Note Collaboration): M6a CRDT + M6b Ownership + M8 Density Engine
2. **Skill audit**: Reconcile 17 existing + 6 new → remove overlaps, unify naming
3. **Ghost text + memory**: Integrate M4 context into GhostTextAgent
4. **Monitoring**: Add observability for intent detection accuracy, skill execution latency, memory search performance
