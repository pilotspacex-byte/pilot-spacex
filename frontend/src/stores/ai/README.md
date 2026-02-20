# AI Stores Architecture

**Scope**: 11 AI-related MobX stores under AIStore hub
**Parent**: [`../README.md`](../README.md)

---

## Store Overview

| Store                     | File                       | Purpose                                      |
| ------------------------- | -------------------------- | -------------------------------------------- |
| **AIStore** (root)        | `AIStore.ts`               | Container + lifecycle for all AI stores      |
| **PilotSpaceStore**       | `PilotSpaceStore.ts`       | Unified agent orchestration (DD-086)         |
| **GhostTextStore**        | `GhostTextStore.ts`        | Inline text suggestions (Gemini Flash, <2s)  |
| **ApprovalStore**         | `ApprovalStore.ts`         | Human-in-the-loop approval workflow (DD-003) |
| **AIContextStore**        | `AIContextStore.ts`        | Issue context aggregation via SSE            |
| **MarginAnnotationStore** | `MarginAnnotationStore.ts` | Per-block margin AI suggestions              |
| **CostStore**             | `CostStore.ts`             | Token usage and cost tracking                |
| **AISettingsStore**       | `AISettingsStore.ts`       | Workspace AI feature flags                   |
| **PRReviewStore**         | `PRReviewStore.ts`         | PR review state (legacy)                     |
| **ConversationStore**     | `ConversationStore.ts`     | Deprecated -- replaced by PilotSpaceStore    |
| **SessionListStore**      | `SessionListStore.ts`      | Chat session listing                         |

---

## AIStore (Root Hub)

**Implementation**: `AIStore.ts` (85 lines)

Container and lifecycle manager. Provides `isGloballyEnabled` master switch, `loadWorkspaceSettings(workspaceId)` to initialize feature flags, `abortAllStreams()` for cleanup, and `reset()` for logout.

---

## PilotSpaceStore (Unified Agent)

**Implementation**: `PilotSpaceStore.ts` (581 lines) -- largest and most critical AI store.

Central orchestration for all user-facing AI conversations per DD-086.

**Key Observables**:

- `messages: ChatMessage[]` -- full conversation history
- `streamingState` -- isStreaming, streamContent, thinkingContent, activeToolName, interrupted, wordCount
- `sessionId`, `sessionState` -- session lifecycle (isActive, createdAt, lastActivityAt)
- `forkSessionId` -- "what-if" session branches
- `totalMessages`, `hasMoreMessages`, `isLoadingMoreMessages` -- scroll-up pagination
- `tasks: Map<string, TaskState>` -- task progress tracking (pending/in_progress/completed/failed)
- `pendingApprovals: ApprovalRequest[]` -- inline approval queue
- `pendingContentUpdates` -- buffered content updates (FIFO, max 100)
- `noteContext`, `issueContext`, `projectContext`, `workspaceId` -- conversation context
- `activeSkill`, `mentionedAgents`, `skills: SkillDefinition[]` -- skill registry
- `error: string | null`

**Key Computed**:

- `isStreaming`, `streamContent`, `pendingToolCalls`, `hasUnresolvedApprovals`
- `activeTasks`, `completedTasks`, `conversationContext`, `tokenBudgetPercent`

**Key Actions**:

- `sendMessage(content, metadata?)` -- handles session resumption, skill activation, context injection, token budget (8K limit). Delegated to `PilotSpaceActions.ts`.
- `addMessage()`, `prependMessages()` -- message management
- `addTask()`, `updateTaskStatus()`, `removeTask()` -- task lifecycle
- `addApproval()`, `approveRequest()`, `rejectRequest()`, `approveAction()`, `rejectAction()` -- approval flow
- `setNoteContext()`, `setIssueContext()`, `setProjectContext()`, `clearContext()` -- context management
- `setActiveSkill()`, `addMentionedAgent()` -- skill invocation
- `abort()`, `clearConversation()`, `reset()`

**Delegates**: Stream handling to `PilotSpaceStreamHandler.ts`, async actions to `PilotSpaceActions.ts`.

**Buffering**: Tool calls and citations buffer in `_pendingToolCalls[]`/`_pendingCitations[]` until `message_stop`. Content updates buffer in `pendingContentUpdates[]` (FIFO, max 100), consumed by noteId.

**Type Interfaces**: See `types/conversation.ts` for `TaskState`, `ApprovalRequest`, `ChatMessage`, `StreamingState`.

---

## GhostTextStore

**Implementation**: `GhostTextStore.ts` (155 lines)

Inline text suggestions with debouncing and LRU caching (DD-067: Gemini Flash, <2s).

**Key Observables**: `suggestion`, `isLoading`, `isEnabled`, `error`

