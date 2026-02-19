# Tasks: AI Workforce Core (Feature 015)

**Spec**: v4.2 | **Plan**: v1.0 | **Generated**: 2026-02-18 | **Updated**: 2026-02-19 (C-1, C-8 applied)

---

## Legend

- **Status**: `[ ]` pending, `[~]` in progress, `[x]` done, `[-]` blocked
- **Layer**: DB (database/migration), BE (backend service), AI (agent/skill), FE (frontend), QA (test)
- **Deps**: Task IDs that must complete first

---

## Sprint 1: Foundation — Agent Loop + Intent Engine (M1 + M2)

### Phase 1a: Database + Domain

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-001 | [ ] Create migration 038: `work_intents` table | M2 | DB | — | Table exists with: UUID PK, workspace_id, what, why, constraints (JSONB), acceptance (JSONB), status enum (detected/confirmed/executing/review/accepted/rejected), dedup_status enum (pending/complete) DEFAULT pending, owner, confidence float(0-1), parent_intent_id FK (self-ref), source_block_id, timestamps. RLS policy on workspace_id. **C-8**: dedup_status column required for ConfirmAll race prevention. |
| T-002 | [ ] Create migration 038: `intent_artifacts` table | M2 | DB | T-001 | Table exists with: UUID PK, intent_id FK → work_intents, artifact_type, reference_id UUID, reference_type, created_at. RLS via join to work_intents.workspace_id. |
| T-003 | [ ] Create WorkIntent domain entity | M2 | BE | T-001 | Rich entity with: status transition validation (detected→confirmed→executing→review→accepted/rejected), confidence range validation (0-1), dedup hash computation. Immutable fields after confirmed: what, why. |
| T-004 | [ ] Create IntentArtifact domain entity | M2 | BE | T-002 | Entity with FK to WorkIntent, artifact_type enum (note_block, issue, note). |
| T-005 | [ ] Create WorkIntentRepository | M2 | BE | T-003 | Async CRUD, RLS enforcement. Queries: by workspace+status, by parent_intent_id, by source_block_id. Batch query for confirmAll (top-N by confidence). |
| T-006 | [ ] Create IntentArtifactRepository | M2 | BE | T-004 | Async CRUD, RLS via workspace join. |
| T-007 | [ ] Unit tests for WorkIntent entity | M2 | QA | T-003 | Status transitions, validation, dedup hash. >80% coverage. |

### Phase 1b: Intent Engine Service

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-008 | [ ] Create IntentDetectionService | M2 | BE | T-005 | `detect(text, source)` → calls Sonnet with structured output prompt → returns WorkIntent[]. Handles: empty text (no intents), low confidence (<70% → add clarification question). |
| T-009 | [ ] Create intent detection LLM prompt | M2 | AI | — | Structured output: what/why/constraints/acceptance/confidence. Few-shot examples (5 chat, 3 note). Test against 20 labeled cases >70% accuracy. |
| T-010 | [ ] Implement chat-priority window | M2 | BE | T-008 | Redis key `intent_lock:{workspace_id}` with 3s TTL. Chat detection sets lock. Note detection checks lock → if locked, discard. Unit test: concurrent chat+note → only chat intent survives. |
| T-011 | [ ] Implement confirmAll with cap=10 | M2 | BE | T-005 | `confirmAll(workspace_id, min_confidence=0.7, max_count=10)` → top-10 by confidence WHERE dedup_status='complete'. Intents with dedup_status='pending' excluded from batch, shown as "Deduplicating..." in response. Returns: confirmed list + remaining count + deduplicating count. **C-8**: Never confirm intents not yet processed by J-1. Unit test: 15 pending (12 complete, 3 pending dedup) → max 10 from complete set confirmed. |
| T-012 | [ ] Implement intent dedup job (J-1) | M2 | AI | T-008, T-032 | Background job: `IntentDedupJobHandler`. Enqueued by `IntentStore.detect()` after returning intents. Embeds intent `what` via Gemini, cosine >0.9 with pending intents → merge (keep higher confidence). **C-8**: Sets `dedup_status='complete'` on processed intents (both merged survivors and kept originals) after dedup check. Emits SSE `intent_merged` event when merge occurs. Unit test: two similar intents → merged; dedup_status='complete' set on survivor. |
| T-013 | [ ] Implement stale intent expiry (J-2) | M2 | DB | T-001 | pg_cron SQL function `fn_expire_stale_intents()`: `UPDATE work_intents SET status='rejected' WHERE status='detected' AND created_at < now() - interval '1 hour'`. Scheduled every 15 min. Added in migration 038. |
| T-014 | [ ] Create Intent API router | M2 | BE | T-008, T-010, T-011 | Endpoints: `POST /detect`, `POST /{id}/confirm`, `POST /{id}/reject`, `POST /{id}/edit`, `POST /confirm-all`. Pydantic v2 schemas. Auth required. |
| T-015 | [ ] Integration tests for Intent API | M2 | QA | T-014 | 10+ test cases: detect from chat, detect from note, confirm, reject, edit+rescore, confirmAll cap, chat-priority window, stale expiry. |

