# ChatView Feature Wiki

> **Location**: `frontend/src/features/ai/ChatView/`
> **Related design decisions**: DD-003, DD-066, DD-086

## Overview

ChatView is the primary AI conversation interface of Pilot Space. It surfaces the `PilotSpaceAgent` orchestrator (DD-086) to users via a real-time SSE-driven conversation UI. It handles message streaming, skill invocation, agent routing, human-in-the-loop approvals (DD-003), task decomposition visualization, session management, and error recovery — all coordinated through a single `PilotSpaceStore` MobX observable tree.

---

## Feature Documents

| Document | What it covers |
|----------|----------------|
| [Core Container & Control Components](./chatview-core-container.md) | `ChatView.tsx` orchestrator, `ChatHeader`, `StreamingBanner`, `WaitingIndicator`, `QueueDepthIndicator`, `ConfirmAllButton`, `ChatViewErrorBoundary`, `types.ts`, `constants.ts` |
| [MessageList System](./chatview-message-list.md) | 23-component polymorphic message renderer: user/assistant messages, streaming, thinking blocks, tool call timelines, structured results, questions, intents, approvals, citations, context |
| [ChatInput System](./chatview-chat-input.md) | Slash-command skill autocomplete, agent `@mention` routing, context indicator, session resume picker, working indicator, `useSkills` hook, `useIntentRehydration` hook |
| [ApprovalOverlay System](./chatview-approval-overlay.md) | DD-003 human-in-the-loop: destructive modal (5-min auto-reject), inline approval cards (24h), content diff, issue preview, batch confirm |
| [SessionList & TaskPanel](./chatview-session-task-panel.md) | Session history with resume/fork, Redis+PG persistence, task decomposition live tracking, SSE-driven step progress |

---

## Component Map

```
ChatView.tsx  (MobX observer, main orchestrator)
│
├── ChatHeader.tsx               ← session title, agent badge, actions
├── StreamingBanner.tsx          ← 9-phase streaming status + elapsed time
├── WaitingIndicator.tsx         ← "AI waiting for user" blocker
├── QueueDepthIndicator.tsx      ← skill queue backlog count
├── ConfirmAllButton.tsx         ← batch approve ≥70% confidence intents
│
├── MessageList/                 ← virtual-scroll conversation transcript
│   ├── MessageGroup             ← session context grouping
│   │   └── ConversationBlock   ← one turn (user + assistant)
│   │       ├── UserMessage
│   │       └── AssistantMessage
│   │           ├── StreamingContent + InlineStreamingIndicator
│   │           ├── MarkdownContent
│   │           ├── ThinkingBlock (live timer, auto-collapse 300ms)
│   │           ├── ReasoningGroup
│   │           ├── ToolCallCard / ToolCallList / ToolStepTimeline
│   │           ├── StructuredResultCard (6 schema variants)
│   │           ├── QuestionBlock → ResolvedSummary
│   │           ├── IntentCard / SkillProgressCard (via IntentMessageRenderer)
│   │           ├── InlineApprovalCard / SkillApprovalCard
│   │           ├── CitationList
│   │           └── ContextCards
│   └── ContextSwitchIndicator   ← between-turn context change divider
│
├── TaskPanel/                   ← AI task decomposition sidebar
│   ├── TaskSummary              ← X/Y complete, ETA, agent badge
│   └── TaskList → TaskItem     ← per-task status, steps, progress bar
│
├── ApprovalOverlay/             ← blocking destructive action modal
│   ├── DestructiveApprovalModal ← 5-min auto-reject, non-dismissable
│   │   ├── ContentDiff          ← before/after text comparison
│   │   ├── IssuePreview         ← issue creation/deletion preview
│   │   ├── IssueUpdatePreview   ← field change preview
│   │   └── GenericJSON          ← fallback for unknown action types
│
├── SessionList/                 ← conversation history + resume
│   └── SessionList              ← date-grouped, context badges, fork
│
└── ChatInput/                   ← intent-detection input engine
    ├── ChatInput                ← textarea, trigger detection, keyboard
    ├── SkillMenu                ← \skill slash-command autocomplete
    ├── AgentMenu                ← @agent mention picker
    ├── ContextIndicator         ← attached note/issue/project badges
    ├── SessionResumeMenu        ← \resume session history picker
    └── WorkingIndicator         ← spinner + rotating idioms
```

---

## Key Flows

### 1. User Sends a Message

