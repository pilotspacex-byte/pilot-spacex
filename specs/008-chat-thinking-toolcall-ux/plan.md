# Implementation Plan: Enhanced Thinking & Tool Call Visualization

**Feature**: Enhanced Thinking & Tool Call Visualization
**Branch**: `008-chat-thinking-toolcall-ux`
**Created**: 2026-02-04
**Spec**: `specs/008-chat-thinking-toolcall-ux/spec.md`
**Author**: Tin Dang

---

## Summary

Enhances the Pilot Space AI chatbox with rich, real-time visualization of agent thinking, tool execution, and streaming state. Frontend-only changes — replaces the current generic spinner + collapsed text approach with frosted-glass thinking blocks, status-driven tool cards, a fixed streaming state banner, vertical step timeline, and token budget ring indicator. All changes modify existing components in `features/ai/ChatView/` and `stores/ai/`.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | TypeScript 5.3+ |
| **Primary Dependencies** | Next.js 14+ (App Router), React 18, MobX 6+, motion/react, lucide-react, shadcn/ui |
| **Storage** | N/A (frontend-only, consumes existing SSE events) |
| **Testing** | Vitest + React Testing Library |
| **Target Platform** | Browser (desktop-first, responsive) |
| **Project Type** | Frontend-only enhancement |
| **Performance Goals** | Thinking indicator renders <100ms from SSE event, tool card status transitions <200ms, Lighthouse >90 |
| **Constraints** | 700-line file limit, WCAG 2.2 AA, prefers-reduced-motion support, dark mode |
| **Scale/Scope** | Single-user chat interface, up to ~100 messages per session |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (TypeScript 5.3+, Next.js 14+)
- [x] Database choice aligns — N/A (no database changes)
- [x] Auth approach follows — N/A (no auth changes)
- [x] Architecture patterns match — MobX for UI state (DD-065), observer components, feature folders

### Simplicity Gate

- [x] Using minimum number of projects/services — all changes within existing `features/ai/ChatView/` and `stores/ai/`
- [x] No future-proofing or speculative features — each component serves a specific FR
- [x] No premature abstractions — utility functions only where shared across 3+ components

### Quality Gate

