# ChatView: MessageList System

> **Location**: `frontend/src/features/ai/ChatView/MessageList/`
> **Design Decisions**: DD-003 (Approvals), DD-066 (SSE Streaming), DD-086 (Agent Architecture)

## Overview

The MessageList is a **polymorphic event renderer** — a 23-component system that maps every SSE event type from the PilotSpaceAgent into a corresponding React component. It renders user messages, AI responses, tool execution timelines, structured results, AI questions, intent lifecycle cards, approval requests, citations, and context indicators. It handles both live streaming (SSE token deltas) and static historical messages.

---

## Architecture

```
MessageList.tsx  (observer, virtual scroll root)
└── MessageGroup.tsx  (groups by session context)
    └── ConversationBlock.tsx  (one turn: user + assistant)
        ├── UserMessage.tsx
        └── AssistantMessage.tsx
            ├── StreamingContent.tsx          ← live SSE token stream
            │   └── InlineStreamingIndicator  ← spinner during content phase
            ├── MarkdownContent.tsx           ← static rendered markdown
            ├── ThinkingBlock.tsx             ← AI reasoning (live timer, collapse)
            ├── ReasoningGroup.tsx            ← groups multiple thinking blocks
            ├── ToolCallCard.tsx              ← single MCP tool call
            ├── ToolCallList.tsx              ← 1–2 tool calls (flat)
            ├── ToolStepTimeline.tsx          ← 3+ tool calls (numbered timeline)
            ├── StructuredResultCard.tsx      ← typed AI result schemas
            ├── QuestionBlock.tsx             ← AI clarification question
            ├── ResolvedSummary.tsx           ← collapsed Q&A after answer
            ├── IntentCard.tsx               ← detected/confirmed intent
            ├── SkillProgressCard.tsx         ← executing skill with steps
            ├── InlineApprovalCard.tsx        ← DEFAULT-tier approval inline
            ├── SkillApprovalCard.tsx         ← skill-level approval
            ├── CitationList.tsx              ← source references
            └── ContextCards.tsx             ← note/issue context attached

ContextSwitchIndicator.tsx  ← between-message context change marker
IntentMessageRenderer.tsx   ← routes intent events to correct card
```

---

## Message Type Taxonomy

| Type | SSE Event Source | Component(s) | Notes |
|------|-----------------|-------------|-------|
| User message | User action | `UserMessage` | Gray bg, timestamp, Markdown |
| AI text | `text_delta` | `MarkdownContent` / `StreamingContent` | GFM, syntax highlight |
| Thinking/reasoning | `thinking_delta` | `ThinkingBlock` | Live timer, auto-collapse 300ms post-stream |
| MCP tool call (1–2) | `tool_use` | `ToolCallCard` / `ToolCallList` | Spinner during execution |
| MCP tool call (3+) | `tool_use` | `ToolStepTimeline` | Numbered timeline |
| Structured result | `tool_result` (schema) | `StructuredResultCard` | 6 schema variants |
| AI question | `question_block` | `QuestionBlock` | Wizard UI, conditional skipping |
| Q&A resolved | User answers all | `ResolvedSummary` | Collapsed view |
| Detected intent | `intent_detected` | `IntentCard` | `detected` state |
| Confirmed intent | `intent_confirmed` | `IntentCard` | `confirmed` state |
| Executing skill | `task_progress` | `SkillProgressCard` | Live step list |
| Non-destructive approval | `approval_request` | `InlineApprovalCard` | 24h countdown |
| Skill approval | `skill_approval_request` | `SkillApprovalCard` | Artifact preview |
| Citations | `citations` | `CitationList` | Source references |
| Context attached | `context_attached` | `ContextCards` | Note/issue badges |
| Context switch | `context_switch` | `ContextSwitchIndicator` | Between-message divider |

---

## SSE Event → Component Pipeline

