# 013 - Task Management: AI-Powered Issue Context & Implementation Tasks

**Version**: 1.0
**Status**: Draft
**Author**: Tin Dang
**Date**: 2026-02-12
**Branch**: `feat/task-management`

---

## 1. Problem Statement

Pilot Space's core promise is "Note-First" — humans think freely in notes, AI helps structure that thinking into actionable issues. But today, the chain breaks after issue creation:

- Issues lack the structured context AI agents need to implement them
- The `decompose-tasks` skill generates ephemeral tasks (session-scoped `AITask`) that vanish when the session ends
- No permanent, issue-scoped task entity exists for tracking implementation steps
- The AI Context tab has the UI shell (~60% built) but missing backend content generation for codebase context

**Core Workflow Gap**:
```
Note (human thinking) → Issue (contract) → ??? → AI implements
```

**Target Workflow**:
```
Note (human thinking) → Issue (AI implementation brief) → Task (AI-executable steps) → Copy to Claude Code
```

---

## 2. Design Philosophy

> **Every issue is a complete AI implementation brief.**

This feature does NOT add traditional PM tools (Kanban, Gantt, milestones). Instead, it makes every issue contain everything an AI agent (or human developer) needs to implement it:

1. **Acceptance Criteria** — What "done" means
2. **Context Files** — Which files to read/modify
3. **Code Snippets** — Key code sections for reference
4. **Git References** — Related PRs, commits, branches
5. **Technical Requirements** — Constraints, patterns to follow
6. **Tasks** — Ordered implementation steps with dependencies
7. **Ready-to-Use Prompts** — One-click copy to Claude Code

---

## 3. Scope

### In Scope (This Spec)

| Priority | Feature | Description |
|----------|---------|-------------|
| P0 | Issue Context Fields | Add acceptance_criteria, technical_requirements to Issue |
| P0 | Task Entity | New permanent, issue-scoped Task model |
| P0 | Task CRUD API | Create, read, update, delete, reorder tasks |
| P0 | AI Task Decomposition | Upgrade decompose-tasks skill to persist Tasks |
| P0 | Ready-to-Use Prompts | Generate and display implementation prompts per task |
| P0 | Clone Context Panel | GitHub-style popover with 3 export formats (Markdown, Claude Code, Task List) |
| P1 | Codebase Context | File tree, code snippets, git references in AI Context tab |
| P1 | Enhance Context Chat | Conversational refinement of issue context |
| P1 | Task Dependency Graph | Visual DAG of task dependencies (canvas) |

### Out of Scope

- Kanban/Board view for tasks
- Gantt/Timeline view
- Milestones entity
- Custom workflow templates
- Project dashboard/metrics
- Bulk operations on tasks
- Table view for issues

---

## 4. Data Model

### 4.1 Issue Model Enhancement

Add fields to existing `issues` table:

```sql
ALTER TABLE issues
  ADD COLUMN acceptance_criteria JSONB DEFAULT '[]',
  ADD COLUMN technical_requirements TEXT;
```

| Field | Type | Description |
|-------|------|-------------|
| `acceptance_criteria` | `JSONB` (array of `{text: str, done: bool}`) | Checklist of what "done" means, with completion tracking |
| `technical_requirements` | `TEXT` | Free-text constraints, patterns, non-functional requirements |

**Rationale**: `context_files`, `context_code_snippets`, and `git_references` are NOT stored on the Issue model. They are generated dynamically by the AI Context generation pipeline (already exists) and cached in Redis. Storing them on the issue would create stale data as the codebase evolves.

### 4.2 New Task Entity