### Phase 1c: Agent Loop Upgrade

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-016 | [ ] Refactor PilotSpaceAgent pipeline | M1 | AI | T-008 | Replace single-shot `agent.query()` with pipeline: recall → analyze → detect intents → present → (await confirmation) → select skill → execute → save → respond. Each step emits SSE event. |
| T-017 | [ ] Add SSE event types for intent lifecycle | M1 | AI | T-016 | New events: `intent_detected` (with intent data), `intent_confirmed`, `intent_executing` (with skill name), `intent_completed` (with artifacts). Wire into existing SSE stream. |
| T-018 | [ ] Implement event-driven resume | M1 | AI | T-016 | FR-084: Agent loop subscribes to approval/confirmation events. Resumes blocked work within 5s. Test: confirm intent → skill starts within 5s. |
| T-019 | [ ] Integration test: full Sprint 1 pipeline | M1 | QA | T-016, T-017, T-018 | E2E: send chat message → intent detected (SSE) → confirm via API → skill selection occurs → SSE events correct. |

---

## Sprint 2: Execution + Knowledge — Skill Fleet + Memory Engine (M3 + M4)

### Phase 2a: Database + Domain

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-020 | [ ] Create migration 039: embedding dimension 1536→768 | M4 | DB | Sprint 1 gate | ALTER `embeddings.embedding` to vector(768). Backup 1536 data in `embedding_1536_backup` column. Re-embed existing rows with Gemini. Reversible: rollback restores from backup column. Migration test passes. |
| T-021 | [ ] Create migration 039: `memory_entries` table | M4 | DB | T-020 | UUID PK, workspace_id (RLS), content text, embedding vector(768), keywords tsvector, source_type enum (intent/skill_outcome/user_feedback/constitution), source_id UUID, pinned boolean, created_at, expires_at. HNSW index on embedding. GIN index on keywords. |
| T-022 | [ ] Create migration 039: `constitution_rules` table | M4 | DB | T-021 | UUID PK, workspace_id (RLS), content text, severity enum (MUST/SHOULD/MAY), version integer, source_block_id UUID, active boolean, created_at. Index on (workspace_id, version). |
| T-023 | [ ] Create migration 039: `memory_dlq` table | M4 | DB | T-021 | UUID PK, workspace_id, payload JSONB, error text, attempts integer (default 0), created_at, next_retry_at timestamp. |
| T-024 | [ ] Create migration 039: `skill_executions` table (full CREATE) | M3 | DB | Sprint 1 gate | **C-1**: Full CREATE TABLE (not ALTER). Columns: UUID PK, intent_id FK → work_intents, skill_name text, approval_status enum (auto_approved/pending_approval/approved/rejected/expired) DEFAULT auto_approved, required_approval_role enum (admin/member/null), output JSONB, created_at, updated_at. RLS on workspace_id via join to work_intents. No prior `skill_executions` table exists — no backfill needed. |
| T-025 | [ ] Create MemoryEntry domain entity | M4 | BE | T-021 | With embedding field, keyword extraction from content, TTL support, pinned flag. |
| T-026 | [ ] Create ConstitutionRule domain entity | M4 | BE | T-022 | With RFC 2119 severity parsing, version tracking, active flag. |
| T-027 | [ ] Create MemoryEntryRepository | M4 | BE | T-025 | Hybrid search: 0.7 * cosine_similarity(embedding) + 0.3 * ts_rank(keywords). RLS enforced. <200ms at 1000 entries. |
| T-028 | [ ] Create ConstitutionRuleRepository | M4 | BE | T-026 | CRUD + version-gated queries (`get_rules_at_version`, `get_latest_version`). |
| T-029 | [ ] Unit tests for M4 domain entities | M4 | QA | T-025, T-026 | Entity creation, validation, keyword extraction, severity parsing. >80% coverage. |