```
SSE stream
  │
  ├─ text_delta
  │   → store.streamContent += delta
  │   → StreamingContent re-renders with new text
  │   → MarkdownContent (after stream ends, static)
  │
  ├─ thinking_delta
  │   → store.thinkingBlocks[] += delta
  │   → ThinkingBlock renders live (timer counts up)
  │   → 300ms after stream ends → auto-collapse
  │
  ├─ tool_use { id, name, input }
  │   → store.pendingToolCalls.set(id, { name, partialInput })
  │   → ToolCallCard appears (spinner active)
  │
  ├─ tool_use { input_json_delta }
  │   → store.pendingToolCalls.get(id).partialInput += delta
  │   → ToolCallCard auto-expands (shows streaming JSON)  ← G-09
  │
  ├─ tool_result { tool_use_id }
  │   → store.pendingToolCalls.delete(id) (spinner removed)
  │   → store.toolResults.set(id, result)
  │   → ToolCallCard shows result
  │   → IF schema matches → StructuredResultCard renders instead
  │
  ├─ task_progress { taskId, step, status }
  │   → store.tasks.get(taskId) updated
  │   → SkillProgressCard live step list updates
  │
  ├─ approval_request { action_type, payload }
  │   → store.pendingApprovals.push(request)
  │   → isDestructiveAction? → DestructiveApprovalModal (ChatView)
  │   → otherwise → InlineApprovalCard in MessageList
  │
  ├─ intent_detected / intent_confirmed / intent_executing
  │   → store.intents.set(id, intent)
  │   → IntentMessageRenderer routes to IntentCard / SkillProgressCard
  │
  └─ citations, context_attached, context_switch
      → store updates respective arrays
      → CitationList / ContextCards / ContextSwitchIndicator render
```

---

## Components Deep-Dive

### `MessageList.tsx`

**Root component**. Uses `react-virtuoso` for virtual scrolling, handles message pagination, and implements smart auto-scroll.

**Virtual scroll**: Only renders visible messages + small overscan. Handles 1000+ messages without performance degradation.

**Auto-scroll**: Double `requestAnimationFrame` pattern scrolls to bottom on new messages. Disabled when user scrolls up (detected via scroll position delta).

**Pagination**: Loads older messages when user scrolls to top (debounced trigger).

**Accessibility**: `aria-label="Conversation"`, `role="log"`, `aria-live="polite"`.

---

### `ConversationBlock.tsx`

Groups one user turn + one assistant turn into a logical unit. Handles the transition between streaming (live) and static (historical) rendering for the assistant message.

**Key logic**: If `message.isStreaming === true`, renders `StreamingContent`. Otherwise renders `MarkdownContent` with the finalized text.

---

### `StreamingContent.tsx`

Renders live SSE token stream as progressively-built Markdown. Uses a ref-based accumulator (not state) to avoid triggering re-renders on every token — instead, updates DOM directly for performance, then syncs to React state at a throttled interval.

**InlineStreamingIndicator**: Animated cursor that appears at the end of streaming text to signal liveness.

---

### `ThinkingBlock.tsx`

Displays the AI's extended thinking/reasoning process.

**States**:
- **Live** (streaming): Pulsing border, live elapsed timer ("Thinking: 4.2s"), content visible
- **Completed** (300ms after stream ends): Auto-collapses to a "Thinking finished in 4.2s" chip
- **Expanded** (user click): Re-opens full reasoning content
- **Redacted**: If backend flags thinking as redacted, shows "Thinking process hidden" placeholder

**Why auto-collapse?** Reasoning blocks can be very long. Auto-collapsing after streaming keeps the conversation readable while preserving access to the full reasoning on demand.

**Timer**: `setInterval` at ~100ms updates elapsed seconds display.

---

### `ToolCallCard.tsx` / `ToolCallList.tsx` / `ToolStepTimeline.tsx`

Three-tier visualization based on tool call count:

| Count | Component | Layout |
|-------|-----------|--------|
| 1 | `ToolCallCard` | Single card with tool name, inputs, result |
| 2 | `ToolCallList` | Two stacked cards |
| 3+ | `ToolStepTimeline` | Numbered vertical timeline |

**ToolCallCard states**:
- **Pending**: Spinner, partial input streaming (G-09: auto-expands when `input_json_delta` arrives)
- **Complete with result**: Shows input + result, collapsible
- **Note-modifying tools**: Shows "View in note" link (e.g., after `update_note`)

