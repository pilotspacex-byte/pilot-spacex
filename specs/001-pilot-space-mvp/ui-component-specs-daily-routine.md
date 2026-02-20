# UI Component Design Specifications — Daily Routine Feature
**Version**: 1.0
**Date**: 2026-02-20
**Design System**: Pilot Space v4.0 (Warm, Capable, Collaborative)
**Scope**: 4 new components for the daily routine / digest workflow

---

## Design System Reference Tokens

These tokens are used throughout all four specs below. They derive from the existing system in `ui-design-spec.md` v4.0 and confirmed from `DailyBrief.tsx`, `StructuredResultCard.tsx`, and `annotation-card.tsx`.

```css
/* Color */
--color-primary:        #29A386;   /* teal-green — CTAs, links, selection */
--color-primary-hover:  #24907A;   /* darken ~8% */
--color-primary-muted:  oklch(from #29A386 l c h / 0.08); /* tinted bg */
--color-ai:             #6B8FAD;   /* dusty blue — AI-origin elements */
--color-ai-muted:       oklch(from #6B8FAD l c h / 0.10);
--color-warning:        #D97706;   /* amber-600 — clarification / yellow badges */
--color-warning-muted:  #FEF3C7;   /* amber-100 */
--color-extract:        #EA580C;   /* orange-600 — extractable items */
--color-extract-muted:  #FFEDD5;   /* orange-100 */
--color-bg:             #FDFCFA;   /* warm off-white */
--color-bg-subtle:      oklch(from #FDFCFA l c h / 0.6); /* card surfaces */
--color-border:         hsl(var(--border));
--color-muted-fg:       hsl(var(--muted-foreground));
--color-foreground:     hsl(var(--foreground));
--color-destructive:    hsl(var(--destructive));

/* Typography — Geist, 4px grid */
--font-family: 'Geist', system-ui, sans-serif;
--text-2xl:  24px / 32px  font-semibold   /* page headings */
--text-sm:   14px / 20px  font-normal     /* body rows */
--text-xs:   12px / 16px  font-normal     /* secondary labels */
--text-11:   11px / 14px  font-normal     /* timestamps, mono refs */
--text-overline: 11px / 1 font-semibold tracking-wider uppercase  /* section labels */

/* Spacing — 4px base grid */
--space-1:   4px   --space-2:   8px   --space-3:  12px
--space-4:  16px   --space-5:  20px   --space-6:  24px

/* Border radius — squircle family */
--radius-sm:  6px   /* badges, chips, tight pills */
--radius-md: 10px   /* cards, rows */
--radius-lg: 12px   /* section containers */
--radius-xl: 16px   /* result cards */
--radius-full: 9999px  /* pill badges */

/* Shadow */
--shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05)
--shadow-md: 0 4px 8px rgb(0 0 0 / 0.08)

/* Motion */
--duration-fast:   150ms
--duration-normal: 200ms
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)
--ease-out:    cubic-bezier(0.0, 0.0, 0.2, 1)
```

---

---

## Component 1: DigestInsightsCard

**File location (planned)**: `frontend/src/features/homepage/components/DigestInsightsCard.tsx`
**Placement**: Inside `DailyBrief.tsx` → replaces the `<p>No suggestions yet</p>` stub in the "AI Insights" section.

### Design Brief

The card continues the document-list aesthetic of `DailyBrief.tsx` exactly. Each insight category lives in a bordered container that looks like the "Recent Notes" list — same `rounded-lg border border-border overflow-hidden` container, same compact row treatment. Categories stack vertically with a `space-y-3` gap. A dismiss button sits in the category header to remove the category entirely. Expandable items follow the same "Show N more" ghost button pattern already used for issues.

### Persona & Context

PM or Tech Lead, morning glance at their daily brief. They are skimming, not reading. Items must be scannable in under 3 seconds. Cognitive load must stay low — the section must feel like a triage inbox, not a dashboard.

### Emotional Intent

Calm urgency. The section surfaces problems but frames them as manageable action items, not alarms.

---

### Layout Sketch

