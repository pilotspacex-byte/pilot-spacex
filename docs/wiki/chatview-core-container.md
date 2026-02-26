# ChatView: Core Container & Control Components

> **Location**: `frontend/src/features/ai/ChatView/`
> **Design Decisions**: DD-003 (Human-in-the-loop), DD-086 (Centralized Agent)

## Overview

`ChatView` is the root orchestrator of the AI conversation interface. It manages a complete AI session lifecycle — SSE streaming, session resume, approval routing, task tracking, and error recovery — and coordinates all sub-panels through a single `PilotSpaceStore` MobX observable. Status components (`StreamingBanner`, `WaitingIndicator`, `QueueDepthIndicator`, `ConfirmAllButton`) are thin single-responsibility renderers driven entirely by store state.

---

## Component Hierarchy

```
ChatView.tsx  (observer, main orchestrator)
├── ChatHeader.tsx              ← title bar
├── StreamingBanner.tsx         ← phase-aware streaming status
├── WaitingIndicator.tsx        ← blocks on user-response-required
├── QueueDepthIndicator.tsx     ← skill queue depth
├── ConfirmAllButton.tsx        ← batch approve high-confidence intents
├── MessageList/                ← conversation transcript
│   └── (24 sub-components)
├── TaskPanel/                  ← AI task decomposition tracker
├── ApprovalOverlay/            ← destructive action modal
│   └── DestructiveApprovalModal
├── ChatInput/                  ← input + command menus
└── ChatViewErrorBoundary.tsx   ← error isolation wrapper
```

---

## `ChatView.tsx`

**488 lines** — The single source of coordination for the entire AI conversation.

### Props

```typescript
interface ChatViewProps {
  workspaceId: string;
  noteId?: string;          // Current note context
  issueId?: string;         // Current issue context
  projectId?: string;       // Current project context
  initialPrompt?: string;   // Auto-send on mount (used from Note Canvas)
  onClose?: () => void;
  className?: string;
}
```

### 4 Critical Lifecycle Effects

#### 1. Session Auto-Resume on Context Change

When `noteId`/`issueId`/`projectId` changes, ChatView checks the backend for an existing session for that context and automatically loads it.

```typescript
const loadedContextRef = useRef<string | null>(null);  // tracks last-loaded context
const isResumingRef = useRef(false);                   // prevents race conditions

// Guard: only run if context actually changed
if (loadedContextRef.current === noteId) return;
loadedContextRef.current = noteId;
```

**Why**: Users navigating between notes should land in their prior conversation for that note, not a blank slate.

#### 2. Initial Prompt Auto-Send (fire-once guard)

```typescript
const initialPromptFiredRef = useRef(false);

if (initialPrompt && !initialPromptFiredRef.current && store.messages.length === 0) {
  initialPromptFiredRef.current = true;
  store.sendMessage(initialPrompt);
}
```

**Why**: The Note Canvas can trigger ChatView with a pre-filled prompt (e.g., "Summarize this note"). The `useRef` guard prevents re-firing on component re-mounts.

#### 3. Task Panel Auto-Open

Watches `store.tasks` — when the first task appears in the stream, auto-opens the TaskPanel side panel without user action.

**Why**: Tasks represent AI work decomposition. Surfacing them immediately keeps users informed of what the agent is doing.

#### 4. Destructive Modal Auto-Open

Watches `store.pendingApprovals` — when a destructive action approval enters the queue, auto-opens `DestructiveApprovalModal`.

**Why**: Destructive actions (delete, merge PR) must be non-deferrable. Auto-surfacing the modal ensures users can't accidentally miss it.

### Approval Routing

ChatView splits pending approvals from `store.pendingApprovals` into two buckets:

```typescript
const DESTRUCTIVE_ACTIONS = new Set([
  'delete_issue', 'merge_pr', 'close_issue',
  'archive_workspace', 'delete_note', 'delete_comment', ...
]);

function isDestructiveAction(actionType: string): boolean {
  return DESTRUCTIVE_ACTIONS.has(actionType);
}
```

| Bucket | Component | Behavior |
|--------|-----------|----------|
| Destructive | `DestructiveApprovalModal` | Blocking, 5-min auto-reject, non-dismissable |
| Non-destructive | `InlineApprovalCard` (in MessageList) | Non-blocking, 24h expiration, optional reason |

### Data Flow

