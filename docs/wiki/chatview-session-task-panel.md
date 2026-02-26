# ChatView: SessionList & TaskPanel

> **Location**: `frontend/src/features/ai/ChatView/SessionList/` and `frontend/src/features/ai/ChatView/TaskPanel/`
> **Design Decisions**: DD-066 (SSE Streaming), DD-086 (Centralized Agent)

## Overview

**SessionList** solves conversation continuity — letting users return to prior AI conversations across page refreshes, navigation, and workspace switches. **TaskPanel** solves execution transparency — surfacing what the AI agent is doing step-by-step in real time. They address orthogonal concerns (past context vs. present progress) and share only the `PilotSpaceStore` as their data source.

---

## SessionList

> Manages conversation history and enables resumption of prior sessions.

### Architecture

```
SessionList.tsx  (observer)
└── Session item (per session)
    ├── Title (first message or "Untitled conversation")
    ├── Context badges (up to 3 unique note/issue contexts)
    ├── Turn count ("5 turns")
    ├── Relative timestamp ("2h ago", "3d ago")
    └── Agent badge (e.g., "@pr-review") if non-default agent
```

**Store**: `SessionListStore` (497 lines) — manages session CRUD, pagination, search, and the resume flow that feeds into `PilotSpaceStore`.

### Session Lifecycle

```
Create: User sends first message in a new context
  → POST /api/v1/ai/sessions { workspaceId, context }
  → store.currentSession = new session

Active: User messages flow; session tracks context history
  → store.sessions.get(id).turnCount++
  → store.sessions.get(id).contextHistory.push(ctx)

Persist: Redis hot cache (30-min sliding TTL) → PostgreSQL (24h durable storage)

Resume: User selects session from SessionList
  → GET /api/v1/ai/sessions/{id}/messages?limit=3  (last 3 messages on resume)
  → PilotSpaceStore.loadSession(session, messages)
  → User can scroll up to load older messages (10 per page)

Expire: After 24h of inactivity → soft-deleted from PostgreSQL
        Session list removes it; no hard delete (audit trail)
```

### Session Persistence Architecture

| Storage | TTL | Purpose |
|---------|-----|---------|
| Redis | 30-min sliding expiry | Hot path: fast session lookup during active conversation |
| PostgreSQL | 24-hour durable | Resume after long gaps, multi-device access, audit |

**Why 24 hours, not longer?** Product decision: AI conversations are ephemeral by nature. Long-term persistence (weeks/months) creates privacy concerns and storage costs without proportional value.

### Session Resume Flow

1. User triggers `\resume` in ChatInput → `SessionResumeMenu` opens
2. User selects a session
3. `onSelectSession(sessionId)` called in ChatView
4. `GET /api/v1/ai/sessions/{id}/messages?limit=3` fetches last 3 messages
5. `PilotSpaceStore.loadSession()` replaces current messages with resumed ones
6. `useIntentRehydration()` fetches any pending `detected`/`executing` intents for the workspace
7. User sees the conversation where they left off
8. Scrolling up triggers pagination (10 messages per fetch)

**Why load only 3 messages on resume?** Showing the full history of a 50-turn conversation would be overwhelming. The last 3 messages give immediate context; older history is available on demand via scroll.

### Session Forking

A session can be "forked" — creating a new independent branch from a point in history. Used for "what if I had said X instead?" exploration.

**Flow**: User right-clicks a message → "Fork from here" → `POST /api/v1/ai/sessions/{id}/fork { fromMessageId }` → new session with history up to that message.

### `SessionList.tsx` (187 lines)

**Responsibility**: Renders the scrollable session list with date grouping and context previews.

**Date groups**: Today / Yesterday / Weekday name (last 7 days) / Full date (older)

**Per-session badge extraction**: Deduplicates context entries across the session's `contextHistory` array. Shows at most 3 badges (note + issue icons with truncated titles).

**Empty state**: "No previous conversations" with a prompt to start a new session.

---

## TaskPanel

> Displays real-time AI task decomposition and execution progress.

### Architecture

```
TaskPanel.tsx  (observer, container)
├── TaskSummary.tsx     ← aggregate stats (X/Y tasks done, ETA)
└── TaskList.tsx        ← scrollable task list
    └── TaskItem.tsx    ← individual task with state indicator
```

### What is a "Task"?

When the `PilotSpaceAgent` receives a complex request, it decomposes it into sub-tasks before executing. Each sub-task is an `AgentTask`:

```typescript
interface AgentTask {
  taskId: string;
  name: string;             // e.g., "Extract issues from note"
  description?: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  progress?: number;        // 0–100 percentage
  eta?: number;             // estimated seconds remaining
  agentName?: string;       // which subagent is executing this task
  modelId?: string;         // which model (claude-opus, gemini-flash, etc.)
  steps?: TaskStep[];       // fine-grained sub-steps within this task
  startedAt?: Date;
  completedAt?: Date;
  error?: string;           // if status === 'failed'
}
```