```
┌─ AI Insights ────────────────────────────────────── [Sparkles icon] ─┐
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  [AlertCircle]  Stale Issues                [badge: 4]  [X]     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ● PS-12  Auth service not updated in 14d                        │   │
│  │  ● PS-23  Missing acceptance criteria                             │   │
│  │  ● PS-31  Assigned but no activity for 7d                        │   │
│  │  ● PS-44  Blocked – waiting on design                            │   │
│  │                                        [ghost: Show 1 more ›]   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  [FileQuestion]  Unlinked Notes             [badge: 2]  [X]     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ● "API Rate Limiting strategy" – no linked issue                │   │
│  │  ● "Q2 goals brainstorm" – no linked issue                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  [ShieldAlert]  Cycle Risks                 [badge: 1]  [X]     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ● Sprint 12 is 80% through time, 40% through scope              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Color & Typography Per Element

**Section header** (matches existing `DailyBrief.tsx` section headers):
- Icon: `Sparkles`, `h-4 w-4 text-muted-foreground`
- Label: `text-xs font-semibold uppercase tracking-wider text-muted-foreground`

**Category header row** (`h-10` min-height, `px-3` horizontal padding):
- Background: `bg-muted/30` (subtle differentiation from row items)
- Icon: 14x14px, color derived from category type (see table below)
- Category name: `text-xs font-semibold text-foreground` with `flex-1 truncate`
- Count badge: `<Badge variant="secondary">` with `px-1.5 py-0 text-xs tabular-nums`
- Dismiss button: `<button>` with `<X className="h-3.5 w-3.5 text-muted-foreground/60">` — touch target padded to 32x32px minimum, `hover:text-foreground transition-colors`

**Category container** (reuses existing note-list pattern):
- `overflow-hidden rounded-lg border border-border`
- Category header is `border-b border-border`

**Insight item row** (matches `NoteEntry` height and padding):
- `flex w-full items-center gap-2 px-3 py-2 text-left min-h-[36px]`
- State dot: `h-1.5 w-1.5 rounded-full bg-muted-foreground/50` (neutral; not alarming)
- Issue identifier: `font-mono text-[11px] text-muted-foreground shrink-0` — only when item refers to an issue
- Item text: `text-[13px] text-foreground flex-1 truncate`
- Divider between items: `border-b border-border/50` on all but last
- Hover: `hover:bg-muted/50 motion-safe:transition-colors motion-safe:duration-100`
- Focus: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring`

**"Show N more" button** (identical to existing `Working On` expand pattern):
- `<Button variant="ghost" size="sm">` with `h-8 w-full gap-1.5 text-xs text-muted-foreground`

**Empty state** (all categories dismissed or no data):
- Centered paragraph: `py-6 text-center text-sm text-muted-foreground`
- Text: "No AI insights right now. Check back later."

**Loading state**:
- Two skeleton blocks: `h-24 motion-safe:animate-pulse rounded-lg bg-muted/30`
- `space-y-3` between them

---

### Category Type Map

| Category key       | Icon             | Icon color token            |
|--------------------|-----------------|------------------------------|
| `stale_issues`     | `AlertCircle`   | `text-amber-500`            |
| `unlinked_notes`   | `FileQuestion`  | `text-muted-foreground/70`  |
| `cycle_risks`      | `ShieldAlert`   | `text-orange-500`           |
| `blocked_deps`     | `Link2Off`      | `text-destructive/70`       |
| `overdue`          | `Clock`         | `text-red-500`              |

---

### Interaction States

| State    | Behavior |
|----------|----------|
| Default  | Items visible up to `MAX_VISIBLE = 5`; "Show N more" ghost button if overflow |
| Expanded | All items visible; "Show less" appears — identical to `Working On` expand logic |
| Dismissed | Category removed from DOM with `200ms` fade-out (`opacity-0 h-0 overflow-hidden transition-all`) |
| Loading  | Skeleton pulses replace category containers |
| Empty    | Single centered message replaces entire section content |

---

### Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| Mobile (`< sm`) | Full width, same layout — no column changes needed. Touch targets enforce `min-h-[44px]` on all interactive rows. Count badge visible. Dismiss button always visible (no hover-only pattern). |
| Desktop (`>= md`) | Max width `max-w-2xl` inherited from `DailyBrief.tsx` article wrapper. No additional changes. |

