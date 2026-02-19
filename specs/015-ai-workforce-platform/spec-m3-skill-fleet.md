# M3 — Skill Fleet

**Feature**: 015 AI Workforce Core
**Module**: M3 — Skill Fleet
**Status**: Implemented (Sprint 2 Phase 2c complete)
**Depends on**: M2 (confirmed WorkIntent required before execution)
**Consumed by**: M1 (Agent Loop calls SkillRunner.execute)

---

## Purpose

Execute skills as SDK subagents, one per confirmed WorkIntent. Skills are stateless SKILL.md files — memory is M4's responsibility. Destructive skill output is held server-side until explicit human approval.

---

## Codebase Anchors

- `backend/src/pilot_space/ai/templates/skills/` — SKILL.md files
- `backend/src/pilot_space/ai/skills/skill_executor.py` — SkillExecutor, TipTapValidator, WorkspaceSkillSemaphore, NoteWriteLockManager
- `backend/src/pilot_space/infrastructure/database/models/skill_execution.py` — SkillExecution ORM model
- `backend/src/pilot_space/api/v1/routers/skill_approvals.py` — Approval API
- `backend/alembic/versions/039_add_skill_executions.py` — full CREATE
- `backend/alembic/versions/041_add_skill_approval_expiry_cron.py` — pg_cron expiry

---

## SkillDefinition Format

SKILL.md file with YAML frontmatter + markdown workflow body. Auto-discovered by SDK.

```markdown
---
name: generate-code
description: Generate implementation code from a confirmed WorkIntent
required_approval_role: member
model: sonnet
---
## Workflow
1. Read memory context for code style + patterns
2. Analyze the confirmed WorkIntent
3. Generate code blocks in target note
## Output Format
TipTap codeBlock nodes written to note.
## Tools Available
write_to_note, insert_block, replace_content
```

---

## Skill Catalog (23 total: 17 existing + 6 new †)

### Specify Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| extract-intents | Sonnet | auto | WorkIntent[] |
| create-spec | Sonnet | suggest | Spec blocks in note |
| plan-tasks | Sonnet | suggest | Task list + issues |
| enhance-issue | Sonnet | auto | Updated issue |
| find-duplicates | Haiku | auto | Duplicate list |
| recommend-assignee | Haiku | auto | Assignee suggestion |

### Build Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| generate-code † | Sonnet | suggest | Code blocks in note |
| write-tests † | Sonnet | suggest | Test blocks in note |
| generate-migration † | Sonnet | **require (admin)** | Migration file |
| generate-docs | Sonnet | auto | Doc note |

### Review Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| review-code † | Opus | auto | Review comments |
| review-architecture † | Opus | auto | Architecture report |
| scan-security † | Sonnet | auto | Security findings |

### Operate Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| deploy | Sonnet | **require (admin)** | Deployment checklist |
| monitor-health | Haiku | auto | Health report |
| hotfix | Sonnet | **require (admin)** | Hotfix PR |

### Context Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| build-context | Sonnet | auto | Context document |
| update-embeddings | Flash | auto | Embedding count |
| search-memory | Flash | auto | Memory results |

### Writing Domain

| Skill | Model | Approval | Output |
|-------|-------|----------|--------|
| ghost-text | Flash | auto | Ghost text (<2s) |
| improve-writing | Flash | auto | Improved text |
| summarize | Flash | auto | Summary |
| generate-diagram | Sonnet | auto | Diagram blocks |

---

## Approval Model (C-7, AD-6)

**`required_approval_role`** in SKILL.md frontmatter:

| Value | Skills | Behavior |
|-------|--------|----------|
| `admin` | generate-migration, deploy, hotfix | Output held `pending_approval` until admin approves |
| `member` | generate-code, write-tests, create-spec, plan-tasks | Output held `pending_approval` until any member approves |
| `null` / omitted | review-*, scan-security, summarize, etc. | Auto-execute, output persisted immediately |

Backend enforces role at `POST /{workspace_id}/skill-approvals/{id}/approve`: returns 403 if caller role is below `required_approval_role`.

---

## Database

**Table**: `skill_executions` (migration 039, full CREATE — C-1)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| intent_id | UUID FK → work_intents | |
| skill_name | TEXT | |
| approval_status | ENUM | auto_approved / pending_approval / approved / rejected / expired |
| required_approval_role | ENUM | admin / member / null |
| output | JSONB | null if pending_approval until approved |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**RLS**: via join to `work_intents.workspace_id`

---

## Approval API Endpoints