### Phase 2b: Memory Engine Service

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-030 | [ ] Create MemorySearchService | M4 | BE | T-027 | `search(query, workspace_id, limit=5)` → embed query with Gemini → hybrid fusion → return results. <200ms SLA. |
| T-031 | [ ] Create MemorySaveService | M4 | BE | T-027, T-023 | `save(entry)` → persist content + keywords synchronously (keyword search works immediately) → enqueue J-3 (memory embedding) to `ai_normal` queue. Callers get MemoryEntry back instantly. Embedding arrives async via worker. On embedding failure after 3 retries → DLQ (FR-112). |
| T-032 | [ ] Switch embedding provider to Gemini | M4 | AI | T-020 | Update provider config: `gemini-embedding-001` (768-dim). Update embedding model in `embedding.py`. Integration test with real Gemini API. |
| T-033 | [ ] Create ConstitutionIngestService | M4 | BE | T-028 | `ingest(rules)` → parse RFC 2119 severity → version bump → keyword index (sync, <10s) → enqueue J-4 (constitution vector indexing) to `ai_normal` queue → return `{ version }`. Vector index completes async (<30s typical). Version gate (T-034) handles consistency. |
| T-034 | [ ] Implement constitution version gate | M4 | BE | T-033 | `getConstitutionVersion(workspace_id)`. Skill pre-check: if current_version > last_indexed_version, block up to 60s polling every 2s. After 60s → proceed keyword-only. |
| T-035 | [ ] Create DLQ reconciliation job (J-5) | M4 | BE | T-031 | `MemoryDLQJobHandler`: retry DLQ entries (max 6 total attempts, exponential backoff). Detect orphaned skill executions (execution exists, no memory entry, >1h old) → log warning. pg_cron function `fn_enqueue_memory_dlq_reconciliation()` triggers hourly by enqueuing to `ai_normal`. Added in migration 039. |
| T-036 | [ ] Create Memory API router | M4 | BE | T-030, T-033 | `POST /api/v1/ai/memory/search`, `GET /api/v1/ai/memory/constitution/version`. Auth required. |
| T-037 | [ ] Load test: memory search at 1000 entries | M4 | QA | T-030 | Seed 1000 memory entries. 10 concurrent searches. p95 <200ms. |

### Phase 2c: Skill Fleet Upgrade

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-038 | [ ] Create SKILL.md: generate-code | M3 | AI | T-024 | YAML frontmatter + workflow. Tools: `write_to_note`, `insert_block`, `replace_content`. Approval: suggest. Integration test: produces valid TipTap blocks. |
| T-039 | [ ] Create SKILL.md: write-tests | M3 | AI | T-024 | Tools: `write_to_note`, `insert_block`, `search_note_content`. Approval: suggest. |
| T-040 | [ ] Create SKILL.md: generate-migration | M3 | AI | T-024 | Tools: `write_to_note`, `insert_block`, `ask_user`. Approval: **require**. |
| T-041 | [ ] Create SKILL.md: review-code | M3 | AI | T-024 | Model: Opus. Tools: `write_to_note`, `insert_block`, `get_issue`, `search_note_content`. Approval: auto. |
| T-042 | [ ] Create SKILL.md: review-architecture | M3 | AI | T-024 | Model: Opus. Tools: `write_to_note`, `create_pm_block`, `get_project`, `search_notes`. Approval: auto. |
| T-043 | [ ] Create SKILL.md: scan-security | M3 | AI | T-024 | Tools: `write_to_note`, `insert_block`, `search_note_content`. Approval: auto. |
| T-044 | [ ] Implement skill executor with approval hold | M3 | AI | T-024, T-038 | Destructive skills → output stored in `skill_executions` with `pending_approval`. Non-destructive → `auto_approved` + persist immediately. |
| T-045 | [ ] Implement TipTap output validation | M3 | AI | T-044 | FR-114: Validate skill output JSON against TipTap block schema. Invalid → intent "failed", chat error. Unit test: valid output passes, malformed rejected. |
| T-046 | [ ] Create Approval API router | M3 | BE | T-044 | `POST /api/v1/ai/approvals/{id}/approve` → persist output to note, `POST .../reject` → discard output, intent "rejected". Auth: workspace member. 24h expiry for pending. |
| T-047 | [ ] Implement skill concurrency manager | M3 | AI | T-044 | Semaphore per workspace (Redis or asyncio). Max 5 concurrent. 6th → queued with "Waiting for slot" SSE event. Configurable via workspace settings. |
| T-048 | [ ] Wire M4 recall into M1 agent loop | M1+M4 | AI | T-030, T-016 | Agent loop `recall` step calls MemorySearchService. Top-5 results injected as context for LLM analysis. |
| T-049 | [ ] Wire M3 execution into M1 agent loop | M1+M3 | AI | T-044, T-016 | Agent loop `execute` step calls skill executor. SSE events for progress. Approval hold for destructive. |
| T-050 | [ ] Wire M4 save into M1 agent loop | M1+M4 | AI | T-031, T-016 | Agent loop `save` step calls MemorySaveService after skill completion. Saves: intent summary, skill name, outcome, any user feedback. |
| T-051 | [ ] Integration tests for Sprint 2 | M3+M4 | QA | T-046, T-048, T-049, T-050 | Full pipeline: chat → intent → confirm → recall memory → skill execute → approval hold (destructive) → approve → persist → save memory. 5+ E2E scenarios. |