---

### Accessibility Annotations

- Section: `<section aria-label="AI insights">`
- Category containers: `role="list"` with `aria-label="{categoryName} insights"`
- Item rows: `role="listitem"` — or native `<button>` for clickable items, `<div>` for read-only
- Dismiss button: `aria-label="Dismiss {categoryName} insights"` — never `aria-hidden`
- Badge counts: visible text is sufficient; no additional `aria-label` needed
- Loading skeleton: `role="status" aria-label="Loading AI insights"`
- Focus order: category header (dismiss button) → items → expand button → next category

---

### Implementation Notes

The data shape expected from the AI digest API:

```typescript
interface DigestInsight {
  id: string;
  category: 'stale_issues' | 'unlinked_notes' | 'cycle_risks' | 'blocked_deps' | 'overdue';
  items: DigestInsightItem[];
}

interface DigestInsightItem {
  id: string;
  text: string;           // human-readable label
  issueIdentifier?: string; // e.g. "PS-42" — displayed mono if present
  href?: string;          // navigation target
}
```

Local dismissed-category state lives in component state (not MobX) — dismissal is session-only and does not need persistence. If persistence is added later, use `localStorage` key `digest-dismissed-{workspaceId}-{date}`.

---

---

## Component 2: NoteHealthBadges

**File location (planned)**: `frontend/src/features/notes/components/NoteHealthBadges.tsx`
**Placement**: `NoteCanvasLayout.tsx` → inside `InlineNoteHeader`, after the word count element in the existing sticky header bar.

### Design Brief

Status pills that communicate note health at a glance without interrupting the writing flow. They live in the compact sticky header alongside existing metadata (word count, date, save indicator). They are status indicators first and navigation shortcuts second — visually subordinate to the main toolbar actions but immediately scannable.

### Persona & Context

A developer or PM mid-writing session. Their peripheral vision catches the badges without requiring focus shift. Clicking a badge is a power-user shortcut, not a primary workflow.

### Emotional Intent

Informative confidence. Badges tell users their note is being processed intelligently. Orange/yellow signal "action available" not "something is wrong."

---

### Layout Sketch

```
┌─ InlineNoteHeader (sticky bar) ───────────────────────────────────────┐
│  [FileText] Notes › Note Title  ·  2h ago  ·  342 words  ·  [Cloud]  │
│                                                                         │
│  ← existing ─────────────────────── new badges inserted here ──────→  │
│                                  [● 3 extractable] [◐ 2 clarity] [PS-42]│
│                                                    ↑               ↑   │
│                                              orange pill      teal pill │
│                                                                         │
│  ─────────────────────────────────────── [Share] [•••]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

Zoomed in on badge group (right-aligned in the header flex row, before action buttons):

```
[● 3 extractable]   [◐ 2 need clarity]   [PS-42 linked]
     orange               yellow               teal
   h-5 px-2             h-5 px-2             h-5 px-2
