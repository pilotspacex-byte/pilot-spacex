# Pilot Space Agent: Skills System & Prompts Intelligence

> **Location**: `backend/src/pilot_space/ai/skills/`, `backend/src/pilot_space/ai/prompts/`, `backend/src/pilot_space/ai/prompt/`
> **Design Decisions**: DD-087 (Filesystem Skill System), DD-003 (Human-in-the-Loop)

## Overview

The Skills system is the **callable capability layer** of the PilotSpaceAgent — a set of single-turn, stateless operations that transform user intent into structured AI output. Skills are defined as YAML files on the filesystem (DD-087), auto-discovered at runtime, versioned, and executed through a 6-step lifecycle with approval gates. The Prompts intelligence layer sits beneath all agent activity: a layered assembly pipeline that constructs the right system prompt for each operation, plus a regex-based intent classifier that routes user messages to the correct skill without a costly LLM call.

---

## Architecture

```
User message
     ↓
IntentClassifier          ← regex-based, 7 intent types, no LLM cost
     ↓
SkillDiscovery            ← filesystem scan → YAML parse → SkillMetadata list
     ↓
RoleSkillMaterializer     ← writes dynamic SKILL.md to sandbox per user role
     ↓
SkillExecutor             ← 6-step execution lifecycle
     ├── 1. Validate input (Pydantic)
     ├── 2. Check approval tier (DD-003)
     ├── 3. Acquire Redis write-lock (~5ms)
     ├── 4. PromptAssembler → 6-layer system prompt
     ├── 5. LLM call (provider-routed per DD-011)
     └── 6. Stream output + VersioningHook snapshot
```

---

## Skills System

### Skill Discovery (`skill_discovery.py`)

**How skills are found**: Filesystem scan of the `.claude/skills/` directory in the agent sandbox. Each `.yaml` file is a skill definition. No code changes needed to add a skill — drop a YAML file and restart.

**24 available skills** organized by category:

| Category | Skills |
|----------|--------|
| Issues | `extract-issues`, `enhance-issue`, `find-duplicates`, `recommend-assignee`, `decompose-tasks` |
| Writing | `improve-writing`, `summarize`, `generate-pm-blocks` |
| Notes | `summarize-note`, `generate-diagram` |
| Planning | `daily-standup`, `generate-implementation-plan` |
| Documentation | `generate-docs`, `generate-api-docs` |
| Code | `generate-tests`, `review-code` |

**YAML skill definition schema**:
```yaml
name: extract-issues
description: Extract actionable issues from note content
category: issues
icon: ListTodo
model: claude-sonnet-4-6        # overrides workspace default
approval_required: false         # DD-003 tier
input_schema:
  note_content: str
  workspace_id: str
output_schema:
  issues: list[IssueCandidate]
examples:
  - "Extract issues from this design doc"
  - "/extract-issues from my notes"
```

**Auto-discovery flow**: On agent startup, `SkillDiscovery.scan()` walks the skills directory, parses each YAML, validates against `SkillDefinition` schema, and registers in the in-memory skill registry. Invalid YAML is skipped with a warning (fail-open for discovery).

---

### Skill Executor (`skill_executor.py`)

**6-step execution lifecycle**:

```
1. Input Validation
   Pydantic model validates incoming parameters against skill's input_schema.
   Raises SkillValidationError on failure → user sees structured error message.

2. Approval Tier Check (DD-003)
   tier = AUTO   → proceed immediately (suggestions, read-only)
   tier = PENDING → emit approval_request SSE, wait for user decision
   tier = ADMIN   → require workspace admin role, else reject

3. Redis Write-Lock Acquisition (~5ms overhead)
   Key: "skill_lock:{workspace_id}:{skill_name}"
   TTL: max skill timeout (default 120s)
   Prevents concurrent same-skill runs per workspace.
   Max 5 concurrent skill executions per workspace.

4. Prompt Assembly
   PromptAssembler builds 6-layer system prompt (see below).
   Context injected: workspace info, user role, note content, issue metadata.

5. LLM Execution
   Provider selected via ProviderSelector (DD-011).
   Streams tokens via SSE task_progress events.
   VersioningHook captures before-state of any note/issue being modified.

6. Output & Snapshot
   Output validated against skill's output_schema.
   VersioningHook captures after-state → stored as reversible snapshot.
   TipTap JSON validated if skill produces note content.
   Result emitted as structured_result SSE event.
```