```sql
CREATE TABLE tasks (
  -- Identity
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,

  -- Content
  title VARCHAR(500) NOT NULL,
  description TEXT,
  acceptance_criteria JSONB DEFAULT '[]',

  -- Status
  status VARCHAR(20) NOT NULL DEFAULT 'todo'
    CHECK (status IN ('todo', 'in_progress', 'done')),

  -- Planning
  sort_order INTEGER NOT NULL DEFAULT 0,
  estimated_hours NUMERIC(5,1),

  -- AI Context
  code_references JSONB DEFAULT '[]',
  ai_prompt TEXT,
  ai_generated BOOLEAN NOT NULL DEFAULT FALSE,

  -- Dependencies (JSONB array of task UUIDs)
  dependency_ids JSONB DEFAULT '[]',

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,

  -- RLS
  CONSTRAINT fk_workspace FOREIGN KEY (workspace_id)
    REFERENCES workspaces(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_tasks_issue_id ON tasks(issue_id) WHERE NOT is_deleted;
CREATE INDEX idx_tasks_workspace_id ON tasks(workspace_id) WHERE NOT is_deleted;
CREATE INDEX idx_tasks_status ON tasks(status) WHERE NOT is_deleted;
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | `VARCHAR(500)` | Task name (imperative form) |
| `description` | `TEXT` | What to do, detailed instructions |
| `acceptance_criteria` | `JSONB` | Array of `{text: str, done: bool}` — per-task done criteria |
| `status` | `VARCHAR(20)` | `todo` / `in_progress` / `done` |
| `sort_order` | `INTEGER` | Display order within issue |
| `estimated_hours` | `NUMERIC(5,1)` | Time estimate (0.5-40h) |
| `code_references` | `JSONB` | `[{file, lines?, description}]` — files to touch |
| `ai_prompt` | `TEXT` | Ready-to-use prompt for Claude Code |
| `ai_generated` | `BOOLEAN` | Whether AI created this task |
| `dependency_ids` | `JSONB` | Array of task UUIDs this depends on |

**Why not self-referential FK for dependencies?** A single `blocked_by_id` (like AITask) only supports one dependency. Tasks commonly depend on multiple predecessors. JSONB array is simpler than a join table for this scale (typically 3-10 tasks per issue).

**Why separate from AITask?** AITask is session-scoped (FK to `ai_sessions`), ephemeral, and designed for tracking agent progress within a conversation. Task is issue-scoped, permanent, and represents the implementation plan.

### 4.3 RLS Policies

```sql
-- tasks: workspace member can read
CREATE POLICY tasks_select ON tasks FOR SELECT
  USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));

-- tasks: workspace member can insert/update/delete
CREATE POLICY tasks_modify ON tasks FOR ALL
  USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));
```

### 4.4 Entity Relationships

```
Issue 1 ──── * Task
  │               │
  │               ├── code_references (JSONB)
  │               ├── ai_prompt (TEXT)
  │               └── dependency_ids (JSONB → Task UUIDs)
  │
  ├── acceptance_criteria (JSONB)
  └── technical_requirements (TEXT)
```

---

## 5. API Design

### 5.1 Task CRUD

**Base path**: `POST /api/v1/workspaces/{workspace_slug}/issues/{issue_id}/tasks`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tasks` | List all tasks for issue (ordered by sort_order) |
| `POST` | `/tasks` | Create a task |
| `PATCH` | `/tasks/{task_id}` | Update a task |
| `DELETE` | `/tasks/{task_id}` | Soft-delete a task |
| `PATCH` | `/tasks/{task_id}/status` | Update task status only |
| `PUT` | `/tasks/reorder` | Bulk reorder tasks |

### 5.2 AI Task Decomposition

**Path**: `POST /api/v1/workspaces/{workspace_slug}/issues/{issue_id}/tasks/decompose`

Triggers the `decompose-tasks` skill and persists results as Task entities (with `ai_generated=true`). Returns created tasks via SSE stream.

**Flow**:
1. Frontend calls decompose endpoint
2. Backend invokes `decompose-tasks` skill with issue context
3. Skill returns subtask JSON (existing format)
4. Backend maps to Task entities, sets `ai_generated=true`, generates `ai_prompt` per task
5. Tasks persisted to DB
6. Response: created Task[] array

**Approval**: Follows DD-003. Decomposition is content creation → configurable approval level. Default: auto-approve (user can re-decompose or edit tasks manually).