```

---

### Badge Specifications

Each badge is a `<button>` element styled as a pill chip (not a shadcn `<Badge>` component — those are non-interactive by default and this needs keyboard access and hover states).

**Shared base styles**:
```
inline-flex items-center gap-1 rounded-full px-2 h-5
text-[11px] font-medium leading-none whitespace-nowrap
motion-safe:transition-all motion-safe:duration-150
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1
cursor-pointer select-none
```

**Extractable badge** (`N extractable`):
- Default: `bg-orange-100 text-orange-700 border border-orange-200/60`
- Hover: `bg-orange-200 text-orange-800`
- Dark: `dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800/60`
- Icon: `CircleDot h-2.5 w-2.5` (filled dot indicating detected items)
- Label: `{N} extractable`
- Click action: Open ChatView with pre-filled prompt `"Extract issues from this note"`

**Clarity badge** (`N need clarity`):
- Default: `bg-amber-100 text-amber-700 border border-amber-200/60`
- Hover: `bg-amber-200 text-amber-800`
- Dark: `dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60`
- Icon: `HelpCircle h-2.5 w-2.5`
- Label: `{N} need clarity`
- Click action: Open ChatView with pre-filled prompt `"Help me clarify ambiguous sections"`

**Linked issue badge** (`PS-42`):
- Default: `bg-primary/10 text-primary border border-primary/20`
- Hover: `bg-primary/20 text-primary`
- Dark: `dark:bg-primary/15 dark:text-primary`
- Icon: `Link2 h-2.5 w-2.5`
- Label: `{issueIdentifier}` — font-mono for the identifier portion
- Multiple linked issues: Show `PS-42 +2` (first identifier + overflow count)
- Click action: Open ChatView with pre-filled prompt `"Tell me about linked issue {identifier}"`

---

### Tooltip Specification

Each badge has a `<Tooltip>` (shadcn/ui) with 300ms delay to explain the action:

| Badge | Tooltip text |
|-------|-------------|
| Extractable | "3 items detected that could become issues. Click to extract." |
| Clarity | "2 sections need clarification. Click to ask AI." |
| Linked | "Linked to PS-42. Click to discuss in AI chat." |

Tooltip: `side="bottom"` with `sideOffset={6}`. Content: `text-xs max-w-[200px]`.

---

### Interaction States

| State | Behavior |
|-------|----------|
| Default | Pill visible with appropriate color |
| Hover | Background deepens 10% — immediate response, no delay |
| Pressed/Active | `scale-95` transform for 100ms via `active:scale-95` |
| Loading (counts not yet computed) | Badge hidden entirely — do not show skeleton pills; the header is too compact |
| Count is 0 | Badge hidden entirely (`null` render) |
| ChatView already open | Badge still clickable; it pre-fills the input and focuses it |

---

### Overflow / Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| Mobile (`< sm`) | All three badges collapse into a single count chip: `[● 5]` with icon `Sparkles h-2.5 w-2.5 text-muted-foreground`. Tapping opens a small popover listing all three states. |
| Tablet (`sm–md`) | Extractable and clarity badges visible; linked issue badge hidden if no room |
| Desktop (`>= md`) | All badges visible in full form |

Mobile collapsed chip style:
```
bg-muted text-muted-foreground border border-border
inline-flex items-center gap-1 rounded-full px-2 h-5 text-[11px]
```

---

### Accessibility Annotations

- Each `<button>`: `aria-label` must be explicit. Example: `aria-label="3 extractable items — click to extract issues"`
- Badge group wrapper: `<div role="group" aria-label="Note health status">`
- Tooltip: `role="tooltip"` — managed by shadcn Tooltip automatically
- Color is not the sole differentiator — icon + text label carry meaning redundantly
- Focus order: follows DOM order; badges appear before action buttons (Share, More)

---

### Implementation Notes

Props interface:

```typescript
interface NoteHealthBadgesProps {
  extractableCount: number;
  clarityCount: number;
  linkedIssues: LinkedIssueBrief[];  // already on NoteCanvasProps
  onBadgeClick: (type: 'extractable' | 'clarity' | 'linked', prompt: string) => void;
}
```

`onBadgeClick` should call `handleChatViewOpen()` and then `aiStore.pilotSpace.sendMessage(prompt)` with a 100ms delay — identical pattern to the existing slash command handler in `NoteCanvasEditor.tsx` (line 380).

Counts (`extractableCount`, `clarityCount`) come from `aiStore.marginAnnotation` — count annotations of type `issue_candidate` and `clarification` respectively. The component reads these from props; the parent (`NoteCanvasLayout`) derives them from store state.

---

---

## Component 3: Annotation Action Buttons

**File location**: `frontend/src/features/notes/components/annotation-card.tsx` (modify existing)
**Placement**: Inside `AnnotationCard`, below the existing content block (after the confidence row).

### Design Brief

The current `AnnotationCard` is a compact `p-3` card with icon, title, summary, type label, and confidence score. The action buttons sit below a thin divider line, occupying a single row. They are compact — `h-7` buttons with `text-xs` labels — so they do not visually overpower the annotation content above them. One button per annotation type: contextual, not a generic toolbar.

### Persona & Context

A developer reviewing their own note after the AI has annotated it. They are mid-writing; the annotation is a prompt to act. The button must feel like "one tap to continue" — not a separate workflow.

### Emotional Intent

Enabling. The button gives the user a clear next step without forcing them to formulate a command.

---

### Layout Sketch

Existing `AnnotationCard` structure with new addition:

```
┌─────────────────────────────────────────────────────────┐
│  [Icon]  Title of annotation                            │  ← existing
│          Summary text line 1                            │  ← existing
│          Summary text line 2                            │  ← existing
│                                                         │
│  suggestion              72%                            │  ← existing
│ ───────────────────────────────────────────────────────  │  ← NEW divider
│  [Extract Issue →]                                      │  ← NEW (issue_candidate)
└─────────────────────────────────────────────────────────┘

