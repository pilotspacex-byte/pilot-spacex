# UI Design Specification: Feature 015 — AI Workforce Chat Engine (M7)

**Version**: 1.0.0
**Created**: 2026-02-19
**Status**: Draft
**Author**: Designer Agent
**Extends**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 (Section 8 — ChatView System)
**Target**: `frontend/src/features/ai/ChatView/` upgrade

---

## Overview

Feature 015 upgrades the existing ChatView right panel (65/35 split) with new message card types for WorkIntent lifecycle, skill execution progress, approval interactions, and queue management. No layout changes — only new renderable message types within the existing `MessageList`.

**Design Principle**: Chat is the command center. Every AI operation is visible, controllable, and reversible from chat.

---

## Component Hierarchy

```
ChatView (existing — no changes)
├── ChatHeader (existing)
├── MessageList (existing container)
│   ├── UserMessage (existing)
│   ├── AssistantMessage (existing)
│   ├── IntentCard (NEW — M7)
│   ├── SkillProgressCard (NEW — M7)
│   ├── ApprovalCard (NEW — M7, extends InlineApprovalCard)
│   ├── ConversationBlock (NEW — M7)
│   └── QueueDepthIndicator (NEW — M7, sticky)
├── TaskPanel (existing — enhanced)
├── StreamingBanner (existing)
├── ApprovalOverlay (existing — for destructive only)
├── ConfirmAllButton (NEW — M7, above ChatInput)
└── ChatInput (existing)
```

---

## 1. IntentCard

Displays a detected WorkIntent for user review. Appears inline in MessageList after intent detection.

### Layout

```
+----------------------------------------------------------+
| [lightbulb icon]  Intent Detected                        |
|----------------------------------------------------------|
|                                                          |
|  WHAT                                                    |
|  Create a feature specification for user authentication  |
|                                                          |
|  WHY                                                     |
|  Current auth flow has too many steps and users drop off |
|                                                          |
|  CONSTRAINTS                                             |
|  - Must support OAuth (Google, GitHub)                   |
|  - Session timeout ≥ 24h                                 |
|                                                          |
|  [████████████░░░░] 82% confidence                       |
|                                                          |
|  [Confirm]  [Edit]  [Dismiss]                            |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | `rounded-lg` (14px), `border` (`--ai-border`), `bg` (`--ai-muted`), `p-4` |
| Header | `text-sm` (13px), `font-medium`, `--ai` color, lightbulb icon (16px Lucide `Lightbulb`) |
| Section Labels | `text-xs` (11px), `uppercase`, `tracking-wider`, `--foreground-muted`, `mb-1` |
| Section Text | `text-sm` (13px), `--foreground`, `mb-3` |
| Constraints | Bulleted list, `text-sm`, `--foreground-muted` |
| Max Height | 320px with overflow scroll (for long intents) |
| Spacing | 12px between sections, 16px internal padding |

### Confidence Bar

| Range | Color | Label |
|-------|-------|-------|
| >= 80% | `#29A386` (primary/teal) | "High confidence" |
| 70–79% | `#D9853F` (amber) | "Medium confidence" |
| < 70% | `#D9534F` (warm red) | "Low confidence — clarification needed" |

| Property | Value |
|----------|-------|
| Bar Height | 6px, `rounded-full` |
| Bar Background | `--border` |
| Bar Fill | Animated from 0 to value, 600ms ease-out |
| Percentage Label | `text-xs`, `tabular-nums`, right-aligned |
| Clarification | When <70%, show italic question text below bar in `--ai` color |

### Action Buttons

| Button | Variant | Behavior |
|--------|---------|----------|
| Confirm | `default` (primary teal), `sm` | Sets intent status to "confirmed", card collapses to summary |
| Edit | `outline`, `sm` | Opens inline edit form replacing WHAT/WHY/CONSTRAINTS |
| Dismiss | `ghost`, `sm` | Fades card out (200ms), intent status "rejected" |

### State Variations