```
User sends message
       ↓
store.sendMessage()  →  POST /api/v1/ai/chat  (SSE stream opens)
       ↓
Backend streams 14 SSE event types
       ↓
PilotSpaceStreamHandler processes each event
       ↓
MobX observables update  →  @observer components re-render
  - messages         → MessageList appends
  - streamingPhase   → StreamingBanner updates
  - tasks            → TaskPanel updates
  - pendingApprovals → InlineApprovalCard / DestructiveApprovalModal appear
  - intents          → IntentCard / SkillProgressCard appear
  - queueDepth       → QueueDepthIndicator updates
```

### MobX Store Integration

Key observables read by ChatView and its children:

| Observable | Type | Consumer |
|-----------|------|---------|
| `store.messages` | `ChatMessage[]` | MessageList |
| `store.streamingPhase` | `StreamingPhase \| null` | StreamingBanner |
| `store.isStreaming` | `boolean` | ChatInput (disable), WorkingIndicator |
| `store.isWaitingForUser` | `boolean` | WaitingIndicator |
| `store.tasks` | `AgentTask[]` | TaskPanel |
| `store.pendingApprovals` | `ApprovalRequest[]` | InlineApprovalCard, DestructiveApprovalModal |
| `store.intents` | `Map<string, Intent>` | IntentCard, SkillProgressCard, ConfirmAllButton |
| `store.queueDepth` | `number` | QueueDepthIndicator |
| `store.error` | `string \| null` | ChatViewErrorBoundary |

---

## `ChatHeader.tsx`

**96 lines** — Compact header bar showing session title and close/actions controls.

**Displays**:
- Session title (or "New Conversation" default)
- Agent badge (e.g., "PilotSpace", "@pr-review") when agent-routing is active
- Session actions: New session, close panel

**Why separate**: Single Responsibility Principle. Header appearance/actions change independently of conversation logic.

---

## `StreamingBanner.tsx`

**167 lines** — Phase-aware streaming status banner positioned above the message list.

### 9 Streaming Phases

| Phase | Display | Extra info |
|-------|---------|-----------|
| `thinking` | "Thinking…" | Elapsed time (e.g., "4.2s") |
| `tool_use` | Tool display name (e.g., "Reading note") | Elapsed time |
| `content` | "Responding…" | Word count (e.g., "42 words") |
| `connecting` | "Connecting…" | — |
| `completing` | "Completing…" | — |
| `message_start` | "Starting…" | — |
| `stopped` | "Stopped" | Auto-hides after 1.5s |
| `null` | Hidden | — |

**Elapsed time**: Computed from `startedAt` timestamp in store, updated every 100ms via `setInterval`.

**Word count**: Counts spaces + 1 in the streaming text buffer.

**Why phase granularity?** Different phases have very different durations. "Thinking" for 8s is normal for complex reasoning; users seeing "Responding…" for 8s would assume it's slow. Phase labels set correct expectations.

---

## `WaitingIndicator.tsx`

**78 lines** — Animated banner that appears when the agent is waiting for required user input.

**Triggered by**: `store.isWaitingForUser === true` (set by SSE `approval_request` events where the action is `requires_response`, not `approval`).

**Visual**: Pulsing amber "Waiting for your response…" with a pause icon.

**Why**: Distinguishes "AI is computing" (StreamingBanner) from "AI has paused and needs the user to act" (WaitingIndicator). Without this distinction, users wait indefinitely not knowing the AI is blocked.

---

## `QueueDepthIndicator.tsx`

**94 lines** — Shows how many skill executions are queued behind the current one.

**Triggers**: Visible only when `store.queueDepth > 0`.

**Display**: "2 more in queue" with an optional concurrency limit badge.

**Architecture context**: PilotSpaceAgent can queue multiple skill invocations (e.g., extract-issues + enhance-issue + recommend-assignee). This indicator lets users see that more work is coming even if the current stream looks complete.

**Why separate from StreamingBanner?** Queue depth is orthogonal to streaming phase. A skill can be completing while 2 more are queued.

---

## `ConfirmAllButton.tsx`

**135 lines** — Batch-approve button for high-confidence pending intents.

**Condition for rendering**: `store.intents` contains ≥ 1 intent with:
- `status === 'detected'` (pending approval)
- `confidence >= 0.70` (≥ 70% — high confidence threshold, T-059)

**Action**: Calls `store.confirmAllHighConfidenceIntents()` which:
1. Filters intents by confidence ≥ 0.70
2. Sends batch POST `/ai/intents/confirm-all`
3. Updates each intent status to `'confirmed'` in store

**Why confidence threshold?** Low-confidence intents (< 70%) may be misclassified. Batch-confirming all would be unsafe. The 70% threshold is the product-level definition of "high confidence" (see T-059).