- [x] Test strategy defined — Vitest unit tests for new components + hook logic, >80% coverage
- [x] Type checking enforced — TypeScript strict mode via `pnpm type-check`
- [x] File size limits respected — 700 lines max per file
- [x] Linting configured — `pnpm lint` (ESLint)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement | Technical Approach | Components |
|-------|------------|-------------------|------------|
| FR-001 | Thinking indicator within 100ms | `StreamingState.isThinking` triggers immediate render; MobX observable auto-updates `ThinkingBlock` | `ThinkingBlock`, `StreamingContent` |
| FR-002 | Stream thinking with cursor | Append `thinkingContent` from `thinking_delta` events; CSS `animate-pulse` cursor span | `ThinkingBlock` (content area) |
| FR-003 | Elapsed time counter | `useElapsedTime` hook reads `StreamingState.thinkingStartedAt`, updates via `requestAnimationFrame` at 1Hz | `useElapsedTime` hook, `ThinkingBlock` |
| FR-004 | Auto-collapse on completion | `useEffect` watching `isStreaming` transition from true→false sets `isExpanded = false` | `ThinkingBlock` |
| FR-005 | Tool call cards with name/status/time | Map `ToolCall.name` → display name via `TOOL_DISPLAY_NAMES` constant; render status icon + timer | `ToolCallCard` (replaces `ToolCallItem`) |
| FR-006 | Tool card status transitions | `ToolCall.status` observable drives icon + color via lookup map | `ToolCallCard` |
| FR-007 | Streaming state banner | New `StreamingBanner` reads `StreamingState.phase` + `currentBlockType`; fixed position above `ChatInput` | `StreamingBanner`, `ChatView` |
| FR-008 | Collapsible tool I/O with syntax highlighting | shadcn `Collapsible` wraps `<pre>` with `font-mono` styling; JSON.stringify for objects | `ToolCallCard` (detail section) |
| FR-009 | Parallel tool call grouping | Check `toolCalls.length > 1` → wrap in group container with `GitBranch` icon header | `ToolCallList` |
| FR-010 | Independent interleaved thinking blocks | Map `thinkingBlocks[]` → individual `ThinkingBlock` instances with independent collapse state | `AssistantMessage`, `ThinkingBlock` |
| FR-011 | Frosted glass thinking block | Apply `glass-subtle` class + `bg-ai-muted` + `border-l-[4px] border-l-ai` | `ThinkingBlock` CSS |
| FR-012 | Token estimate on completed blocks | `estimateTokens()` (existing function) renders as badge in collapsed header | `ThinkingBlock` |
| FR-013 | Vertical step timeline for 3+ tool calls | New `ToolStepTimeline` component with vertical line + numbered circles | `ToolStepTimeline`, `ToolCallList` |
| FR-014 | Token budget ring indicator | New `TokenBudgetRing` SVG component reads `SessionState.totalTokens` / 8000 | `TokenBudgetRing`, `ChatInput` |
| FR-015 | prefers-reduced-motion | Use existing `globals.css` `@media (prefers-reduced-motion)` + Tailwind `motion-reduce:` prefix | All new components |
| FR-016 | Dark mode | Use existing CSS variables (`--ai`, `--ai-muted`, etc.) — auto-adapts via `.dark` class | All new components |
| FR-017 | Preserve partial content on interruption | Existing `abort()` preserves `streamContent`; add `interrupted` flag to `StreamingState` | `PilotSpaceStore`, `ThinkingBlock` |
| FR-018 | Fade-in new text at line/sentence boundaries | Track `previousContentLength` in store; `MarkdownContent` wraps new content chunks in `<span>` with CSS `animate-fade-up` (150ms) | `MarkdownContent`, `StreamingContent` |
| FR-019 | Previously streamed content stays full opacity | Only the latest chunk `<span>` has fade animation; prior spans rendered without animation class | `MarkdownContent` |
| FR-020 | AI edit highlight with fade-out | Add `ai-block-edited` CSS class after processing completes; CSS transitions background from `var(--ai-muted)` to transparent over 1s; class removed after transition ends | `useContentUpdates` hook, `globals.css` |
| FR-021 | New blocks slide-in animation | Add `ai-block-new` CSS class to appended blocks; CSS animates translateY(8px)→0 + opacity 0→1 over 300ms; class removed after animation ends | `useContentUpdates` hook, `globals.css` |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Shared Utilities |
|------------|-------------------|--------------------|----|
| US1: Real-Time Thinking Visualization | None | `ThinkingBlock` (edit), `StreamingContent` (edit) | `useElapsedTime` hook |
| US2: Tool Call Status Cards | None | `ToolCallCard` (new, replaces `ToolCallItem`), `ToolCallList` (edit) | `TOOL_DISPLAY_NAMES` constant |
| US3: Streaming State Banner | None | `StreamingBanner` (new), `ChatView` (edit) | — |
| US4: Thinking Block Design Enhancement | None | `ThinkingBlock` (edit) | — |
| US5: Tool Call Timeline View | None | `ToolStepTimeline` (new), `ToolCallList` (edit) | — |
| US6: Token Budget Ring | None | `TokenBudgetRing` (new), `ChatInput` (edit) | — |
| US7: Streaming Text Fade-In | None | `MarkdownContent` (edit), `StreamingContent` (edit) | — |
| US8: AI Block Edit Highlight | None | `useContentUpdates` hook (edit), `globals.css` (edit), `AIBlockProcessingExtension` (edit) | — |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| Elapsed time implementation | A) `setInterval(1000)`, B) `requestAnimationFrame` with 1Hz throttle, C) MobX computed from store timestamp | **B) rAF with 1Hz throttle** | FR-003: Avoids stale interval cleanup issues; pauses when tab hidden (saves CPU); more accurate than setInterval drift |
| Tool name mapping location | A) Backend sends display names in SSE, B) Frontend constant map, C) i18n locale file | **B) Frontend constant map** | Clarification: frontend-only scope; no backend changes. Map maintained in `features/ai/ChatView/constants.ts` |
| Timeline component | A) Horizontal Gantt chart (D3/recharts), B) Vertical step list (pure CSS/Tailwind), C) Third-party timeline lib | **B) Vertical step list** | FR-013: Fits chat flow better; no new dependencies; user selected this in clarification |
| Token budget ring | A) shadcn Progress bar, B) SVG circle with stroke-dasharray, C) CSS conic-gradient | **B) SVG circle** | FR-014: User selected circular ring; SVG gives precise control over arc + color transitions; 24px compact size |
| Banner positioning | A) Inline with messages (current StreamingContent), B) Fixed above input, C) Both | **B) Fixed above input** | User selected; always visible regardless of scroll position; replaces inline streaming indicator role |
| Streaming text fade-in approach | A) CSS animation on wrapper per chunk, B) Motion library stagger, C) Custom React transition group | **A) CSS animation on wrapper** | FR-018: Simplest approach — split content at line boundaries, wrap latest chunk in `<span className="animate-fade-up">`. Existing `animate-fade-up` keyframe in globals.css (300ms fadeUp). No new dependency. Motion library adds bundle weight for a simple opacity transition. |
| Auto-collapse mechanism | A) CSS transition on height, B) Conditional render (mount/unmount), C) `max-height` transition with overflow | **A) CSS transition** | FR-004: Smooth collapse animation; existing `Collapsible` component handles this; 200ms ease-out per design system |