**Concurrency limits**: Max 5 concurrent skill executions per workspace. 6th request receives `queue_depth` SSE event and waits. Implemented via Redis sorted set (workspace_id → active count).

---

### Skill Metadata (`skill_metadata.py`)

Thin model layer — maps YAML fields to Python `SkillDefinition` dataclass for UI consumption:

```python
@dataclass
class SkillDefinition:
    name: str
    description: str
    category: SkillCategory
    icon: str                      # lucide icon name for frontend
    model: str | None              # None = workspace default
    approval_required: bool
    input_schema: dict
    output_schema: dict
    examples: list[str]
    version: str
```

**Why expose metadata to frontend?** The `GET /api/v1/ai/skills` endpoint returns `SkillDefinition` list — this populates the `SkillMenu` slash-command picker in the ChatInput with live server-side skill definitions, not hardcoded constants.

---

### Skill Versioning (`versioning_hook.py`)

For skills that **mutate** notes or issues, the versioning hook captures before/after snapshots to enable reversal.

**Trigger**: Any skill with `mutates: [note, issue]` in its YAML definition.

**Snapshot structure**:
```python
@dataclass
class SkillSnapshot:
    skill_name: str
    execution_id: str
    workspace_id: str
    before: dict           # serialized entity state before skill ran
    after: dict            # serialized entity state after skill ran
    executed_at: datetime
    reversed: bool = False
```

**Storage**: PostgreSQL `skill_snapshots` table (not Redis — must survive restarts for reversal).

**Reversal**: `POST /api/v1/ai/skills/{execution_id}/reverse` applies the `before` snapshot, sets `reversed=True`.

**Why not use Alembic for this?** Skill snapshots are user-data reversals, not schema migrations. They capture content state (note text, issue fields), not schema structure.

---

### Role Skill Materializer (`role_skill_materializer.py`)

**Purpose**: Dynamically write a `SKILL.md` file to the user's agent sandbox that describes which skills are available for their workspace role.

**Why needed**: The Claude Agent SDK discovers skills by reading the sandbox filesystem. The materialized `SKILL.md` tells the SDK what slash commands exist and their descriptions, enabling the SDK's native skill dispatch.

**Materialization flow**:
```
User connects to workspace
  → role = workspace_members[user_id].role (owner/admin/member/guest)
  → Filter skills: guest gets read-only skills, admin gets all skills
  → Render SKILL.md template with allowed skills
  → Write to /sandbox/{user_id}/{workspace_id}/.claude/skills/SKILL.md
  → SDK reads on next request
```

**Role → skill access mapping**:
| Role | Skill access |
|------|-------------|
| Owner/Admin | All 24 skills |
| Member | All except admin-tier (`archive_workspace`, `delete_*`) |
| Guest | Read-only skills only (`summarize`, `generate-diagram`) |

---

## Prompts Intelligence Layer

### Prompt Assembler (`prompt/prompt_assembler.py`)

**6-layer assembly pipeline** — each layer adds context without redundancy:

```
Layer 1: Base System Prompt
  Role definition, output format rules, safety constraints.
  Static per agent type (PilotSpaceAgent vs GhostTextAgent vs PRReviewAgent).

Layer 2: Workspace Context
  Workspace name, project list, team size, active cycles.
  Loaded once per session, cached in Redis (30-min TTL).

Layer 3: User Role & Permissions
  Role name, allowed skills, approval thresholds.
  Determines what the agent can propose vs must request approval for.

Layer 4: Document Context
  Note content (if context.note_id set), issue metadata (if context.issue_id set).
  Chunked to fit token budget (max 6K tokens for context).

Layer 5: Conversation History
  Last N turns from session (N = 8 by default, configurable).
  Compressed via summarization if history exceeds token budget.

Layer 6: User Message
  The actual user request, with detected intent tag prepended.
```

**Why layering?** Each layer is loaded and cached independently. When only the user message changes (layers 1-5 unchanged), only layer 6 is reloaded. Reduces token usage by 20-40% vs sending full context each turn.

