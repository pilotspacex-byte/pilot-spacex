# Approval & User Input UX Enhancement Specification

**Version**: 1.0.0
**Created**: 2026-02-13
**Status**: Draft
**Scope**: ChatView Approval/Input system in 35% sidebar panel
**References**: DD-003, DD-066, DD-086, ui-design-spec.md v4.0

> **v1 Scope Notice**: The following sections are **deferred to v2** and should NOT be implemented in the initial release. The authoritative v1 scope is defined in `spec.md` and `tasks.md`.
>
> | Section | Feature | Status |
> |---------|---------|--------|
> | 4.2 | Edit & Approve flow | Deferred — v1 uses Reject + re-ask |
> | 4.3 | DestructiveApprovalModal typed confirmation | Deferred — v1 uses standard Confirm/Cancel |
> | 4.4 | BatchApprovalCard | Deferred — v1 stacks approvals vertically |
> | 5.2, 7.7 | SeverityBadge | Deferred — v1 has single visual style |
> | 5.3, 7.6 | ApprovalHistorySummary | Deferred |
> | 5.4, 7.8 | UndoToast + 8s undo window | Deferred — v1: approve = execute immediately |
> | 5.5 | Token cost indicator | Deferred |
> | P4 | "Recoverable by Default" principle | v2 — v1 has no undo affordance |

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Current State Analysis](#2-current-state-analysis)
3. [AskUserQuestion Component System](#3-askuserquestion-component-system)
4. [Tool Approval Enhancement](#4-tool-approval-enhancement)
5. [Trust & Confidence Indicators](#5-trust--confidence-indicators)
6. [Micro-interactions & Animation](#6-micro-interactions--animation)
7. [Component Specifications](#7-component-specifications)
8. [Complete Flow Mockups](#8-complete-flow-mockups)
9. [Accessibility Requirements](#9-accessibility-requirements)
10. [Implementation Priority](#10-implementation-priority)

---

## 1. Design Principles

Five principles specific to the approval/input system, derived from the Pilot Space brand ("Warm, Capable, Collaborative"):

### P1: Conversation, Not Interruption

Approvals and questions appear as natural turns in the conversation flow, not as modal interruptions. The AI is a colleague asking a question, not a system demanding input. Only truly destructive actions warrant a blocking modal.

### P2: Severity Proportional Response

The visual weight of an approval request scales with its risk level. A safe "add label" action gets a subtle inline card. A "delete workspace" gets a full modal with explicit confirmation. The user develops instinct for risk without reading fine print.

### P3: Answer Once, Move On

After the user responds to a question or approves an action, the UI collapses to a compact summary. Past decisions remain visible for auditability but do not clutter the conversation. The chat stays focused on forward progress.

### P4: Recoverable by Default *(v2 — not implemented in v1)*

> **v1**: Approve = execute immediately, no undo. Safety gate is the approval card/modal itself.

Every approved action shows an undo affordance for 8 seconds after execution (where technically feasible). Rejected actions can be re-requested by the AI. The user should never feel anxiety about making a wrong choice.

### P5: Contextual Brevity

In a 35% sidebar, every word and pixel counts. Labels are short. Descriptions are one line. Details are progressive-disclosure (collapsed by default, expandable on demand). The default view is scannable in under 2 seconds.

---

## 2. Current State Analysis

### What Exists

| Component | Location | State |
|-----------|----------|-------|
| `ApprovalOverlay` | `ChatView/ApprovalOverlay/` | Floating button + Dialog modal for destructive actions |
| `ApprovalDialog` | `ChatView/ApprovalOverlay/` | Full modal with countdown, payload preview, reject form |
| `SuggestionCard` | `ChatView/MessageList/` | Inline card for non-destructive approvals (amber theme) |
| `QuestionCard` | `ChatView/MessageList/` | Inline card for AskUserQuestion (warm cream bg) |
| `ApprovalCard` | `features/approvals/` | Card for approval queue page (separate from ChatView) |
| `ApprovalDetailModal` | `features/approvals/` | Detail modal for approval queue page |

### Gaps Identified

1. **QuestionCard** exists but lacks polish: no multi-question stepping, no visual distinction between single-select and multi-select, submit button is unstyled, no answer transition animation.
2. **SuggestionCard** uses amber/yellow theme inconsistent with the AI dusty-blue palette (`--ai: #6B8FAD`).
3. **ApprovalOverlay** uses a fixed `bottom-4 left-4` floating button that overlaps the sidebar content in the 35% layout.
4. No "approve with changes" capability. Users can only accept or reject.
5. No batch approval UI when multiple tools need approval.
6. No undo/rollback affordance after approval.
7. No trust indicators (severity badges, cost per action, approval history).
8. No "AI is waiting" indicator when the chat is in `QUESTION_PENDING` or `APPROVAL_PENDING` state.

---

## 3. AskUserQuestion Component System

### 3.1 Design Decision: Inline Stepped Questions

Questions appear inline in the chat flow, positioned between the AI message that triggered them and the chat input. For 1-2 questions, show them stacked. For 3-4 questions, show them as a stepped flow with a compact progress indicator.

**Rationale**: A 35% sidebar cannot display 4 full questions simultaneously. Stepping keeps each question focused and readable. The step indicator provides progress awareness without consuming vertical space.

### 3.2 QuestionBlock (Enhanced QuestionCard)

Replaces the existing `QuestionCard`. Appears as an AI-authored "turn" in the conversation.

```
+-----------------------------------------------+
|  [?] Agent needs your input              1/2   |  <-- Header with step indicator
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  How should the output be formatted?           |  <-- Question text
|                                                |
|  +-------------------------------------------+|
|  | ( ) Summary                               ||  <-- Radio option
|  |     Brief overview of changes             ||
|  +-------------------------------------------+|
|  +-------------------------------------------+|
|  | (*) Detailed                    [selected] ||  <-- Selected state
|  |     Full explanation with code samples    ||
|  +-------------------------------------------+|
|  +-------------------------------------------+|
|  | ( ) Custom                                ||
|  |     [Type your preference...]             ||  <-- Inline text input
|  +-------------------------------------------+|
|                                                |
|                        [Back]  [Next ->]       |  <-- Step navigation
+-----------------------------------------------+
```

#### Single Question (No Stepping)

```
+-----------------------------------------------+
|  [?] Agent needs your input                    |
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  Which database migration strategy?            |
|                                                |
|  +-------------------------------------------+|
|  | (*) Incremental     [recommended]         ||
|  |     Apply changes one at a time           ||
|  +-------------------------------------------+|
|  +-------------------------------------------+|
|  | ( ) Full rebuild                          ||
|  |     Drop and recreate all tables          ||
|  +-------------------------------------------+|
|                                                |
|  [Or type a different approach...]             |
|                                                |
|                              [Submit answer]   |
+-----------------------------------------------+
```

#### Multi-Select Visual Distinction

Single-select uses radio circles. Multi-select uses square checkboxes. The header indicates the mode:

```
  Select one:                    Select all that apply:
  ( ) Option A                   [ ] Option A
  (*) Option B                   [x] Option B
  ( ) Option C                   [x] Option C
```

#### Answered State (Collapsed)

After submission, the block collapses to a single-line summary:

```
+-----------------------------------------------+
|  [checkmark] Answered: Detailed, Incremental   |
+-----------------------------------------------+
```

Clicking the collapsed state expands to show the full question and selected answer (read-only). This supports auditability without cluttering the conversation.

### 3.3 Multi-Question Step Flow

For 2+ questions, a compact step indicator appears in the header:

```
[?] Agent needs your input                 2/3
```

Navigation:
- **Next** button advances to the next question (enabled when current question has a selection).
- **Back** button returns to the previous question (preserves selections).
- **Submit** button appears on the final question.
- Keyboard: Enter advances, Shift+Enter goes back, Escape dismisses (with confirmation if selections exist).

After all questions are answered and submitted, the entire block collapses:

```
+-----------------------------------------------+
|  [checkmark] Answered 3 questions              |
|  Format: Detailed | Strategy: Incremental |    |
|  Scope: Backend only                           |
+-----------------------------------------------+
```

### 3.4 "AI is processing your answer" Transition

After the user submits their answers:

1. The QuestionBlock collapses with a slide-up animation (200ms, ease-out).
2. A brief "Processing your answer..." indicator appears for 300ms (the AI typically responds within 1-2 seconds).
3. The AI's next message streams in below.

This transition avoids a jarring jump from question UI to streaming text.

---

## 4. Tool Approval Enhancement

### 4.1 Tiered Approval Model

Three tiers, matching DD-003 categories with distinct visual treatments:

| Tier | Risk | Visual | Interaction |
|------|------|--------|-------------|
| **Auto** | None (read ops) | No UI shown | Silently approved |
| **Inline** | Low-Medium (content creation) | Inline card in chat | One-tap approve/dismiss |
| **Modal** | High (destructive) | Blocking dialog | Explicit confirmation required |

### 4.2 InlineApprovalCard (Replaces SuggestionCard)

Redesigned with the AI dusty-blue palette instead of amber. Appears inline in the chat stream.

```
+-----------------------------------------------+
|  [sparkle] PilotSpace wants to:          [ai]  |  <-- AI badge
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  Create 3 issues from "Auth Refactor" note     |  <-- Action description
|                                                |
|  [v] View details                              |  <-- Collapsed detail toggle
|                                                |
|  [Approve]  [Dismiss]  [Edit & Approve]        |  <-- Action buttons
+-----------------------------------------------+
```

#### Severity Indicator

A left border color encodes risk:

| Risk | Border Color | Token |
|------|-------------|-------|
| Safe | `--primary` (#29A386) | Teal-green, thin 2px |
| Caution | `--warning` (#D4A843) | Warm amber, 2px |
| Destructive | `--destructive` (#D9534F) | Red, 3px |

#### Expanded Details

Clicking "View details" expands the card to show the payload preview:

```
+-----------------------------------------------+
|  [sparkle] PilotSpace wants to:          [ai]  |
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  Create 3 issues from "Auth Refactor" note     |
|                                                |
|  [^] Hide details                              |
|  +-------------------------------------------+|
|  | Issue 1: "Migrate auth to Supabase"       ||
|  | Issue 2: "Update RLS policies"            ||
|  | Issue 3: "Remove legacy JWT handler"      ||
|  +-------------------------------------------+|
|                                                |
|  [Approve]  [Dismiss]  [Edit & Approve]        |
+-----------------------------------------------+
```

#### "Edit & Approve" Flow

When the user clicks "Edit & Approve":

1. The payload becomes editable inline (text fields for issue titles, checkbox deselection for batch items).
2. The "Approve" button changes to "Approve with changes".
3. Modified fields show a subtle diff indicator (original crossed out, new value below).

```
+-----------------------------------------------+
|  [sparkle] PilotSpace wants to:          [ai]  |
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  Create issues from "Auth Refactor" note       |
|                                                |
|  [x] Issue 1: [Migrate auth to Supabase    ]  |
|  [x] Issue 2: [Update RLS policies         ]  |
|  [ ] Issue 3: Remove legacy JWT handler        |  <-- Unchecked = skip
|                                                |
|  [Approve 2 items]  [Cancel edit]              |
+-----------------------------------------------+
```

### 4.3 DestructiveApprovalModal (Enhanced ApprovalDialog)

For destructive actions, the existing `ApprovalDialog` is enhanced:

```
+===================================================+
||                                                  ||
||  [!] Destructive Action                          ||
||                                                  ||
||  PilotSpace wants to delete 5 issues             ||
||  from project "Backend API"                      ||
||                                                  ||
||  +---------------------------------------------+||
||  | This action cannot be undone.                |||
||  | 5 issues and their comments, links, and     |||
||  | activity history will be permanently removed.|||
||  +---------------------------------------------+||
||                                                  ||
||  +---------------------------------------------+||
||  | - PS-142: Auth middleware refactor           |||
||  | - PS-143: Session cleanup task              |||
||  | - PS-147: Rate limit config                 |||
||  | - PS-148: CORS policy update                |||
||  | - PS-151: Token rotation logic              |||
||  +---------------------------------------------+||
||                                                  ||
||  [Why?] Agent reasoning (collapsed)              ||
||                                                  ||
||  Type "delete 5 issues" to confirm:              ||
||  +---------------------------------------------+||
||  | [                                          ] |||
||  +---------------------------------------------+||
||                                                  ||
||                  [Cancel]  [Delete permanently]   ||
||                                                  ||
||  Expires in 23:45:12                             ||
||                                                  ||
+===================================================+
```

**Enhancements over current ApprovalDialog**:
- Typed confirmation for destructive actions (like GitHub repository deletion).
- Consequence description is front-and-center, not buried in metadata.
- "Why?" collapsed section shows the AI's reasoning (progressive disclosure).
- Countdown timer is de-emphasized (bottom, smaller text) -- urgency should come from understanding, not time pressure.

### 4.4 Batch Approval

When multiple tool approvals are pending simultaneously (e.g., AI wants to create 3 issues and update 2 labels):

```
+-----------------------------------------------+
|  [sparkle] 3 actions pending           [ai]    |
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  [x] Create issue "Auth migration"     [safe]  |
|  [x] Create issue "RLS update"         [safe]  |
|  [x] Add label "backend" to PS-142  [safe]     |
|                                                 |
|  [Approve all 3]  [Review individually]         |
+-----------------------------------------------+
```

"Review individually" expands each into its own InlineApprovalCard with sequential approval.

### 4.5 Rejection Flow

When dismissing an inline approval:

```
+-----------------------------------------------+
|  [x] Dismissed: Create 3 issues                |
|  [Undo] [Tell AI why]                          |
+-----------------------------------------------+
```

"Tell AI why" opens a small text input that sends a rejection reason back to the agent, which can then adjust its approach.

---

## 5. Trust & Confidence Indicators

### 5.1 Waiting Indicator

When the chat is in `QUESTION_PENDING` or `APPROVAL_PENDING` state, the ChatInput area transforms:

```
+-----------------------------------------------+
|  [pulse dot] Waiting for your response...      |
|  Answer the question above to continue.        |
+-----------------------------------------------+
```

The input textarea is disabled (grayed out) with a clear message explaining why. This prevents confusion when users try to type during a pending state.

### 5.2 Severity Badges

Compact badges on approval cards indicating risk level:

```
[safe]      -- bg: primary/10, text: primary, border: primary/20
[caution]   -- bg: warning/10, text: warning-foreground, border: warning/20
[critical]  -- bg: destructive/10, text: destructive, border: destructive/20
```

Tailwind classes:

```
// Safe
className="bg-primary/10 text-primary border border-primary/20 text-[11px] px-1.5 py-0.5 rounded-md font-medium"

// Caution
className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 text-[11px] px-1.5 py-0.5 rounded-md font-medium"

// Critical
className="bg-destructive/10 text-destructive border border-destructive/20 text-[11px] px-1.5 py-0.5 rounded-md font-medium"
```

### 5.3 Approval History Summary

A collapsible section at the top of the chat, showing a running count:

```
+-----------------------------------------------+
|  Session: 5 approved, 1 dismissed, 0 pending   |
+-----------------------------------------------+
```

Clicking expands to a compact list of past decisions in this session:

```
+-----------------------------------------------+
|  [checkmark] Created 3 issues      2 min ago   |
|  [checkmark] Added label "urgent"  5 min ago   |
|  [x] Dismissed: Delete comment     8 min ago   |
|  [checkmark] Updated note title    12 min ago  |
|  [checkmark] Assigned to @sarah    15 min ago  |
+-----------------------------------------------+
```

### 5.4 Undo Toast

After approving a reversible action, a toast appears at the bottom of the ChatView:

```
+-----------------------------------------------+
|  [checkmark] 3 issues created.  [Undo] 8s      |
+-----------------------------------------------+
```

The toast auto-dismisses after 8 seconds. Clicking "Undo" reverses the action and shows a confirmation:

```
+-----------------------------------------------+
|  [undo icon] 3 issues removed. Action undone.  |
+-----------------------------------------------+
```

For non-reversible actions (destructive), no undo toast appears -- the modal confirmation serves as the safeguard.

### 5.5 Token Cost Indicator

A subtle indicator on approval cards showing estimated token cost:

```
  ~120 tokens
```

This appears only when the action involves AI processing (not for simple CRUD). Styled in `text-xs text-muted-foreground`.

---

## 6. Micro-interactions & Animation

All animations respect `prefers-reduced-motion`. When reduced motion is preferred, transitions are instant (opacity only, no transforms).

### 6.1 QuestionBlock Entrance

```
Animation: slide-in-from-bottom + fade-in
Duration: 200ms
Easing: cubic-bezier(0.25, 0.46, 0.45, 0.94)  // ease-out-quad
Trigger: When pendingQuestion is set on store

Tailwind: animate-in slide-in-from-bottom-3 duration-200
```

### 6.2 Option Selection

```
Animation: border-color transition + subtle scale pulse
Duration: 150ms
Easing: ease-out

Selected state:
  border: --primary/40 (from border/100)
  background: --primary-muted (from background)
  scale: 1.0 -> 1.01 -> 1.0 (50ms pulse)

Tailwind: transition-all duration-150
```

### 6.3 QuestionBlock Collapse (After Submit)

```
Animation: height collapse + content fade
Duration: 250ms
Easing: cubic-bezier(0.4, 0, 0.2, 1)  // ease-in-out

Sequence:
  1. Content fades out (opacity 1 -> 0, 100ms)
  2. Height collapses to summary height (150ms)
  3. Summary fades in (opacity 0 -> 1, 100ms)

Implementation: AnimatePresence + motion.div with layout animation
```

### 6.4 Approval Card Entrance

```
Animation: slide-in-from-left + fade-in
Duration: 200ms
Delay: 50ms (staggered if multiple cards)
Easing: ease-out

Left border grows from 0px to full height (200ms, 50ms delay after card appears)
```

### 6.5 Approval Success Feedback

After approving:

```
Sequence:
  1. Approve button shows checkmark icon (swap from text, 100ms)
  2. Card background briefly flashes primary/5 (150ms)
  3. Card collapses to summary line (200ms, after 500ms delay)
  4. Undo toast slides up from bottom (200ms)
```

No confetti. No celebration animation. The warmth comes from the smooth, confident transition -- not from decorative effects. This is a professional tool, not a game.

### 6.6 Dismissal Animation

```
Animation: slide-out-to-right + fade-out
Duration: 200ms
Easing: ease-in

Card slides right 20px while fading out.
Dismissed summary slides in from left to replace it.
```

### 6.7 "AI is processing" Transition

```
Three-dot pulse animation (same as existing ConversationMessage streaming indicator):
  Dot 1: scale 1 -> 1.2 -> 1 (800ms, repeat)
  Dot 2: same, 200ms delay
  Dot 3: same, 400ms delay
```

---

## 7. Component Specifications

### 7.1 QuestionBlock

**File**: `frontend/src/features/ai/ChatView/MessageList/QuestionBlock.tsx`

**Props Interface**:

```typescript
interface QuestionBlockProps {
  /** Unique ID for submitting the answer */
  questionId: string;
  /** Array of 1-4 questions from AskUserQuestion */
  questions: AgentQuestion[];
  /** Callback when user submits all answers */
  onSubmit: (questionId: string, answers: Record<string, string>) => void;
  /** Whether all questions have been answered */
  isResolved: boolean;
  /** Map of question text to selected answer */
  resolvedAnswers?: Record<string, string>;
  /** Additional CSS classes */
  className?: string;
}

interface AgentQuestion {
  question: string;
  header?: string;          // max 12 chars, shown as badge
  options: QuestionOption[];
  multiSelect: boolean;
}

interface QuestionOption {
  label: string;
  description?: string;
}
```

**States**:

| State | Visual | Interaction |
|-------|--------|-------------|
| Default (unanswered) | Full card with options | Selectable options, submit enabled when selection made |
| Stepping (question 2/3) | Single question with step indicator | Next/Back buttons |
| Submitting | Submit button shows spinner | All inputs disabled |
| Resolved | Collapsed summary line | Click to expand read-only view |

**Tailwind Classes**:

```
// Container
"rounded-[14px] border-[1.5px] border-ai/30 bg-[#F5F0EB] dark:bg-[#252220]"
"shadow-[0_2px_8px_rgba(0,0,0,0.06)]"

// Header
"flex items-center gap-2 px-4 pt-3 pb-2"

// Option button (unselected)
"flex w-full items-start gap-3 rounded-[10px] border border-border bg-background px-3 py-2.5"
"hover:border-ai/30 hover:bg-ai-muted transition-all duration-150"

// Option button (selected)
"border-ai/40 bg-ai-muted"

// Submit button
"rounded-[10px] bg-primary px-4 py-2 text-sm font-medium text-white"
"hover:bg-primary-hover disabled:bg-muted disabled:text-muted-foreground"

// Resolved state
"flex items-center gap-2 rounded-[10px] border border-primary/20 bg-primary-muted px-3 py-2"
```

**Keyboard Navigation**:

| Key | Action |
|-----|--------|
| Tab | Move focus between options |
| Space/Enter | Select/deselect focused option |
| Arrow Down/Up | Move between options within a question |
| Enter (when on Submit) | Submit answer |
| Escape | Dismiss question (with confirmation if selections exist) |

**ARIA**:

```html
<div role="region" aria-label="Agent question: {question.header || 'Input needed'}">
  <div role="radiogroup" aria-label="{question.question}">  <!-- or role="group" for multiSelect -->
    <button role="radio" aria-checked="true|false" aria-label="{option.label}: {option.description}">
    <!-- or role="checkbox" for multiSelect -->
  </div>
</div>
```

**Responsive (35% sidebar)**:

- Options stack vertically (always, no horizontal layout).
- Option descriptions truncate to 2 lines with `line-clamp-2`.
- Step indicator moves inline with header text (no separate row).
- Minimum touch target: 44px height per option.

---

### 7.2 InlineApprovalCard

**File**: `frontend/src/features/ai/ChatView/MessageList/InlineApprovalCard.tsx`

**Props Interface**:

```typescript
interface InlineApprovalCardProps {
  /** Approval request data */
  approval: ApprovalRequest;
  /** Risk level classification */
  severity: 'safe' | 'caution' | 'critical';
  /** Called when user approves */
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  /** Called when user rejects */
  onReject: (id: string, reason?: string) => Promise<void>;
  /** Additional CSS classes */
  className?: string;
}
```

**States**:

| State | Visual | Interaction |
|-------|--------|-------------|
| Default | Compact card, collapsed details | Approve/Dismiss/Edit buttons |
| Expanded | Details visible (payload preview) | Same buttons, scroll if tall |
| Editing | Payload fields editable | Approve with changes / Cancel |
| Approving | Approve button shows spinner | All buttons disabled |
| Approved | Collapsed to summary + undo toast | Click to expand read-only |
| Dismissed | Collapsed to "Dismissed" + undo link | Undo restores the card |

**Tailwind Classes**:

```
// Container
"mx-0 my-2 rounded-[14px] border bg-background"
"shadow-[0_1px_4px_rgba(0,0,0,0.04)]"

// Left border by severity
"border-l-2 border-l-primary"          // safe
"border-l-2 border-l-amber-500"        // caution
"border-l-3 border-l-destructive"      // critical

// Header
"flex items-center gap-2 px-3 pt-3 pb-1"

// Action buttons
"flex items-center gap-2 px-3 pb-3"

// Approve button
"rounded-[10px] bg-primary px-3 py-1.5 text-sm font-medium text-white"

// Dismiss button
"rounded-[10px] border border-border px-3 py-1.5 text-sm text-muted-foreground"
"hover:bg-muted"

// Edit button
"rounded-[10px] border border-ai/20 bg-ai-muted px-3 py-1.5 text-sm text-ai"
```

---

### 7.3 DestructiveApprovalModal

**File**: `frontend/src/features/ai/ChatView/ApprovalOverlay/DestructiveApprovalModal.tsx`

**Props Interface**:

```typescript
interface DestructiveApprovalModalProps {
  /** Approval request data */
  approval: ApprovalRequest;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Called when user approves after confirmation */
  onApprove: (id: string) => Promise<void>;
  /** Called when user rejects */
  onReject: (id: string, reason: string) => Promise<void>;
  /** Called when modal is dismissed (same as reject without reason) */
  onClose: () => void;
}
```

**States**:

| State | Visual | Interaction |
|-------|--------|-------------|
| Open | Full modal, confirm input empty | Confirm button disabled |
| Confirmed | Typed confirmation matches | Confirm button enabled (destructive variant) |
| Executing | Confirm button shows spinner | All inputs disabled |
| Rejected | Shows reject form | Submit rejection reason |

**Typed Confirmation Format**:

The confirmation phrase is generated from the action:
- `delete_issue` -> "delete issue"
- `delete_workspace` -> "delete workspace"
- `bulk_delete` -> "delete N items"
- `merge_pr` -> "merge PR"

---

### 7.4 BatchApprovalCard

**File**: `frontend/src/features/ai/ChatView/MessageList/BatchApprovalCard.tsx`

**Props Interface**:

```typescript
interface BatchApprovalCardProps {
  /** Array of related approval requests */
  approvals: ApprovalRequest[];
  /** Overall severity (highest of the batch) */
  severity: 'safe' | 'caution' | 'critical';
  /** Called when user approves selected items */
  onApproveSelected: (ids: string[], modifications?: Record<string, Record<string, unknown>>) => Promise<void>;
  /** Called when user rejects all */
  onRejectAll: (ids: string[], reason?: string) => Promise<void>;
  /** Additional CSS classes */
  className?: string;
}
```

---

### 7.5 WaitingIndicator

**File**: `frontend/src/features/ai/ChatView/ChatInput/WaitingIndicator.tsx`

Note: A `WorkingIndicator.tsx` already exists. `WaitingIndicator` is distinct -- it shows when the AI is waiting for the user (not when the AI is working).

**Props Interface**:

```typescript
interface WaitingIndicatorProps {
  /** What the AI is waiting for */
  waitingFor: 'question' | 'approval';
  /** Additional CSS classes */
  className?: string;
}
```

**Layout**:

```
+-----------------------------------------------+
|  [pulse] Waiting for your answer...            |
|  Respond to the question above to continue     |
+-----------------------------------------------+
```

**Tailwind Classes**:

```
"flex items-center gap-2 px-4 py-3 border-t bg-muted/30"
"text-sm text-muted-foreground"

// Pulse dot
"h-2 w-2 rounded-full bg-ai animate-pulse"
```

---

### 7.6 ApprovalHistorySummary

**File**: `frontend/src/features/ai/ChatView/ApprovalHistorySummary.tsx`

**Props Interface**:

```typescript
interface ApprovalHistorySummaryProps {
  /** Count of approved actions in session */
  approvedCount: number;
  /** Count of dismissed actions in session */
  dismissedCount: number;
  /** Count of pending actions */
  pendingCount: number;
  /** Past approval decisions for expanded view */
  history: ApprovalHistoryEntry[];
  /** Additional CSS classes */
  className?: string;
}

interface ApprovalHistoryEntry {
  id: string;
  actionDescription: string;
  decision: 'approved' | 'dismissed';
  timestamp: Date;
}
```

**Layout (Collapsed)**:

```
+-----------------------------------------------+
|  5 approved, 1 dismissed               [v]     |
+-----------------------------------------------+
```

**Layout (Expanded)**:

```
+-----------------------------------------------+
|  5 approved, 1 dismissed               [^]     |
|-  - - - - - - - - - - - - - - - - - - - - - - |
|  [check] Created 3 issues         2m ago       |
|  [check] Added label "urgent"     5m ago       |
|  [x] Dismissed: Delete comment    8m ago       |
+-----------------------------------------------+
```

---

### 7.7 SeverityBadge

**File**: `frontend/src/features/ai/ChatView/MessageList/SeverityBadge.tsx`

**Props Interface**:

```typescript
interface SeverityBadgeProps {
  severity: 'safe' | 'caution' | 'critical';
  className?: string;
}
```

**Rendering**:

```typescript
const config = {
  safe: {
    label: 'safe',
    className: 'bg-primary/10 text-primary border-primary/20',
  },
  caution: {
    label: 'caution',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20',
  },
  critical: {
    label: 'critical',
    className: 'bg-destructive/10 text-destructive border-destructive/20',
  },
};
```

---

### 7.8 UndoToast

Uses the existing `sonner` toast library with a custom render:

```typescript
toast.custom((t) => (
  <div className="flex items-center gap-3 rounded-[10px] border bg-background px-4 py-3 shadow-lg">
    <Check className="h-4 w-4 text-primary" />
    <span className="text-sm flex-1">{message}</span>
    <button
      onClick={() => { onUndo(); toast.dismiss(t); }}
      className="text-sm font-medium text-primary hover:underline"
    >
      Undo
    </button>
    <CountdownRing durationMs={8000} className="h-5 w-5" />
  </div>
), { duration: 8000 });
```

**CountdownRing**: A small SVG circle that animates its stroke-dashoffset from full to zero over the undo window.

---

## 8. Complete Flow Mockups

### Flow 1: User sends message -> AI asks clarifying question -> User answers -> AI proceeds

```
STEP 1: User sends message
+-----------------------------------------------+
| ChatView (35% sidebar)                         |
|-----------------------------------------------|
| [User avatar]                                  |
|   "Extract issues from this note"              |
|                                                |
| [AI avatar]                                    |
|   "I found several actionable items in your    |
|    note. Before I extract them, I have a       |
|    question:"                                  |
|                                                |
| +-------------------------------------------+ |
| | [?] Agent needs your input                 | |
| |- - - - - - - - - - - - - - - - - - - - - -| |
| | How should I categorize the items?         | |
| |                                            | |
| | (*) By type (bug, feature, task)           | |
| | ( ) By priority (high, medium, low)        | |
| | ( ) Both type and priority                 | |
| |                                            | |
| | [Or type a different approach...]          | |
| |                                            | |
| |                          [Submit answer]   | |
| +-------------------------------------------+ |
|                                                |
| +-------------------------------------------+ |
| | [pulse] Waiting for your answer...         | |
| | Respond to the question above to continue  | |
| +-------------------------------------------+ |
+-----------------------------------------------+

STEP 2: User selects "By type" and submits
+-----------------------------------------------+
| ...previous messages...                        |
|                                                |
| +-------------------------------------------+ |
| | [check] Answered: By type (bug, feature,  | |
| |         task)                              | |
| +-------------------------------------------+ |
|                                                |
| [AI avatar]                                    |
|   [streaming] "I'll categorize the items by    |
|    type. Here's what I found..."               |
|   [dot dot dot]                                |
|                                                |
| +-------------------------------------------+ |
| | Type a message...                   [Send] | |
| +-------------------------------------------+ |
+-----------------------------------------------+

STEP 3: AI finishes and shows approval for extracted issues
+-----------------------------------------------+
| ...previous messages...                        |
|                                                |
| [AI avatar]                                    |
|   "I found 4 actionable items. Here they are:" |
|                                                |
| +-------------------------------------------+ |
| | [sparkle] Create 4 issues          [safe]  | |
| |- - - - - - - - - - - - - - - - - - - - - -| |
| | [x] Bug: "Login timeout on slow networks" | |
| | [x] Feature: "Add SSO support"            | |
| | [x] Task: "Update auth documentation"     | |
| | [x] Task: "Remove deprecated JWT code"    | |
| |                                            | |
| | [Approve all]  [Dismiss]  [Edit]          | |
| +-------------------------------------------+ |
|                                                |
| +-------------------------------------------+ |
| | Type a message...                   [Send] | |
| +-------------------------------------------+ |
+-----------------------------------------------+
```

### Flow 2: AI requests tool approval -> User reviews -> Approves -> AI continues

```
STEP 1: AI streaming pauses for approval
+-----------------------------------------------+
| [User avatar]                                  |
|   "Update the note title to match the project" |
|                                                |
| [AI avatar]                                    |
|   "I'll update the note title to 'Backend API  |
|    Refactor Plan'. This requires your approval:"|
|                                                |
| +-------------------------------------------+ |
| | [sparkle] Update note title      [safe]    | |
| |- - - - - - - - - - - - - - - - - - - - - -| |
| | "Meeting Notes" -> "Backend API Refactor   | |
| |  Plan"                                     | |
| |                                            | |
| | [Approve]  [Dismiss]                       | |
| +-------------------------------------------+ |
|                                                |
| +-------------------------------------------+ |
| | [pulse] Waiting for your approval...       | |
| +-------------------------------------------+ |
+-----------------------------------------------+

STEP 2: User clicks Approve
+-----------------------------------------------+
| ...                                            |
| +-------------------------------------------+ |
| | [check] Approved: Updated note title       | |
| +-------------------------------------------+ |
|                                                |
| [toast at bottom of ChatView]                  |
| +-------------------------------------------+ |
| | [check] Note title updated. [Undo] 8s     | |
| +-------------------------------------------+ |
|                                                |
| [AI avatar]                                    |
|   [streaming] "Done! The note title has been   |
|    updated. Let me also..."                    |
|                                                |
| +-------------------------------------------+ |
| | Type a message...                   [Send] | |
| +-------------------------------------------+ |
+-----------------------------------------------+
```

### Flow 3: AI requests destructive action -> Enhanced warning -> User rejects with reason

```
STEP 1: Destructive action triggers modal
+-----------------------------------------------+
| [User avatar]                                  |
|   "Clean up the old issues from last sprint"   |
|                                                |
| [AI avatar]                                    |
|   "I identified 5 issues from Sprint 12 that   |
|    appear to be stale. I'd like to delete them."|
|                                                |
+===============================================+
||                                              ||
||  [!] Destructive Action                      ||
||                                              ||
||  Delete 5 issues from "Sprint 12"            ||
||                                              ||
||  +------------------------------------------+||
||  | This cannot be undone. All comments,     |||
||  | links, and activity will be removed.     |||
||  +------------------------------------------+||
||                                              ||
||  - PS-201: Legacy API endpoint              ||
||  - PS-203: Deprecated webhook handler       ||
||  - PS-204: Old migration script             ||
||  - PS-207: Unused test fixture              ||
||  - PS-210: Stale config entry               ||
||                                              ||
||  Type "delete 5 issues" to confirm:         ||
||  +------------------------------------------+||
||  | [                                       ]|||
||  +------------------------------------------+||
||                                              ||
||           [Cancel]  [Delete permanently]     ||
||                                              ||
||  Expires in 23:58:30                        ||
||                                              ||
+===============================================+

STEP 2: User clicks Cancel, then "Tell AI why"
+-----------------------------------------------+
| ...                                            |
| +-------------------------------------------+ |
| | [x] Rejected: Delete 5 issues             | |
| | [Tell AI why...]                           | |
| +-------------------------------------------+ |
|                                                |
| Expanded:                                      |
| +-------------------------------------------+ |
| | [x] Rejected: Delete 5 issues             | |
| | +---------------------------------------+ | |
| | | Don't delete them, move to Cancelled   | | |
| | | state instead so we keep the history.  | | |
| | +---------------------------------------+ | |
| |                              [Send reason] | |
| +-------------------------------------------+ |
|                                                |
| [AI avatar]                                    |
|   "Understood. I'll move the 5 issues to       |
|    Cancelled state instead of deleting them."  |
+-----------------------------------------------+
```

### Flow 4: Multiple pending approvals queue

```
STEP 1: AI generates batch of actions
+-----------------------------------------------+
| [AI avatar]                                    |
|   "Based on the PR review, I have several      |
|    suggestions:"                               |
|                                                |
| +-------------------------------------------+ |
| | [sparkle] 4 actions pending         [ai]   | |
| |- - - - - - - - - - - - - - - - - - - - - -| |
| | [x] Post review comment on PR #42  [safe]  | |
| | [x] Create issue "Fix N+1 query"   [safe]  | |
| | [x] Add label "needs-review"       [safe]  | |
| | [x] Request changes on PR #42    [caution] | |
| |                                            | |
| | [Approve all 4]  [Review individually]     | |
| +-------------------------------------------+ |
|                                                |
| +-------------------------------------------+ |
| | [pulse] Waiting for your approval...       | |
| +-------------------------------------------+ |
+-----------------------------------------------+

STEP 2: User clicks "Review individually"
+-----------------------------------------------+
| +-------------------------------------------+ |
| | [sparkle] Post review comment       [safe] | |
| |- - - - - - - - - - - - - - - - - - - - - -| |
| | Comment on line 42: "This query runs       | |
| | inside a loop, causing N+1..."             | |
| |                                            | |
| | [Approve]  [Skip]                    1/4   | |
| +-------------------------------------------+ |
|                                                |
| +-------------------------------------------+ |
| | [pulse] 3 more actions after this one      | |
| +-------------------------------------------+ |
+-----------------------------------------------+

STEP 3: After approving all
+-----------------------------------------------+
| +-------------------------------------------+ |
| | [check] 3 approved, 1 skipped             | |
| +-------------------------------------------+ |
|                                                |
| [AI avatar]                                    |
|   "Done! I've posted the review comment,       |
|    created the issue, and added the label.     |
|    The 'request changes' was skipped."         |
+-----------------------------------------------+
```

---

## 9. Accessibility Requirements

### 9.1 Focus Management

| Event | Focus Behavior |
|-------|---------------|
| QuestionBlock appears | Focus moves to first option |
| Approval card appears | Focus moves to "Approve" button |
| Modal opens | Focus trapped inside modal |
| Modal closes | Focus returns to the element that triggered it (or ChatInput) |
| Question resolved | Focus moves to ChatInput |
| Batch: next item | Focus moves to next card's "Approve" button |

### 9.2 ARIA Roles and Properties

```html
<!-- QuestionBlock -->
<div role="region" aria-label="Agent question" aria-live="polite">
  <div role="radiogroup" aria-label="{question text}">
    <button role="radio" aria-checked="true|false">
  </div>
  <!-- or for multi-select -->
  <div role="group" aria-label="{question text}">
    <button role="checkbox" aria-checked="true|false|mixed">
  </div>
</div>

<!-- InlineApprovalCard -->
<div role="region" aria-label="Approval: {action description}">
  <button aria-label="Approve: {action}">Approve</button>
  <button aria-label="Dismiss: {action}">Dismiss</button>
</div>

<!-- Waiting indicator -->
<div role="status" aria-live="polite">
  Waiting for your answer. Respond to the question above to continue.
</div>

<!-- Severity badge -->
<span role="status" aria-label="Risk level: safe">safe</span>

<!-- Undo toast -->
<div role="alert" aria-live="assertive">
  3 issues created. Press Undo to reverse this action. 8 seconds remaining.
</div>

<!-- Destructive modal -->
<div role="alertdialog" aria-modal="true" aria-labelledby="destructive-title" aria-describedby="destructive-desc">
```

### 9.3 Keyboard Shortcuts

| Context | Key | Action |
|---------|-----|--------|
| QuestionBlock | Tab | Cycle through options |
| QuestionBlock | Space/Enter | Select option |
| QuestionBlock | Arrow Up/Down | Move between options |
| QuestionBlock step | Enter | Advance to next question |
| QuestionBlock step | Shift+Enter | Go back to previous question |
| InlineApprovalCard | Enter | Approve (when Approve is focused) |
| InlineApprovalCard | Escape | Dismiss |
| BatchApproval | Tab | Cycle through items |
| DestructiveModal | Escape | Cancel (close modal) |
| UndoToast | Ctrl+Z | Trigger undo |

### 9.4 Screen Reader Announcements

| Event | Announcement |
|-------|-------------|
| Question appears | "Agent needs your input. {question text}. {N} options available." |
| Option selected | "{option label} selected." |
| Answer submitted | "Answer submitted: {answer summary}." |
| Approval appears | "Approval needed. {action description}. Risk level: {severity}." |
| Action approved | "{action} approved." |
| Action dismissed | "{action} dismissed. Undo available for 8 seconds." |
| Undo triggered | "{action} undone." |
| Destructive modal | "Warning: destructive action. {description}. Type confirmation to proceed." |

### 9.5 Color Contrast

All text-on-background combinations meet WCAG AA 4.5:1 minimum:

| Element | Foreground | Background | Ratio |
|---------|-----------|-----------|-------|
| Question text | #171717 | #F5F0EB | 11.2:1 |
| Option label | #171717 | #FDFCFA | 14.7:1 |
| Muted description | #737373 | #FDFCFA | 4.6:1 |
| Safe badge text | #29A386 on primary/10 | ~#E8F5F1 | 4.5:1 |
| Caution badge | #B45309 on amber/10 | ~#FEF3C7 | 4.8:1 |
| Critical badge | #D9534F on destructive/10 | ~#FEE2E2 | 4.5:1 |

---

## 10. Implementation Priority

### Phase 1: Core Question UX (Sprint 1, ~5 days)

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | QuestionBlock (single question) | 2d | Replaces generic QuestionCard with polished UX |
| P0 | WaitingIndicator | 0.5d | Prevents user confusion during pending states |
| P1 | QuestionBlock (multi-question stepping) | 1.5d | Supports 2-4 question flows |
| P1 | QuestionBlock collapse animation | 0.5d | Smooth answered-state transition |
| P1 | Tests for QuestionBlock | 0.5d | Coverage for all states |

**Deliverable**: Users can answer AI questions inline with a delightful, accessible experience.

### Phase 2: Approval Enhancement (Sprint 2, ~5 days)

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | InlineApprovalCard (replaces SuggestionCard) | 2d | Consistent AI palette, severity badges |
| P0 | SeverityBadge | 0.5d | Risk communication |
| P1 | "Edit & Approve" flow | 1.5d | Users can modify before approving |
| P1 | Approval collapse animation | 0.5d | Smooth post-approval transition |
| P1 | Tests for InlineApprovalCard | 0.5d | Coverage for all states |

**Deliverable**: Non-destructive approvals are inline, severity-coded, and editable.

### Phase 3: Destructive & Batch (Sprint 3, ~4 days)

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | DestructiveApprovalModal (typed confirmation) | 1.5d | Safer destructive operations |
| P1 | BatchApprovalCard | 1.5d | Handle multiple pending approvals |
| P1 | Tests for both | 1d | Coverage for destructive flows |

**Deliverable**: Destructive actions require typed confirmation. Batch approvals are reviewable.

### Phase 4: Trust & Polish (Sprint 4, ~3 days)

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P1 | UndoToast with CountdownRing | 1d | Reversibility confidence |
| P2 | ApprovalHistorySummary | 1d | Session auditability |
| P2 | Rejection reason flow ("Tell AI why") | 0.5d | Feedback loop for AI |
| P2 | Token cost indicator on approvals | 0.5d | Transparency |

**Deliverable**: Full trust infrastructure. Users feel confident approving actions.

### Total Estimated Effort: ~17 days (4 sprints)

### File Impact Summary

| File | Action |
|------|--------|
| `ChatView/MessageList/QuestionCard.tsx` | Replace with `QuestionBlock.tsx` |
| `ChatView/MessageList/SuggestionCard.tsx` | Replace with `InlineApprovalCard.tsx` |
| `ChatView/MessageList/SeverityBadge.tsx` | New file |
| `ChatView/MessageList/BatchApprovalCard.tsx` | New file |
| `ChatView/ApprovalOverlay/ApprovalDialog.tsx` | Enhance to `DestructiveApprovalModal.tsx` |
| `ChatView/ApprovalOverlay/ApprovalOverlay.tsx` | Update to use new modal |
| `ChatView/ChatInput/WaitingIndicator.tsx` | New file |
| `ChatView/ApprovalHistorySummary.tsx` | New file |
| `ChatView/ChatView.tsx` | Update to integrate new components |
| `stores/ai/PilotSpaceStore.ts` | Add approval history tracking, batch approval actions |
| `stores/ai/types/events.ts` | Extend with batch approval types |

---

## Appendix A: Design Token Additions

New CSS custom properties needed:

```css
/* Approval severity */
--color-severity-safe: var(--primary);
--color-severity-caution: #D4A843;
--color-severity-critical: var(--destructive);

/* Question block */
--color-question-bg: #F5F0EB;
--color-question-bg-dark: #252220;
--color-question-border: var(--ai-border);

/* Undo toast */
--undo-duration: 8000ms;
```

## Appendix B: State Machine Update

```
IDLE
  -> STREAMING (user sends message)
  -> QUESTION_PENDING (AI asks question via AskUserQuestion)
  -> APPROVAL_PENDING (AI requests tool approval)

STREAMING
  -> IDLE (message_stop received)
  -> QUESTION_PENDING (AskUserQuestion during stream)
  -> APPROVAL_PENDING (approval_request during stream)

QUESTION_PENDING
  -> STREAMING (user submits answer, AI resumes)
  -> IDLE (user dismisses question)

APPROVAL_PENDING
  -> STREAMING (user approves, AI resumes)
  -> IDLE (user rejects)
  -> BATCH_APPROVAL_PENDING (multiple approvals queued)

BATCH_APPROVAL_PENDING
  -> STREAMING (all items resolved)
  -> APPROVAL_PENDING (reviewing individually)
```

## Appendix C: Store Extensions

```typescript
// PilotSpaceStore additions
class PilotSpaceStore {
  // Existing...

  // New: Approval history for session
  @observable approvalHistory: ApprovalHistoryEntry[] = [];

  // New: Batch approval state
  @observable batchApprovals: ApprovalRequest[] = [];

  @action
  approveMultiple(ids: string[], modifications?: Record<string, Record<string, unknown>>): Promise<void>;

  @action
  rejectMultiple(ids: string[], reason?: string): Promise<void>;

  @computed
  get approvalCounts(): { approved: number; dismissed: number; pending: number };
}
```