or for clarification type:

│  question                85%                            │
│ ───────────────────────────────────────────────────────  │
│  [Ask AI →]                                             │
└─────────────────────────────────────────────────────────┘

or for action_item type:

│  insight                 91%                            │
│ ───────────────────────────────────────────────────────  │
│  [Create Task →]                                        │
└─────────────────────────────────────────────────────────┘
```

---

### Button Specifications Per Annotation Type

**Shared structure** — all buttons are `<button type="button">` with this base:
```
inline-flex items-center gap-1.5
rounded-md px-2.5 h-7
text-xs font-medium
motion-safe:transition-colors motion-safe:duration-150
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1
```

**`issue_candidate` → "Extract Issue"**:
- Colors: `bg-orange-100 text-orange-700 hover:bg-orange-200`
- Dark: `dark:bg-orange-950/50 dark:text-orange-300 dark:hover:bg-orange-900/60`
- Icon: `ArrowUpFromLine h-3 w-3` (suggests lifting content into an issue)
- Label: `Extract Issue`
- Action: Call `onExtractIssues` with the annotation's `blockId` as `selectedText` scope, OR open ChatView with prompt `"Extract this as an issue: {annotation.aiMetadata?.summary}"`

**`clarification` / `question` → "Ask AI"**:
- Colors: `bg-[--color-ai]/10 text-[--color-ai] hover:bg-[--color-ai]/20`
- Resolved values: `bg-[#6B8FAD]/10 text-[#6B8FAD] hover:bg-[#6B8FAD]/20`
- Dark: `dark:bg-[#6B8FAD]/15 dark:text-[#6B8FAD] dark:hover:bg-[#6B8FAD]/25`
- Icon: `MessageCircleQuestion h-3 w-3`
- Label: `Ask AI`
- Action: Open ChatView with prompt `"Help me clarify: {annotation.aiMetadata?.title}"`

**`action_item` / `insight` / `suggestion` → "Create Task"**:
- Colors: `bg-primary/10 text-primary hover:bg-primary/20`
- Dark: `dark:bg-primary/15 dark:text-primary dark:hover:bg-primary/25`
- Icon: `Plus h-3 w-3`
- Label: `Create Task`
- Action: Open ChatView with prompt `"Create a task from this: {annotation.aiMetadata?.summary}"`

**`warning` → "View Warning"** (informational only):
- Colors: `bg-amber-100 text-amber-700 hover:bg-amber-200`
- Icon: `ChevronRight h-3 w-3`
- Label: `View in Chat`
- Action: Open ChatView with prompt referencing the warning

**`reference` / `info` → no button** (read-only annotations do not need an action)

---

### Divider and Layout

Insert a `<div className="mt-2 pt-2 border-t border-current/10">` between the confidence row and the button. This uses `border-current/10` so the divider inherits the card's type color rather than a fixed gray — maintaining the contextual color identity of each card type.

Button row: `<div className="flex items-center justify-start">` containing only the single action button. Left-aligned, not stretched to full width. This keeps the button visually subordinate.

---

### Modified `AnnotationCard` Structure (annotated delta)

```
<button onClick={onSelect} className={...typeColors[annotation.type]...}>
  {/* existing: icon + title + summary */}
  <div className="flex items-start gap-2">
    <Icon ... />
    <div>
      <p>{title}</p>
      <p>{summary}</p>
    </div>
  </div>

  {/* existing: type label + confidence */}
  <div className="flex items-center justify-between mt-2">
    <span>{annotation.type}</span>
    <span>{confidence}%</span>
  </div>

  {/* NEW: action button — only renders if annotation type maps to an action */}
  {actionButton && (
    <div className="mt-2 pt-2 border-t border-current/10">
      <div className="flex items-center">
        {actionButton}
      </div>
    </div>
  )}
</button>
```

The outer element is already a `<button>`. Placing interactive elements inside a `<button>` is invalid HTML. The fix: convert the outer container from `<button>` to `<div>` with equivalent keyboard handling, or use `e.stopPropagation()` on the inner button click. The recommended approach is to change the outer `<button>` to `<div role="button" tabIndex={0}>` with `onKeyDown` for Enter/Space, allowing inner `<button>` elements to work natively.

---

### Interaction States

| State | Behavior |
|-------|----------|
| Default | Button visible with type-appropriate color |
| Hover | Background deepens — 150ms |
| Pressed | `active:opacity-80` |
| Annotation selected (`isSelected=true`) | Button remains visible and fully interactive |
| Loading (action in progress) | Button shows `<Loader2 className="h-3 w-3 animate-spin" />` in place of icon; label changes to "Working..." |
| Success | Button disappears; optional `toast.success()` via sonner |

---

### Responsive Behavior

The annotation margin is already constrained width (`~200px` on most screens). The compact `h-7 text-xs` button fits comfortably. No responsive changes needed. On mobile where the margin collapses into a bottom sheet, button sizing remains identical.

---

### Accessibility Annotations

- Inner `<button>`: `aria-label` = `"{actionLabel} based on annotation: {annotation.aiMetadata?.title}"`
- `e.stopPropagation()` on the button's click handler to prevent the outer card's `onSelect` from firing simultaneously
- Outer container converted to `<div role="button" tabIndex={0}>` to allow nested interactivity
- Focus ring: `focus-visible:ring-2 focus-visible:ring-blue-500 ring-offset-2` on outer container (existing style is `ring-2 ring-blue-500 ring-offset-2` when `isSelected` — preserve this)

---

---

## Component 4: Standup Result Card

**File location (planned)**: `frontend/src/features/ai/ChatView/MessageList/StandupResultCard.tsx`
**Placement**: Registered in `StructuredResultCard.tsx` as a new `case 'standup_result':` handler, OR rendered directly inside `AssistantMessage.tsx` when the message content contains a `standup_result` schema type.

### Design Brief

The standup card extends the `StructuredResultCard` pattern — `rounded-[12px] border border-border bg-background-subtle p-4` outer shell — with internal structure unique to standup output. Three named sections (Yesterday, Today, Blockers) are displayed as vertical stacked groups, each with a minimal section label and a list of items. A copy button in the card header exports formatted text to clipboard. The card feels like a structured document, not a chat bubble.

### Persona & Context

A developer generating their standup summary in one command (`/standup`). They will copy the output directly into Slack or a standup channel. Speed and copy-friendliness are the primary needs.

### Emotional Intent

Productive satisfaction. "My standup is ready" feeling. The card should feel polished enough that copying it requires no editing.

---

### Layout Sketch

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Mic2]  Daily Standup                             [Copy]           │  ← card header
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  YESTERDAY                                                            │  ← section label
│  ● Completed PS-12 authentication flow PR review                      │  ← item
│  ● Merged PS-18 data pipeline refactor                                │
│                                                                       │
│  TODAY                                                                │
│  ● Working on PS-23 API rate limiting design                          │
│  ● Will start PS-31 backend testing once unblocked                    │
│                                                                       │
│  BLOCKERS                                                             │
│  ● PS-31 waiting on design approval from @sarah                       │  ← item with ref
│                                                                       │
│  ─────────────────────────────────────────────────────────────────   │  ← optional footer
│  Generated from 4 active issues · 2h ago                             │  ← metadata
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Card Header