---

## Data Model

No database entities. All state is transient UI state within existing MobX stores.

### StreamingState (existing, extended)

**Purpose**: Track in-progress streaming phases for UI rendering.
**Source**: FR-001, FR-003, FR-007, FR-017

| Field | Type | Status | Notes |
|-------|------|--------|-------|
| isStreaming | boolean | Existing | Active streaming flag |
| streamContent | string | Existing | Accumulated text |
| currentMessageId | string \| null | Existing | Message being streamed |
| phase | StreamingPhase | Existing | Current phase |
| isThinking | boolean | Existing | Thinking active |
| thinkingContent | string | Existing | Accumulated thinking |
| thinkingStartedAt | number \| null | Existing | Timestamp for duration calc |
| currentBlockType | 'text' \| 'tool_use' \| 'thinking' | Existing | G13 block type |
| thinkingBlocks | ThinkingBlockEntry[] | Existing | G-07 interleaved |
| **activeToolName** | **string \| null** | **New** | Currently executing tool name (for banner) |
| **interrupted** | **boolean** | **New** | Stream was aborted by user |
| **wordCount** | **number** | **New** | Accumulated word count for writing phase |

### ToolCall (existing, no changes)

All fields already present: `id`, `name`, `input`, `output`, `status`, `errorMessage`, `partialInput`, `parentToolUseId`, `durationMs`.

### SessionState (existing, extended)

| Field | Type | Status | Notes |
|-------|------|--------|-------|
| sessionId | string \| null | Existing | — |
| totalCostUsd | number | Existing | — |
| **totalTokens** | **number** | **New** | Accumulated token count for budget ring |

---

## API Contracts

No new API endpoints. All data consumed from existing SSE events:

### Existing SSE Events Used

| SSE Event | Data Fields Used | Component |
|-----------|-----------------|-----------|
| `thinking_delta` | `content` (string) | ThinkingBlock, StreamingBanner |
| `tool_use` | `id`, `name` | ToolCallCard, StreamingBanner |
| `tool_result` | `id`, `output`, `status`, `durationMs` | ToolCallCard |
| `tool_input_delta` | `id`, `partial_input` | ToolCallCard |
| `content_block_start` | `type`, `index` | StreamingBanner (phase detection) |
| `text_delta` | `text` | StreamingBanner (word count) |
| `message_stop` | — | ThinkingBlock (auto-collapse trigger), StreamingBanner (hide) |
| `budget_warning` | `usage_percent`, `tokens_used` | TokenBudgetRing |

---

## Project Structure