| State | Visual |
|-------|--------|
| `detected` | Full card as above |
| `confirmed` | Collapsed to single line: "[check] Intent confirmed: {what}" in `--primary` with undo link |
| `executing` | Replaced by SkillProgressCard |
| `rejected` | Collapsed: "[x] Dismissed: {what}" in `--foreground-muted`, strikethrough |
| `editing` | WHAT/WHY become editable textareas, constraints become editable list, [Save] [Cancel] buttons |

### Accessibility

- `role="article"`, `aria-label="Work intent: {what}"`
- Buttons: `aria-label` on each ("Confirm intent", "Edit intent", "Dismiss intent")
- Confidence bar: `role="progressbar"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`
- Focus order: Confirm > Edit > Dismiss (Tab navigation)
- Keyboard: Enter on focused button activates, Escape from edit mode cancels

---

## 2. SkillProgressCard

Displays real-time execution progress of a skill processing a confirmed intent.

### Layout

```
+----------------------------------------------------------+
| [cpu icon]  create-spec                    Running...     |
|----------------------------------------------------------|
|                                                          |
|  Intent: Create a feature specification for user auth    |
|                                                          |
|  [████████░░░░░░░░] Step 2/4                             |
|  Reading workspace constitution...                       |
|                                                          |
|  Artifacts:                                              |
|  [doc] Auth Spec Note  [link icon]                       |
|                                                          |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | `rounded-lg` (14px), `border` (`--border`), `bg-background`, `p-4` |
| Header Row | Flex between: skill name (`text-sm`, `font-medium`, `font-mono`) + status badge |
| Skill Icon | 16px Lucide `Cpu` in `--ai` color |
| Intent Summary | `text-sm`, `--foreground-muted`, single line, truncated with ellipsis |
| Progress Bar | 4px height, `rounded-full`, animated fill, `--primary` color |
| Step Label | `text-xs`, `--foreground-muted`, below progress bar |
| Artifact Links | `text-sm`, icon + name, `--primary` color, hover underline |

### Status Badge

| Status | Badge |
|--------|-------|
| `queued` | `secondary` badge, "Queued" |
| `running` | `ai` badge with pulse animation, "Running..." |
| `completed` | `default` badge (teal), "Complete" with check icon |
| `failed` | `destructive` badge, "Failed" with x icon |

### Animated Progress

- Progress bar fills smoothly (CSS transition 300ms)
- Step counter uses `tabular-nums` for stable width
- Spinner animation on "Running..." badge: 1s infinite rotation on icon
- When complete, progress bar briefly flashes `--primary` then settles

### Completion State

When skill completes, card transforms:

```
+----------------------------------------------------------+
| [check-circle]  create-spec              Complete         |
|----------------------------------------------------------|
|  Created "Auth Spec Note" (42 blocks)                    |
|  [View in Note]  [Revise]  [Dismiss]                     |
+----------------------------------------------------------+
```

- Collapsed to 2 rows: summary + actions
- [View in Note]: `outline` button, navigates to artifact
- [Revise]: `ai` variant button, starts new intent cycle
- [Dismiss]: `ghost` button, hides card

### Error State

```
+----------------------------------------------------------+
| [alert-triangle]  create-spec              Failed         |
|----------------------------------------------------------|
|  Token budget exhausted at step 3/4                      |
|  Partial output saved (28 blocks)                        |
|  [View Partial]  [Retry]                                 |
+----------------------------------------------------------+
```

### Accessibility

- `role="status"`, `aria-live="polite"` for progress updates
- Progress bar: `role="progressbar"`, `aria-valuenow`, `aria-valuetext="Step 2 of 4"`
- Status transitions announced via `aria-live` region

---

## 3. ApprovalCard

Inline approval card for destructive skill output (deploy, generate-migration, hotfix). Extends existing `InlineApprovalCard` pattern.

### Layout

```
+----------------------------------------------------------+
| [shield-alert]  Approval Required           [04:32]      |
|----------------------------------------------------------|
|                                                          |
|  Action: Generate database migration                     |
|  Skill: generate-migration                               |
|                                                          |
|  Preview:                                                |
|  +------------------------------------------------------+|
|  | -- migration: 038_add_memory_entries                  ||
|  | CREATE TABLE memory_entries (                         ||
|  |   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),      ||
|  |   content TEXT NOT NULL,                              ||
|  |   ...                                                 ||
|  +------------------------------------------------------+|
|                                                          |
|  [Reject ▾]                          [Approve]           |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | `rounded-xl` (18px), `border-2` (`#D9853F` amber), `bg-background`, `p-4`, `shadow` |
| Header | `text-sm`, `font-semibold`, `--foreground`, shield-alert icon (18px, `#D9853F`) |
| Countdown | `CountdownTimer` component (existing), top-right, `tabular-nums` |
| Action Label | `text-sm`, `font-medium` |
| Skill Name | `text-xs`, `font-mono`, `--foreground-muted` |
| Preview Box | `rounded` (10px), `bg-background-subtle`, `border`, `p-3`, `font-mono`, `text-xs`, max-height 200px scroll |
| Button Row | Flex between, `mt-4` |