### Phase 2d: Background Jobs + Worker

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-067 | [ ] Create MemoryEmbeddingJobHandler (J-3 + J-4) | M4 | AI | T-032 | Handles both `memory_embedding` task_type. Loads entry by ID from `memory_entries` or `constitution_rules` (determined by `table` field in payload). Embeds via Gemini 768-dim. Updates row. For constitution: sets `indexed_version`. Unit test with mock Gemini. |
| T-068 | [ ] Create MemoryWorker | M4 | AI | T-012, T-067, T-035 | Single worker polling `ai_normal` queue. Routes by `task_type`: `intent_dedup` → IntentDedupJobHandler, `memory_embedding` → MemoryEmbeddingJobHandler, `memory_dlq_reconciliation` → MemoryDLQJobHandler. Follows DigestWorker pattern: poll → process → ack/nack/dead-letter. Sleeps 2s on empty queue. |
| T-069 | [ ] Wire MemoryWorker in main.py lifespan | M4 | BE | T-068 | `asyncio.create_task(memory_worker.start())` at startup. `memory_worker.stop()` + `task.cancel()` at shutdown. Alongside existing DigestWorker. |
| T-070 | [ ] Create approval expiry pg_cron function (J-6) | M3 | DB | T-024 | SQL function `fn_expire_pending_approvals()`: `UPDATE skill_executions SET approval_status='expired' WHERE approval_status='pending_approval' AND created_at < now() - interval '24 hours'`. Scheduled hourly. Added in migration 039. |
| T-071 | [ ] Integration tests for background jobs | M2+M4 | QA | T-068, T-069 | Test J-1: detect similar intents → dedup merges. Test J-3: save memory → embedding appears within 30s. Test J-5: DLQ entry retried and recovered. Test J-2: stale intent expires after 1h. |

---

## Sprint 3: UX — Chat Engine Upgrade (M7)

### Phase 3a: Chat Message Types

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-052 | [ ] Create IntentCard component | M7 | FE | Sprint 2 gate | Renders: what, why, confidence bar (color-coded: green >80%, yellow 70-80%, red <70%), [Confirm] [Edit] [Dismiss] buttons. Handles SSE `intent_detected` event. Accessible (ARIA labels, keyboard nav). |
| T-053 | [ ] Create SkillProgressCard component | M7 | FE | T-052 | Renders: intent summary, skill name, animated status (executing→completed/failed), artifact links. Handles SSE `intent_executing` + `intent_completed` events. |
| T-054 | [ ] Create ApprovalCard component | M7 | FE | T-053 | For destructive skills: TipTap block preview (read-only), [Approve] [Reject] buttons. Calls approval API (T-046). Shows expiry countdown (24h). Loading states. Error handling. |
| T-055 | [ ] Create ConversationBlock component | M7 | FE | T-052 | Threaded Q&A: AI question + human reply input. 5s processing SLA indicator. FR-066-068. |
| T-056 | [ ] Create polymorphic message renderer | M7 | FE | T-052, T-053, T-054, T-055 | Route message type → correct component: text, intent_card, skill_progress, approval, conversation. Default: text. |