### SSE-Driven Updates

```
PilotSpaceAgent dispatches task_progress SSE events
       ↓
{ taskId, name, status, progress, eta, steps, agentName }
       ↓
PilotSpaceStreamHandler.handleTaskProgress()
       ↓
store.tasks.get(taskId) updated (or created if new)
       ↓
TaskPanel (observer) re-renders automatically
```

**Auto-open**: ChatView watches `store.tasks` and auto-opens TaskPanel when the first task appears.

### `TaskPanel.tsx` (container, ~120 lines)

**Responsibility**: Provides the collapsible side panel shell and a "View tasks" toggle button.

**Collapse behavior**: TaskPanel can be minimized to a header tab. When minimized, a badge shows the count of in-progress tasks.

**Why a separate panel (not in MessageList)?** Tasks are operational metadata — _how_ the agent is doing work, not _what_ it's saying. Mixing them into the conversation stream would obscure the conversation thread. The panel keeps them accessible without polluting the message feed.

### `TaskSummary.tsx` (~100 lines)

**Responsibility**: Aggregate header showing overall session progress.

**Displays**:
- "X of Y tasks complete" count
- Estimated total remaining time (sum of task ETAs)
- Success/failure badge for completed sessions
- Active agent and model name (if single agent is running)

**Computed from**: `store.tasks` MobX observable — recomputes automatically as tasks update.

### `TaskList.tsx` (~80 lines)

**Responsibility**: Scrollable list of `TaskItem` components. Sorts tasks: `running` first, then `pending`, then `done`/`failed`.

**Why running first?** The user's primary interest is what's happening now, not what's queued or done.

### `TaskItem.tsx` (~80 lines)

**Responsibility**: Renders a single task with its current state.

**Status indicators**:

| Status | Visual | Description |
|--------|--------|-------------|
| `pending` | Gray circle | Queued, not started |
| `running` | Orange spinner | Currently executing |
| `done` | Green checkmark | Completed successfully |
| `failed` | Red X | Failed with error |

**Step expansion**: If a task has `steps[]`, a "Show steps" chevron expands them inline.

**Progress bar**: Shown when `progress` is provided (0–100%). Useful for long-running tasks like embedding generation.

**ETA display**: "~30s remaining" shown in gray when `eta` is provided and task is `running`.

**Agent badge**: When multiple subagents are running, each task shows which agent is executing it (e.g., "PR Review", "AI Context").

**Error message**: For `failed` tasks, shows the error string in red below the task name.

---

## Implicit Features

| Feature | Mechanism | Location |
|---------|-----------|---------|
| Session date bucketing | Computed from `updatedAt` diff | `SessionList.tsx` |
| Context badge deduplication | `Set<string>` per note/issue ID | `SessionList.tsx` |
| Auto-open TaskPanel on first task | `store.tasks` watcher in ChatView | `ChatView.tsx` |
| TaskList auto-sort (running first) | Sort in `TaskList.tsx` computed | `TaskList.tsx` |
| Task ETA countdown | Re-renders via MobX reaction | `TaskItem.tsx` |
| Progress bar for long tasks | `AgentTask.progress` field | `TaskItem.tsx` |
| In-progress count badge (minimized) | MobX `computed()` | `TaskPanel.tsx` |
| Message pagination on scroll-up | Debounced scroll listener | `MessageList.tsx` |
| Session forking | Right-click context menu | `SessionList.tsx` |
| Session search | Debounced query → API | `SessionList.tsx` |
| Resume with 3 messages then paginate | Limit=3 on initial load | `SessionListStore` |
| 30-min Redis TTL auto-extend | Backend middleware | Backend (not frontend) |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| TaskPanel separate from MessageList | Tasks are operational metadata, not conversation content. Separate panel prevents clutter. |
| Auto-open TaskPanel on first task | Users should be informed of AI work decomposition automatically, not have to find a toggle. |
| Sessions limited to 24h | Balances resume convenience with storage cost and privacy. |
| 3 messages on resume, paginate for more | Shows immediate context without overwhelming the user with a long backscroll. |
| Running tasks sorted first | Primary user interest during execution is what's active now. |
| Step expansion optional | Most users care about task-level status; step detail is for debugging. |
| Session forking | Enables experimentation without losing the original conversation thread. |
| Redis + PostgreSQL dual persistence | Redis for latency-critical lookup during active sessions; PostgreSQL for durable cross-session resume. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `SessionList/SessionList.tsx` | ~187 | Session history list with date grouping |
| `SessionList/index.ts` | ~5 | Barrel export |
| `TaskPanel/TaskPanel.tsx` | ~120 | Collapsible task panel container |
| `TaskPanel/TaskSummary.tsx` | ~100 | Aggregate stats (X/Y tasks, ETA) |
| `TaskPanel/TaskList.tsx` | ~80 | Sorted task list |
| `TaskPanel/TaskItem.tsx` | ~80 | Individual task with status, steps, ETA |