**Tool display names** come from `constants.ts TOOL_DISPLAY_NAMES`:
```
"note.read_note"      → "Reading note"
"issue.create_issue"  → "Creating issue"
"note.update_note"    → "Updating note"
...
```

---

### `StructuredResultCard.tsx`

Renders typed AI output schemas as rich cards rather than raw JSON. Activated when `tool_result.schema` is recognized.

**6 schema variants**:

| Schema | Display | Key features |
|--------|---------|-------------|
| `extraction` | Issue extraction result | Issue count, rainbow badges |
| `decomposition` | Task breakdown | Numbered steps, dependencies |
| `standup` | Daily standup | Copy-to-clipboard button |
| `ai_context` | AI context result | Collapsible sections |
| `diagram` | Mermaid diagram | Live preview |
| `default` | Generic key-value | Fallback for new schemas |

---

### `QuestionBlock.tsx` / `ResolvedSummary.tsx`

**QuestionBlock**: Wizard-style multi-question UI for AI clarification.

**Features**:
- One question displayed at a time
- Multiple choice or free-text answers
- Custom "Other" option with auto-focusing textarea
- **Conditional skipping**: Questions can declare `skipIf` conditions based on prior answers
- Progress indicator ("Question 2 of 4")
- "Skip question" link for optional questions

**ResolvedSummary**: After all questions are answered, the QuestionBlock collapses to a compact summary showing each Q&A pair. Keeps the conversation readable after interaction.

**Why wizard (not all-at-once)?** Sequential questions feel conversational. Showing all questions simultaneously looks like a form, breaking the Note-First chat metaphor.

---

### `IntentCard.tsx` / `SkillProgressCard.tsx` / `IntentMessageRenderer.tsx`

**Intent lifecycle visualization**:

```
detected → (user confirms or batch-confirms) → confirmed → (skill starts) → executing → completed
```

**IntentCard** renders the `detected` and `confirmed` states:
- Shows AI's interpreted intent (`what`), reasoning (`why`), confidence bar
- Approve / Reject buttons (for `detected`)
- Collapses to chip on `confirmed`

**SkillProgressCard** renders the `executing` state:
- Live step list (steps stream in as `task_progress` SSE events arrive)
- Each step: name, status indicator (pending/running/done/failed)
- Skill name, start time, elapsed timer

**IntentMessageRenderer** is the routing layer — reads the intent's `status` from `store.intents` and selects the correct card.

---

### `ContextCards.tsx` / `ContextSwitchIndicator.tsx`

**ContextCards**: Compact badge row showing what context (notes, issues, projects) the AI was given for a specific turn. Rendered below the user message.

**ContextSwitchIndicator**: A horizontal divider with a label ("Context changed: Note switched from X to Y") rendered between message groups when the attached context changes mid-conversation.

**Why**: Transparency. Users must be able to audit what data the AI had access to for each turn.

---

### `CitationList.tsx`

Renders source references the AI used to generate a response. Shown below assistant messages when `citations` SSE event is received.

**Each citation**: Source title, URL (if external), block ID (if note), relevance score.

---

## Implicit Features

| Feature | Mechanism | Location |
|---------|-----------|---------|
| Virtual scrolling | `react-virtuoso` | `MessageList.tsx` |
| Smart auto-scroll | Double `rAF` + user scroll detection | `MessageList.tsx` |
| Scroll-up to paginate | Debounced scroll listener | `MessageList.tsx` |
| Thinking auto-collapse 300ms | `setTimeout` after streaming ends | `ThinkingBlock.tsx` |
| Tool input auto-expand (G-09) | `input_json_delta` → card auto-opens | `ToolCallCard.tsx` |
| Live elapsed timers | `setInterval` 100ms | `ThinkingBlock.tsx`, `SkillProgressCard.tsx` |
| "View in note" link | Note-modifying tool result check | `ToolCallCard.tsx` |
| Copy-to-clipboard for standup | `navigator.clipboard.writeText` | `StructuredResultCard.tsx` |
| Question conditional skipping | `skipIf` predicate evaluation | `QuestionBlock.tsx` |
| "Other" auto-focus | `autoFocus` on textarea reveal | `QuestionBlock.tsx` |
| Countdown amber/red thresholds | Time remaining comparisons | `InlineApprovalCard.tsx`, `SkillApprovalCard.tsx` |
| Streaming cursor (blinking) | CSS animation | `InlineStreamingIndicator.tsx` |
| Block order preservation | SSE arrival order in store array | `AssistantMessage.tsx` |
| Markdown GFM + syntax highlight | `react-markdown` + `rehype-highlight` | `MarkdownContent.tsx` |
| Reasoning redaction detection | Backend `redacted: true` flag | `ThinkingBlock.tsx` |