**Key Actions**:

- `requestSuggestion(noteId, context, prefix, workspaceId)` -- 500ms debounce, LRU cache (max 10), cache key = noteId + context suffix + prefix suffix
- `clearSuggestion()`, `abort()`, `setEnabled()`

Rate limit 429 handled silently.

---

## ApprovalStore

**Implementation**: `ApprovalStore.ts` (150+ lines)

Human-in-the-loop approval workflow (DD-003).

**Key Observables**: `requests: ApprovalRequest[]`, `pendingCount`, `isLoading`, `error`, `selectedRequest`, `filter`

**Key Computed**: `groupedByAgent` -- groups requests by agent name

**Key Actions**:

- `loadPending()`, `loadAll(status?)`
- `approveRequest(requestId)`, `rejectRequest(requestId, reason?)`
- `selectRequest()`, `setFilter()`

---

## AIContextStore

**Implementation**: `AIContextStore.ts` (200+ lines)

Issue context aggregation with SSE streaming and structured sections.

**Key Observables**: `isLoading`, `isEnabled`, `error`, `currentIssueId`, `result: AIContextResult | null`, `sectionErrors`

**Result Structure**: `AIContextResult` contains `summary`, `relatedIssues`, `relatedDocs`, `tasks`, `prompts`. See `types/` for full interfaces.

**Key Actions**:

- `generateContext(issueId)` -- streams SSE from `/api/v1/ai/context/{issueId}`, populates sections incrementally
- `abort()`, `setEnabled()`, `getContextForIssue(issueId)` (cached, max 20 items)

---

## MarginAnnotationStore

**Implementation**: `MarginAnnotationStore.ts`

Per-block margin AI suggestions.

**Key Observables**: `annotations: Map<string, NoteAnnotation[]>` (noteId keyed), `isLoading`, `isEnabled`, `error`

**Key Actions**: `generateAnnotations(noteId, content)`, `acceptAnnotation()`, `rejectAnnotation()`, `clearAnnotations()`

---

## CostStore

**Implementation**: `CostStore.ts`

Read-only token usage and cost tracking.

**Key Observables**: `costs: AICost[]`, `isLoading`

**Key Actions**: `loadCosts(workspaceId, dateRange)`, `getCostByAgent()`, `getCostTrend(days)`, `getTotalCost(dateRange?)`

---

## AISettingsStore

**Implementation**: `AISettingsStore.ts`

Workspace AI feature flags and provider configuration.

**Key Observables**: `ghostTextEnabled`, `aiContextEnabled`, `prReviewEnabled`, `annotationsEnabled`, `isLoading`

**Key Actions**: `loadSettings(workspaceId)`, `updateSetting(key, value)`

---

## PRReviewStore

**Implementation**: `PRReviewStore.ts`

PR review state (legacy -- being migrated to PilotSpaceStore subagent model).

**Key Observables**: `reviews: Map<string, PRReview>`, `isLoading`, `error`

**Key Actions**: `requestReview(prId)`, `abort()`

---

## File Organization

```
frontend/src/stores/ai/
├── AIStore.ts                       # Root AI store (hub + lifecycle)
├── PilotSpaceStore.ts               # Unified agent orchestration (581 lines)
├── PilotSpaceStreamHandler.ts       # SSE stream handling
├── PilotSpaceActions.ts             # Async actions
├── PilotSpaceSSEParser.ts           # Event parsing
├── PilotSpaceToolCallHandler.ts     # Tool call processing
├── PilotSpaceApprovals.ts           # Approval delegation
├── GhostTextStore.ts                # Inline suggestions (155 lines)
├── AIContextStore.ts                # Issue context aggregation
├── ApprovalStore.ts                 # Human-in-the-loop approvals
├── AISettingsStore.ts               # Feature flags
├── PRReviewStore.ts                 # PR review (legacy)
├── MarginAnnotationStore.ts         # Margin annotations
├── CostStore.ts                     # Cost tracking
├── ConversationStore.ts             # Deprecated
├── SessionListStore.ts              # Session list
├── types/
│   ├── conversation.ts              # ChatMessage, ToolCall, TaskState, etc.
│   ├── events.ts                    # SSE event types
│   ├── skills.ts                    # Skill definitions
│   └── index.ts
├── __tests__/
├── PILOTSPACE_STORE_USAGE.md        # Usage guide
└── index.ts
```

---

## Related Documentation

- **Parent Store Architecture**: [`../README.md`](../README.md)
- **AI Feature Module**: [`../../features/ai/README.md`](../../features/ai/README.md)
- **Design Decisions**: DD-003 (approvals), DD-065 (state split), DD-086 (centralized agent)
