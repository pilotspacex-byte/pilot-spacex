# Data Model: AI Workforce Platform

**Feature**: 015 — AI Workforce Platform
**Spec**: `specs/015-ai-workforce-platform/spec.md`
**Plan**: `specs/015-ai-workforce-platform/plan.md`

---

## New Entities

### WorkIntent

**Purpose**: System primitive — represents a unit of work detected from user input (chat or note).
**Source**: FR-010 to FR-019, US-2, US-3
**Phase**: A

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | Multi-tenant isolation |
| note_id | UUID | FK → notes.id, NULL | Source note (nullable if chat-only) |
| what | TEXT | NOT NULL | What needs to happen |
| why | TEXT | NOT NULL | Business reason / requirement source |
| constraints | JSONB | NOT NULL, default '[]' | [{rule, source, severity}] |
| acceptance | JSONB | NOT NULL, default '[]' | [{description, verifiable, verified}] |
| status | VARCHAR(20) | NOT NULL, default 'detected' | Enum: detected, confirmed, executing, review, accepted, rejected |
| owner | VARCHAR(100) | NOT NULL, default 'human' | 'human' or skill name |
| parent_intent_id | UUID | FK → work_intents.id, NULL | For sub-intents / revision cycles |
| source_block_id | VARCHAR(100) | NULL | TipTap block UUID (if from note) |
| source_message | TEXT | NULL | Chat message text (if from chat) |
| artifacts | JSONB | NOT NULL, default '[]' | [{artifact_id, type, content_ref}] |
| confidence | DECIMAL(3,2) | NOT NULL, CHECK 0.0-1.0 | Detection confidence |
| skill_name | VARCHAR(100) | NULL | Assigned skill (set on execution) |
| feedback | TEXT | NULL | User feedback on rejection |
| created_by | UUID | FK → users.id, NOT NULL | User who triggered detection |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |
| updated_at | TIMESTAMP WITH TZ | NOT NULL, auto-update | |
| is_deleted | BOOLEAN | NOT NULL, default FALSE | Soft delete |

**Relationships**:
- Belongs to Workspace (N:1, RLS)
- Belongs to Note (N:1, optional)
- Belongs to User via created_by (N:1)
- Has many IntentArtifacts (1:N)
- Self-referential: parent_intent_id for revision chains

**Indexes**:
- `ix_work_intents_workspace_status` (workspace_id, status) — list by status
- `ix_work_intents_workspace_created` (workspace_id, created_at DESC) — recent intents
- `ix_work_intents_note_id` (note_id) — intents per note
- `ix_work_intents_parent_id` (parent_intent_id) — revision chains
- `ix_work_intents_created_by` (created_by) — user's intents

**RLS Policy**:
```sql
CREATE POLICY work_intents_workspace_isolation ON work_intents
  USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));
```

---

### NoteVersion

**Purpose**: Point-in-time snapshot of note content for version history, diff, and restore.
**Source**: FR-034 to FR-042, US-14
**Phase**: A (schema), B (features)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| note_id | UUID | FK → notes.id, NOT NULL | |
| version_number | INTEGER | NOT NULL | Auto-increment per note |
| content | JSONB | NOT NULL | Full TipTap document snapshot |
| yjs_state_vector | BYTEA | NULL | Yjs document state vector (binary) |
| author_id | UUID | FK → users.id, NULL | NULL for auto-versions |
| source | VARCHAR(20) | NOT NULL | Enum: manual, auto, ai_before, ai_after, intent |
| label | VARCHAR(500) | NULL | e.g., "Before AI: create-spec", "Intent #3: auth spec" |
| is_pinned | BOOLEAN | NOT NULL, default FALSE | Exempt from retention cleanup |
| ai_change_digest | TEXT | NULL | Cached AI-generated summary |
| ai_impact_analysis | JSONB | NULL | Cached [{entity_type, entity_id, change_type}] |
| word_count | INTEGER | NOT NULL, default 0 | Snapshot word count |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |

**Relationships**:
- Belongs to Note (N:1, CASCADE delete)
- Belongs to Workspace (N:1, RLS)
- Belongs to User via author_id (N:1, optional)

**Indexes**:
- `ix_note_versions_note_created` (note_id, created_at DESC) — version timeline
- `ix_note_versions_note_number` (note_id, version_number DESC) — version lookup
- `ix_note_versions_workspace` (workspace_id) — RLS optimization
- `ix_note_versions_source` (note_id, source) — filter by source type

**RLS Policy**: Same pattern as WorkIntent — workspace member access.

---

### SkillExecution