### 5.3 Context Export (for Clone Context Panel)

**Path**: `GET /api/v1/workspaces/{workspace_slug}/issues/{issue_id}/context/export`

**Query param**: `format=markdown|claude_code|task_list` (default: `markdown`)

Returns a pre-formatted string combining issue context in the requested format:

**Markdown format** — Full structured markdown:
- Issue title, description, acceptance criteria, technical requirements
- Related issues (from issue_relations)
- Related documents (from note_issue_links)
- Codebase context (from AI context cache or on-demand generation)
- Tasks with prompts
- Acceptance criteria checklist

**Claude Code format** — Optimized prompt with sections:
- `# Context` — Issue summary
- `# Tasks` — Ordered task list with estimates and dependencies
- `# Constraints` — Technical requirements
- `# Acceptance Criteria` — Checklist
- `# Files to Reference` — Code references with badges

**Task List format** — Per-task prompts:
- Each task with its `ai_prompt` content, separated by `---`
- Includes task title, estimate, dependencies, and full prompt

**Response**: `{ content: string, format: string, generated_at: string }`

### 5.4 Schemas

```python
# Task schemas
class TaskCreate(BaseModel):
    title: str = Field(max_length=500)
    description: str | None = None
    acceptance_criteria: list[str] = []
    estimated_hours: float | None = None
    code_references: list[CodeReference] = []
    dependency_ids: list[UUID] = []

class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    status: Literal['todo', 'in_progress', 'done'] | None = None
    estimated_hours: float | None = None
    code_references: list[CodeReference] | None = None
    ai_prompt: str | None = None
    dependency_ids: list[UUID] | None = None

class TaskResponse(BaseModel):
    id: UUID
    issue_id: UUID
    title: str
    description: str | None
    acceptance_criteria: list[str]
    status: str
    sort_order: int
    estimated_hours: float | None
    code_references: list[CodeReference]
    ai_prompt: str | None
    ai_generated: bool
    dependency_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

class CodeReference(BaseModel):
    file: str
    lines: str | None = None  # e.g., "45-62"
    description: str | None = None
    badge: Literal['modified', 'new', 'reference'] | None = None

class TaskReorder(BaseModel):
    task_ids: list[UUID]  # Ordered list of task IDs

# Issue enhancement schemas (extend existing)
class IssueUpdate(BaseModel):  # extend existing
    acceptance_criteria: list[str] | None = None
    technical_requirements: str | None = None

class ContextExportResponse(BaseModel):
    content: str
    format: Literal['markdown', 'claude_code', 'task_list']
    generated_at: datetime
```

---

## 6. Frontend Components

### 6.1 Component Map (AI Context Tab)

Aligns with prototype `design-system/prototype/issue-detail-full.html`:

```
ai-context-tab.tsx (existing, enhance)
├── context-summary-card.tsx (existing, enhance with stats)
├── related-issues-section.tsx (existing)
├── related-docs-section.tsx (existing)
├── codebase-context-section.tsx (NEW)
│   ├── file-tree.tsx (NEW)
│   ├── code-snippet-card.tsx (NEW)
│   └── git-references.tsx (NEW)
├── ai-tasks-section.tsx (existing, enhance)
│   ├── task-dependency-graph.tsx (NEW - canvas)
│   ├── task-checklist.tsx (enhance existing)
│   └── prompt-block.tsx (existing)
├── enhance-context-chat.tsx (NEW)
└── clone-context-panel.tsx (NEW — GitHub-style popover with 3 export formats)
```

**Existing (6 components to enhance)**:
- `ai-context-tab.tsx` — Add codebase context section, copy all button
- `context-summary-card.tsx` — Add stats (related issues, docs, files, tasks counts)
- `ai-tasks-section.tsx` — Wire to real Task CRUD, add expand/collapse
- `prompt-block.tsx` — Already functional, keep as-is
- `related-issues-section.tsx` — Already functional
- `related-docs-section.tsx` — Already functional

