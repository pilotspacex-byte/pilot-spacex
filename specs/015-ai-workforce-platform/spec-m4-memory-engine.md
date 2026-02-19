# M4 — Memory Engine

**Feature**: 015 AI Workforce Core
**Module**: M4 — Memory Engine
**Status**: Implemented (Sprint 2 Phase 2a + 2b complete)
**Depends on**: None (standalone storage + search)
**Consumed by**: M1 (Agent Loop — recall step + save step), M3 (constitution version gate)

---

## Purpose

Persistent workspace knowledge store. Hybrid vector + keyword search for context recall. Constitution rules extracted from note blocks provide workspace-level constraints for all skills.

---

## Codebase Anchors

- `backend/src/pilot_space/domain/memory_entry.py`
- `backend/src/pilot_space/domain/constitution_rule.py`
- `backend/src/pilot_space/infrastructure/database/repositories/memory_repository.py`
- `backend/src/pilot_space/infrastructure/database/repositories/constitution_repository.py`
- `backend/src/pilot_space/application/services/memory/`
- `backend/src/pilot_space/ai/workers/memory_worker.py`
- `backend/alembic/versions/040_add_memory_engine.py`

---

## MemoryEntry Entity

```typescript
interface MemoryEntry {
  content: string;
  embedding: Vector768;           // pgvector cosine similarity (Gemini gemini-embedding-001)
  keywords: string[];             // PostgreSQL FTS (GIN/tsvector)
  source_type: 'intent' | 'skill_outcome' | 'user_feedback' | 'constitution';
  workspace_id: UUID;             // RLS-enforced
  pinned: boolean;
  expires_at: datetime | null;
}
```

---

## Database

**Migration**: `040_add_memory_engine.py`

**Tables**:

`memory_entries`
- UUID PK, workspace_id (RLS), content text, embedding vector(768), keywords tsvector, source_type enum, source_id UUID, pinned boolean, created_at, expires_at
- HNSW index on embedding (cosine)
- GIN index on keywords (tsvector)

`constitution_rules`
- UUID PK, workspace_id (RLS), content text, severity enum (MUST/SHOULD/MAY), version integer, source_block_id UUID, active boolean, created_at
- Index on (workspace_id, version)

`memory_dlq`
- UUID PK, workspace_id, payload JSONB, error text, attempts integer DEFAULT 0, created_at, next_retry_at

**Embedding dimension**: 768 (Gemini `gemini-embedding-001`). Migration 040 alters existing `embeddings` table from 1536-dim (OpenAI) to 768-dim. Reversible: 1536 data kept in `embedding_1536_backup` column.

---

## Hybrid Search

```
score = 0.7 × cosine_similarity(query_embedding, entry_embedding)
      + 0.3 × ts_rank(keywords, to_tsquery(query))
```

Returns top-N results ordered by fusion score. <200ms SLA at 1000+ entries.

---

## Services

### MemorySearchService

```python
search(query: str, workspace_id: UUID, limit: int = 5) -> list[MemoryEntry]
```

Flow: embed query via Gemini → hybrid fusion query → return results.

### MemorySaveService

```python
save(entry: MemoryEntry) -> MemoryEntry
```

Flow: persist content + keywords synchronously (keyword search available immediately) → enqueue J-3 (memory embedding) to `ai_normal` queue → return entry. Embedding arrives async via MemoryWorker. On 3 consecutive embedding failures → DLQ (FR-112).

### ConstitutionIngestService

```python
ingest(rules: list[ConstitutionRule]) -> dict[str, int]  # {"version": N}
```

Flow: parse RFC 2119 severity → version bump → keyword index sync (<10s) → enqueue J-4 (vector indexing) → return `{ version }`.

### Constitution Version Gate

```python
get_constitution_version(workspace_id: UUID) -> int
```

Skill pre-check: if `current_version > last_indexed_version`, block up to 60s polling every 2s. After 60s timeout → proceed keyword-only. Guarantees skills never execute against stale MUST-level constitution rules within the 60s window (FR-073).

---

## API Endpoints

`POST /api/v1/ai/memory/search`
`GET  /api/v1/ai/memory/constitution/version`

---

## Module Interface

```python
search(query: str, workspace_id: UUID, limit: int = 5) -> list[MemoryEntry]
save(entry: MemoryEntry) -> MemoryEntry
delete(entry_id: UUID) -> None
ingest_constitution(rules: list[ConstitutionRule]) -> dict[str, int]
get_constitution_version(workspace_id: UUID) -> int
```

---

## Background Jobs

### J-3 — Memory Embedding (pgmq worker)