**Purpose**: Records each SDK subagent execution for audit, cost tracking, and debugging.
**Source**: FR-085 to FR-090, US-22
**Phase**: B

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| intent_id | UUID | FK → work_intents.id, NOT NULL | |
| skill_name | VARCHAR(100) | NOT NULL | |
| model | VARCHAR(50) | NOT NULL | e.g., 'sonnet', 'opus', 'haiku', 'flash' |
| token_budget | INTEGER | NOT NULL | Max tokens allocated |
| tokens_used | INTEGER | NOT NULL, default 0 | Actual tokens consumed |
| timeout_seconds | INTEGER | NOT NULL | Max execution time |
| started_at | TIMESTAMP WITH TZ | NOT NULL | |
| completed_at | TIMESTAMP WITH TZ | NULL | |
| duration_ms | INTEGER | NULL | Computed from started/completed |
| status | VARCHAR(20) | NOT NULL, default 'running' | Enum: running, completed, failed, timeout, cancelled |
| approval_level | VARCHAR(10) | NOT NULL | Enum: auto, suggest, require |
| output_target | VARCHAR(20) | NOT NULL | 'note' or 'new_note' |
| output_note_id | UUID | FK → notes.id, NULL | Target note for output |
| error_message | TEXT | NULL | Error detail on failure |
| tool_calls | JSONB | NOT NULL, default '[]' | [{tool_name, input, output, duration_ms}] |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |

**Relationships**:
- Belongs to Workspace (N:1, RLS)
- Belongs to WorkIntent (N:1)
- Belongs to Note via output_note_id (N:1, optional)

**Indexes**:
- `ix_skill_executions_workspace_status` (workspace_id, status) — active executions
- `ix_skill_executions_intent` (intent_id) — executions per intent
- `ix_skill_executions_workspace_skill` (workspace_id, skill_name) — per-skill analytics
- `ix_skill_executions_workspace_created` (workspace_id, created_at DESC) — audit trail

---

### MemoryEntry

**Purpose**: Persistent workspace knowledge for the memory engine (AD-11).
**Source**: FR-100 to FR-104, US-23
**Phase**: B

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| content | TEXT | NOT NULL | Textual content for keyword search |
| embedding | VECTOR(768) | NOT NULL | pgvector embedding (Gemini gemini-embedding-001) |
| keywords | TSVECTOR | GENERATED ALWAYS | PostgreSQL FTS from content |
| source_type | VARCHAR(20) | NOT NULL | Enum: intent, skill_outcome, user_feedback, constitution |
| source_id | UUID | NULL | FK to source entity |
| metadata | JSONB | NOT NULL, default '{}' | Structured context (skill_name, intent_id, etc.) |
| is_pinned | BOOLEAN | NOT NULL, default FALSE | Exempt from cleanup |
| expires_at | TIMESTAMP WITH TZ | NULL | Optional TTL |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |

**Indexes**:
- `ix_memory_entries_embedding` HNSW (embedding vector_cosine_ops) — vector similarity search
- `ix_memory_entries_keywords` GIN (keywords) — full-text search
- `ix_memory_entries_workspace_created` (workspace_id, created_at DESC) — recent entries
- `ix_memory_entries_workspace_source` (workspace_id, source_type) — filter by source

**RLS Policy**: Workspace member access only.

**Migration Note**: Existing `embeddings` table uses `VECTOR(1536)` (text-embedding-3-large). Decision C-4: standardize to 768-dim (Gemini). Migration `042_memory_engine` creates new `memory_entries` table with `VECTOR(768)`. A follow-up migration should re-embed existing `embeddings` rows with Gemini and update the vector column to `VECTOR(768)`. Until migration completes, both dimensions coexist with separate HNSW indexes.

---

### IntentArtifact

**Purpose**: Output of skill execution linked to an intent.
**Source**: US-10, US-22
**Phase**: B

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| intent_id | UUID | FK → work_intents.id, NOT NULL | |
| skill_name | VARCHAR(100) | NOT NULL | |
| artifact_type | VARCHAR(20) | NOT NULL | spec, plan, task, issue, code, test, migration, doc, deployment |
| note_id | UUID | FK → notes.id, NULL | Target note |
| block_ids | JSONB | NOT NULL, default '[]' | Block UUIDs in target note |
| new_note_id | UUID | FK → notes.id, NULL | If output created new note |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |

**Indexes**:
- `ix_intent_artifacts_intent` (intent_id) — artifacts per intent
- `ix_intent_artifacts_workspace` (workspace_id) — RLS

---

### PMBlockInsight

**Purpose**: AI-generated analysis for PM blocks (sprint board, dependency map, capacity).
**Source**: FR-048 to FR-060, US-11, US-12
**Phase**: B

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| note_id | UUID | FK → notes.id, NOT NULL | |
| block_id | VARCHAR(100) | NOT NULL | TipTap PM block UUID |
| insight_type | VARCHAR(50) | NOT NULL | velocity_risk, dependency_delay, capacity_overload, etc. |
| severity | VARCHAR(10) | NOT NULL | green, yellow, red |
| title | VARCHAR(200) | NOT NULL | Badge text |
| detail | TEXT | NOT NULL | Tooltip content |
| referenced_issue_ids | JSONB | NOT NULL, default '[]' | [UUID, ...] |
| suggested_actions | JSONB | NOT NULL, default '[]' | [{action, reason}] |
| is_dismissed | BOOLEAN | NOT NULL, default FALSE | |
| computed_at | TIMESTAMP WITH TZ | NOT NULL | |
| expires_at | TIMESTAMP WITH TZ | NOT NULL | Cache expiry |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |

