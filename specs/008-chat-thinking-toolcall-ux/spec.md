# Feature Specification: Enhanced Thinking & Tool Call Visualization

**Feature Number**: 008
**Branch**: `008-chat-thinking-toolcall-ux`
**Created**: 2026-02-04
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All Pilot Space users interacting with the AI chatbox (Architects, Tech Leads, PMs, Developers)

**Problem**: When the AI agent is thinking or executing tool calls, users see minimal visual feedback — a generic spinner and a collapsed "Agent Reasoning" block. Users cannot tell what the agent is doing, how long it has been working, which tools are running, or whether progress is being made. This creates anxiety ("Is it stuck?"), breaks trust ("What did it just do?"), and reduces the perceived intelligence of the system.

**Impact**: Users abort long-running operations prematurely (wasted tokens/cost). Users lose trust when tool calls happen silently. The chatbox feels like a black box rather than a transparent collaborator. Competing products (Cursor, Windsurf, ChatGPT) have set expectations for rich thinking/tool visualizations that Pilot Space currently doesn't meet.

**Success**: Users feel informed and in control at every stage of AI processing. Thinking is visually distinct from content. Tool calls are transparent with clear status progression. Users can follow the agent's reasoning in real-time without feeling lost or anxious.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Architect / Product Owner | UX quality, design system consistency | Design direction approval | Spec review |
| End Users | AI Chat Users | Transparency, responsiveness, trust | Usability feedback | Acceptance test |

---

## User Scenarios & Testing

### User Story 1 — Real-Time Thinking Visualization (Priority: P1)

When the AI agent enters a thinking/reasoning phase, the user sees a visually distinct, animated indicator that communicates "the agent is reasoning" — not just a generic spinner. The thinking content streams in real-time with a typewriter effect inside a collapsible block. The block header shows elapsed time and a contextual label (e.g., "Analyzing code structure..." or "Reasoning about your request..."). When thinking completes, the block auto-collapses to a summary line showing total duration.

**Why this priority**: Thinking is the most frequent intermediate state. Without clear feedback, users assume the system is frozen. This is the highest-impact UX improvement for perceived responsiveness.

**Independent Test**: Send any message to the AI agent that triggers extended thinking. Observe the thinking block appears immediately, streams content, shows elapsed time, and collapses on completion.

**Acceptance Scenarios**:

1. **Given** the AI agent begins thinking, **When** the `thinking_delta` SSE event arrives, **Then** a thinking block appears with an animated "brain" indicator, a pulsing border in the AI accent color, and elapsed time counter starting from 0s
2. **Given** thinking content is streaming, **When** the user clicks the thinking block header, **Then** the block expands to show raw thinking text with a typewriter cursor effect
3. **Given** thinking completes (next non-thinking event arrives), **When** the block transitions to completed state, **Then** the header updates to show total duration (e.g., "Thought for 3.2s"), the pulsing animation stops, the block auto-collapses, and a subtle completion indicator appears
4. **Given** multiple interleaved thinking blocks exist (G-07), **When** they render in the message, **Then** each block is independently collapsible with its own duration label

---

### User Story 2 — Tool Call Status Cards (Priority: P1)

When the AI agent invokes a tool, the user sees a compact, visually rich card showing: the tool name (human-readable), current status (pending/running/completed/failed), execution duration, and a collapsible section for input/output details. Multiple parallel tool calls display side-by-side or stacked with a visual grouping indicator.

**Why this priority**: Tool calls are the primary way the agent acts on behalf of the user. Silent tool execution breaks the transparency contract of DD-003 (human-in-the-loop). Users need to see what tools are being used and their results.

**Independent Test**: Trigger a skill that invokes MCP tools (e.g., `/extract-issues`). Observe each tool call appears as a distinct card with status progression from pending through completion.

**Acceptance Scenarios**:

1. **Given** the agent invokes a tool, **When** the `tool_use` SSE event arrives, **Then** a tool card appears with: human-readable tool name, "Running..." status with animated indicator, and elapsed time counter
2. **Given** a tool call is in progress, **When** `tool_input_delta` events stream partial input (T65), **Then** the card's collapsible detail section shows the input being assembled in real-time with syntax highlighting
3. **Given** a tool call completes successfully, **When** the `tool_result` event arrives, **Then** the card transitions to "Completed" with a check icon, shows execution duration, and the output is available in the collapsible detail
4. **Given** a tool call fails, **When** the `tool_result` event arrives with an error, **Then** the card transitions to "Failed" with a red indicator, shows the error message prominently, and optionally suggests retry
5. **Given** multiple tools execute in parallel (G-13), **When** they render, **Then** they appear grouped under a "Parallel Execution" label with individual status indicators

---

