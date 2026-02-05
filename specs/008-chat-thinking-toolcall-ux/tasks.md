# Tasks: Enhanced Thinking & Tool Call Visualization

**Feature**: Enhanced Thinking & Tool Call Visualization
**Branch**: `008-chat-thinking-toolcall-ux`
**Created**: 2026-02-04
**Source**: `specs/008-chat-thinking-toolcall-ux/`
**Author**: Tin Dang

---

## Phase 1: Foundation

### Shared Utilities

- [ ] T001 [P] Create `useElapsedTime` hook in `frontend/src/hooks/useElapsedTime.ts`
  - Accepts `startTimestamp: number | null` and `isActive: boolean`
  - Uses `requestAnimationFrame` throttled to 1Hz (update display once per second)
  - Returns formatted string: `"0s"`, `"3.2s"`, `"1m 12s"`
  - Cancels rAF on unmount or when `isActive` becomes false
  - Uses `tabular-nums` font-variant hint in return metadata
  - Per research.md RD-001

- [ ] T002 [P] Add `TOOL_DISPLAY_NAMES` constant in `frontend/src/features/ai/ChatView/constants.ts`
  - Map of raw MCP tool name → human-readable display name:
    - `update_note_block` → `"Updating Note Block"`
    - `enhance_text` → `"Enhancing Text"`
    - `summarize_note` → `"Summarizing Note"`
    - `extract_issues` → `"Extracting Issues"`
    - `create_issue_from_note` → `"Creating Issue"`
    - `link_existing_issues` → `"Linking Issues"`
  - Export helper: `getToolDisplayName(rawName: string): string` — returns mapped name or title-cased fallback
  - Per research.md RD-002

### Store Extensions

- [ ] T003 Extend `StreamingState` interface in `frontend/src/stores/ai/types/conversation.ts`
  - Add `activeToolName?: string | null` — currently executing tool name for banner display
  - Add `interrupted?: boolean` — stream was aborted by user (FR-017)
  - Add `wordCount?: number` — accumulated word count during text generation phase

- [ ] T004 Extend `SessionState` interface in `frontend/src/stores/ai/types/conversation.ts`
  - Add `totalTokens?: number` — accumulated token count for budget ring (FR-014)

- [ ] T005 Update `PilotSpaceStore` in `frontend/src/stores/ai/PilotSpaceStore.ts`
  - Initialize new `StreamingState` fields: `activeToolName: null`, `interrupted: false`, `wordCount: 0`
  - In `abort()` method: set `streamingState.interrupted = true`
  - In `clear()` / `clearStreamingState()`: reset `activeToolName`, `interrupted`, `wordCount`
  - Add `@computed get tokenBudgetPercent(): number` — returns `(sessionState.totalTokens ?? 0) / 8000 * 100`

- [ ] T006 Update `PilotSpaceStreamHandler` in `frontend/src/stores/ai/PilotSpaceStreamHandler.ts`
  - On `tool_use` event: set `streamingState.activeToolName = event.name`
  - On `tool_result` event: set `streamingState.activeToolName = null`
  - On `text_delta` event: increment `streamingState.wordCount` by word count of delta text
  - On `message_stop` event: reset `activeToolName`, `interrupted`, `wordCount`
  - On `budget_warning` event: update `sessionState.totalTokens` from event payload

**Checkpoint**: Foundation complete. `useElapsedTime` hook works, store has new observable fields, stream handler populates them. `pnpm type-check` passes.

---

## Phase 2: US1 — Real-Time Thinking Visualization (P1)

**Goal**: Frosted-glass thinking blocks with live elapsed time, streaming content, and auto-collapse on completion.
**Verify**: Send any message triggering extended thinking. Block appears immediately, streams content, shows elapsed time, auto-collapses to summary.

### Tests

- [ ] T007 [P] [US1] Write unit tests for `useElapsedTime` in `frontend/src/hooks/__tests__/useElapsedTime.test.ts`
  - Test: returns "0s" when startTimestamp is null
  - Test: returns formatted elapsed time when active (mock rAF with `vi.useFakeTimers`)
  - Test: stops updating when `isActive` becomes false
  - Test: formats correctly at boundaries: 999ms → "0s", 1000ms → "1.0s", 60000ms → "1m 0s"
  - Test: cancels rAF on unmount (no memory leak)