### Countdown Timer

| Time Remaining | Color | Behavior |
|----------------|-------|----------|
| > 5 minutes | `--foreground-muted` | Static display |
| 1–5 minutes | `#D9853F` (amber) | Subtle pulse every 30s |
| < 1 minute | `#D9534F` (warm red) | Continuous pulse animation |
| Expired | `#D9534F` | "Expired" text, buttons disabled |

### Action Buttons

| Button | Variant | Size | Behavior |
|--------|---------|------|----------|
| Approve | `default` (primary), `sm` | Calls `store.approveAction(id)`, card collapses to "[check] Approved" |
| Reject | `outline`, `sm`, with dropdown caret | Opens reject reason textarea inline |

### Reject Flow

When "Reject" dropdown clicked:
```
+----------------------------------------------------------+
|  Reason for rejection:                                   |
|  +------------------------------------------------------+|
|  | [textarea, 3 rows]                                   ||
|  +------------------------------------------------------+|
|  [Cancel]                              [Reject]          |
+----------------------------------------------------------+
```

### Accessibility

- `role="alertdialog"`, `aria-label="Approval required: {action}"`
- Countdown: `aria-live="assertive"` when < 1 minute
- Focus trapped within card when active (Tab cycles Approve/Reject)
- Reject reason textarea: `aria-label="Reason for rejection"`

---

## 4. ConversationBlock

Threaded Q&A block for AI clarification questions (FR-066 to FR-068).

### Layout

```
+----------------------------------------------------------+
| [message-circle]  AI Question                            |
|----------------------------------------------------------|
|                                                          |
|  Should the OAuth integration support PKCE flow for      |
|  mobile clients, or is browser-only sufficient?          |
|                                                          |
|  +------------------------------------------------------+|
|  | Your answer...                              [Reply]  ||
|  +------------------------------------------------------+|
|                                                          |
|  Thread (2 replies):                                     |
|  ┌ You: Browser-only for MVP, PKCE in phase 2          |
|  └ AI: Noted. I'll add a constraint for browser-only    |
|        and flag PKCE as a future requirement.            |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | `rounded-lg` (14px), `border` (`--ai-border`), `bg-background`, `p-4` |
| Header | `text-sm`, `font-medium`, `--ai` color, `MessageCircle` icon (16px) |
| Question Text | `text-sm`, `--foreground`, `mt-2`, `mb-3` |
| Reply Input | Standard input style (38px height, `rounded`, `border`), inline send button |
| Thread | Indented 16px left, vertical line (`--border`, 2px), `text-sm` |
| Thread Entry | `text-xs` role label ("You" / "AI") in bold, text in normal weight |
| Thread Spacing | 8px between entries |

### States

| State | Visual |
|-------|--------|
| Pending (no reply) | Input visible, question highlighted with left border (`--ai`, 3px) |
| Answered | Input hidden, thread visible, card border returns to `--ai-border` |
| Processing | After reply, "AI is thinking..." with inline spinner (< 5s per FR-068) |

### Accessibility

- `role="article"`, `aria-label="AI clarification question"`
- Reply input: `aria-label="Reply to AI question"`
- Thread: `role="list"`, entries `role="listitem"`
- Focus: Tab to reply input, Enter to send

---

## 5. ConfirmAll Button

Floating action above ChatInput for batch-confirming intents (FR-019, FR-113).

### Layout

```
+----------------------------------------------------------+
| [check-check]  Confirm All (7)                           |
+----------------------------------------------------------+
| [Context: Auth Note]                                     |
| Type a message...                               [Send]   |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Container | `mx-4`, `mb-2`, above ChatInput, full width |
| Button | `ai` variant, `sm` size, full width |
| Icon | Lucide `CheckCheck` (16px) |
| Count Badge | Inline count in parentheses, `tabular-nums` |
| Visibility | Only shown when >= 2 pending intents with confidence >= 70% |