```
User types → ChatInput detects trigger or submits
  → store.sendMessage(text, context)
  → POST /api/v1/ai/chat (SSE stream opens)
  → PilotSpaceStreamHandler processes events:
      text_delta         → StreamingContent updates
      thinking_delta     → ThinkingBlock renders
      tool_use           → ToolCallCard appears
      tool_result        → ToolCallCard shows result (or StructuredResultCard)
      task_progress      → TaskPanel step list updates
      approval_request   → DestructiveApprovalModal or InlineApprovalCard
      intent_detected    → IntentCard appears
      message_stop       → streaming ends, StreamingContent → MarkdownContent
```

### 2. Slash Command Invocation

```
User types \e → SkillMenu opens
User selects \extract-issues → "\\extract-issues " inserted in textarea
User adds context ("from the note above") → submits
  → Backend routes to extract-issues skill
  → SSE task_progress events → SkillProgressCard live updates
  → SSE tool_result with extraction schema → StructuredResultCard
```

### 3. Approval Flow (DD-003)

```
SSE approval_request { action_type: "delete_issue", ... }
  → store.pendingApprovals.push(request)
  → ChatView: isDestructiveAction("delete_issue") === true
  → DestructiveApprovalModal opens (blocking, 5-min countdown)
  → User reviews IssuePreview, clicks Approve
  → POST /api/v1/ai/approvals/{id}/resolve { decision: "approved" }
  → Backend executes delete
  → SSE content_update → UI reflects result
  → Modal unmounts
```

### 4. Session Resume

```
User types \resume → SessionResumeMenu opens
User selects a session from yesterday
  → onSelectSession(sessionId) called
  → GET /api/v1/ai/sessions/{id}/messages?limit=3
  → store.loadSession(session, last3Messages)
  → useIntentRehydration() fetches pending intents
  → Conversation appears where user left off
  → Scroll up to paginate older messages (10/page)
```

---

## SSE Event → Component Mapping (Quick Reference)

| SSE Event | Store Update | Component Rendered |
|-----------|-------------|-------------------|
| `text_delta` | `streamContent` | `StreamingContent` → `MarkdownContent` |
| `thinking_delta` | `thinkingBlocks[]` | `ThinkingBlock` |
| `tool_use` | `pendingToolCalls` | `ToolCallCard` (spinner) |
| `input_json_delta` | `partialInput` | `ToolCallCard` (auto-expand) |
| `tool_result` | `toolResults` | `ToolCallCard` / `StructuredResultCard` |
| `task_progress` | `tasks` | `TaskPanel` → `TaskItem` |
| `approval_request` | `pendingApprovals` | `DestructiveApprovalModal` or `InlineApprovalCard` |
| `skill_approval_request` | `pendingApprovals` | `SkillApprovalCard` |
| `intent_detected` | `intents` | `IntentCard` (detected state) |
| `intent_confirmed` | `intents` | `IntentCard` (confirmed state) |
| `task_progress` (executing) | `intents` | `SkillProgressCard` |
| `question_block` | `questions[]` | `QuestionBlock` |
| `citations` | `citations[]` | `CitationList` |
| `context_attached` | `contextHistory` | `ContextCards` |
| `context_switch` | `contextHistory` | `ContextSwitchIndicator` |
| `message_stop` | `isStreaming=false` | `StreamingBanner` hides, `WorkingIndicator` unmounts |

---

## Design Principles Applied

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | 23 MessageList components, each handles one message type |
| **Human-in-the-Loop (DD-003)** | Destructive actions: blocking modal. Content creation: inline card. Suggestions: auto. |
| **Centralized Agent (DD-086)** | One `PilotSpaceStore` drives all UI state. No local state for message data. |
| **Transparency** | ContextCards show what data AI accessed. ToolCallCards show what tools ran. ThinkingBlock shows reasoning. |
| **Graceful Degradation** | GenericJSON fallback for unknown action types. FALLBACK_SKILLS when API fails. Error boundary for rendering crashes. |
| **Performance** | Virtual scroll for 1000+ messages. Ref-based streaming accumulator. MobX computed for grouping. |
| **Accessibility (WCAG 2.2 AA)** | `aria-live`, `role="log"`, `aria-label`, focus management, `motion-reduce` |

---

## Files at a Glance

```
ChatView/
├── ChatView.tsx                  ~488 lines
├── ChatHeader.tsx                ~96 lines
├── StreamingBanner.tsx           ~167 lines
├── WaitingIndicator.tsx          ~78 lines
├── QueueDepthIndicator.tsx       ~94 lines
├── ConfirmAllButton.tsx          ~135 lines
├── ChatViewErrorBoundary.tsx     ~64 lines
├── types.ts                      ~152 lines
├── constants.ts                  ~244 lines
├── index.ts                      ~44 lines
├── MessageList/                  23 components
├── ChatInput/                    6 components + 2 hooks
├── ApprovalOverlay/              5 components
├── SessionList/                  1 component
├── TaskPanel/                    4 components
└── __tests__/                    ~15 test files
```