- [ ] T008 [P] [US1] Write unit tests for enhanced `ThinkingBlock` in `frontend/src/features/ai/ChatView/MessageList/__tests__/ThinkingBlock.test.tsx`
  - Test: renders frosted glass styling (`glass-subtle`, `bg-ai-muted`, `border-l-ai`) when streaming
  - Test: shows brain icon + "Thinking..." label + pulsing indicator when `isStreaming=true`
  - Test: displays elapsed time counter (mock `useElapsedTime`)
  - Test: auto-collapses when `isStreaming` transitions from true to false
  - Test: collapsed state shows "Thought for X.Xs" + "~N tokens" badge
  - Test: expand/collapse toggle works via click
  - Test: streaming cursor visible when expanded and streaming
  - Test: content area has `max-h-[400px]` and is scrollable
  - Test: returns null when content is empty
  - Test: renders "Interrupted" label when `interrupted=true`
  - Test: handles redacted content (REDACTED_SENTINEL)

### Implementation

- [ ] T009 [US1] Redesign `ThinkingBlock` in `frontend/src/features/ai/ChatView/MessageList/ThinkingBlock.tsx`
  - Replace current div-based expand/collapse with shadcn `Collapsible` (controlled, `open` prop)
  - Add `frosted glass` treatment: combine `glass-subtle` class + `bg-ai-muted` + `border-l-[4px] border-l-ai`
  - Add pulsing left border during streaming: `motion-safe:animate-ai-pulse` on border element
  - Import and use `useElapsedTime(thinkingStartedAt, isStreaming)` for live timer
  - Timer display: `<span className="font-mono text-xs tabular-nums text-ai">{elapsed}</span>`
  - Auto-collapse: `useEffect` watching `isStreaming` — when transitions false→true: expand; true→false: collapse after 300ms delay
  - Collapsed header: Brain icon + "Thought for {duration}" + "~{tokens} tokens" badge
  - Streaming header: Brain icon + "Thinking..." + pulsing dot + elapsed timer
  - Add `interrupted` prop: when true, show "Interrupted" label instead of "Thought for..."
  - Content area: keep existing `max-h-[400px] overflow-y-auto scrollbar-thin`
  - Streaming cursor: keep existing `animate-pulse bg-ai` span
  - Interface: add `thinkingStartedAt?: number | null`, `interrupted?: boolean` props
  - Keep file under 200 lines (current: 134)

- [ ] T010 [US1] Update `StreamingContent` in `frontend/src/features/ai/ChatView/MessageList/StreamingContent.tsx`
  - Pass `thinkingStartedAt` and `interrupted` props through to `ThinkingBlock`
  - Add `thinkingStartedAt` and `interrupted` to `StreamingContentProps` interface
  - Remove the generic `Loader2` spinner — thinking block now handles its own indicator

- [ ] T011 [US1] Update `AssistantMessage` in `frontend/src/features/ai/ChatView/MessageList/AssistantMessage.tsx`
  - No changes needed for US1 — completed thinking blocks already render from `message.thinkingBlocks`/`message.thinkingContent`
  - Verify existing render order is correct: thinking blocks → content → structured results → citations → tool calls

- [ ] T012 [US1] Update `MessageList` in `frontend/src/features/ai/ChatView/MessageList/MessageList.tsx`
  - Pass new props to `StreamingContent`: `thinkingStartedAt={store.streamingState.thinkingStartedAt}`, `interrupted={store.streamingState.interrupted}`
  - Add `thinkingStartedAt` and `interrupted` to `MessageListProps`

- [ ] T013 [US1] Update `ChatView` in `frontend/src/features/ai/ChatView/ChatView.tsx`
  - Pass `thinkingStartedAt={store.streamingState.thinkingStartedAt}` to `MessageList`
  - Pass `interrupted={store.streamingState.interrupted}` to `MessageList`

**Checkpoint**: US1 complete — Thinking blocks render with frosted glass styling, live elapsed time, streaming content with cursor, and auto-collapse to summary. Verify with quickstart.md Scenario 1.

---