### User Story 3 — Streaming State Banner (Priority: P1)

While the agent is processing (thinking, calling tools, or generating text), a persistent but non-intrusive banner appears between the last message and the input area. This banner shows the current phase: "Thinking...", "Using tool: update_note_block", "Generating response...", with appropriate iconography and animation for each phase. It replaces the current generic spinner approach.

**Why this priority**: Users need a single glanceable indicator of what the agent is doing right now, without scrolling up to find the relevant thinking block or tool card. This is the "status bar" of the conversation.

**Independent Test**: Send a complex request that triggers thinking + tool calls + text generation. Observe the banner transitions through each phase with appropriate labels.

**Acceptance Scenarios**:

1. **Given** the agent starts thinking, **When** the streaming state changes to `isThinking: true`, **Then** the banner shows a brain icon with "Thinking..." and a subtle pulsing animation
2. **Given** the agent calls a tool, **When** the streaming state changes to `currentBlockType: 'tool_use'`, **Then** the banner shows a wrench/gear icon with "Using [tool name]..." and elapsed time
3. **Given** the agent generates text, **When** the streaming state changes to `currentBlockType: 'text'`, **Then** the banner shows a pencil icon with "Writing response..." and streaming word count
4. **Given** the user clicks the abort button, **When** the stream is cancelled, **Then** the banner shows "Stopped" briefly then disappears, and the partial response is preserved

---

### User Story 4 — Thinking Block Design Enhancement (Priority: P2)

The thinking block adopts a visually distinct "frosted glass" card style with the AI accent color (`--ai`) that clearly separates it from regular message content. The header includes: a brain icon, contextual label, duration badge, and token estimate badge. When collapsed, it shows a one-line summary. The block supports code syntax highlighting within thinking content.

**Why this priority**: The current thinking block is visually identical to regular content except for the header text. Users need instant visual recognition that "this is the agent's internal reasoning, not the final answer."

**Independent Test**: Compare a message with thinking blocks against one without. The thinking blocks should be immediately distinguishable through color, shape, and iconography.

**Acceptance Scenarios**:

1. **Given** a thinking block renders, **When** the user views it, **Then** it has a frosted glass background with AI accent color border-left (4px), rounded corners, and is visually distinct from text content
2. **Given** a completed thinking block is collapsed, **When** the user views the header, **Then** it shows: brain icon + "Thought for X.Xs" + token estimate badge (e.g., "~120 tokens")
3. **Given** thinking content contains code blocks, **When** expanded, **Then** code blocks render with syntax highlighting matching the rest of the chat

---

### User Story 5 — Tool Call Timeline View (Priority: P2)

For complex operations with multiple sequential and parallel tool calls, users can view a timeline/waterfall visualization showing the execution order, dependencies, and duration of each tool call. This is accessible via a "View Timeline" toggle on the tool call section.

**Why this priority**: Complex agent operations (PR review, AI context aggregation) involve many tool calls. A timeline helps users understand the execution flow and identify bottlenecks. Less critical than individual tool cards but valuable for power users.

**Independent Test**: Trigger a subagent operation (e.g., `@pr-review`) that spawns multiple tool calls. Toggle the timeline view to see waterfall execution.

**Acceptance Scenarios**:

1. **Given** a message contains 3+ tool calls, **When** the user clicks "View Timeline", **Then** a horizontal waterfall chart appears showing each tool as a bar on a time axis, color-coded by status (running=blue, completed=green, failed=red)
2. **Given** tools ran in parallel (G-13), **When** the timeline renders, **Then** parallel tools appear on separate lanes at the same time position
3. **Given** the timeline is open, **When** the user hovers a tool bar, **Then** a tooltip shows: tool name, duration, input summary, output summary

---

### User Story 6 — Token Budget Indicator (Priority: P3)

Users see a subtle progress indicator near the chat input showing how much of the session's 8K token budget has been consumed. The indicator changes color as usage increases (green → yellow → orange → red). At 80%, a toast notification warns the user. At 95%, the indicator pulses.

**Why this priority**: Nice-to-have transparency feature. Users currently have no visibility into token consumption, which affects cost and session continuity.

**Independent Test**: Send several messages in a session. Observe the token budget indicator incrementing with each exchange.

**Acceptance Scenarios**:

1. **Given** the user has an active chat session, **When** they view the chat input area, **Then** a thin progress bar or circular indicator shows current token usage as a percentage of 8K budget
2. **Given** token usage exceeds 80%, **When** the `budget_warning` event arrives, **Then** a non-blocking toast appears and the indicator turns orange
3. **Given** token usage exceeds 95%, **When** the indicator updates, **Then** it turns red and pulses subtly to signal the session is nearly exhausted

---

### User Story 7 — Streaming Text Fade-In Effect (Priority: P1)