### Behavior

1. Click triggers `confirmAll(workspace_id, min_confidence=0.7, max_count=10)`.
2. Button shows spinner during confirmation.
3. On success, displays result toast: "10 confirmed, 5 remaining".
4. If >10 pending, shows queue depth: "(7 of 12 eligible — top 10 will be confirmed)".

### Post-Confirm Display

After confirmation, a summary card replaces the button:

```
+----------------------------------------------------------+
| [check-check]  Batch Confirmed                           |
|  10 intents confirmed, 5 remaining in queue              |
|  [View Queue]                                            |
+----------------------------------------------------------+
```

### Accessibility

- `aria-label="Confirm all {count} eligible intents"`
- Result: `aria-live="polite"` announcement

---

## 6. Queue Depth Indicator

Sticky bar showing running/queued skill execution state (FR-109).

### Layout

```
+----------------------------------------------------------+
| [activity]  2 running  |  3 queued  |  max 5             |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Position | Sticky top of MessageList, below ChatHeader |
| Container | `px-4`, `py-2`, `bg-background-subtle`, `border-b`, `text-xs` |
| Running Count | `--primary` color dot (6px, pulse), `font-medium` |
| Queued Count | `--foreground-muted` dot (6px), `font-medium` |
| Max Label | `--foreground-muted`, `text-xs` |
| Separator | Vertical line (`--border`, 1px, 16px height) |
| Visibility | Only shown when at least 1 skill is running or queued |
| Icon | Lucide `Activity` (14px, `--foreground-muted`) |

### States

| State | Display |
|-------|---------|
| Idle (0 running, 0 queued) | Hidden |
| Active (1+ running) | Green dot pulse, counts shown |
| Queue Full (5 running) | Amber warning: "Queue full — new skills will wait" |
| Queued skill starts | Smooth count transition (number slides) |

### Accessibility

- `role="status"`, `aria-live="polite"`
- `aria-label="Skill execution queue: {running} running, {queued} queued"`

---

## Responsive Behavior

All new components inherit the existing ChatView responsive rules:

| Breakpoint | Behavior |
|------------|----------|
| Ultra-wide (>1920px) | Full card widths, comfortable spacing |
| Desktop (1280–1920px) | Standard layout within 35% ChatView panel |
| Tablet (768–1279px) | Cards adapt to overlay sidebar width (min 320px) |
| Mobile (<768px) | Full-width cards in modal overlay, stacked vertically |

### Card Width Adaptation

- IntentCard, SkillProgressCard, ApprovalCard: `max-w-full`, horizontal padding adjusts
- ConversationBlock thread: Indentation reduced to 8px on mobile
- ConfirmAll button: Full width at all breakpoints
- Queue indicator: Full width, text wraps if needed

---

## Animation & Transitions

| Animation | Duration | Easing | Trigger |
|-----------|----------|--------|---------|
| IntentCard appear | 300ms | ease-out | New intent detected |
| IntentCard collapse (confirm/dismiss) | 200ms | ease-in | User action |
| Confidence bar fill | 600ms | ease-out | Card mount |
| SkillProgressCard progress | 300ms | linear | Progress update |
| SkillProgressCard status pulse | 1000ms | ease-in-out, infinite | Running state |
| ApprovalCard border pulse | 2000ms | ease-in-out, infinite | < 1 min remaining |
| ConversationBlock thread expand | 200ms | ease-out | New thread entry |
| Queue indicator count change | 150ms | ease-out | Count update |

### Reduced Motion

All animations respect `prefers-reduced-motion: reduce`:
- Pulse animations replaced with static indicators
- Slide/fade transitions reduced to instant opacity changes
- Progress bar updates instantly (no fill animation)

---

## Dark Mode

All components use CSS custom properties from the design system. Dark mode adjustments:

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| IntentCard bg | `--ai-muted` (#6B8FAD15) | `--ai-muted` (auto-adjusted) |
| Confidence bar bg | `--border` | `--border` (darker) |
| ApprovalCard border | `#D9853F` | `#D9853F` (same — high contrast needed) |
| Code preview bg | `--background-subtle` | `--background-subtle` |
| Queue indicator bg | `--background-subtle` | `--background-subtle` |

