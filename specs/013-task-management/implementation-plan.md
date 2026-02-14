# 013 - Task Management: Implementation Plan

**Spec**: `specs/013-task-management/spec.md`
**Branch**: `feat/task-management`

---

## Phase 1: Backend Foundation (P0)

### 1.1 Issue Model Enhancement

**Files**:
- `backend/src/pilot_space/infrastructure/database/models/issue.py`
- New Alembic migration

**Changes**:
- Add `acceptance_criteria: Mapped[list[str] | None]` (JSONB, default `[]`)
- Add `technical_requirements: Mapped[str | None]` (TEXT)
- Generate migration: `alembic revision --autogenerate -m "Add acceptance_criteria and technical_requirements to issues"`

### 1.2 Issue Schema Updates

**Files**:
- `backend/src/pilot_space/api/v1/schemas/issue.py`

**Changes**:
- Add `acceptance_criteria: list[str] = []` to `IssueCreate`, `IssueUpdate`
- Add `technical_requirements: str | None = None` to `IssueCreate`, `IssueUpdate`
- Add both fields to `IssueResponse`

### 1.3 Issue Service Update

**Files**:
- `backend/src/pilot_space/application/services/issue_service.py`

**Changes**:
- Ensure `create_issue` and `update_issue` pass new fields through to repository

### 1.4 Task Model

**Files**:
- `backend/src/pilot_space/infrastructure/database/models/task.py` (NEW)
- `backend/src/pilot_space/infrastructure/database/models/__init__.py` (update exports)
- New Alembic migration

**Model**: See spec section 4.2. Key fields:
- `id`, `workspace_id`, `issue_id`, `title`, `description`
- `acceptance_criteria` (JSONB), `status` (todo/in_progress/done), `sort_order`
- `estimated_hours`, `code_references` (JSONB), `ai_prompt`, `ai_generated`
- `dependency_ids` (JSONB), timestamps, soft delete

### 1.5 Task Repository

**Files**:
- `backend/src/pilot_space/infrastructure/repositories/task_repository.py` (NEW)
- `backend/src/pilot_space/infrastructure/repositories/__init__.py` (update exports)

**Methods**:
- `list_by_issue(issue_id, workspace_id) → list[Task]` (ordered by sort_order)
- `get_by_id(task_id, workspace_id) → Task | None`
- `create(data) → Task`
- `update(task_id, data) → Task`
- `soft_delete(task_id) → None`
- `bulk_update_order(task_ids_ordered) → None`
- `bulk_create(tasks) → list[Task]` (for decompose)

### 1.6 Task Service

**Files**:
- `backend/src/pilot_space/application/services/task_service.py` (NEW)

**Methods**:
- `list_tasks(issue_id, workspace_id) → list[TaskResponse]`
- `create_task(issue_id, workspace_id, payload: TaskCreate) → TaskResponse`
- `update_task(task_id, workspace_id, payload: TaskUpdate) → TaskResponse`
- `delete_task(task_id, workspace_id) → None`
- `update_status(task_id, workspace_id, status) → TaskResponse`
- `reorder_tasks(issue_id, workspace_id, task_ids) → list[TaskResponse]`
- `decompose_issue(issue_id, workspace_id) → list[TaskResponse]`
  - Calls decompose-tasks skill
  - Maps output to Task entities
  - Generates ai_prompt per task
  - Persists with ai_generated=True
- `export_context(issue_id, workspace_id) → ContextExportResponse`
  - Aggregates issue + tasks + relations + context
  - Formats as markdown string