**New (5 components)**:
- `codebase-context-section.tsx` — Container for file tree + snippets + git refs
- `file-tree.tsx` — Collapsible file tree with modified/new/reference badges
- `code-snippet-card.tsx` — Code block with file path, line range, copy button
- `git-references.tsx` — PR/commit/branch references with icons
- `task-dependency-graph.tsx` — Canvas-based DAG visualization
- `enhance-context-chat.tsx` — Inline chat for context refinement
- `clone-context-panel.tsx` — GitHub-style popover with Markdown/Claude Code/Task List tabs, dark preview, copy button

### 6.2 Store Changes

**AIContextStore.ts** — Add types:

```typescript
// New types
interface ContextCodeFile {
  path: string;
  badge: 'modified' | 'new' | 'reference';
  children?: ContextCodeFile[];
}

interface ContextCodeSnippet {
  file: string;
  lineRange: string;  // "45-62"
  code: string;
  language: string;
}

interface ContextGitRef {
  type: 'pr' | 'commit' | 'branch';
  title: string;
  meta: string;  // "Draft - Updated 2 days ago"
  url?: string;
}

// Extend AIContextResult
interface AIContextResult {
  // ... existing fields ...
  codeFiles: ContextCodeFile[];
  codeSnippets: ContextCodeSnippet[];
  gitRefs: ContextGitRef[];
}
```

**New: TaskStore.ts** — MobX store for task CRUD:

```typescript
class TaskStore {
  tasks: Map<string, Task[]> = new Map(); // issueId → Task[]
  loading: boolean = false;

  // Actions
  fetchTasks(issueId: string): Promise<void>;
  createTask(issueId: string, data: TaskCreate): Promise<Task>;
  updateTask(taskId: string, data: TaskUpdate): Promise<Task>;
  deleteTask(taskId: string): Promise<void>;
  updateStatus(taskId: string, status: TaskStatus): Promise<void>;
  reorderTasks(issueId: string, taskIds: string[]): Promise<void>;
  decomposeTasks(issueId: string): Promise<Task[]>;

  // Computed
  get tasksForIssue(issueId: string): Task[];
  get completionPercent(issueId: string): number;
}
```

### 6.3 Issue Detail Enhancements

Add to existing issue detail form:
- **Acceptance Criteria** — Editable checklist (add/remove/reorder items)
- **Technical Requirements** — Markdown text area

These render in the Description tab AND are included in AI Context tab's exported markdown.

---

## 7. AI Integration

### 7.1 Decompose-Tasks Skill Upgrade

Current skill generates ephemeral output. Upgrade to:

1. Accept issue context (description, acceptance_criteria, technical_requirements, related issues)
2. Generate tasks with `code_references` and `ai_prompt` per task
3. Return structured JSON that maps directly to Task entity schema
4. Backend persists as Task entities with `ai_generated=true`

**Prompt Template Enhancement**:
```
Given issue context:
- Title: {title}
- Description: {description}
- Acceptance Criteria: {acceptance_criteria}
- Technical Requirements: {technical_requirements}
- Related Issues: {related_issues}
- Codebase Files: {relevant_files}

Generate implementation tasks. For each task include:
- title: Imperative action (e.g., "Create magic link service")
- description: What to do and how
- acceptance_criteria: Per-task done criteria
- estimated_hours: 0.5-8h range
- code_references: [{file, lines, description, badge}]
- dependencies: [task_order_numbers]
- ai_prompt: A complete, ready-to-use prompt for Claude Code
```

### 7.2 AI Prompt Generation

Each task's `ai_prompt` follows this template:

```markdown
{task.title}

## Context
Issue: {issue.identifier} - {issue.title}
{issue.description_summary}

## Requirements
{task.description}

## Acceptance Criteria
{task.acceptance_criteria as checklist}

## Files to Reference
{task.code_references formatted}

## Technical Constraints
{issue.technical_requirements}

## Dependencies
{completed predecessor tasks summary}
```

### 7.3 Context Export Formats

The Clone Context Panel offers 3 export formats:

#### Format 1: Markdown (Full Context)