When the AI agent generates text responses, new lines and sentences fade in with a smooth opacity transition rather than appearing instantly. Each new block of content (line or sentence boundary) animates from transparent to fully visible, creating a polished "reveal" effect. The cursor remains at the end of the latest content. Previously rendered content stays fully opaque.

**Why this priority**: The current text streaming shows content appearing character by character with no visual transition — it pops in abruptly. This feels jarring compared to the smooth, intentional feel of the rest of the design system. A line-by-line fade-in transforms the streaming experience from "raw data dump" to "thoughtful communication", matching the Warm/Capable/Collaborative design philosophy.

**Independent Test**: Send any message to the AI agent. Observe the response text appearing line by line with a smooth opacity fade-in on each new line/sentence.

**Acceptance Scenarios**:

1. **Given** the AI agent is generating a text response, **When** a new line or sentence boundary is detected in the stream, **Then** the new content fades in from `opacity: 0` to `opacity: 1` over 150-200ms
2. **Given** multiple lines are streaming, **When** the user watches the response, **Then** previously rendered lines are fully opaque while only the latest line/chunk has the fade-in animation
3. **Given** the response contains markdown elements (code blocks, lists, headers), **When** they stream in, **Then** each markdown block fades in as a complete unit (not character by character)
4. **Given** `prefers-reduced-motion` is enabled, **When** text streams, **Then** content appears instantly without fade animation (respects accessibility)
5. **Given** the stream completes (`message_stop`), **When** the final content renders, **Then** all content is fully opaque with no lingering animations

---

### User Story 8 — AI Block Edit Highlight & New Content Fade-In (Priority: P1)

When the AI modifies a note block via `content_update` operations, the edited block receives a visible highlight effect — an AI-blue background glow that fades out over 1 second after the edit completes. When the AI appends new blocks, the new content slides in from below with a fade-in animation. This gives users clear visual confirmation of what the AI changed and where new content was added.

**Why this priority**: The current indicator is a 2px pulsing left border, which is too subtle — users miss AI edits, especially when the edited block is not in the viewport. A highlight glow makes edits unmissable and the fade-out signals completion. New block slide-in prevents content from "jumping" into view.

**Independent Test**: Use the AI chat with a note context active. Ask the AI to enhance or summarize text. Observe the edited block glows AI-blue then fades, and new blocks slide in smoothly.

**Acceptance Scenarios**:

1. **Given** the AI replaces content in a note block (`replace_block` operation), **When** the edit completes and the block exits the processing state, **Then** the block background transitions from `var(--ai-muted)` to transparent over 1 second
2. **Given** the AI appends new blocks (`append_blocks` operation), **When** the new blocks are inserted into the editor, **Then** each new block slides in from below (translateY 8px → 0) with opacity fade (0 → 1) over 300ms
3. **Given** multiple blocks are edited in sequence, **When** each edit completes, **Then** each block independently highlights and fades without interfering with other blocks' animations
4. **Given** `prefers-reduced-motion` is enabled, **When** AI edits a block, **Then** the highlight appears instantly and disappears instantly (no transition), new blocks appear without slide animation
5. **Given** the edited block is not visible in the viewport, **When** the AI edit completes, **Then** the highlight is applied but no scroll occurs (user's viewport is not disrupted)

---

### Edge Cases

- What happens when thinking content is extremely long (>2000 tokens)? The expanded block should be scrollable with a max-height, showing a "Show more" button.
- What happens when a tool call takes longer than 30 seconds? The status card should show elapsed time prominently and the banner should remain visible.
- What happens when the SSE connection drops mid-thinking? The thinking block should show an "Interrupted" state with the last received content preserved.
- What happens when thinking events arrive but contain empty content? Skip rendering empty blocks; only show blocks with actual content.
- What happens when the user scrolls up during active streaming? Auto-scroll pauses (existing behavior), but the streaming banner remains visible at the bottom.
- What happens when dark mode is active? All new components must support dark mode variants using existing `dark:` token system.
- What happens when `prefers-reduced-motion` is set? All pulsing, bouncing, and continuous animations should be replaced with static indicators or gentle opacity transitions.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display a visually distinct thinking indicator within 100ms of receiving the first `thinking_delta` event
- **FR-002**: System MUST stream thinking content in real-time with a visible cursor/typewriter effect
- **FR-003**: System MUST show elapsed time on thinking blocks, updating every second during active thinking
- **FR-004**: System MUST auto-collapse thinking blocks when thinking completes, showing duration in the header
- **FR-005**: System MUST render each tool call as a distinct card with human-readable name, status icon, and elapsed time
- **FR-006**: System MUST transition tool call cards through status states: pending → running → completed/failed
- **FR-007**: System MUST display a streaming state banner showing the current processing phase (thinking/tool use/text generation)
- **FR-008**: System MUST support collapsible tool input/output details with formatting (syntax highlighting for code/JSON)
- **FR-009**: System MUST visually group parallel tool calls (G-13) under a shared container
- **FR-010**: System MUST support independently collapsible interleaved thinking blocks (G-07)
- **FR-011**: System SHOULD display a frosted-glass visual treatment for thinking blocks using the AI accent color
- **FR-012**: System SHOULD show estimated token count on completed thinking blocks
- **FR-013**: System SHOULD provide a timeline/waterfall view when 3+ tool calls exist in a message
- **FR-014**: System MAY display a token budget progress indicator near the chat input
- **FR-015**: System MUST respect `prefers-reduced-motion` by replacing continuous animations with static or subtle opacity indicators
- **FR-016**: System MUST support dark mode for all new visual components
- **FR-017**: System MUST preserve partial thinking/tool content if the stream is interrupted
- **FR-018**: System MUST animate new text content with a fade-in effect (opacity 0→1 over 150-200ms) at line/sentence boundaries during streaming
- **FR-019**: System MUST render previously streamed content at full opacity while only the latest chunk animates
- **FR-020**: System MUST apply a background highlight (AI accent color, fading to transparent over 1 second) to note blocks after AI edit completion
- **FR-021**: System MUST animate new blocks appended by AI with a slide-in effect (translateY 8px → 0, opacity 0 → 1, 300ms duration)

### Key Entities

- **ThinkingBlock**: Represents an agent reasoning phase. Key attributes: content, duration, token estimate, status (streaming/completed/interrupted), block index. Relationships: belongs to ChatMessage
- **ToolCallCard**: Visual representation of a tool invocation. Key attributes: tool name (display name), status, elapsed time, input, output, error message, parallel group ID. Relationships: belongs to ChatMessage, may belong to a parallel group
- **StreamingStateBanner**: Transient UI indicator. Key attributes: current phase (thinking/tool_use/text), active tool name, elapsed time. Relationships: derived from StreamingState in PilotSpaceStore
- **ToolTimeline**: Aggregated waterfall view. Key attributes: tool entries with start/end times, parallel lanes. Relationships: derived from ToolCall[] in ChatMessage

---

## Success Criteria

- **SC-001**: Users identify agent state (thinking vs. tool use vs. text generation) within 1 second of state change, measured by the presence of distinct visual indicators per phase
- **SC-002**: Thinking block appears within 100ms of first `thinking_delta` event (no perceivable delay)
- **SC-003**: Tool call status transitions are reflected in the UI within 200ms of the corresponding SSE event
- **SC-004**: All new components pass WCAG 2.2 AA accessibility audit (keyboard navigation, ARIA labels, contrast ratios, reduced-motion support)
- **SC-005**: No visual regressions in existing chat functionality (message rendering, approvals, structured results, citations)
- **SC-006**: All new components render correctly in both light and dark modes
- **SC-007**: Lighthouse performance score for the chat page remains above 90 after changes

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | Yes | Thinking blocks and tool cards increase transparency into AI reasoning, supporting informed human oversight (DD-003) |
| II. Note-First | No | Feature is chat-specific, not note-related |
| III. Documentation-Third | No | No documentation generation involved |
| IV. Task-Centric | Yes | Each user story is independently testable and deliverable as a standalone improvement |
| V. Collaboration | No | Single-user chat experience |
| VI. Agile Integration | Yes | Stories are prioritized P1-P3 and fit sprint-sized increments |
| VII. Notation Standards | No | No diagrams or notation changes |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names in requirements (component names are domain terms, not implementation)
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P3
- [x] Functional requirements numbered sequentially (FR-001 through FR-017)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Design Inspiration Reference

The following products exemplify the target UX quality for thinking and tool call visualization:

1. **ChatGPT** — Thinking blocks with "Thought for X seconds" collapsible headers, real-time streaming of reasoning
2. **Cursor** — Tool call cards with status indicators, inline code execution feedback
3. **Claude.ai** — Extended thinking with duration display, clean collapsible blocks
4. **Vercel v0** — Step-by-step execution cards with progress indicators and code previews

The Pilot Space implementation should match or exceed these benchmarks while adhering to the Warm/Capable/Collaborative design language (squircle corners, AI dusty blue accent, frosted glass surfaces).

---

## Next Phase

After this spec passes all checklists:

1. **Proceed to planning** — Use `template-plan.md` to create the implementation plan with component architecture, data flow, and styling decisions
2. **Design mockups** — Create visual mockups for thinking blocks, tool cards, streaming banner, and timeline view
3. **Share for review** — This spec is the alignment artifact for design and development