**Why separate from individual IntentCard confirm buttons?** Power users with many detected intents from a long note should not have to click 8 individual confirmations. One button for the common case.

---

## `ChatViewErrorBoundary.tsx`

**64 lines** — React error boundary wrapping the entire ChatView tree.

**Catches**: Any unhandled exception from ChatView or its children.

**Recovery UI**: Friendly error message + "Try again" button that calls `this.setState({ hasError: false })` to reset the boundary and re-mount the subtree.

**Why not just a `try/catch`?** React rendering errors cannot be caught with `try/catch`. Error boundaries are the React-native mechanism. Without it, a single rendering error would unmount the entire workspace.

---

## `types.ts` — Shared Type Hub

**152 lines** — Canonical TypeScript types for the entire ChatView subsystem.

Key types:
- `AgentTask` — task item with `state: 'pending' | 'running' | 'done' | 'failed'`
- `ApprovalRequest` — destructive vs. non-destructive approval
- `NoteContext`, `IssueContext`, `ProjectContext` — typed context containers
- `SkillDefinition`, `AgentDefinition` — slash-command and `@mention` descriptors
- `SessionSummary` — condensed session for history picker
- `StreamingPhase` — union type of all 9 phases

**Why centralized types?** ChatInput, MessageList, ApprovalOverlay, and TaskPanel all share these types. A single source prevents drift and type mismatches across the 80+ files in the ChatView subtree.

---

## `constants.ts` — Static Definitions

**244 lines** — Static skill/agent/category/tool display names.

**Sections**:
- `SKILLS` — 10 hardcoded fallback skills with category, icon, examples
- `SESSION_SKILLS` — `\resume`, `\new` (always available)
- `AGENTS` — 3 agent definitions (pr-review, ai-context, doc-generator)
- `SKILL_CATEGORIES` — ordered category list with display labels
- `TOOL_DISPLAY_NAMES` — maps MCP tool IDs (`note.read_note`) → human labels ("Reading note")
- `FALLBACK_SKILLS` — subset of SKILLS for when API is unreachable

**Why tool display names here?** `StreamingBanner` and `ToolCallCard` need human-readable names for MCP tool calls. Centralizing them prevents 6+ files each having their own string mappings.

---

## `index.ts` — Public Exports

**44 lines** — Barrel file exporting only the public API of the ChatView feature:
- `ChatView` (default)
- `ChatViewErrorBoundary`
- Key types re-exported for consumers

**Why selective exports?** Internal components like `MessageList`, `StreamingBanner`, and `ConfirmAllButton` are implementation details. External consumers (e.g., the Note Canvas or Issue Detail page) only need `ChatView`.

---

## Implicit Features

| Feature | Mechanism | Location |
|---------|-----------|---------|
| Session auto-resume on context change | `loadedContextRef` + effect | `ChatView.tsx` |
| Initial prompt fire-once guard | `initialPromptFiredRef` | `ChatView.tsx` |
| TaskPanel auto-open on first task | `store.tasks` watcher | `ChatView.tsx` |
| Destructive modal auto-open | `store.pendingApprovals` watcher | `ChatView.tsx` |
| Phase-specific elapsed time | `setInterval` 100ms | `StreamingBanner.tsx` |
| "Stopped" state auto-hide after 1.5s | `setTimeout` on `stopped` phase | `StreamingBanner.tsx` |
| Word count during content phase | Space-count on streaming buffer | `StreamingBanner.tsx` |
| Queue depth badge | `store.queueDepth` observable | `QueueDepthIndicator.tsx` |
| Batch confirm 70% threshold | `confidence >= 0.70` filter | `ConfirmAllButton.tsx` |
| Error boundary retry | `setState({ hasError: false })` | `ChatViewErrorBoundary.tsx` |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `ChatView.tsx` | ~488 | Main orchestrator, session lifecycle, approval routing |
| `ChatHeader.tsx` | ~96 | Session title, agent badge, close/new session actions |
| `StreamingBanner.tsx` | ~167 | 9-phase streaming status with elapsed time / word count |
| `WaitingIndicator.tsx` | ~78 | "AI waiting for user" blocker indicator |
| `QueueDepthIndicator.tsx` | ~94 | Skill queue backlog display |
| `ConfirmAllButton.tsx` | ~135 | Batch approve high-confidence intents (≥70%) |
| `ChatViewErrorBoundary.tsx` | ~64 | React error boundary with retry |
| `types.ts` | ~152 | Canonical shared types for ChatView subsystem |
| `constants.ts` | ~244 | Skills, agents, tool display names, categories |
| `index.ts` | ~44 | Public barrel exports |
