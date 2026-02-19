# M2 — Intent Engine

**Feature**: 015 AI Workforce Core
**Module**: M2 — Intent Engine
**Status**: Implemented (Sprint 1 complete)
**Depends on**: None (standalone detection + storage)
**Consumed by**: M1 (Agent Loop), M7 (Chat Engine, via SSE events)

---

## Purpose

Detect, score, and manage `WorkIntent` records from human text. Intents are the atomic unit of work — the system MUST NOT execute skills against unconfirmed intents.

**Primary path**: User types in chat → `extract-intents` → present in chat.
**Secondary path**: User writes in note → 2s debounce → intents detected → present in chat.

---

## Codebase Anchors

- `backend/src/pilot_space/domain/work_intent.py`
- `backend/src/pilot_space/infrastructure/database/repositories/intent_repository.py`
- `backend/src/pilot_space/api/v1/routers/intents.py`
- `backend/alembic/versions/038_add_work_intents.py`

---

## WorkIntent Entity

```typescript
interface WorkIntent {
  id: UUID;
  what: string;                    // What needs to happen
  why: string;                     // Business reason
  constraints: Constraint[];
  acceptance: AcceptanceCriteria[];
  status: 'detected' | 'confirmed' | 'executing' | 'review' | 'accepted' | 'rejected';
  dedup_status: 'pending' | 'complete';  // C-8: ConfirmAll race prevention
  owner: 'human' | SkillName;
  confidence: number;              // 0.0–1.0
  parent_intent_id: UUID | null;
  source_block_id: UUID | null;
}
```

**Status transitions** (enforced in domain entity):
```
detected → confirmed → executing → review → accepted
         ↘ rejected (from any state)
```

---

## Database

**Migration**: `038_add_work_intents.py`

**Tables**:
- `work_intents` — UUID PK, workspace_id (RLS), what, why, constraints (JSONB), acceptance (JSONB), status enum, dedup_status enum DEFAULT 'pending', owner, confidence, parent_intent_id (self-ref FK), source_block_id, timestamps
- `intent_artifacts` — UUID PK, intent_id FK, artifact_type, reference_id, reference_type

**RLS**:
```sql
CREATE POLICY work_intents_workspace_isolation ON work_intents
  USING (workspace_id IN (
    SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
  ));
```

**Indexes**:
- `(workspace_id, status)` — list by status
- `(workspace_id, created_at DESC)` — recent intents
- `(note_id)` — intents per note
- `(parent_intent_id)` — revision chains

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-010 | Extract structured WorkIntents from chat (primary) and note blocks (secondary) |
| FR-011 | Each WorkIntent MUST contain: what, why, constraints, acceptance criteria, confidence (0–1) |
| FR-012 | Trigger on chat receipt (primary) and block stabilization (2s debounce, secondary) |
| FR-013 | Present in chat with [Confirm] [Edit] [Dismiss] |
| FR-014 | Confidence < 70% MUST include clarification question |
| FR-015 | MUST NOT execute intents with status other than "confirmed" |
| FR-016 | Confirm → status "confirmed", eligible for execution |
| FR-017 | Edit → re-score and re-present |
| FR-018 | Reject → dismiss with optional feedback |
| FR-019 | "Confirm All" auto-confirms intents >= 70% |
| FR-113 | ConfirmAll cap: max 10 per invocation; if >10, confirm top-10 by confidence; chat MUST show queue depth |
| FR-020-I | Chat-priority window: chat intents suppress note detection for 3s in same workspace |
| FR-020-II | ConfirmAll dedup guard (C-8): MUST only confirm intents with `dedup_status = 'complete'` |

---

## API Endpoints

`POST /api/v1/ai/intents/detect`
`POST /api/v1/ai/intents/{id}/confirm`
`POST /api/v1/ai/intents/{id}/reject`
`POST /api/v1/ai/intents/{id}/edit`
`POST /api/v1/ai/intents/confirm-all`

---

## Module Interface

```python
detect(text: str, source: Literal['chat', 'note']) -> list[WorkIntent]
confirm(intent_id: UUID) -> WorkIntent
reject(intent_id: UUID, feedback: str | None) -> None
edit(intent_id: UUID, changes: dict) -> WorkIntent
confirm_all(workspace_id: UUID, min_confidence: float = 0.7, max_count: int = 10) -> list[WorkIntent]
```

---

## Background Jobs

### J-1 — Intent Dedup (pgmq worker)

**Handler**: `IntentDedupJobHandler`
**Trigger**: Enqueued by `detect()` after returning intents
**Logic**: Embed intent `what` via Gemini → cosine >0.9 with pending intents → merge (keep higher confidence) → set `dedup_status = 'complete'` on all processed intents

**C-8 guarantee**: `confirmAll` only processes intents with `dedup_status = 'complete'`, preventing confirmation of intents that will be merged/discarded by J-1.

### J-2 — Stale Intent Expiry (pg_cron)

**Function**: `fn_expire_stale_intents()`
**Schedule**: Every 15 min
**Logic**: `UPDATE work_intents SET status='rejected' WHERE status='detected' AND created_at < NOW() - INTERVAL '1 hour'`

---

## Chat-Priority Window (FR-020-I)

Redis key: `intent_lock:{workspace_id}` with 3s TTL.
- Chat detection: sets lock
- Note detection: checks lock before proceeding → if locked, discard note intent

---

## Tasks

| ID | Task | Status |
|----|------|--------|
| T-001 | Migration 038: work_intents table | Done |
| T-002 | Migration 038: intent_artifacts table | Done |
| T-003 | WorkIntent domain entity | Done |
| T-004 | IntentArtifact domain entity | Done |
| T-005 | WorkIntentRepository | Done |
| T-006 | IntentArtifactRepository | Done |
| T-007 | Unit tests for WorkIntent entity | Done |
| T-008 | IntentDetectionService | Done |
| T-009 | Intent detection LLM prompt | Done |
| T-010 | Chat-priority window | Done |
| T-011 | ConfirmAll with cap=10 | Done |
| T-012 | Intent dedup job (J-1) | Done |
| T-013 | Stale intent expiry pg_cron (J-2) | Done |
| T-014 | Intent API router | Done |
| T-015 | Integration tests for Intent API | Done |

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Duplicate intents on re-detection | Deduplicate by semantic similarity (>90% cosine → merge) |
| Chat + note fire simultaneously | Chat-priority 3s window suppresses note detection |
| ConfirmAll with >10 pending | Top-10 by confidence confirmed (only dedup_status=complete), rest stay pending |
| ConfirmAll while dedup job running | Intents with dedup_status=pending show "Deduplicating..." in UI, excluded from batch |
| Confirmed intent's source block deleted | Intent remains, source_block_id marked orphaned |
| Block text too short ("TODO") | No intents below minimum confidence threshold |
| No actionable content | No intents created, natural chat response from LLM |
| Stale queued intent (>1h since detection) | Auto-expire to "rejected" via J-2 |

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Detection accuracy (labeled test set) | >80% |
| Zero unconfirmed executions | 0 in audit log |
| Chat-priority window suppression | Note intents suppressed during 3s chat window |
| ConfirmAll respects cap | Max 10 per invocation |
| ConfirmAll dedup guard | 0 race conditions in audit log |