No hardcoded colors — all values from CSS custom properties.

---

## Interaction Patterns

### Intent Lifecycle in Chat

1. User types message in ChatInput.
2. AI responds with text + 1-N IntentCards (inline in MessageList).
3. User reviews each IntentCard: Confirm, Edit, or Dismiss.
4. Confirmed intents spawn SkillProgressCards.
5. Destructive skills spawn ApprovalCards.
6. Completed skills show artifact links.

### ConfirmAll Flow

1. Multiple IntentCards accumulate (>= 2 eligible).
2. ConfirmAll button appears above ChatInput.
3. User clicks — top 10 by confidence confirmed.
4. Summary card shows results.
5. Confirmed intents begin execution (SkillProgressCards appear).

### Approval Flow (Destructive)

1. Skill completes with destructive output.
2. ApprovalCard appears inline with preview + countdown.
3. ChatInput disabled while approval pending (existing behavior).
4. Approve: output persisted, card collapses.
5. Reject: output discarded, reason stored, card collapses.

---

## Implementation Notes

### File Organization

```
ChatView/MessageList/
├── IntentCard.tsx              (NEW)
├── IntentCard.test.tsx         (NEW)
├── SkillProgressCard.tsx       (NEW)
├── SkillProgressCard.test.tsx  (NEW)
├── ApprovalCard.tsx            (EXTEND InlineApprovalCard)
├── ConversationBlock.tsx       (NEW)
├── ConversationBlock.test.tsx  (NEW)
ChatView/
├── ConfirmAllButton.tsx        (NEW)
├── QueueDepthIndicator.tsx     (NEW)
```

### Store Integration

All new components consume `PilotSpaceStore` via `observer()` wrapper:

- IntentCard: reads from `store.pendingIntents`, actions call `store.confirmIntent()`, `store.editIntent()`, `store.dismissIntent()`
- SkillProgressCard: reads from `store.tasks` (Map), filtered by skill execution
- ApprovalCard: reads from `store.pendingApprovals`
- ConfirmAllButton: reads `store.eligibleIntentCount`, calls `store.confirmAllIntents()`
- QueueDepthIndicator: reads `store.runningSkillCount`, `store.queuedSkillCount`

### SSE Event Mapping

| SSE Event | Component Update |
|-----------|-----------------|
| `intent_detected` (new) | Add IntentCard to MessageList |
| `intent_confirmed` (new) | Collapse IntentCard to summary |
| `task_progress` (existing) | Update SkillProgressCard |
| `approval_request` (existing) | Show ApprovalCard |
| `skill_completed` (new) | Transform SkillProgressCard to completion state |
| `queue_update` (new) | Update QueueDepthIndicator |