## Phase 3: US2 — Tool Call Status Cards (P1)

**Goal**: Rich tool call cards with friendly names, status icons, elapsed time, and collapsible I/O details. Parallel grouping.
**Verify**: Trigger `/extract-issues`. Tool cards show friendly names, status progression, elapsed time. Parallel tools grouped.

### Tests

- [ ] T014 [P] [US2] Write unit tests for `ToolCallCard` in `frontend/src/features/ai/ChatView/MessageList/__tests__/ToolCallCard.test.tsx`
  - Test: renders mapped display name from `TOOL_DISPLAY_NAMES` (e.g., "Extracting Issues")
  - Test: falls back to title-cased raw name for unknown tools
  - Test: shows `Loader2` spinning icon + AI blue color when status is `pending`/running
  - Test: shows `CheckCircle2` green icon when status is `completed`
  - Test: shows `XCircle` red icon when status is `failed`
  - Test: displays error message prominently when `errorMessage` is set
  - Test: shows elapsed time via `useElapsedTime` when status is `pending`
  - Test: shows final duration from `durationMs` when `completed`
  - Test: collapsible detail expands to show input JSON with formatting
  - Test: collapsible detail shows output when available
  - Test: shows partial input with pulsing indicator when `partialInput` is set (T65)

- [ ] T015 [P] [US2] Write unit tests for updated `ToolCallList` in `frontend/src/features/ai/ChatView/MessageList/__tests__/ToolCallList.test.tsx`
  - Test: renders `ToolCallCard` for each tool call
  - Test: shows "Parallel (N tools)" header with `GitBranch` icon when `toolCalls.length > 1`
  - Test: wraps parallel calls in container with left border
  - Test: returns null when `toolCalls` is empty

### Implementation

- [ ] T016 [US2] Create `ToolCallCard` component in `frontend/src/features/ai/ChatView/MessageList/ToolCallCard.tsx`
  - New component replacing inline `ToolCallItem` from `ToolCallList.tsx`
  - Props: `toolCall: ToolCall`, `className?: string`
  - Import `getToolDisplayName` from `constants.ts`
  - Status icon map: `{ pending: Loader2, completed: CheckCircle2, failed: XCircle }`
  - Status color map: `{ pending: 'text-ai', completed: 'text-primary', failed: 'text-destructive' }`
  - Pending icon: add `animate-spin` class (with `motion-reduce:animate-none`)
  - Elapsed time: use `useElapsedTime` when status is `pending` (start time inferred from first render)
  - Completed duration: format `toolCall.durationMs` with `formatDuration`
  - Use shadcn `Collapsible` for detail section
  - Detail section: Input label + `<pre>` with `JSON.stringify(input, null, 2)`, Output label + formatted output
  - Partial input (T65): show `partialInput` with pulsing dot when status is `pending`
  - Error display: red text below tool name when `errorMessage` is set
  - ARIA: `role="article"`, `aria-label="{displayName} — {statusLabel}"`
  - Keep file under 180 lines