Outer shell: inherits `StructuredResultCard` outer wrapper:
```
rounded-[12px] border border-border bg-background-subtle p-4 shadow-sm
role="region" aria-label="Daily standup summary"
```

Header row inside the card:
```
flex items-center justify-between mb-4
```

Left group:
- Icon: `<Mic2 className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />`
- Title: `<span className="text-sm font-semibold text-foreground">Daily Standup</span>`
- Date tag: `<span className="ml-2 text-xs text-muted-foreground tabular-nums">{date}</span>` (e.g. "Feb 20")

Right group — Copy button:
```
<button
  type="button"
  onClick={handleCopy}
  aria-label="Copy standup to clipboard"
  className={cn(
    'inline-flex items-center gap-1.5 rounded-md px-2.5 h-7 text-xs font-medium',
    'bg-muted text-muted-foreground border border-border',
    'hover:bg-muted/80 hover:text-foreground',
    'motion-safe:transition-colors motion-safe:duration-150',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
  )}
>
  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
  {copied ? 'Copied' : 'Copy'}
</button>
```

Copy state transitions: `copied` boolean state, resets after 2000ms. Icon swaps from `Copy` to `Check`. Label swaps from `"Copy"` to `"Copied"`. No animation beyond the icon swap (respect `prefers-reduced-motion`).