---

## Performance Architecture

| Concern | Solution |
|---------|---------|
| 1000+ messages | Virtual scrolling (`react-virtuoso`) |
| Streaming re-renders | Ref-based accumulator, throttled React sync |
| Complex computed values | MobX `computed()` for message grouping |
| Repeated components | `React.memo()` on stable sub-components |
| Tool call explosions | 3+ calls → timeline (visual compression) |
| Long thinking blocks | Auto-collapse keeps viewport clean |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| 23 specialized components vs. 1 generic | Each message type has unique UX needs. A generic renderer would be if-else chaos. |
| `react-virtuoso` for scroll | Standard React virtualization for large lists; handles dynamic heights. |
| Auto-collapse thinking blocks | Reasoning can be 500+ words. Collapsing keeps the conversation scannable. |
| 3-tier tool call visualization | 1–2 tools: cards are readable. 3+ tools: timeline is more scannable. |
| Wizard (not form) for questions | Maintains conversational feel; each Q&A is a micro-turn. |
| IntentMessageRenderer routing | Separates routing logic from rendering logic. Intent lifecycle is complex enough to warrant its own router. |
| Double rAF for auto-scroll | Single rAF can fire before DOM paint. Double rAF ensures scroll runs after layout is committed. |
| `StreamingContent` direct DOM mutation | React state updates on every token (30–50/sec) would cause jank. Direct DOM + throttled sync prevents this. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `MessageList.tsx` | ~280 | Virtual scroll root, auto-scroll, pagination |
| `MessageGroup.tsx` | ~80 | Session context grouping |
| `ConversationBlock.tsx` | ~120 | User + assistant turn container |
| `AssistantMessage.tsx` | ~200 | Polymorphic assistant message renderer |
| `UserMessage.tsx` | ~80 | User turn display |
| `StreamingContent.tsx` | ~140 | Live SSE token rendering |
| `InlineStreamingIndicator.tsx` | ~40 | Streaming cursor |
| `ThinkingBlock.tsx` | ~180 | AI reasoning with timer + collapse |
| `ReasoningGroup.tsx` | ~60 | Groups multiple thinking blocks |
| `MarkdownContent.tsx` | ~100 | GFM + syntax highlight renderer |
| `ToolCallCard.tsx` | ~220 | Single MCP tool call card |
| `ToolCallList.tsx` | ~80 | 1–2 tool calls flat |
| `ToolStepTimeline.tsx` | ~160 | 3+ tool calls numbered timeline |
| `StructuredResultCard.tsx` | ~300 | 6 typed AI result schemas |
| `QuestionBlock.tsx` | ~280 | Wizard Q&A with conditional skip |
| `ResolvedSummary.tsx` | ~100 | Collapsed Q&A after completion |
| `IntentCard.tsx` | ~180 | detected/confirmed intent card |
| `SkillProgressCard.tsx` | ~200 | Executing skill with live steps |
| `IntentMessageRenderer.tsx` | ~60 | Intent lifecycle router |
| `InlineApprovalCard.tsx` | ~180 | Non-blocking approval (24h) |
| `SkillApprovalCard.tsx` | ~160 | Skill approval with artifacts |
| `CitationList.tsx` | ~100 | Source references |
| `ContextCards.tsx` | ~120 | Per-turn context badges |
| `ContextSwitchIndicator.tsx` | ~60 | Between-message context change |