```markdown
# {identifier}: {title}

## Summary
{description}

## Acceptance Criteria
- [ ] {criterion_1}
- [ ] {criterion_2}

## Technical Requirements
{technical_requirements}

## Related Issues
- {PS-XXX} ({RELATION}): {title} — {status}

## Related Documents
- {doc_title} ({type}): {summary}

## Relevant Files
- {path} ({badge})

## Implementation Tasks
1. {task_title} (~{estimate}h)
   Dependencies: {deps or "None"}
2. {task_title} (~{estimate}h)
   Dependencies: Task 1

## Task Prompts

### Task 1: {title}
{ai_prompt}

### Task 2: {title}
{ai_prompt}
```

#### Format 2: Claude Code (Optimized Prompt)

```markdown
# Context
Issue: {identifier} - {title}
{description_summary}

# Tasks
1. {task_title} (~{estimate}h) - {deps or "No dependencies"}
2. {task_title} (~{estimate}h) - Depends on: Task 1

# Constraints
{technical_requirements as bullet list}

# Acceptance Criteria
- [ ] {criterion_1}
- [ ] {criterion_2}

# Files to Reference
- {path} ({badge})
```

#### Format 3: Task List (Per-Task Prompts)

```markdown
## Task 1: {task_title} (~{estimate}h)
{deps or "No dependencies"}

### Prompt
{ai_prompt}

---

## Task 2: {task_title} (~{estimate}h)
Depends on: Task 1

### Prompt
{ai_prompt}
```

---

## 8. Implementation Plan

### Phase 1: Foundation (P0) — Backend

| # | Task | Files | Est |
|---|------|-------|-----|
| 1.1 | Add `acceptance_criteria`, `technical_requirements` to Issue model | `models/issue.py`, new migration | 1h |
| 1.2 | Update Issue schemas (create/update/response) | `schemas/issue.py` | 0.5h |
| 1.3 | Update Issue service to handle new fields | `services/issue_service.py` | 0.5h |
| 1.4 | Create Task model + migration | `models/task.py`, new migration | 1.5h |
| 1.5 | Create Task repository | `repositories/task_repository.py` | 1h |
| 1.6 | Create Task service (CRUD + reorder + decompose) | `services/task_service.py` | 2h |
| 1.7 | Create Task router (6 endpoints) | `routers/workspace_tasks.py` | 1.5h |
| 1.8 | Create Task schemas | `schemas/task.py` | 0.5h |
| 1.9 | Create context export endpoint | `routers/issues_context_export.py` | 1.5h |
| 1.10 | RLS policies for tasks table | migration | 0.5h |
| 1.11 | Register router + DI container | `routers/__init__.py`, `containers.py` | 0.5h |
| 1.12 | Unit tests for Task service | `tests/services/test_task_service.py` | 2h |
| 1.13 | Unit tests for Task router | `tests/routers/test_workspace_tasks.py` | 1.5h |

**Subtotal**: ~14.5h

### Phase 2: Foundation (P0) — Frontend

| # | Task | Files | Est |
|---|------|-------|-----|
| 2.1 | Add Task API client | `services/api/tasks.ts` | 1h |
| 2.2 | Create TaskStore (MobX) | `stores/TaskStore.ts` | 1.5h |
| 2.3 | Register TaskStore in RootStore | `stores/RootStore.ts` | 0.5h |
| 2.4 | Add acceptance_criteria + technical_requirements to issue forms | issue detail components | 1.5h |
| 2.5 | Enhance ai-tasks-section.tsx with real CRUD | `ai-tasks-section.tsx` | 2h |
| 2.6 | Create clone-context-panel.tsx (popover with 3 export formats) | new component | 2h |
| 2.7 | Wire "Decompose Tasks" button to new API | `ai-context-tab.tsx` | 1h |
| 2.8 | Enhance prompt-block.tsx with copy feedback | existing component | 0.5h |
| 2.9 | Update context-summary-card.tsx with stats | existing component | 0.5h |
| 2.10 | Unit tests for TaskStore | `tests/stores/TaskStore.test.ts` | 1.5h |
| 2.11 | Unit tests for task components | `tests/components/` | 2h |