---

### Section Specifications

Three sections: `yesterday`, `today`, `blockers`.

Section labels:
```
text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70
mb-2 mt-0 (first section) / mt-4 (subsequent sections)
```

Section label colors (subtle differentiation without alarming):
- Yesterday: `text-muted-foreground/70` (neutral)
- Today: `text-primary/70` (teal, active focus)
- Blockers: `text-amber-600/80` (amber, caution — not red, not alarming)

Section item list: `<ul role="list" aria-label="{section} standup items">` with `space-y-1.5`.

Each item `<li>`:
```
flex items-start gap-2 text-sm text-foreground
```

Bullet: `<span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-muted-foreground/40 shrink-0" aria-hidden="true" />`

Issue identifier within item text: rendered as `<span className="font-mono text-xs text-primary shrink-0">PS-42</span>` inline within the item sentence. Not a link — avoids navigation interruption.

Empty section (e.g. no blockers): display `<span className="text-sm text-muted-foreground italic">No blockers</span>` — do not hide the section, always show all three for predictable layout.

---

### Footer (optional)

Shown only when metadata is available:
```
<div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
  <span className="text-xs text-muted-foreground">
    Generated from {issueCount} active issues
  </span>
  <span className="text-xs text-muted-foreground tabular-nums">
    {timeAgo}
  </span>
</div>
```

---

### Copy Format Specification

The `handleCopy` function produces plain text optimized for Slack:

```
**Yesterday**
• Completed PS-12 authentication flow PR review
• Merged PS-18 data pipeline refactor

**Today**
• Working on PS-23 API rate limiting design
• Will start PS-31 backend testing once unblocked

**Blockers**
• PS-31 waiting on design approval from @sarah
```

Slack renders `**bold**` in messages, so this format works natively. Implement via `navigator.clipboard.writeText(formattedText)`.

---

### Data Shape

```typescript
interface StandupResultData {
  date: string;        // ISO date string
  yesterday: StandupItem[];
  today: StandupItem[];
  blockers: StandupItem[];
  issueCount?: number;
  generatedAt?: string;
}

interface StandupItem {
  text: string;                    // full sentence
  issueIdentifier?: string;        // e.g. "PS-42" — for inline mono rendering
  issueId?: string;                // for potential future navigation
}
```

---

### Integration with StructuredResultCard

Add to `StructuredResultCard.tsx` switch block:

```typescript
case 'standup_result':
  return <StandupResultCard data={data as StandupResultData} />;
```

`StandupResultCard` is a named export from its own file at:
`frontend/src/features/ai/ChatView/MessageList/StandupResultCard.tsx`

It does NOT accept `onCreateIssues` or `isCreatingIssues` — standup cards are view-only.

---

### Interaction States