**Token budget enforcement**: `config/token_limits.py` defines hard limits per layer. If document context exceeds limit, it's chunked and only the most relevant chunks are injected (cosine similarity against user message via pgvector).

---

### Intent Classifier (`prompt/intent_classifier.py`)

**Purpose**: Route user messages to the correct skill or free-conversation handler **without an LLM call** (regex-based, ~1ms).

**7 intent types**:

| Intent | Detection pattern | Dispatch |
|--------|------------------|---------|
| `skill_invocation` | Starts with `\skillname` | SkillExecutor with named skill |
| `agent_mention` | Contains `@agentname` | Subagent router |
| `issue_extraction_hint` | Keywords: "extract", "create issues", "tasks from" | Suggests `\extract-issues` |
| `question` | Ends with `?`, starts with interrogative | Free conversation |
| `note_editing` | "improve", "rewrite", "fix grammar" | Suggests `\improve-writing` |
| `code_review_hint` | "review", "PR", "pull request" | Suggests `@pr-review` |
| `free_conversation` | All other patterns | PilotSpaceAgent free response |

**Context bias**: If `context.note_id` is set (user is on Note Canvas), `note_editing` and `issue_extraction_hint` intents are boosted — a message like "clean this up" is more likely to mean `\improve-writing` than a general question.

**Why regex, not LLM?** Intent classification adds ~200ms if done with an LLM. At scale (5-100 users/workspace), this compounds. Regex covers 90%+ of real patterns with 0 cost and <2ms latency.

---

### Prompt Templates

#### `prompts/issue_extraction.py`

Builds the extraction prompt for the `extract-issues` skill.

**Template structure**:
- Persona: "Senior PM who identifies actionable work items from unstructured notes"
- Task: Extract issues with confidence scores, classify as explicit/implicit/related
- Format: Structured JSON with `IssueCandidate[]` output
- Constraints: Don't invent issues not implied by the text; assign confidence 0-1

**Key injection variables**: `{note_content}`, `{workspace_project_list}`, `{existing_issue_titles}` (for deduplication hint)

#### `prompts/issue_enhancement.py`

Builds the enhancement prompt for the `enhance-issue` skill.

**Template structure**:
- Persona: "Technical PM who writes clear, actionable issue descriptions"
- Task: Enrich title, description, acceptance criteria, effort estimate
- Constraints: Don't change the core intent; preserve the reporter's framing

**Key injection variables**: `{issue_title}`, `{issue_description}`, `{related_issues}`, `{workspace_context}`

#### `prompts/ghost_text.py`

Builds the completion prompt for the GhostTextAgent (Gemini Flash, <500ms target).

**Template structure**:
- Ultra-brief: No persona, no explanation, just complete the thought
- Single sentence instruction: "Continue this text naturally, 1-2 sentences max"
- **Why minimal**: Every token in the prompt costs latency. Ghost text must return in <1.5s after the 500ms typing pause.

**Key injection variables**: `{cursor_context}` (text before cursor, max 500 chars), `{note_title}`

#### `prompts/margin_annotation.py` / `margin_annotation_sdk.py`

Builds the annotation prompt for the MarginAnnotationAgent.

**Template structure**:
- Detects: Ambiguous requirements, missing acceptance criteria, contradictions, unanswered questions
- Output: Annotation with `type` (question/suggestion/warning), `block_id`, `content`
- Annotation SDK variant: Adapts output for the Claude Agent SDK's native annotation format

#### `prompts/pr_review.py`

Builds the review prompt for the PRReviewSubagent (Claude Opus — highest quality).

**Template structure**:
- Persona: "Senior engineer with 15 years experience in code review"
- Severity levels: critical / major / minor / nitpick
- Coverage: Architecture, security, performance, testing, documentation
- Output: Structured comments with file path, line number, severity, explanation

---

### AI Context Assembly (`context.py`)

**`AIRequestContext`** — the request-scoped object passed through the entire agent stack:

```python
@dataclass
class AIRequestContext:
    workspace_id: str
    user_id: str
    session_id: str
    note_id: str | None        # attached note context
    issue_id: str | None       # attached issue context
    project_id: str | None     # attached project context
    selected_block_ids: list[str] | None  # specific blocks in scope
    user_role: WorkspaceRole
    token_budget: int          # remaining session budget (8K default)
    api_key_anthropic: str | None  # BYOK key (decrypted from Vault)
    api_key_gemini: str | None
```

**Context propagation**: Created at the API boundary (`POST /api/v1/ai/chat`), passed through: `PilotSpaceAgent → SkillExecutor → PromptAssembler → ProviderSelector → LLM call`. Never stored in Redis (contains decrypted keys — in-memory only).

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Skill auto-discovery on startup | Filesystem scan of `.claude/skills/` | `skill_discovery.py` |
| No-LLM intent routing (~1ms) | Regex pattern matching | `intent_classifier.py` |
| Context bias for note canvas | `note_id` in context boosts note intents | `intent_classifier.py` |
| Per-workspace concurrent skill limit (5) | Redis sorted set | `skill_executor.py` |
| Redis write-lock prevents duplicate runs | `skill_lock:{ws}:{skill}` key | `skill_executor.py` |
| Prompt layer caching | Redis 30-min TTL per layer | `layer_loaders.py` |
| Token budget enforcement per layer | `token_limits.py` hard limits | `prompt_assembler.py` |
| Relevant chunk selection for long notes | pgvector cosine similarity | `prompt_assembler.py` |
| History summarization on overflow | Compresses old turns to fit budget | `prompt_assembler.py` |
| Role-based skill access | Materialized `SKILL.md` per user | `role_skill_materializer.py` |
| Reversible skill executions | Before/after snapshots | `versioning_hook.py` |
| TipTap JSON validation for note skills | Schema check on output | `skill_executor.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| YAML-defined skills (DD-087) | Skills are configuration, not code. PMs/designers can add skills without touching Python. |
| Filesystem discovery (not database) | Version-controlled, reviewable, rollbackable. No migration needed to add/remove skills. |
| Regex intent classifier (not LLM) | Zero cost, <2ms, handles 90%+ of patterns. LLM classification would add 200ms per turn. |
| 6-layer prompt assembly | Independent caching per layer. Only changed layers reload. 20-40% token savings. |
| Role materialization to sandbox | Claude Agent SDK reads skill definitions from filesystem — materialization bridges role system to SDK's native discovery. |
| Skill versioning in PostgreSQL | In-memory or Redis snapshots would be lost on restart. Reversal must survive server restarts. |
| Max 5 concurrent skills/workspace | Prevents one workspace from starving others on shared LLM quota. |
| Ghost text prompt ultra-minimized | Every prompt token adds latency. <1.5s target demands maximum brevity. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `skills/skill_discovery.py` | ~150 | Filesystem scan → YAML parse → skill registry |
| `skills/skill_executor.py` | ~280 | 6-step execution lifecycle, Redis locking, approval |
| `skills/skill_metadata.py` | ~80 | `SkillDefinition` dataclass for API/frontend |
| `skills/versioning_hook.py` | ~120 | Before/after snapshots for reversible mutations |
| `agents/role_skill_materializer.py` | ~100 | Role-filtered `SKILL.md` written to sandbox |
| `prompt/prompt_assembler.py` | ~220 | 6-layer prompt assembly with caching |
| `prompt/layer_loaders.py` | ~140 | Cached template file I/O per layer |
| `prompt/models.py` | ~90 | `PromptLayer`, `AssembledPrompt` Pydantic schemas |
| `prompt/intent_classifier.py` | ~130 | Regex-based 7-intent classifier |
| `prompts/issue_extraction.py` | ~100 | Extract-issues prompt template |
| `prompts/issue_enhancement.py` | ~90 | Enhance-issue prompt template |
| `prompts/ghost_text.py` | ~50 | Ultra-brief ghost text completion prompt |
| `prompts/margin_annotation.py` | ~110 | Margin annotation detection prompt |
| `prompts/margin_annotation_sdk.py` | ~90 | SDK-adapted annotation prompt |
| `prompts/pr_review.py` | ~140 | PR review prompt (Opus-grade) |
| `context.py` | ~80 | `AIRequestContext` in-memory request scope |
| `config/token_limits.py` | ~60 | Hard token limits per prompt layer |