- [ ] T017 [US2] Update `ToolCallList` in `frontend/src/features/ai/ChatView/MessageList/ToolCallList.tsx`
  - Replace inline `ToolCallItem` component with imported `ToolCallCard`
  - Remove `ToolCallItem` definition (it's now `ToolCallCard.tsx`)
  - Keep parallel grouping logic: `isParallel = toolCalls.length > 1`
  - Update header text from "Tool Calls (N)" to "Parallel (N tools)" when parallel, "Tool Call" when single
  - Keep `GitBranch` icon for parallel indicator
  - Keep left border styling for parallel group

**Checkpoint**: US2 complete — Tool cards show friendly names, spinning/check/X status icons, elapsed time, and collapsible JSON I/O. Parallel tools grouped. Verify with quickstart.md Scenario 2 and 3.

---

## Phase 4: US3 — Streaming State Banner (P1)

**Goal**: Fixed banner above chat input showing current agent processing phase with icon, label, and elapsed time.
**Verify**: Send a complex request. Banner transitions through thinking → tool use → writing phases.

### Tests

- [ ] T018 [P] [US3] Write unit tests for `StreamingBanner` in `frontend/src/features/ai/ChatView/__tests__/StreamingBanner.test.tsx`
  - Test: renders nothing when `isStreaming=false`
  - Test: shows brain icon + "Thinking..." when phase is `thinking`
  - Test: shows wrench icon + mapped tool name when phase is `tool_use` and `activeToolName` is set
  - Test: shows pencil icon + "Writing response..." + word count when phase is `content`
  - Test: shows "Stopped" briefly when `interrupted=true`
  - Test: elapsed time counter displays and updates
  - Test: uses `glass-subtle` class for frosted glass background
  - Test: has `border-t border-t-border-subtle` for top border
  - Test: smooth phase transition via AnimatePresence
  - Test: accessible — has `role="status"` and `aria-live="polite"`

### Implementation

- [ ] T019 [US3] Create `StreamingBanner` in `frontend/src/features/ai/ChatView/StreamingBanner.tsx`
  - Props: `isStreaming: boolean`, `phase: StreamingPhase | undefined`, `activeToolName: string | null`, `wordCount: number`, `interrupted: boolean`, `thinkingStartedAt: number | null`, `className?: string`
  - Returns null when `!isStreaming && !interrupted`
  - Phase icon map: `{ thinking: Brain, tool_use: Wrench, content: Pencil, connecting: Loader2, completing: Check }`
  - Phase label map:
    - `thinking` → "Thinking..."
    - `tool_use` → `"Using {getToolDisplayName(activeToolName)}..."`
    - `content` → `"Writing response..."`
    - `connecting` → "Connecting..."
    - `completing` → "Finishing..."
  - Right side: elapsed time (from `useElapsedTime`) or word count (`"{N}w"` for content phase)
  - Interrupted state: Square icon + "Stopped" label, auto-hides after 1.5s via `setTimeout`
  - Layout: `h-9 flex items-center justify-between px-3` + `glass-subtle` + `border-t border-t-border-subtle`
  - Phase transitions: wrap icon+label in `AnimatePresence` with `motion.div` fade (150ms)
  - ARIA: `role="status"` + `aria-live="polite"`
  - Keep file under 150 lines

- [ ] T020 [US3] Integrate `StreamingBanner` into `ChatView` in `frontend/src/features/ai/ChatView/ChatView.tsx`
  - Import `StreamingBanner`
  - Insert between the main content `</div>` (line ~333) and inline suggestion cards (line ~336)
  - Pass props from store:
    - `isStreaming={store.isStreaming}`
    - `phase={store.streamingState.phase}`
    - `activeToolName={store.streamingState.activeToolName}`
    - `wordCount={store.streamingState.wordCount ?? 0}`
    - `interrupted={store.streamingState.interrupted ?? false}`
    - `thinkingStartedAt={store.streamingState.thinkingStartedAt}`

**Checkpoint**: US3 complete — Streaming banner appears above input during processing, shows current phase with icon and elapsed time, transitions smoothly between phases, shows "Stopped" on abort. Verify with quickstart.md Scenario 4.

---

## Phase 5: US4 — Thinking Block Design Enhancement (P2)

**Goal**: Polished frosted-glass visual treatment with AI accent color, token estimate badge, and code highlighting in thinking content.
**Verify**: Compare thinking blocks visually against design-mood.md specs. Blocks are immediately distinguishable from regular content.

### Implementation

- [ ] T021 [US4] Refine `ThinkingBlock` visual polish in `frontend/src/features/ai/ChatView/MessageList/ThinkingBlock.tsx`
  - This task is incremental polish on top of T009 (which implements the core redesign)
  - Verify frosted glass: `glass-subtle` + `bg-ai-muted` renders correctly in both light and dark mode
  - Add subtle `shadow-warm-sm` on hover state
  - Token estimate badge in collapsed header: `<Badge variant="secondary" className="text-xs">{estimateTokens(content).toLocaleString()} tokens</Badge>`
  - Verify collapsed state shows brain icon + "Thought for {duration}" + token badge + chevron
  - Verify code blocks within thinking content render with `font-mono` (already handled by `<pre>`)
  - Verify dark mode: `--ai-muted` shifts to `#1f2d38`, left border uses `--ai` dark value `#7da3c1`
  - Verify `prefers-reduced-motion`: pulsing border becomes static, cursor doesn't animate

**Checkpoint**: US4 complete — Thinking blocks have polished frosted-glass design, clearly distinguishable from text content. Token badges show on completed blocks.

---

## Phase 6: US5 — Tool Call Timeline View (P2)

**Goal**: Vertical step list showing numbered tool execution steps with status indicators and duration badges.
**Verify**: Trigger 3+ tool calls. "View steps" toggle appears. Timeline shows numbered vertical steps.

### Tests

- [ ] T022 [P] [US5] Write unit tests for `ToolStepTimeline` in `frontend/src/features/ai/ChatView/MessageList/__tests__/ToolStepTimeline.test.tsx`
  - Test: renders nothing when `toolCalls.length < 3`
  - Test: renders numbered step circles for each tool call
  - Test: completed steps show green checkmark circle
  - Test: running steps show AI-blue spinning indicator
  - Test: failed steps show red X circle
  - Test: pending steps show muted hollow circle
  - Test: connecting vertical line between steps
  - Test: shows mapped display name per step
  - Test: shows duration badge for completed tools
  - Test: accessible — ordered list with `aria-label` per step

### Implementation

- [ ] T023 [US5] Create `ToolStepTimeline` in `frontend/src/features/ai/ChatView/MessageList/ToolStepTimeline.tsx`
  - Props: `toolCalls: ToolCall[]`, `className?: string`
  - Returns null when `toolCalls.length < 3`
  - Layout: `<ol>` with vertical connecting line via `border-l-2 border-l-border-subtle ml-[9px]`
  - Each step `<li>`:
    - Circle (20px): positioned over the vertical line with negative margin
    - Pending: `border-2 border-muted-foreground bg-background` (hollow)
    - Running: `bg-ai border-2 border-ai` + inner `Loader2 h-2.5 w-2.5 animate-spin text-white`
    - Completed: `bg-primary` + inner `Check h-2.5 w-2.5 text-white`
    - Failed: `bg-destructive` + inner `X h-2.5 w-2.5 text-white`
    - Tool name: `text-sm font-medium` via `getToolDisplayName`
    - Duration: `font-mono text-xs tabular-nums text-muted-foreground` — `formatDuration(durationMs)` or `useElapsedTime` if running
  - ARIA: `<ol aria-label="Tool execution steps">`, each `<li aria-label="{name} — {status}">`
  - Keep file under 150 lines

- [ ] T024 [US5] Add "View steps" toggle to `ToolCallList` in `frontend/src/features/ai/ChatView/MessageList/ToolCallList.tsx`
  - Add `const [showTimeline, setShowTimeline] = useState(false)` state
  - Show toggle button only when `toolCalls.length >= 3`: `<button className="text-xs text-ai hover:underline">{showTimeline ? 'Hide steps' : 'View steps'}</button>`
  - When `showTimeline=true`: render `<ToolStepTimeline toolCalls={toolCalls} />` below the tool cards
  - Import `ToolStepTimeline`

**Checkpoint**: US5 complete — Timeline appears for 3+ tool calls with numbered steps, status circles, and duration badges. Verify with quickstart.md Scenario 5.

---

## Phase 7: US6 — Token Budget Ring (P3)

**Goal**: Compact circular progress ring near the send button showing session token consumption.
**Verify**: Exchange messages in a session. Ring fills proportionally, changes color, tooltip shows token count.

### Tests

- [ ] T025 [P] [US6] Write unit tests for `TokenBudgetRing` in `frontend/src/components/ui/__tests__/token-budget-ring.test.tsx`
  - Test: renders SVG with viewBox and circle elements
  - Test: stroke-dasharray reflects percentage (0% = no fill, 50% = half, 100% = full)
  - Test: stroke color is green (`--primary`) when < 60%
  - Test: stroke color is yellow (`--warning`) when 60-79%
  - Test: stroke color is orange when 80-94%
  - Test: stroke color is red (`--destructive`) when >= 95%
  - Test: tooltip shows "X.XK / 8K tokens (N%)" on hover
  - Test: ring pulses when >= 95% (CSS class `motion-safe:animate-pulse`)
  - Test: renders nothing when percentage is 0 or undefined (optional: show empty ring)
  - Test: accessible — `role="progressbar"`, `aria-valuenow`, `aria-valuemin=0`, `aria-valuemax=100`, `aria-label`

### Implementation

- [ ] T026 [US6] Create `TokenBudgetRing` in `frontend/src/components/ui/token-budget-ring.tsx`
  - Props: `percentage: number`, `tokensUsed?: number`, `tokenBudget?: number`, `className?: string`
  - SVG: 24x24 viewBox, two circles (background track + progress arc)
  - Background circle: `stroke="var(--border-subtle)"`, `stroke-width="2"`, `fill="none"`
  - Progress circle: `stroke-dasharray` computed from percentage, `stroke-linecap="round"`
  - Color thresholds: `< 60% → var(--primary)`, `60-79% → var(--warning)`, `80-94% → #D98040`, `>= 95% → var(--destructive)`
  - Pulse at 95%: `motion-safe:animate-pulse` class on SVG element
  - Wrap in shadcn `Tooltip`: content = `"{tokensUsed/1000}K / {tokenBudget/1000}K tokens ({percentage}%)"`
  - ARIA: `role="progressbar"`, `aria-valuenow={percentage}`, `aria-valuemin={0}`, `aria-valuemax={100}`, `aria-label="Token budget usage"`
  - Keep file under 100 lines

- [ ] T027 [US6] Integrate `TokenBudgetRing` into `ChatInput` in `frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx`
  - Add props: `tokenBudgetPercent?: number`, `tokensUsed?: number`
  - Import `TokenBudgetRing`
  - Add ring to the inline toolbar (line ~158), before the `SkillMenu` button:
    ```
    {tokenBudgetPercent != null && tokenBudgetPercent > 0 && (
      <TokenBudgetRing percentage={tokenBudgetPercent} tokensUsed={tokensUsed} tokenBudget={8000} />
    )}
    ```
  - Adjust `pr-20` to `pr-24` on textarea if ring is visible (to avoid overlap)

- [ ] T028 [US6] Pass token budget props through `ChatView` in `frontend/src/features/ai/ChatView/ChatView.tsx`
  - Pass to `ChatInput`: `tokenBudgetPercent={store.tokenBudgetPercent}`, `tokensUsed={store.sessionState.totalTokens}`

**Checkpoint**: US6 complete — Token budget ring appears near send button, fills proportionally, changes color at thresholds, tooltip shows token count. Verify with quickstart.md Scenario 6.

---

## Phase 7b: US7 — Streaming Text Fade-In Effect (P1)

**Goal**: AI text responses fade in line-by-line during streaming instead of appearing instantly, creating a polished reveal effect.
**Verify**: Send any message. Response text appears with smooth opacity fade-in at each new line/sentence boundary.

### Tests

- [ ] T036 [P] [US7] Write unit tests for streaming fade-in in `frontend/src/features/ai/ChatView/MessageList/__tests__/MarkdownContent.test.tsx`
  - Test: when `isStreaming=false`, renders content without any animation wrappers
  - Test: when `isStreaming=true`, latest content chunk has `animate-fade-up` class
  - Test: previously rendered content does not have animation class (full opacity)
  - Test: content splits correctly at line boundaries (`\n`)
  - Test: cursor still renders at the end when streaming
  - Test: `prefers-reduced-motion` — no animation class applied (handled by existing CSS rule)
  - Test: empty content returns null

### Implementation

- [ ] T037 [US7] Implement line-by-line fade-in in `frontend/src/features/ai/ChatView/MessageList/MarkdownContent.tsx`
  - Add `previousContentLength` tracking via `useRef<number>(0)`
  - When `isStreaming=true`:
    - Split `content` into `stableContent` (up to last `\n` before `previousContentLength`) and `newContent` (remainder)
    - Render `stableContent` via `ReactMarkdown` without animation
    - Render `newContent` wrapped in `<span className="motion-safe:animate-fade-up">` via second `ReactMarkdown`
    - On each render with new content, update `previousContentLength` ref after a 200ms delay (so the fade completes before marking as "stable")
  - When `isStreaming=false`:
    - Reset `previousContentLength` to 0
    - Render all content normally via single `ReactMarkdown` (no animation wrappers)
  - Keep streaming cursor at the end of `newContent` block
  - Keep file under 100 lines

- [ ] T038 [US7] Verify `StreamingContent` passes `isStreaming` correctly to `MarkdownContent` in `frontend/src/features/ai/ChatView/MessageList/StreamingContent.tsx`
  - Confirm `MarkdownContent` receives `isStreaming` prop (already passes `isStreaming` on line 40)
  - No changes expected — verification only

**Checkpoint**: US7 complete — AI responses fade in line by line during streaming. Previously rendered text is fully opaque. Cursor visible at end. Reduced motion respected.

---

## Phase 7c: US8 — AI Block Edit Highlight & New Content Fade-In (P1)

**Goal**: Edited note blocks glow with AI-blue highlight that fades out after completion. New blocks appended by AI slide in with fade animation.
**Verify**: Ask AI to enhance text in a note. Edited block highlights blue then fades. New blocks slide in smoothly.

### Tests

- [ ] T039 [P] [US8] Write unit tests for block highlight behavior in `frontend/src/features/notes/hooks/__tests__/useContentUpdates.test.ts`
  - Test: after `replace_block` completes, `ai-block-edited` class is added to the block's DOM node
  - Test: `ai-block-edited` class is removed after 1.1s (transition duration + buffer)
  - Test: after `append_blocks` completes, new blocks have `ai-block-new` class
  - Test: `ai-block-new` class is removed after 400ms (animation duration + buffer)
  - Test: multiple sequential edits each get independent highlight/removal

### Implementation

- [ ] T040 [US8] Add CSS classes for block edit highlight and new block slide-in in `frontend/src/app/globals.css`
  - Add `ai-block-edited` class:
    ```css
    [data-block-id].ai-block-edited {
      background: var(--ai-muted);
      transition: background 1s ease-out;
    }
    [data-block-id].ai-block-edited.ai-block-fade-out {
      background: transparent;
    }
    ```
  - Add `ai-block-new` class:
    ```css
    [data-block-id].ai-block-new {
      animation: blockSlideIn 300ms ease-out forwards;
    }
    @keyframes blockSlideIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    ```
  - Add both classes to the `prefers-reduced-motion` section:
    ```css
    [data-block-id].ai-block-edited {
      transition: none !important;
    }
    [data-block-id].ai-block-new {
      animation: none !important;
    }
    ```
  - Place in the existing "AI BLOCK PROCESSING INDICATOR" section (~line 1234)

- [ ] T041 [US8] Add highlight/fade logic to `useContentUpdates` hook in `frontend/src/features/notes/hooks/useContentUpdates.ts`
  - After a `replace_block` operation succeeds and blockId is removed from `processingBlockIds`:
    - Query DOM: `document.querySelector(\`[data-block-id="${blockId}"]\`)`
    - Add `ai-block-edited` class
    - After 50ms (next frame): add `ai-block-fade-out` class (triggers CSS transition)
    - After 1100ms: remove both classes
  - After an `append_blocks` operation succeeds:
    - Query DOM for newly inserted blocks (by blockId if available, or last N blocks)
    - Add `ai-block-new` class
    - After 400ms: remove class
  - Use `setTimeout` for class removal; clean up timeouts on unmount via `useEffect` cleanup
  - Keep changes minimal — add a helper function `highlightBlock(blockId, type: 'edited' | 'new')` to encapsulate the logic

- [ ] T042 [US8] Verify `AIBlockProcessingExtension` still works correctly alongside new classes in `frontend/src/components/editor/extensions/AIBlockProcessingExtension.ts`
  - Confirm `ai-block-processing` (pulsing during edit) and `ai-block-edited` (highlight after edit) don't conflict
  - `ai-block-processing` is removed when block exits processingBlockIds
  - `ai-block-edited` is added immediately after `ai-block-processing` is removed
  - No changes expected to extension — verification only

**Checkpoint**: US8 complete — AI-edited blocks glow blue and fade out over 1s. New blocks slide in from below. Multiple edits animate independently. Reduced motion respected.

---

## Phase 8: Polish

- [ ] T029 [P] Run full quickstart.md validation — all 9 scenarios including dark mode (Scenario 7), reduced motion (Scenario 8), and interruption (Scenario 9)
- [ ] T030 [P] Verify all new components support dark mode — toggle dark mode, visual inspection of ThinkingBlock, ToolCallCard, StreamingBanner, ToolStepTimeline, TokenBudgetRing
- [ ] T031 [P] Verify `prefers-reduced-motion` — enable reduced motion, confirm no continuous animations, all indicators static
- [ ] T032 [P] Verify WCAG 2.2 AA — keyboard navigation through all new interactive elements, ARIA labels present, focus rings visible, contrast ratios pass
- [ ] T033 Verify file size limits — all new/edited files under 700 lines
- [ ] T034 Run full quality gates: `pnpm lint && pnpm type-check && pnpm test`
- [ ] T035 Verify test coverage > 80% for all new files — `pnpm test --coverage`

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified. All new components accessible, dark-mode compatible, and reduced-motion safe.

---

## Dependencies

### Phase Order

```
Phase 1 (Foundation) → Phase 2 (US1) → Phase 3 (US2) → Phase 4 (US3) → Phase 5 (US4) ‖ Phase 6 (US5) ‖ Phase 7 (US6) ‖ Phase 7b (US7) ‖ Phase 7c (US8) → Phase 8 (Polish)
```

### Story Independence

- US1 (Thinking) and US2 (Tool Cards) can run in parallel after Foundation — they edit different files
- US3 (Banner) depends on US1 store extensions (`thinkingStartedAt`, `interrupted`) — sequential after US1
- US4 (Thinking Polish) depends on US1 — incremental refinement of same file
- US5 (Timeline) depends on US2 — adds toggle to `ToolCallList` edited in US2
- US6 (Token Ring) is independent — can run in parallel with US4/US5
- US7 (Streaming Fade-In) is independent — edits `MarkdownContent.tsx` which is not touched by other stories. Can run in parallel with US4/US5/US6
- US8 (Block Edit Highlight) is independent — edits `useContentUpdates` hook and `globals.css`, not touched by other stories. Can run in parallel with US4-US7

### Within Each Story

```
Tests (write first) → Implementation → Integration with parent components
```

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 1 | Shared utilities | T001, T002 |
| Phase 2 | US1 tests | T007, T008 |
| Phase 2+3 | US1 impl + US2 tests | T009-T013 ‖ T014, T015 |
| Phase 4 | US3 tests | T018 |
| Phase 6+7 | US5 tests + US6 tests | T022 ‖ T025 |
| Phase 8 | Polish checks | T029, T030, T031, T032 |

---

## Execution Strategy

**Selected Strategy**: **B — Incremental**

```
Foundation → US1 (Thinking) → US2 (Tool Cards) → US3 (Banner) → US4 (Polish) ‖ US5 (Timeline) ‖ US6 (Token Ring) ‖ US7 (Fade-In) ‖ US8 (Block Highlight) → Polish
```

Rationale: Requirements are stable (clarified in pre-plan). Each story delivers a visible improvement that can be reviewed independently. P1 stories ship first for maximum impact, followed by P2/P3 enhancements.

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase (US1-US6 → Phases 2-7)
- [x] Every state extension from plan.md data model has a creation task (T003-T006)
- [x] Every component from plan.md project structure has an implementation task
- [x] Every quickstart scenario has a validation task (T029 covers all 9 scenarios)
- [x] Setup (Phase 1) and Polish (Phase 8) phases included

### Task Quality

- [x] Task IDs sequential (T001-T035) with no gaps
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent (different files)
- [x] `[USn]` markers on all Phase 2+ tasks

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced: Foundation → Stories → Polish
- [x] Within-story order: Tests → Implementation → Integration
- [x] Cross-story shared utilities placed in Foundation phase (T001-T006)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase (T034)
- [x] Execution strategy selected with rationale

---

## Next Phase

After this task list passes all checklists:

1. **Create feature branch** — `git checkout -b 008-chat-thinking-toolcall-ux`
2. **Begin Phase 1** — T001 and T002 in parallel, then T003-T006 sequentially
3. **Track progress** — Check off tasks, verify checkpoints at phase boundaries