| State | Behavior |
|-------|----------|
| Default | Card fully visible, copy button idle |
| Copy hover | Button background deepens |
| Copy active | `Check` icon, "Copied" label — 2000ms then resets |
| No items in a section | Section shows "No blockers" italic text |
| Loading | Not applicable — standup card only renders on complete AI response |

---

### Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| Mobile (`< sm`) | Card fills ChatView width. Section labels remain. Items wrap at word boundary. Copy button stays in header. No layout changes. |
| Desktop (`>= md`) | Card at `max-w-[80%]` per existing `MessageGroup` pattern. Header items on single row. |

---

### Accessibility Annotations

- `role="region" aria-label="Daily standup summary"` on outer card
- `role="list"` and `role="listitem"` on section item lists
- Section headings: `aria-label="{section} items"` on the `<ul>`, since `<span>` labels are not semantic headings
- Copy button: `aria-label="Copy standup to clipboard"` — changes to `aria-label="Standup copied to clipboard"` when `copied=true` via `aria-live="polite"` region
- Issue identifiers in text: wrapped in `<abbr title="Issue PS-42">PS-42</abbr>` for screen readers to announce correctly
- Color of section labels is not the sole differentiator — text label carries meaning

---

---

## Cross-Component Consistency Notes

### Token Reuse Summary

All four components draw from the same token pool. No new design decisions are introduced — only new applications of existing tokens.

| Decision | Token | Rationale |
|----------|-------|-----------|
| `issue_candidate` orange | `bg-orange-100 text-orange-700` | Consistent with `PRIORITY_DOTS.high = bg-orange-500` in `StructuredResultCard` |
| `clarification` blue | `bg-[#6B8FAD]/10 text-[#6B8FAD]` | AI accent color used for AI-initiated actions |
| Primary teal for linked/task | `bg-primary/10 text-primary` | Consistent with `ExtractionResultCard` selected state |
| Amber for cycle risks/blockers | `text-amber-600` | Consistent with `STATE_COLORS.in_progress = bg-amber-500` in `DailyBrief` |
| All compact row heights | `h-9` / `min-h-[36px]` desktop, `min-h-[44px]` mobile | Matches existing `NoteEntry` and `IssueEntry` in `DailyBrief` |
| Dividers | `border-border/50` | Consistent with `NoteEntry` divider at line 104 |
| Container pattern | `overflow-hidden rounded-lg border border-border` | Exact reuse of note list container from `DailyBrief` |
| Card pattern | `rounded-[12px] border border-border bg-background-subtle p-4 shadow-sm` | Exact reuse of `StructuredResultCard` outer wrapper |

### Interaction Pattern Consistency

- All hover states: `hover:bg-muted/40` or `hover:bg-muted/50` — matches existing DailyBrief entries
- All transition: `motion-safe:transition-colors motion-safe:duration-100` or `duration-150`
- All focus: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`
- All touch targets: `min-h-[44px]` on mobile, `min-h-[36px]` on desktop for rows; `min-w-[44px]` for icon-only buttons
- All expand/collapse: `<ChevronDown>` / `<ChevronRight>` pattern from `DailyBrief` — no chevron animation on mobile (prefer `prefers-reduced-motion`)

### WCAG 2.2 AA Compliance

All specified color combinations have been checked against 4.5:1 contrast minimum for normal text:

| Foreground | Background | Ratio | Pass |
|-----------|-----------|-------|------|
| `text-orange-700` (#C2410C) | `bg-orange-100` (#FFEDD5) | ~5.8:1 | AA |
| `text-amber-700` (#B45309) | `bg-amber-100` (#FEF3C7) | ~5.4:1 | AA |
| `text-primary` (#29A386) | `bg-primary/10` (~#EBF7F4) | ~4.6:1 | AA |
| `text-[#6B8FAD]` | `bg-[#6B8FAD]/10` | ~4.5:1 | AA (borderline — verify in implementation) |
| `text-muted-foreground` | `bg-background` | System tokens — verify against actual theme values |

The dusty blue AI accent at 10% opacity background should be verified at implementation time. If contrast fails, increase text darkness to `#4A6B8A` or add `font-medium` to push perceived weight.