### Phase 3b: Chat Interaction Model

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-057 | [ ] SSE event handlers for intent lifecycle | M7 | FE | T-056 | Handle all intent SSE events → update ChatHistoryStore. Optimistic UI for confirm/reject actions. |
| T-058 | [ ] Wire ApprovalCard → ApprovalStore → API | M7 | FE | T-054 | Approve → POST approve API → update card to "approved" state. Reject → POST reject API → update card. Error toast on failure. |
| T-059 | [ ] Create ConfirmAll UI | M7 | FE | T-057 | Button in chat header when pending intents >0. Shows count badge. Calls confirmAll API (max 10). Shows "N confirmed, M remaining" result. |
| T-060 | [ ] Create queue depth indicator | M7 | FE | T-057 | When >5 skills running, show "N skills queued, M running" bar in chat. Updates live via SSE. |
| T-061 | [ ] Skill output preview in chat | M7 | FE | T-054 | For `suggest` approval: render TipTap blocks read-only in chat. [Approve] → write to note via API. [Revise] → new intent cycle. |

### Phase 3c: Polish + Integration

| ID | Task | Module | Layer | Deps | Acceptance Criteria |
|----|------|--------|-------|------|---------------------|
| T-062 | [ ] Chat session rehydration | M7 | FE | T-057 | On page refresh: fetch active intents + pending approvals from API → render correct card states. No flash of empty state. |
| T-063 | [ ] Ghost text documentation | M7 | FE | — | Add note to GhostText component README: memory-unaware by design, deferred to Feature 016. |
| T-064 | [ ] Unit tests for chat components | M7 | QA | T-056, T-059, T-060 | IntentCard, SkillProgressCard, ApprovalCard, ConfirmAll, queue indicator. >80% coverage. Storybook stories for each. |
| T-065 | [ ] E2E test: full user flow | M7 | QA | T-062 | Type command → intent card → confirm → skill progress → approve → note updated. Verify with Playwright. |
| T-066 | [ ] Accessibility audit | M7 | QA | T-064 | Lighthouse accessibility >95 for all new components. WCAG 2.2 AA compliance. Focus management for card actions. |

---

## Summary

| Sprint | Tasks | New Tables | New Migrations | New Endpoints | Background Jobs |
|--------|-------|------------|----------------|---------------|-----------------|
| Sprint 1 | T-001 → T-019 (19) | work_intents, intent_artifacts | 038 | 5 intent API endpoints | J-2 (pg_cron: stale intent expiry) |
| Sprint 2 | T-020 → T-071 (37) | memory_entries, constitution_rules, memory_dlq, skill_executions (full CREATE — C-1) + alter embeddings | 039 | 3 memory API + 2 approval API endpoints | J-1 (intent dedup), J-3 (memory embedding), J-4 (constitution indexing), J-5 (DLQ reconciliation), J-6 (approval expiry) + MemoryWorker |
| Sprint 3 | T-052 → T-066 (15) | — | — | — (frontend only) | — |
| **Total** | **71 tasks** | **5 new tables + 2 altered** | **2 migrations** | **10 new endpoints** | **6 jobs + 1 worker** |

### Background Jobs Summary

| Job | Type | Owner Module | Trigger |
|-----|------|-------------|---------|
| J-1 Intent dedup | Python (pgmq worker) | IntentStore (M2) | Enqueued by `detect()` |
| J-2 Stale intent expiry | pg_cron SQL | M2 | Every 15 min |
| J-3 Memory embedding | Python (pgmq worker) | MemoryStore (M4) | Enqueued by `save()` |
| J-4 Constitution indexing | Python (pgmq worker) | MemoryStore (M4) | Enqueued by `ingest_constitution()` |
| J-5 DLQ reconciliation | Python (pgmq worker) | MemoryStore (M4) | pg_cron → enqueue hourly |
| J-6 Approval expiry | pg_cron SQL | SkillRunner (M3) | Every 1 hour |

### Dependency Graph (Critical Path)

```
T-001 → T-003 → T-005 → T-008 → T-014 → T-016 → Sprint 1 Gate
                                    ↓                     ↓
                              T-012 (J-1 dedup)    T-013 (J-2 pg_cron)
                                                         ↓
T-020 → T-021 → T-025 → T-027 → T-030 → T-048 ─┐
                                                   │
T-032 → T-067 (J-3+J-4) → T-068 (worker) → T-069 │
                                                   ├→ T-051 → T-071 → Sprint 2 Gate
T-024 → T-038 → T-044 → T-045 → T-046 → T-049 ─┘                        ↓
         T-070 (J-6 pg_cron) ─────────────────────┘
                                                    T-052 → T-056 → T-057 → T-062 → T-065
```
