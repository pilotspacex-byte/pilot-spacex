# AI Module - Conversational Interface

_For project overview, see main `README.md` and `frontend/README.md`_

## Purpose

Unified conversational AI interface for PilotSpace. Provides chat with skill invocation, task tracking, human-in-the-loop approvals (DD-003), and context-aware execution via SSE streaming (DD-066).

**Design Decisions**: DD-003 (approval), DD-066 (SSE streaming), DD-086 (centralized agent), DD-087 (skill system), DD-088 (MCP tools)

---

## Directory Structure

```
frontend/src/features/ai/
├── ChatView/                          # Main conversational interface
│   ├── ChatView.tsx                   # Top-level container, store integration
│   ├── ChatHeader.tsx
│   ├── ChatInput/                     # Message input + skill/agent selection
│   ├── MessageList/                   # Virtualized conversation (1000+ messages)
│   ├── TaskPanel/                     # Long-running task tracking
│   ├── ApprovalOverlay/               # Human-in-the-loop approval UI
│   ├── SessionList/                   # Session management
│   └── __tests__/
├── components/                        # Sub-components (15+ files)
│   ├── UserMessage.tsx, AssistantMessage.tsx
│   ├── StreamingContent.tsx           # Animated streaming indicator
│   ├── ThinkingBlock.tsx              # Extended thinking display
│   ├── ToolCallList.tsx, MarkdownContent.tsx
│   └── __tests__/
├── hooks/
│   ├── useSkills.ts                   # Fetch available skills
│   └── index.ts
└── types/
    ├── conversation.ts, events.ts, skills.ts
```

---

## Component Tree

```
ChatView (observer, store integration)
├── ChatHeader (title, status)
├── MessageList (virtualized via Virtuoso)
│   ├── MessageGroup (role-based grouping)
│   └── Message types (User, Assistant, Tool)
├── TaskPanel (collapsible, progress tracking)
├── StreamingBanner (phase indicator)
├── ApprovalOverlay (destructive action approval)
└── ChatInput (auto-resize textarea, slash/mention detection)
```

---

## SSE Streaming Events (DD-066)

| Event              | Purpose                 | UI Effect                   |
| ------------------ | ----------------------- | --------------------------- |
| `message_start`    | Begin assistant message | Show streaming indicator    |
| `text_delta`       | Stream text chunk       | Append text, animate cursor |
| `tool_use`         | Record tool invocation  | Add tool card               |
| `tool_result`      | Store tool output       | Update tool card            |
| `task_progress`    | Update task status      | TaskPanel refresh           |
| `approval_request` | Queue approval (DD-003) | Show modal/card             |
| `message_stop`     | Finalize message        | Clear streaming state       |

SSE client: `frontend/src/lib/sse-client.ts` (POST support, JWT auth, 3-retry reconnect).

---

## Store Integration

All AI state managed by **PilotSpaceStore** (`stores/ai/PilotSpaceStore.ts`).

**Observable**: messages, streamingState, sessionId, tasks (Map), pendingApprovals, noteContext, issueContext, projectContext.

**Actions**: `sendMessage(content)`, `abort()`, `approveAction(id, modifications?)`, `rejectAction(id, reason)`, `setNoteContext(ctx)`.

**Computed**: `isStreaming`, `activeTasks`, `completedTasks`, `hasUnresolvedApprovals`.

---

## Skill & Agent Invocation

**Skills** (single-turn, slash commands): Defined in `.claude/skills/` (backend). Discovered via `useSkills()` hook. Invoked as `/extract-issues`, `/enhance-issue`.

**Agents** (multi-turn, @mentions): `@pr-review`, `@ai-context`, `@doc-generator`.

---

## Approval Classification (DD-003)

| Category         | Examples                   | Approval Required  | UI                      |
| ---------------- | -------------------------- | ------------------ | ----------------------- |
| Non-destructive  | Add label, assign          | No (auto-execute)  | SuggestionCard (inline) |
| Content creation | Create issue, post comment | Yes (configurable) | SuggestionCard (inline) |
| Destructive      | Delete issue, merge PR     | Always             | ApprovalOverlay (modal) |

---

## API Integration

**Chat endpoint**: `POST /api/v1/ai/chat` with body `{ message, context: { note_id, issue_id, project_id }, session_id }`. Returns SSE stream.

---

## Troubleshooting

| Problem                        | Solution                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------- |
| Messages not appearing         | Check `store.messages` in DevTools, verify `message_start` SSE event, ensure `observer()` wrapper |
| Approval modal not showing     | Check `store.pendingApprovals`, verify event type (destructive vs non-destructive)                |
| Context not retained on resume | Check `store.noteContext` after resume, verify `SessionListStore.resumeSessionForContext()`       |
| SSE connection dropping        | Check network tab, monitor auto-reconnect (3 retries), verify auth token                          |

---

## Related Documentation

- `docs/architect/pilotspace-agent-architecture.md`
- `docs/dev-pattern/45-pilot-space-patterns.md`
- `docs/dev-pattern/21c-frontend-mobx-state.md`