```text
frontend/src/
├── features/ai/ChatView/
│   ├── ChatView.tsx                        # EDIT: Insert StreamingBanner between messages and input
│   ├── constants.ts                        # EDIT: Add TOOL_DISPLAY_NAMES map
│   ├── MessageList/
│   │   ├── ThinkingBlock.tsx               # EDIT: Frosted glass, elapsed time, auto-collapse
│   │   ├── ToolCallList.tsx                # EDIT: Add timeline toggle, pass display names
│   │   ├── ToolCallCard.tsx                # NEW:  Redesigned tool card (replaces ToolCallItem)
│   │   ├── ToolStepTimeline.tsx            # NEW:  Vertical step timeline for 3+ tools
│   │   ├── MarkdownContent.tsx              # EDIT: Line-by-line fade-in during streaming
│   │   ├── StreamingContent.tsx            # EDIT: Integrate enhanced ThinkingBlock
│   │   └── AssistantMessage.tsx            # EDIT: Minor — pass new props
│   ├── StreamingBanner.tsx                 # NEW:  Fixed banner above input
│   └── ChatInput/
│       └── ChatInput.tsx                   # EDIT: Add TokenBudgetRing to toolbar
├── components/ui/
│   └── token-budget-ring.tsx               # NEW:  Reusable SVG ring component
├── hooks/
│   └── useElapsedTime.ts                   # NEW:  rAF-based elapsed time hook
└── stores/ai/
    ├── PilotSpaceStore.ts                  # EDIT: Add activeToolName, interrupted, wordCount, totalTokens
    └── PilotSpaceStreamHandler.ts          # EDIT: Set activeToolName on tool_use, wordCount on text_delta
```

**Structure Decision**: Follows existing feature-folder pattern. `ToolCallCard` is a new file because the redesign changes the interface significantly (elapsed time, display names, status icons) — editing `ToolCallItem` inline within `ToolCallList.tsx` would exceed the component's scope. `ToolStepTimeline` and `StreamingBanner` are distinct UI concerns warranting their own files. `TokenBudgetRing` goes in `components/ui/` as it's a reusable primitive. `useElapsedTime` goes in shared `hooks/` since it's useful beyond this feature.

---

## Quickstart Validation

### Scenario 1: Thinking Block Streams and Auto-Collapses

1. Open a chat session in Pilot Space
2. Send a message that triggers extended thinking (e.g., "Analyze the architecture of this note")
3. **Verify**: A frosted-glass thinking block appears with brain icon, "Thinking..." label, and pulsing left border
4. **Verify**: Elapsed time counter increments every second
5. Click the thinking block header to expand — raw thinking text streams with a blinking cursor
6. Wait for thinking to complete
7. **Verify**: Block auto-collapses to show "Thought for X.Xs" + "~N tokens" badge
8. **Verify**: Pulsing animation stops; border becomes static

### Scenario 2: Tool Cards with Status Progression

1. Send `/extract-issues` in the chat input
2. **Verify**: Tool card appears with friendly name "Extracting Issues", spinning loader icon, and running timer
3. **Verify**: Streaming banner above input shows wrench icon + "Using Extracting Issues..."
4. Wait for tool to complete
5. **Verify**: Card transitions to green checkmark + "Completed" with duration
6. Click card to expand — input/output JSON visible with formatting

### Scenario 3: Parallel Tool Execution

1. Trigger a skill that invokes multiple tools simultaneously
2. **Verify**: Tools appear grouped under "Parallel (N tools)" header with `GitBranch` icon
3. **Verify**: Each tool has independent status progression
4. **Verify**: Streaming banner shows the currently active tool name

### Scenario 4: Streaming Banner Phase Transitions

1. Send a complex request
2. **Verify**: Banner shows brain icon + "Thinking..." during thinking phase
3. **Verify**: Banner transitions to wrench icon + tool name during tool use
4. **Verify**: Banner transitions to pencil icon + "Writing response..." + word count during text generation
5. Click "Stop" button
6. **Verify**: Banner briefly shows "Stopped" then disappears; partial content preserved

### Scenario 5: Vertical Step Timeline

1. Trigger an operation that invokes 3+ sequential tool calls
2. **Verify**: A "View steps" toggle appears below the tool cards
3. Click "View steps"
4. **Verify**: Vertical timeline shows numbered steps with connecting line, tool names, duration badges
5. **Verify**: Completed steps show green checkmarks, running step shows spinning indicator

### Scenario 6: Token Budget Ring

1. Open a chat session
2. **Verify**: Small circular ring appears near the send button area, mostly empty (green)
3. Exchange several messages
4. **Verify**: Ring fills proportionally; hover shows tooltip "X.XK / 8K tokens (N%)"
5. When usage exceeds 80%
6. **Verify**: Ring turns orange; toast notification appears

### Scenario 7: Dark Mode