### 1.7 Task Router

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_tasks.py` (NEW)

**Endpoints** (under `/api/v1/workspaces/{workspace_slug}/issues/{issue_id}/tasks`):
```
GET    /                    → list_tasks
POST   /                    → create_task
PATCH  /{task_id}           → update_task
DELETE /{task_id}           → delete_task
PATCH  /{task_id}/status    → update_task_status
PUT    /reorder             → reorder_tasks
POST   /decompose           → decompose_tasks
```

**Context Export** (under `/api/v1/workspaces/{workspace_slug}/issues/{issue_id}/context`):
```
GET    /export              → export_context
```

### 1.8 Task Schemas

**Files**:
- `backend/src/pilot_space/api/v1/schemas/task.py` (NEW)

**Schemas**: `TaskCreate`, `TaskUpdate`, `TaskResponse`, `TaskStatusUpdate`, `TaskReorder`, `CodeReference`, `ContextExportResponse`

See spec section 5.4 for full schema definitions.

### 1.9 RLS Policies

**Files**:
- New Alembic migration (can combine with model migration)

**Policies**: Workspace member can read/write tasks within their workspace.

### 1.10 DI Container + Router Registration

**Files**:
- `backend/src/pilot_space/infrastructure/containers.py`
- `backend/src/pilot_space/api/v1/routers/__init__.py`

**Changes**:
- Register TaskRepository and TaskService in DI container
- Add workspace_tasks router to app

### 1.11 Backend Tests

**Files**:
- `backend/tests/services/test_task_service.py` (NEW)
- `backend/tests/routers/test_workspace_tasks.py` (NEW)

**Test coverage**:
- Task CRUD operations
- Reorder validation (all task_ids must belong to issue)
- Status transitions
- Decompose integration (mock skill output)
- Context export format validation
- Authorization (workspace membership)
- Soft delete behavior

---

## Phase 2: Frontend Foundation (P0)

### 2.1 Task API Client

**Files**:
- `frontend/src/services/api/tasks.ts` (NEW)
- `frontend/src/services/api/index.ts` (update exports)

**Methods**:
- `listTasks(workspaceSlug, issueId) → Task[]`
- `createTask(workspaceSlug, issueId, data) → Task`
- `updateTask(workspaceSlug, issueId, taskId, data) → Task`
- `deleteTask(workspaceSlug, issueId, taskId) → void`
- `updateTaskStatus(workspaceSlug, issueId, taskId, status) → Task`
- `reorderTasks(workspaceSlug, issueId, taskIds) → Task[]`
- `decomposeTasks(workspaceSlug, issueId) → Task[]`
- `exportContext(workspaceSlug, issueId) → { markdown, generated_at }`

### 2.2 TaskStore

**Files**:
- `frontend/src/stores/TaskStore.ts` (NEW)

**Store**: MobX observable with task CRUD actions, loading states, computed completion percentage.

### 2.3 Register in RootStore

**Files**:
- `frontend/src/stores/RootStore.ts`

**Changes**: Add `taskStore: TaskStore` instance.

### 2.4 Issue Form Enhancements

**Files**:
- Issue detail description tab components

**Changes**:
- Add "Acceptance Criteria" editable checklist (add/remove/reorder items)
- Add "Technical Requirements" markdown textarea
- Wire to existing issue update API with new fields

### 2.5 Enhanced AI Tasks Section

**Files**:
- `frontend/src/features/issues/components/ai-tasks-section.tsx`

**Changes**:
- Wire checkboxes to `TaskStore.updateStatus`
- Add inline edit for task title
- Add "Decompose Tasks" button (calls `TaskStore.decomposeTasks`)
- Show completion percentage

### 2.6 Clone Context Panel (Popover)

**Files**:
- `frontend/src/features/issues/components/clone-context-panel.tsx` (NEW)

**Design**: GitHub-style popover (like green "Code" button) with:
- Trigger: "Clone Context" button with Terminal icon in AI Context tab header
- 420px popover with tabs: Markdown / Claude Code / Task List
- Dark preview area (#1E1E1E, Geist Mono, max-height 280px, scrollable)
- Footer: stats row + Copy button with success feedback (blue→green)
- Responsive: Bottom sheet on mobile (<640px)

**Behavior**:
- Calls export API with `?format=markdown|claude_code|task_list`
- Renders preview in dark code block
- Copy button copies active tab content to clipboard
- Uses `useCopyFeedback()` hook for "Copied!" state (1.5s)

### 2.7 Wire Decompose Button

**Files**:
- `frontend/src/features/issues/components/ai-context-tab.tsx`

**Changes**:
- Add header with "Copy All Context" and "Regenerate" buttons
- Wire "Decompose Tasks" to TaskStore

### 2.8-2.9 Component Enhancements

- `prompt-block.tsx`: Add copy feedback toast
- `context-summary-card.tsx`: Add stats (related issues, docs, files, tasks counts)

### 2.10-2.11 Frontend Tests

**Files**:
- `frontend/src/stores/__tests__/TaskStore.test.ts` (NEW)
- `frontend/src/features/issues/components/__tests__/ai-tasks-section.test.tsx` (NEW)
- `frontend/src/features/issues/components/__tests__/copy-all-context-button.test.tsx` (NEW)

---

## Phase 3: AI Integration (P1)

### 3.1 Upgrade decompose-tasks Skill

**Files**:
- `backend/src/pilot_space/ai/templates/skills/decompose-tasks/SKILL.md`

**Changes**:
- Add `code_references` and `ai_prompt` to output schema
- Enhance prompt to include issue's acceptance_criteria and technical_requirements
- Generate ready-to-use prompts per task

### 3.2-3.3 Task Persistence + Prompt Generation

**Files**:
- `backend/src/pilot_space/application/services/task_service.py`

**Changes**:
- `decompose_issue` method: parse skill output → create Task entities → generate ai_prompt per task
- Prompt template per spec section 7.2

### 3.4-3.7 Codebase Context Components (Frontend)

**New files**:
- `frontend/src/features/issues/components/codebase-context-section.tsx`
- `frontend/src/features/issues/components/file-tree.tsx`
- `frontend/src/features/issues/components/code-snippet-card.tsx`
- `frontend/src/features/issues/components/git-references.tsx`

**Design**: Match prototype sections (lines 2295-2486).

### 3.8 AIContextStore Extension

**Files**:
- `frontend/src/stores/ai/AIContextStore.ts`

**Changes**:
- Add `ContextCodeFile`, `ContextCodeSnippet`, `ContextGitRef` types
- Add `codeFiles`, `codeSnippets`, `gitRefs` to `AIContextResult`

### 3.9 Backend Codebase Context Generation

**Files**:
- AI context generation service (existing pipeline)

**Changes**:
- Generate file tree from issue's code references + related PR files
- Extract code snippets from referenced files
- Pull git references (PRs, commits, branches) from GitHub integration

### 3.10 Tests

Unit tests for all new components and store changes.

---

## Phase 4: Enhanced UX (P1)

### 4.1 Task Dependency Graph

**Files**:
- `frontend/src/features/issues/components/task-dependency-graph.tsx` (NEW)

**Implementation**: Canvas-based DAG per prototype (lines 2850-2920). Force-directed layout with task nodes and dependency arrows.

### 4.2-4.3 Enhance Context Chat

**Files**:
- `frontend/src/features/issues/components/enhance-context-chat.tsx` (NEW)

**Implementation**: Inline chat that sends context refinement requests to PilotSpace agent via SSE. Updates AI context on responses.

### 4.4-4.5 Task Interaction UX

- Drag-and-drop reordering
- Click-to-edit inline editing

### 4.6 Tests

Unit tests for graph, chat, and interaction components.

---

## File Change Summary

### New Files (Backend: 6)
1. `backend/src/pilot_space/infrastructure/database/models/task.py`
2. `backend/src/pilot_space/infrastructure/repositories/task_repository.py`
3. `backend/src/pilot_space/application/services/task_service.py`
4. `backend/src/pilot_space/api/v1/routers/workspace_tasks.py`
5. `backend/src/pilot_space/api/v1/schemas/task.py`
6. 2 Alembic migrations

### New Files (Frontend: 8)
1. `frontend/src/services/api/tasks.ts`
2. `frontend/src/stores/TaskStore.ts`
3. `frontend/src/features/issues/components/codebase-context-section.tsx`
4. `frontend/src/features/issues/components/file-tree.tsx`
5. `frontend/src/features/issues/components/code-snippet-card.tsx`
6. `frontend/src/features/issues/components/git-references.tsx`
7. `frontend/src/features/issues/components/task-dependency-graph.tsx`
8. `frontend/src/features/issues/components/enhance-context-chat.tsx`

### Modified Files (Backend: ~5)
1. `backend/src/pilot_space/infrastructure/database/models/issue.py`
2. `backend/src/pilot_space/infrastructure/database/models/__init__.py`
3. `backend/src/pilot_space/api/v1/schemas/issue.py`
4. `backend/src/pilot_space/infrastructure/containers.py`
5. `backend/src/pilot_space/api/v1/routers/__init__.py`

### Modified Files (Frontend: ~6)
1. `frontend/src/stores/RootStore.ts`
2. `frontend/src/stores/ai/AIContextStore.ts`
3. `frontend/src/features/issues/components/ai-context-tab.tsx`
4. `frontend/src/features/issues/components/ai-tasks-section.tsx`
5. `frontend/src/features/issues/components/context-summary-card.tsx`
6. `frontend/src/features/issues/components/prompt-block.tsx`

### Test Files (New: ~6)
1. `backend/tests/services/test_task_service.py`
2. `backend/tests/routers/test_workspace_tasks.py`
3. `frontend/src/stores/__tests__/TaskStore.test.ts`
4. `frontend/src/features/issues/components/__tests__/ai-tasks-section.test.tsx`
5. `frontend/src/features/issues/components/__tests__/copy-all-context-button.test.tsx`
6. Additional component tests

---

## Execution Strategy

```
Week 1: Phase 1 (Backend Foundation)
  Day 1-2: Issue model enhancement + Task model + migrations (1.1-1.4, 1.9-1.10)
  Day 3:   Repository + Service (1.5-1.6)
  Day 4:   Router + Schemas + DI (1.7-1.8, 1.11)
  Day 5:   Backend tests (1.12-1.13)

Week 2: Phase 2 (Frontend Foundation)
  Day 1:   API client + TaskStore (2.1-2.3)
  Day 2:   Issue form enhancements (2.4)
  Day 3:   AI tasks section + copy button (2.5-2.6)
  Day 4:   Wire decompose + component tweaks (2.7-2.9)
  Day 5:   Frontend tests (2.10-2.11)

Week 3: Phase 3 (AI Integration)
  Day 1:   Skill upgrade + persistence (3.1-3.3)
  Day 2-3: Codebase context components (3.4-3.7)
  Day 4:   Store extension + backend generation (3.8-3.9)
  Day 5:   Tests (3.10)

Week 4: Phase 4 (Enhanced UX)
  Day 1-2: Dependency graph (4.1)
  Day 3-4: Enhance context chat (4.2-4.3)
  Day 5:   Task interaction UX + tests (4.4-4.6)
```
