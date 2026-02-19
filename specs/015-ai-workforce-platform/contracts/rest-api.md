# API Contracts: AI Workforce Platform

**Feature**: 015 — AI Workforce Platform
**Plan**: `specs/015-ai-workforce-platform/plan.md`

---

## Intent Management (Phase A)

### List Intents: GET /api/v1/{workspace_id}/intents

**Auth**: Bearer (workspace member)
**Source**: US-2, US-3

**Query Parameters**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| status | string | No | One of: detected, confirmed, executing, review, accepted, rejected |
| note_id | UUID | No | Filter by source note |
| limit | integer | No | 1-100, default 20 |
| offset | integer | No | >=0, default 0 |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| items | WorkIntent[] | List of intents |
| total | integer | Total count |
| has_next | boolean | More pages available |

**Errors**: 401 UNAUTHORIZED, 403 FORBIDDEN (not workspace member)

---

### Get Intent: GET /api/v1/{workspace_id}/intents/{intent_id}

**Auth**: Bearer (workspace member)
**Source**: US-3

**Response (200)**: Full WorkIntent object with artifacts.

**Errors**: 401, 403, 404 NOT_FOUND

---

### Update Intent: PATCH /api/v1/{workspace_id}/intents/{intent_id}

**Auth**: Bearer (workspace member)
**Source**: US-3 (edit)

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| what | string | No | 1-2000 chars |
| why | string | No | 1-1000 chars |
| constraints | object[] | No | [{rule, source, severity}] |
| acceptance | object[] | No | [{description, verifiable}] |

**Response (200)**: Updated WorkIntent (re-scored, status reset to 'detected')

**Errors**: 401, 403, 404, 409 CONFLICT (intent already executing)

---

### Confirm Intent: POST /api/v1/{workspace_id}/intents/{intent_id}/confirm

**Auth**: Bearer (workspace member)
**Source**: US-3, FR-016

**Request**: Empty body (or optional `{}`)

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| intent | WorkIntent | Status = 'confirmed' |
| skill_name | string | Selected skill for execution |

**Errors**: 401, 403, 404, 409 (already confirmed or executing)

---

### Reject Intent: POST /api/v1/{workspace_id}/intents/{intent_id}/reject

**Auth**: Bearer (workspace member)
**Source**: US-3, FR-018

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| feedback | string | No | Optional feedback for learning |

**Response (200)**: Updated WorkIntent (status = 'rejected')

**Errors**: 401, 403, 404, 409 (already rejected)

---

### Confirm All Intents: POST /api/v1/{workspace_id}/intents/confirm-all

**Auth**: Bearer (workspace member)
**Source**: FR-019

**Request**: Empty body

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| confirmed_count | integer | Number of intents confirmed (>=70% confidence only) |
| skipped_count | integer | Number skipped (<70% confidence) |
| confirmed_ids | UUID[] | IDs of confirmed intents |

**Errors**: 401, 403

---

## Version History (Phase A schema, Phase B features)

### List Versions: GET /api/v1/{workspace_id}/notes/{note_id}/versions

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-038

**Query Parameters**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| source | string | No | Filter: manual, auto, ai_before, ai_after, intent |
| limit | integer | No | 1-100, default 50 |
| offset | integer | No | >=0, default 0 |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| items | NoteVersionSummary[] | id, version_number, source, label, author_id, word_count, created_at, is_pinned |
| total | integer | Total versions |

---

### Create Manual Version: POST /api/v1/{workspace_id}/notes/{note_id}/versions

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-035

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| label | string | No | 1-500 chars |

**Response (201)**: NoteVersionSummary

---

### Get Version: GET /api/v1/{workspace_id}/versions/{version_id}

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-038

**Response (200)**: Full NoteVersion with content

---

### Diff Versions: GET /api/v1/{workspace_id}/versions/{version_id}/diff

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-038

**Query Parameters**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| compare_to | UUID | No | Other version ID (default: previous version) |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| base_version_id | UUID | Older version |
| target_version_id | UUID | Newer version |
| additions | integer | Blocks added |
| deletions | integer | Blocks removed |
| modifications | integer | Blocks changed |
| diff_blocks | DiffBlock[] | [{block_id, type: 'added'|'removed'|'modified', old_content?, new_content?}] |

---

### Restore Version: POST /api/v1/{workspace_id}/versions/{version_id}/restore

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-039

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| restored_version | NoteVersionSummary | The restored version entry (new version created) |
| note | NoteResponse | Updated note |

---

### Get AI Digest: GET /api/v1/{workspace_id}/versions/{version_id}/digest

**Auth**: Bearer (workspace member)
**Source**: US-14, FR-040

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| digest | string | Natural language summary of changes |
| impact_analysis | ImpactEntry[] | [{entity_type, entity_id, change_type}] |
| cached | boolean | Whether result was from cache |

**Errors**: 404, 503 (digest unavailable — LLM timeout)