1. Toggle dark mode
2. **Verify**: Thinking blocks use dark AI-muted background (`#1f2d38`)
3. **Verify**: Tool cards, banner, timeline, and ring all adapt to dark theme
4. **Verify**: No contrast issues; all text remains legible

### Scenario 8: Reduced Motion

1. Enable `prefers-reduced-motion` in OS settings
2. **Verify**: No pulsing animations on thinking blocks
3. **Verify**: No spinning on loader icons — static indicators instead
4. **Verify**: Phase transitions are instant (no crossfade)

### Scenario 9: Stream Interruption

1. Send a message that triggers a long thinking phase
2. Click "Stop" while thinking is in progress
3. **Verify**: Thinking block shows "Interrupted" state with partial content preserved
4. **Verify**: Streaming banner disappears
5. **Verify**: Chat input is re-enabled

---

## Complexity Tracking

No violations. All gates pass.

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping (FR-001 through FR-017)
- [x] Every user story maps to frontend components (no backend needed)
- [x] Data model covers all state extensions (StreamingState, SessionState)
- [x] API contracts cover all SSE event consumption
- [x] Research documents each decision with 2+ alternatives (6 decisions)

### Constitution Compliance

- [x] Technology standards gate passed (TypeScript 5.3+, Next.js 14+, MobX 6+)
- [x] Simplicity gate passed — no new dependencies, no premature abstractions
- [x] Quality gate passed — Vitest >80%, pyright strict, 700-line limit, ESLint
- [x] All violations documented — none needed

### Traceability

- [x] Every technical decision references FR-NNN
- [x] Every scenario references the user story it validates
- [x] Every data extension references the spec requirement it implements
- [x] Project structure matches existing feature-folder architecture

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining — all clarified in pre-plan questions
- [x] Performance constraints have concrete targets (<100ms thinking render, <200ms status transition)
- [x] Security documented — N/A (frontend-only, no new data flows)
- [x] Error handling: interrupted state for abort, failed state for tool errors
- [x] File creation order specified in project structure (shared hooks → UI primitives → components → store edits → integration)

---

## Implementation Order

### Phase 1: Foundation (shared utilities + store extensions)

1. `hooks/useElapsedTime.ts` — rAF-based elapsed time hook
2. `stores/ai/PilotSpaceStore.ts` — Add `activeToolName`, `interrupted`, `wordCount`, `totalTokens`
3. `stores/ai/PilotSpaceStreamHandler.ts` — Set new fields on relevant SSE events
4. `features/ai/ChatView/constants.ts` — Add `TOOL_DISPLAY_NAMES` map

### Phase 2: Core Components (P1)

5. `ThinkingBlock.tsx` — Frosted glass redesign + elapsed time + auto-collapse
6. `ToolCallCard.tsx` — New component with status progression + display names
7. `ToolCallList.tsx` — Integrate ToolCallCard, parallel grouping
8. `StreamingBanner.tsx` — New fixed banner with phase transitions
9. `StreamingContent.tsx` — Integrate enhanced ThinkingBlock
10. `AssistantMessage.tsx` — Pass new props through
11. `ChatView.tsx` — Insert StreamingBanner between content and input

### Phase 3: Enhanced Components (P2)

12. `ToolStepTimeline.tsx` — Vertical step timeline
13. `ToolCallList.tsx` — Add "View steps" toggle for 3+ tools

### Phase 4: Token Budget (P3)

14. `components/ui/token-budget-ring.tsx` — SVG ring component
15. `ChatInput.tsx` — Add TokenBudgetRing to toolbar

### Phase 5: Tests

16. Unit tests for `useElapsedTime`
17. Unit tests for `ThinkingBlock` (streaming, collapsed, completed, interrupted)
18. Unit tests for `ToolCallCard` (all status states)
19. Unit tests for `StreamingBanner` (phase transitions)
20. Unit tests for `ToolStepTimeline` (3+ items, parallel detection)
21. Unit tests for `TokenBudgetRing` (color thresholds, tooltip)
22. Integration test for store extensions (activeToolName, wordCount)

---

## Next Phase

After this plan passes all checklists:

1. **Proceed to task breakdown** — Use `template-tasks.md` to create `tasks.md` from the Implementation Order
2. **Begin implementation** — Phase 1 foundation first, then P1 components