**Subtotal**: ~13h

### Phase 3: AI Integration (P1)

| # | Task | Files | Est |
|---|------|-------|-----|
| 3.1 | Upgrade decompose-tasks SKILL.md template | `skills/decompose-tasks/SKILL.md` | 1h |
| 3.2 | Implement task persistence in decompose handler | `services/task_service.py` | 1.5h |
| 3.3 | AI prompt generation per task | `services/task_service.py` | 1h |
| 3.4 | Create codebase-context-section.tsx | new component | 2h |
| 3.5 | Create file-tree.tsx | new component | 1.5h |
| 3.6 | Create code-snippet-card.tsx | new component | 1h |
| 3.7 | Create git-references.tsx | new component | 1h |
| 3.8 | Extend AIContextStore with codebase types | `AIContextStore.ts` | 1h |
| 3.9 | Backend: codebase context in AI generation pipeline | AI context service | 2h |
| 3.10 | Unit tests for new components | test files | 2h |

**Subtotal**: ~14h

### Phase 4: Enhanced UX (P1)

| # | Task | Files | Est |
|---|------|-------|-----|
| 4.1 | Create task-dependency-graph.tsx (canvas DAG) | new component | 3h |
| 4.2 | Create enhance-context-chat.tsx | new component | 2h |
| 4.3 | Wire enhance chat to PilotSpace SSE | store integration | 1.5h |
| 4.4 | Drag-and-drop task reordering | `ai-tasks-section.tsx` | 1.5h |
| 4.5 | Task inline editing (click to edit title/description) | task components | 1.5h |
| 4.6 | Unit tests | test files | 2h |

**Subtotal**: ~11.5h

### Total Estimate: ~53h across 4 phases

### Execution Order

```
Phase 1 (backend foundation) → Phase 2 (frontend foundation) → Phase 3 (AI) → Phase 4 (UX)
```

Phase 1 and 2 can partially overlap — frontend can start on 2.1-2.4 (schemas/store/forms) while backend finishes 1.4-1.13.

---

## 9. Acceptance Criteria (Feature-Level)

- [ ] Issue has editable acceptance_criteria (checklist) and technical_requirements fields
- [ ] Tasks are created, read, updated, deleted, and reordered within an issue
- [ ] "Decompose Tasks" button generates AI tasks that persist as Task entities
- [ ] Each task has a ready-to-use AI prompt
- [ ] "Copy All Context" exports complete issue context as markdown
- [ ] AI Context tab shows: summary, related issues, related docs, codebase context, tasks, prompts
- [ ] Task dependency graph renders as visual DAG
- [ ] Enhance context chat allows conversational refinement
- [ ] All new code has >80% test coverage
- [ ] RLS policies enforce workspace isolation for tasks
- [ ] All files under 700 lines

---

## 10. Design Reference

**Prototype**: `design-system/prototype/issue-detail-full.html` (3230 lines)
- AI Context tab: lines 2162-2699
- Task dependency graph: lines 2850-2920
- Copy All Context: lines 2932-2980
- Design tokens: CSS variables at top of file

---

## 11. Migration from AITask

The existing `AITask` entity (session-scoped) remains unchanged. It serves a different purpose:

| Aspect | AITask (existing) | Task (new) |
|--------|-------------------|------------|
| Scope | Session (ephemeral) | Issue (permanent) |
| FK | `session_id → ai_sessions` | `issue_id → issues` |
| Purpose | Track agent work within conversation | Implementation plan for issue |
| Status | pending/in_progress/completed/failed/blocked | todo/in_progress/done |
| Lifecycle | Dies with session | Lives with issue |
| Created by | AI agent during conversation | AI decompose skill OR human |

The `decompose-tasks` skill will be updated to create Task entities (permanent) instead of only AITask entities (ephemeral). AITask remains for tracking real-time agent progress during conversations.