---

## Memory Engine (Phase B)

### Search Memory: POST /api/v1/{workspace_id}/memory/search

**Auth**: Bearer (workspace member)
**Rate Limit**: 30 requests/minute per user (vector search is compute-intensive)
**Source**: US-23, FR-101

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| query | string | Yes | 1-1000 chars |
| source_type | string | No | Filter: intent, skill_outcome, user_feedback, constitution |
| limit | integer | No | 1-20, default 5 |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| results | MemorySearchResult[] | [{entry_id, content, score, source_type, metadata, created_at}] |
| search_time_ms | integer | Search latency |

---

### List Memory Entries: GET /api/v1/{workspace_id}/memory/entries

**Auth**: Bearer (workspace admin)
**Source**: US-23

**Query Parameters**: source_type, limit, offset

**Response (200)**: Paginated MemoryEntry list

---

### Delete Memory Entry: DELETE /api/v1/{workspace_id}/memory/entries/{entry_id}

**Auth**: Bearer (workspace admin)
**Source**: US-23 (PII deletion)

**Response (204)**: No content

---

## Skill Management (Phase B)

### List Core Skills: GET /api/v1/{workspace_id}/skills/core

**Auth**: Bearer (workspace member)
**Source**: US-25, FR-091

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| skills | SkillDefinition[] | Core skills (read-only): name, description, model, approval_level, tools |

---

### List Workspace Custom Skills: GET /api/v1/{workspace_id}/skills/custom

**Auth**: Bearer (workspace member)
**Source**: US-25, FR-092

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| skills | SkillDefinition[] | Workspace custom skills |

---

### Create Custom Skill: POST /api/v1/{workspace_id}/skills/custom

**Auth**: Bearer (workspace admin)
**Source**: US-25, FR-092

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| name | string | Yes | 1-100 chars, unique per workspace |
| description | string | Yes | 1-500 chars |
| model | string | Yes | One of: sonnet, opus, haiku, flash |
| approval_level | string | Yes | One of: auto, suggest, require |
| tools | string[] | Yes | Subset of available MCP tools |
| workflow | string | Yes | Markdown workflow description |
| output_format | string | No | Expected output format |

**Response (201)**: Created SkillDefinition

**Errors**: 401, 403, 409 CONFLICT (name exists)

---

### Update Custom Skill: PUT /api/v1/{workspace_id}/skills/custom/{skill_name}

**Auth**: Bearer (workspace admin)
**Source**: US-25

**Request**: Same as Create (all fields optional except name)

**Response (200)**: Updated SkillDefinition

**Errors**: 401, 403, 404

---

### Delete Custom Skill: DELETE /api/v1/{workspace_id}/skills/custom/{skill_name}

**Auth**: Bearer (workspace admin)
**Source**: US-25

**Response (204)**: No content

**Errors**: 401, 403, 404

---

## SSE Event Types (New)

### intent_detected (Phase A)

Emitted when extract-intents skill detects WorkIntents from user input.

```json
{
  "event": "intent_detected",
  "data": {
    "intents": [
      {
        "id": "uuid",
        "what": "Implement user authentication with email/password and OAuth",
        "why": "Users need secure access to accounts",
        "constraints": [],
        "acceptance": [{"description": "Login form accepts email+password", "verifiable": true}],
        "confidence": 0.85,
        "status": "detected"
      }
    ],
    "note_id": "uuid-or-null",
    "source": "chat"
  }
}
```

### intent_confirmed (Phase A)

Emitted when user confirms an intent.

```json
{
  "event": "intent_confirmed",
  "data": {
    "intent_id": "uuid",
    "skill_name": "create-spec",
    "status": "confirmed"
  }
}
```

### skill_progress (Phase B)

Emitted during skill execution with progress updates.

```json
{
  "event": "skill_progress",
  "data": {
    "intent_id": "uuid",
    "execution_id": "uuid",
    "skill_name": "create-spec",
    "status": "running",
    "progress_pct": 45,
    "current_step": "Generating acceptance criteria",
    "artifacts": [
      {"artifact_id": "uuid", "type": "spec", "note_id": "uuid", "block_count": 12}
    ]
  }
}
```

### skill_presence (Phase B)

Emitted when AI skills join/leave collaborative editing.

```json
{
  "event": "skill_presence",
  "data": {
    "skill_name": "create-spec",
    "intent_id": "uuid",
    "intent_summary": "Auth spec",
    "action": "join",
    "note_id": "uuid"
  }
}
```

### Existing Events Extended

| Event | Extension | Phase |
|-------|-----------|-------|
| `content_update` | New operations: `set_block_owner`, `insert_ai_blocks` | A |
| `approval_request` | UI-layer approval: destructive skill output held in chat for explicit user approval | B |
| `memory_update` | Already exists (T73); add `entries_saved`, `search_context` fields | B |
| `task_progress` | Reuse existing for skill execution progress | B |