**Indexes**:
- `ix_pm_insights_note_block` (note_id, block_id) — insights per PM block
- `ix_pm_insights_workspace` (workspace_id) — RLS

---

### ConstitutionRule

**Purpose**: Extracted rules from constitution-tagged note blocks.
**Source**: FR-069 to FR-073, US-16
**Phase**: B

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, NOT NULL, RLS filter | |
| note_id | UUID | FK → notes.id, NOT NULL | Source note |
| block_id | VARCHAR(100) | NOT NULL | Source block UUID |
| rule_text | TEXT | NOT NULL | Extracted rule |
| severity | VARCHAR(10) | NOT NULL | must, should, may (RFC 2119) |
| scope | VARCHAR(200) | NULL | e.g., "backend/src/**", "all endpoints" |
| is_active | BOOLEAN | NOT NULL, default TRUE | |
| extracted_at | TIMESTAMP WITH TZ | NOT NULL | |
| created_at | TIMESTAMP WITH TZ | NOT NULL, default NOW | |
| updated_at | TIMESTAMP WITH TZ | NOT NULL, auto-update | |

**Indexes**:
- `ix_constitution_rules_workspace_active` (workspace_id, is_active) — active rules
- `ix_constitution_rules_note_block` (note_id, block_id) — rules per block

---

## Extended Entities

### GhostTextCacheEntry — Add `expires_at` TTL

**Phase**: A (FR-045-047)

Existing ghost text LRU cache entries gain a TTL field:

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| expires_at | TIMESTAMP | NOT NULL | `Date.now() + 5 * 60 * 1000` (5-min TTL) |

**Note**: This is a frontend-only in-memory cache (not a database table). The `expires_at` is added to the existing `GhostTextStore.ts` LRU cache entry interface. On cache hit, check `Date.now() > entry.expires_at` → evict and fetch fresh suggestion.

---

### Issue — Add `estimate_hours`

**Phase**: C (FR-061)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| estimate_hours | DECIMAL(6,1) | NULL | Effort estimate in hours |

### WorkspaceMember — Add `weekly_available_hours`

**Phase**: C (FR-062)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| weekly_available_hours | DECIMAL(5,1) | NOT NULL, default 40.0 | Available hours per week |

### Note content JSONB — Block `owner` attribute

**Phase**: A (FR-001)

No schema change — the `owner` attribute is added to TipTap block nodes at the application level. Existing blocks without `owner` default to `"human"` at runtime (FR-009).

```json
{
  "type": "paragraph",
  "attrs": {
    "id": "block-uuid",
    "owner": "human"
  },
  "content": [...]
}
```

---

## Entity Relationship Diagram (Text)

```
Workspace ─┬── WorkIntent ──── IntentArtifact
            │       │
            │       └── SkillExecution
            │
            ├── Note ──── NoteVersion
            │     │
            │     ├── PMBlockInsight
            │     └── ConstitutionRule
            │
            ├── MemoryEntry
            │
            ├── Issue (+ estimate_hours)
            └── WorkspaceMember (+ weekly_available_hours)
```

---

## Transient Runtime Objects

These objects exist only in memory (not persisted to database). They are documented here for architectural completeness.

### AISkillPresence

**Purpose**: Represents an AI skill actively editing a note via Yjs CRDT awareness protocol.
**Source**: FR-027, FR-031-033, US-13
**Phase**: B

| Field | Type | Notes |
|-------|------|-------|
| type | string | Always `"skill"` |
| skill_name | string | e.g., `"create-spec"` |
| intent_id | UUID | The intent being executed |
| intent_summary | string | Short description of intent |
| note_id | UUID | Note being edited |
| joined_at | timestamp | When skill announced presence |

**Storage**: Yjs awareness protocol (ephemeral, broadcast via Supabase Realtime channel). Announced within 2s of skill start, removed within 5s of completion (FR-033).

---

### CollaborativeSession

**Purpose**: Tracks active Yjs document connections per note for presence display.
**Source**: FR-024-029, US-4
**Phase**: A

| Field | Type | Notes |
|-------|------|-------|
| note_id | UUID | The collaborative document |
| client_id | number | Yjs awareness client ID |
| user_id | UUID | Authenticated user |
| cursor_position | object | `{from, to}` selection range |
| color | string | Assigned presence color |
| name | string | Display name |

**Storage**: Yjs awareness state (ephemeral, per-connection). Cleaned up automatically on WebSocket disconnect.