**Handler**: `MemoryEmbeddingJobHandler`
**Queue**: `ai_normal`
**Trigger**: Enqueued by `MemorySaveService.save()` after persisting content
**Logic**: Load entry from `memory_entries` → embed content via Gemini 768-dim → update `embedding` column

### J-4 — Constitution Vector Indexing (pgmq worker)

**Handler**: `MemoryEmbeddingJobHandler` (same handler, `table` field distinguishes)
**Queue**: `ai_normal`
**Trigger**: Enqueued by `ConstitutionIngestService.ingest()` after keyword index
**Logic**: Load rule from `constitution_rules` → embed → update `embedding` + set `indexed_version`

### J-5 — DLQ Reconciliation (pgmq + pg_cron)

**Handler**: `MemoryDLQJobHandler`
**Schedule**: pg_cron hourly → enqueues to `ai_normal`
**Logic**: Retry DLQ entries (max 6 total attempts, exponential backoff 1-4-16-64-256-1024s). Detect orphaned skill executions (execution exists, no memory entry, >1h old) → log warning.

---

## MemoryWorker

**File**: `backend/src/pilot_space/ai/workers/memory_worker.py`

Single worker polling `ai_normal` queue. Routes by `task_type`:
- `intent_dedup` → IntentDedupJobHandler
- `memory_embedding` → MemoryEmbeddingJobHandler
- `memory_dlq_reconciliation` → MemoryDLQJobHandler

Pattern: poll → process → ack/nack → sleep 2s on empty. Started in `main.py` lifespan alongside DigestWorker.

---

## Constitution Rules (FR-069–073)

- Extracted from note blocks tagged with `constitution` metadata
- RFC 2119 severity: MUST (blocking) / SHOULD (advisory) / MAY (optional)
- Version monotonically increments on each rule change
- Skills check version at execution start
- Keyword propagation <10s, vector indexing <30s typical
- Version gate blocks up to 60s if version ahead of indexed version, then keyword-only fallback

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-101 | Hybrid search: 0.7 vector + 0.3 keyword fusion |
| FR-102 | Persist learnings (intent, skill, outcome, feedback) after each skill execution |
| FR-103 | Search <200ms at 1000+ entries |
| FR-104 | Workspace-scoped (RLS enforced) |
| FR-112 | Memory save failures MUST retry with exponential backoff (3 attempts). After 3 failures → dead-letter queue. Reconciliation job runs hourly. |
| FR-069 | Extract rules from constitution-tagged human blocks |
| FR-070 | Provide rules to skills as constraints via memory |
| FR-071 | Support RFC 2119 severity (MUST/SHOULD/MAY) |
| FR-072 | Warn on unparseable constitution blocks |
| FR-073 | Version gate: block up to 60s if constitution version ahead of indexed; keyword-only after timeout |

---

## Tasks

| ID | Task | Status |
|----|------|--------|
| T-020 | Migration: embedding dimension 1536→768 | Done |
| T-021 | Migration: memory_entries table | Done |
| T-022 | Migration: constitution_rules table | Done |
| T-023 | Migration: memory_dlq table | Done |
| T-025 | MemoryEntry domain entity | Done |
| T-026 | ConstitutionRule domain entity | Done |
| T-027 | MemoryEntryRepository | Done |
| T-028 | ConstitutionRuleRepository | Done |
| T-029 | Unit tests for M4 domain entities | Done |
| T-030 | MemorySearchService | Done |
| T-031 | MemorySaveService | Done |
| T-032 | Switch embedding provider to Gemini | Done |
| T-033 | ConstitutionIngestService | Done |
| T-034 | Constitution version gate | Done |
| T-035 | DLQ reconciliation job (J-5) | Done |
| T-036 | Memory API router | Done |
| T-037 | Load test: memory search at 1000 entries | Pending |
| T-067 | MemoryEmbeddingJobHandler (J-3 + J-4) | Done |
| T-068 | MemoryWorker | Done |
| T-069 | Wire MemoryWorker in main.py lifespan | Done |
| T-071 | Integration tests for background jobs | Pending |

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No search results | LLM proceeds with message-only context |
| Storage full | Oldest non-pinned entries archived, admin notified |
| Embedding API unavailable | Keyword-only fallback; entries queued for embedding |
| Memory save fails after 3 retries | DLQ entry, hourly reconciliation job retries (FR-112) |
| Constitution updated during skill execution | Version gate blocks up to 60s, then keyword-only fallback |
| PII in entries | Workspace admin can delete; entries scoped by RLS |

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Search latency at 1000+ entries | <200ms p95 |
| Memory DLQ recovery rate | >95% within 1 hour |
| Constitution version gate — zero stale MUST-rule violations | 0 violations |
| Embedding migration reversibility | Data preserved, backup column retained |