`GET  /{workspace_id}/skill-approvals/pending` — list pending approvals (paginated)
`POST /{workspace_id}/skill-approvals/{execution_id}/approve` — persist output to note
`POST /{workspace_id}/skill-approvals/{execution_id}/reject` — discard output

---

## SkillExecutor

**File**: `skill_executor.py`

### TipTap Output Validation (T-045, FR-114)

All skill output is validated against TipTap block schema before persistence. Invalid output → intent status "failed", error in chat with [Retry]. Malformed blocks MUST NOT reach the note editor.

```python
TipTapValidator.validate_doc(doc)   # validates root type='doc', content is list
TipTapValidator.validate_block(block)  # validates dict with 'type'; unknown types allowed (forward-compat)
TipTapValidator.validate_json_string(json_str)  # parse JSON then validate_doc
```

### Concurrency Manager (T-047, FR-109)

Per-workspace asyncio semaphore, max 5 concurrent skills.

```python
WorkspaceSkillSemaphore.acquire(workspace_id)  -> (semaphore, was_queued)
WorkspaceSkillSemaphore.release(semaphore)
```

6th concurrent request returns `was_queued=True` → SSE event `skill_queued` emitted to chat.

### Note Write Lock (C-3)

Redis mutex acquired before any note mutation. Prevents concurrent skill writes from corrupting note state.

```
Lock key:  note_write_lock:{note_id}
TTL:       30 seconds
Acquire:   SET NX EX (atomic)
Timeout:   5s → NoteLockTimeoutError → intent "failed", chat [Retry]
```

Read-only tools (`search_notes`, `search_note_content`) do not acquire the lock.

---

## Module Interface

```python
execute(intent: WorkIntent, skill_name: str) -> AsyncIterator[SkillEvent]
list_skills() -> list[SkillDefinition]
```

---

## Background Job

### J-6 — Approval Expiry (pg_cron)

**Function**: `fn_expire_pending_skill_approvals()`
**Schedule**: Every 30 min
**Migration**: `041_add_skill_approval_expiry_cron.py`
**Logic**: `UPDATE skill_executions SET approval_status='expired' WHERE approval_status='pending_approval' AND created_at < NOW() - INTERVAL '24 hours'`

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-085 | Skills execute as SDK subagents, one per WorkIntent |
| FR-086 | Tools whitelisted in SKILL.md; `AgentDefinition.tools` enforces |
| FR-087 | Configurable token budget and max turns |
| FR-088 | Skills are stateless — memory engine handles persistence |
| FR-089 | Output MUST be persisted before completion reported |
| FR-090 | Destructive skills require approval before persisting |
| FR-091 | Discover core skills from repo, custom from DB sandbox |
| FR-092 | Support workspace-specific custom skills |
| FR-093 | SKILL.md declares name/description (YAML) + workflow/output format/tools (markdown) |
| FR-109 | Max 5 concurrent skills per workspace |
| FR-110 | Chains execute sequentially unless independent |
| FR-111 | Chain failure → stop subsequent; partial output persisted; intent = "review" |
| FR-114 | Skill output MUST be validated against TipTap block schema before persistence |

---

## Tasks

| ID | Task | Status |
|----|------|--------|
| T-024 | Migration 039: skill_executions table (full CREATE) | Done |
| T-038 | SKILL.md: generate-code | Done |
| T-039 | SKILL.md: write-tests | Done |
| T-040 | SKILL.md: generate-migration | Done |
| T-041 | SKILL.md: review-code | Done |
| T-042 | SKILL.md: review-architecture | Done |
| T-043 | SKILL.md: scan-security | Done |
| T-044 | Skill executor with approval hold | Done |
| T-045 | TipTap output validation | Done |
| T-046 | Approval API router | Done |
| T-047 | Skill concurrency manager | Done |
| T-070 | Approval expiry pg_cron (J-6) | Done |

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Skill crashes mid-execution | Intent = "failed", partial output persisted, chat: [Retry] |
| Token budget exhausted | Graceful termination, partial output, intent = "review" |
| Two skills modify same note | Note write lock (C-3): second skill waits or fails with lock timeout |
| Large output (>50 blocks) | New linked note created instead of inline blocks |
| Tool not in SKILL.md tools list | SDK rejects natively via AgentDefinition.tools |
| 6th concurrent skill | Queued with "Waiting for slot" SSE event |
| Approval expired after 24h | `approval_status = 'expired'` via J-6, intent → "review", chat notification |

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Subagent spawn time | <3 seconds |
| Tool whitelist enforcement | 0 violations |
| Output persistence before completion | 100% |
| Destructive skill auto-persist rate | 0% |
| TipTap schema validation before persistence | 100% validated |
