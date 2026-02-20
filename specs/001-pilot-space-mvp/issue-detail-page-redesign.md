# Issue Detail Page -- Revised Design Spec

**Version**: 1.0.0
**Created**: 2026-02-20
**Status**: Draft
**Addresses**: 9 UX issues from devil's advocate review
**Scope**: Minimal targeted fixes, not a full redesign

---

## Table of Contents

1. [Issues Addressed](#1-issues-addressed)
2. [Revised Page Layout](#2-revised-page-layout)
3. [Revised Description Tab](#3-revised-description-tab)
4. [Revised AI Context Tab](#4-revised-ai-context-tab)
5. [Revised Properties Sidebar](#5-revised-properties-sidebar)
6. [Revised Delete Flow](#6-revised-delete-flow)
7. [Component-Level Specs](#7-component-level-specs)
8. [ASCII Mockups](#8-ascii-mockups)
9. [Implementation Checklist](#9-implementation-checklist)

---

## 1. Issues Addressed

| ID | Issue | Severity | Fix |
|----|-------|----------|-----|
| H-1 | Type selector permanently disabled | High | Remove from properties panel |
| H-2 | `window.confirm()` for delete | High | Replace with `DeleteConfirmDialog` (already exists) |
| H-3 | Zero-value stat pills prominent | Medium | Hide pills where count === 0 |
| H-4 | "Hours: 0.0" when unset | Medium | Empty placeholder, not "0.0" |
| H-5 | Description tab flat — no grouping | Medium | Collapsible sections with anchored headers |
| H-6 | Tasks buried in AI Context tab | High | Surface task progress summary on Description tab |
| H-7 | Mobile: properties panel above content | High | Collapsible `Sheet` drawer on mobile |
| H-8 | Per-field save errors invisible | Medium | Inline field-level error indicator |
| H-9 | Estimate vs Hours confusion | Low | Merge into single "Effort" field with unit toggle |

---

## 2. Revised Page Layout

### Design Rationale

The fundamental two-column layout (main + sidebar) is sound for desktop. The problems are exclusively about (a) mobile stacking, (b) flat content hierarchy in the main column, and (c) one buried feature. No structural overhaul needed.

### Desktop (md and above): unchanged 2-column

```
Header bar (identifier, breadcrumb, actions)
+-----------------------------------------+------------------+
| Main content (65-70%)                   | Sidebar (30-35%) |
|  [Description] [AI Context] tabs        | Properties       |
|  Content area (scrollable)              | (scrollable)     |
+-----------------------------------------+------------------+
```

No changes to desktop proportions or tab system.

### Mobile (below md): Sheet-based sidebar

**Current behavior**: Properties sidebar renders with `order-first`, pushing the issue title below the fold. Users see metadata before content.

**Revised behavior**: Sidebar becomes a `Sheet` (bottom drawer) triggered by a floating button. Main content area takes full width with title visible immediately.

```
Header bar
+------------------------------------------+
| Main content (100% width)                |
|  [Description] [AI Context] tabs         |
|  Content area (scrollable)               |
+------------------------------------------+
         [Properties button - FAB]
```

### Implementation

**File**: `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`

Replace the current mobile `order-first` div with:

```tsx
{/* Desktop sidebar */}
<div
  className="hidden shrink-0 overflow-y-auto md:block md:w-[35%] md:border-l lg:w-[35%] xl:w-[30%]"
  role="complementary"
  aria-label="Issue properties"
>
  <IssuePropertiesPanel {...panelProps} />
</div>

{/* Mobile: Sheet trigger + drawer */}
<div className="fixed bottom-6 right-6 z-40 md:hidden">
  <Sheet open={mobilePropertiesOpen} onOpenChange={setMobilePropertiesOpen}>
    <SheetTrigger asChild>
      <Button
        size="icon"
        className="size-12 rounded-full shadow-lg"
        aria-label="Open issue properties"
      >
        <SlidersHorizontal className="size-5" />
      </Button>
    </SheetTrigger>
    <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
      <SheetHeader>
        <SheetTitle>Properties</SheetTitle>
      </SheetHeader>
      <IssuePropertiesPanel {...panelProps} />
    </SheetContent>
  </Sheet>
</div>
```

**New state**: `const [mobilePropertiesOpen, setMobilePropertiesOpen] = React.useState(false);`

**New imports**: `Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle` from `@/components/ui/sheet`, `SlidersHorizontal` from `lucide-react`.

**Touch target**: The floating button is `size-12` (48px), exceeding the 44px WCAG minimum.

**Thumb zone**: Bottom-right placement lands in the natural thumb arc for right-handed users.

---

## 3. Revised Description Tab

### Current Problem

Five sections stacked vertically with only `<Separator />` between them. No visual grouping, no section navigation, no collapsibility. Scrolling through an empty Acceptance Criteria and empty Technical Requirements to reach Sub-Issues and Activity is wasteful.

### Solution: Collapsible Section Groups

Group the content into three logical zones with `Collapsible` wrappers:

| Zone | Sections | Default State | Rationale |
|------|----------|---------------|-----------|
| **Core** | Title + Description | Always open, not collapsible | Primary content, always visible |
| **Specification** | Acceptance Criteria + Technical Requirements | Collapsed if both empty, open if either has data | Progressive disclosure -- empty specs don't steal space |
| **Activity** | Sub-Issues + Activity Timeline | Open | Users need to see sub-tasks and comments immediately |

Additionally, a **Task Progress Summary** widget from the AI Context tab gets surfaced here (see Section 4).

### Revised JSX Structure

```tsx
<TabsContent value="description" className="mt-0 flex-1 overflow-y-auto p-6">
  <div className="max-w-3xl space-y-6">
    {/* Zone 1: Core (always open) */}
    <IssueTitle ... />
    <IssueDescriptionEditor ... />

    {/* Zone 2: AI Tasks summary (surfaced from AI Context) */}
    {hasAITasks && (
      <TaskProgressWidget
        issueId={issueId}
        completedCount={completedCount}
        totalCount={totalCount}
        onViewAll={() => setActiveTab('ai-context')}
      />
    )}

    {/* Zone 3: Specification (collapsible) */}
    <CollapsibleSection
      title="Specification"
      icon={<ClipboardList className="size-4" />}
      defaultOpen={hasSpecData}
      count={specItemCount}
    >
      <AcceptanceCriteriaEditor ... />
      <Separator className="my-4" />
      <TechnicalRequirementsEditor ... />
    </CollapsibleSection>

    {/* Zone 4: Work breakdown */}
    <SubIssuesList ... />

    {/* Zone 5: Activity */}
    <CollapsibleSection
      title="Activity"
      icon={<MessageSquare className="size-4" />}
      defaultOpen={true}
    >
      <ActivityTimeline ... />
    </CollapsibleSection>
  </div>
</TabsContent>
```

### CollapsibleSection Component Spec

**New component**: `CollapsibleSection`

**File**: `frontend/src/features/issues/components/collapsible-section.tsx`

```tsx
interface CollapsibleSectionProps {
  title: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  count?: number;      // badge showing item count
  children: React.ReactNode;
}
```

**Visual treatment**:
- Header row: icon + title + optional count badge + chevron toggle
- `border-b border-border` when open, `border-b border-transparent` when collapsed
- `ChevronRight` rotates to `ChevronDown` on open (CSS transform, `motion-safe:transition-transform duration-150`)
- Content area uses `Collapsible` + `CollapsibleContent` from shadcn/ui

**Tailwind classes**:
```
/* Header trigger */
className="flex w-full items-center justify-between py-3 text-sm font-medium
  text-foreground hover:text-foreground/80 transition-colors"

/* Count badge */
className="ml-auto mr-2 rounded-full bg-muted px-2 py-0.5 text-xs
  text-muted-foreground tabular-nums"

/* Chevron */
className="size-4 text-muted-foreground transition-transform duration-150
  motion-safe:transition-transform"
  data-[state=open]:rotate-90
```

**Accessibility**:
- `<Collapsible>` from Radix handles `aria-expanded`, `aria-controls` automatically
- Focus ring: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`
- Keyboard: Enter/Space toggles, Tab navigates

### TaskProgressWidget Component Spec

**Purpose**: Surface the AI task checklist progress on the Description tab so users discover it without switching tabs.

**New component**: `TaskProgressWidget`

**File**: `frontend/src/features/issues/components/task-progress-widget.tsx`

```tsx
interface TaskProgressWidgetProps {
  issueId: string;
  completedCount: number;
  totalCount: number;
  onViewAll: () => void;
}
```

**Visual treatment**: A compact card styled with the AI accent.

```
+----------------------------------------------------------+
| [Sparkles] Implementation Tasks    3/7 completed         |
| [================------]                    View all -->  |
+----------------------------------------------------------+
```

**Tailwind classes**:
```
/* Container */
className="rounded-xl border border-ai/20 bg-ai/5 p-4"

/* Header row */
className="flex items-center justify-between"

/* Title */
className="flex items-center gap-2 text-sm font-medium"
  <Sparkles className="size-4 text-ai" />

/* Count text */
className="text-xs text-muted-foreground tabular-nums"

/* Progress bar */
className="mt-2"  // reuse existing <Progress /> component

/* View all link */
className="text-xs text-ai hover:text-ai/80 font-medium cursor-pointer"
```

**Behavior**:
- Only renders when `totalCount > 0`
- Clicking "View all" calls `onViewAll` which programmatically switches to AI Context tab
- Progress bar reuses the existing `<Progress>` component with `className="h-1.5"`

**Accessibility**:
- `aria-label="Implementation tasks: {completed} of {total} complete"`
- "View all" is a `<button>` (not a link) since it changes tab, not navigates

---

## 4. Revised AI Context Tab

### Changes

**Removed from AI Context tab**: Nothing. All content stays. The Description tab gets a summary widget pointing here, not a duplication.

**Fixed**: Zero-value stat pills in `ContextSummaryCard`.

### ContextSummaryCard Fix

**File**: `frontend/src/features/issues/components/context-summary-card.tsx`

**Current**: All four `StatPill` components render unconditionally, showing "0 Issues", "0 Docs", etc.

**Revised**: Only render `StatPill` when `count > 0`. If all counts are zero, show a single muted text line instead.

```tsx
// Before (line 32-37):
<StatPill icon={Link2} label="Issues" count={summary.stats.relatedCount} />
<StatPill icon={BookOpen} label="Docs" count={summary.stats.docsCount} />
<StatPill icon={Code} label="Files" count={summary.stats.filesCount} />
<StatPill icon={ListChecks} label="Tasks" count={summary.stats.tasksCount} />

// After:
{allZero ? (
  <p className="text-xs text-muted-foreground italic">
    No related items found yet
  </p>
) : (
  <div className="flex items-center gap-3 pt-1 flex-wrap">
    {summary.stats.relatedCount > 0 && (
      <StatPill icon={Link2} label="Issues" count={summary.stats.relatedCount} />
    )}
    {summary.stats.docsCount > 0 && (
      <StatPill icon={BookOpen} label="Docs" count={summary.stats.docsCount} />
    )}
    {summary.stats.filesCount > 0 && (
      <StatPill icon={Code} label="Files" count={summary.stats.filesCount} />
    )}
    {summary.stats.tasksCount > 0 && (
      <StatPill icon={ListChecks} label="Tasks" count={summary.stats.tasksCount} />
    )}
  </div>
)}
```

Where `allZero = relatedCount + docsCount + filesCount + tasksCount === 0`.

---

## 5. Revised Properties Sidebar

### H-1: Remove Type Selector

**Current**: `IssueTypeSelect` renders with `disabled` prop hardcoded to `true`. The handler `handleTypeChange` is a no-op. Backend has no `type` column.

**Action**: Remove the `PropertyRow label="Type"` block entirely from `IssuePropertiesPanel`. Remove the `IssueTypeSelect` import. Keep the component file (`IssueTypeSelect.tsx`) for future use if backend adds type support.

**Lines to remove in `issue-properties-panel.tsx`** (lines 338-345):
```tsx
// DELETE this block:
<PropertyRow label="Type">
  <IssueTypeSelect
    value={issue.type ?? 'task'}
    onChange={handleTypeChange}
    disabled
    className="h-8 flex-1"
  />
</PropertyRow>
```

Also remove: `handleTypeChange` callback (lines 239-243), `IssueTypeSelect` import (line 29), unused `IssueType` type import.

### H-4: Fix "Hours: 0.0" Display

**Current**: `defaultValue={issue.estimateHours ?? ''}` renders `0.0` when the backend returns `0.0` (which it does for all new issues).

**Fix**: Treat `0` and `0.0` as "not set". Change:

```tsx
// Before:
defaultValue={issue.estimateHours ?? ''}

// After:
defaultValue={issue.estimateHours ? String(issue.estimateHours) : ''}
```

And update the placeholder:

```tsx
placeholder="Not set"
```

This way, `0`, `0.0`, `null`, and `undefined` all show the placeholder.

### H-9: Merge Estimate and Hours into "Effort"

**Current**: Two separate fields:
- "Estimate" -- story points via `EstimateSelector` (fibonacci dropdown: 1, 2, 3, 5, 8, 13, 21)
- "Hours" -- decimal hours via number input

Users don't understand the difference. Both measure effort.

**Revised**: Replace both with a single "Effort" row that has a unit toggle.

```
Effort:    [ 5 ]  [pts|hrs]
```

**Component**: `EffortField`

**File**: `frontend/src/features/issues/components/effort-field.tsx`

```tsx
interface EffortFieldProps {
  estimatePoints?: number;
  estimateHours?: number;
  onPointsChange: (points: number | undefined) => void;
  onHoursChange: (hours: number | undefined) => void;
  disabled?: boolean;
}
```

**Behavior**:
- Default view shows whichever field has data. If both are empty, shows points mode.
- Toggle is a segmented control: `[Points | Hours]` using two small `Button` variants.
- Points mode renders the existing `EstimateSelector` dropdown.
- Hours mode renders the existing number input.
- Toggling preserves both values independently (does not clear the other).

**Tailwind for segmented toggle**:
```
/* Container */
className="inline-flex rounded-lg border border-input p-0.5 bg-muted/50"

/* Active segment */
className="rounded-md bg-background px-2 py-0.5 text-xs font-medium shadow-sm"

/* Inactive segment */
className="rounded-md px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
```

**Properties panel row** (replaces both Estimate and Hours rows):
```tsx
<PropertyRow label="Effort">
  <EffortField
    estimatePoints={issue.estimatePoints ?? undefined}
    estimateHours={issue.estimateHours || undefined}
    onPointsChange={handleEstimateChange}
    onHoursChange={(hours) => {
      wrapHours(() => onUpdate({ estimateHours: hours })).catch(() => {});
    }}
    disabled={disabled}
  />
</PropertyRow>
```

### H-8: Per-Field Save Error Indicator

**Current**: `SaveStatus` component renders at the section header level showing aggregate status. When a field fails, users see "Error" but don't know which field.

**Revised**: Add a tiny inline indicator next to each field that enters error state.

**Component**: `FieldSaveIndicator`

**File**: `frontend/src/features/issues/components/field-save-indicator.tsx`

```tsx
interface FieldSaveIndicatorProps {
  fieldName: string;
}
```

**Behavior**:
- Reads `useSaveStatus(fieldName)` hook.
- `'idle'`: renders nothing (null).
- `'saving'`: renders a small spinner (`size-3 animate-spin text-muted-foreground`).
- `'saved'`: renders a check mark (`size-3 text-emerald-500`) that fades out after 2s.
- `'error'`: renders an alert icon (`size-3 text-destructive`) with a tooltip explaining "Failed to save. Click to retry." The icon persists until status changes.

**Tailwind classes**:
```
/* Container */
className="inline-flex items-center ml-1"

/* Saved fade-out */
className="motion-safe:animate-[fadeOut_0.3s_ease-in_2s_forwards]"

/* Error icon */
className="size-3 text-destructive cursor-pointer"
aria-label="Save failed. Click to retry."
```

**Integration**: Add `<FieldSaveIndicator fieldName="state" />` inside each `PropertyRow` after the control. The indicator is tiny enough to not disturb layout.

**Revised PropertyRow**:
```tsx
function PropertyRow({ label, fieldName, children }: PropertyRowProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {children}
        {fieldName && <FieldSaveIndicator fieldName={fieldName} />}
      </div>
    </div>
  );
}
```

**Keep the aggregate SaveStatus** in the section header -- it still serves as a summary. The field-level indicator adds precision.

---

## 6. Revised Delete Flow

### Current Problem

`handleDelete` in `page.tsx` uses `window.confirm()`:

```tsx
const confirmed = window.confirm('Are you sure you want to delete this issue?');
```

This is a native browser dialog with no styling, no context, and no brand consistency.

### Solution

The codebase already has `DeleteConfirmDialog` at `frontend/src/components/issues/DeleteConfirmDialog.tsx`. It uses shadcn `AlertDialog`, shows the issue name, lists what will be destroyed, and handles approval workflows. It just needs to be wired up.

### Implementation

**File**: `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`

Add state:

```tsx
const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
const [isDeleting, setIsDeleting] = React.useState(false);
```

Replace `handleDelete`:

```tsx
const handleDeleteClick = React.useCallback(() => {
  setDeleteDialogOpen(true);
}, []);

const handleDeleteConfirm = React.useCallback(async () => {
  if (!workspaceId || !issue?.id) return;
  setIsDeleting(true);
  try {
    await issueStore.deleteIssue(workspaceId, issue.id);
    router.push(`/${workspaceSlug}/issues`);
  } finally {
    setIsDeleting(false);
    setDeleteDialogOpen(false);
  }
}, [workspaceId, issue?.id, issueStore, router, workspaceSlug]);
```

Add dialog to JSX (after the main layout div):

```tsx
{issue && (
  <DeleteConfirmDialog
    open={deleteDialogOpen}
    onOpenChange={setDeleteDialogOpen}
    issues={[issue]}
    onConfirm={handleDeleteConfirm}
    isDeleting={isDeleting}
  />
)}
```

Pass `handleDeleteClick` (not `handleDelete`) to `IssueHeader.onDelete`.

**Import**: `import { DeleteConfirmDialog } from '@/components/issues/DeleteConfirmDialog';`

---

## 7. Component-Level Specs

### 7.1 All Modified Components Summary

| Component | File | Change Type |
|-----------|------|-------------|
| `IssueDetailPage` | `app/.../[issueId]/page.tsx` | Modify: mobile Sheet, delete dialog, tab control, task widget |
| `IssuePropertiesPanel` | `features/issues/components/issue-properties-panel.tsx` | Modify: remove Type, replace Estimate+Hours with Effort |
| `ContextSummaryCard` | `features/issues/components/context-summary-card.tsx` | Modify: hide zero-count pills |
| `CollapsibleSection` | `features/issues/components/collapsible-section.tsx` | **New** |
| `TaskProgressWidget` | `features/issues/components/task-progress-widget.tsx` | **New** |
| `EffortField` | `features/issues/components/effort-field.tsx` | **New** |
| `FieldSaveIndicator` | `features/issues/components/field-save-indicator.tsx` | **New** |

### 7.2 Interaction States

#### CollapsibleSection

| State | Visual |
|-------|--------|
| Collapsed | Chevron right, content hidden, bottom border transparent |
| Open | Chevron down (rotated 90deg), content visible, bottom border visible |
| Hover (header) | `text-foreground/80` subtle dim |
| Focus | Ring-2 ring-offset-2 |
| Disabled | Not applicable (always interactive) |

#### EffortField

| State | Visual |
|-------|--------|
| Points mode | Points toggle active (white bg, shadow), dropdown visible |
| Hours mode | Hours toggle active, number input visible |
| Empty | Placeholder "Not set" |
| Has value | Value displayed normally |
| Disabled | `opacity-50 cursor-not-allowed` on both toggle and input |

#### FieldSaveIndicator

| State | Visual | Duration |
|-------|--------|----------|
| Idle | Nothing rendered | -- |
| Saving | `Loader2` spinner, `size-3`, muted | Until resolved |
| Saved | `Check` icon, emerald-500, fades out | 2s visible, 300ms fade |
| Error | `AlertCircle` icon, destructive, persistent | Until retry or new save |

#### Mobile Properties Sheet

| State | Visual |
|-------|--------|
| Closed | FAB button visible at bottom-right |
| Opening | Sheet slides up from bottom, 300ms ease-out |
| Open | Sheet visible, max-h-[80vh], rounded-t-2xl, backdrop overlay |
| Closing | Sheet slides down, 200ms ease-in |

### 7.3 Keyboard & Focus

| Action | Keys | Behavior |
|--------|------|----------|
| Toggle collapsible section | Enter, Space | Opens/closes section |
| Navigate sections | Tab | Moves focus through section headers |
| Force save | Cmd+S | Unchanged -- dispatches `issue-force-save` event |
| Open mobile properties | Not keyboard-triggered | FAB button focusable, Enter opens Sheet |
| Close Sheet | Escape | Closes Sheet, returns focus to FAB |
| Tab between effort modes | Tab | Moves from toggle to input, then to next field |

### 7.4 Responsive Breakpoints

| Breakpoint | Sidebar | Layout | Notes |
|------------|---------|--------|-------|
| `< md` (768px) | Sheet drawer | Single column, full width | FAB trigger at bottom-right |
| `md` - `lg` | 35% width, border-left | Two columns | Current behavior preserved |
| `lg` - `xl` | 35% width | Two columns | Current behavior preserved |
| `xl+` | 30% width | Two columns | Current behavior preserved |

---

## 8. ASCII Mockups

### 8.1 Desktop -- Description Tab (Revised)

```
+-- Header --------------------------------------------------------+
| [<-] PILOT-42  [AI Generated]            [Copy link] [...] menu  |
+------------------------------------------------------------------+
|                                        |                         |
| [Description] [Sparkles AI Context]    | PROPERTIES              |
|                                        | [SaveStatus: idle]      |
| Issue Title (h1, editable)             |                         |
| ===================================    | State      [In Progress]|
|                                        | Priority   [High]       |
| Description                            | Assignee   [Jane D.]    |
| (TipTap rich text editor)              | Labels     [frontend]   |
|                                        | Cycle      [Sprint 12]  |
|                                        | Effort     [5] [pts|hrs]|
| +-- Implementation Tasks -----+        |                         |
| | [Sparkles] 3/7 completed    |        | DATES                   |
| | [==========------]  View -> |        | Start      [Feb 15]     |
| +-----------------------------+        | Due        [Feb 28]     |
|                                        |                         |
| v Specification (2 items)              | DETAILS                 |
| +--------------------------------+     | Reporter   [TD] Tin D.  |
| | Acceptance Criteria            |     | Created    Feb 10, 2026 |
| | [ ] Feature loads in < 2s     |     | Updated    Feb 20, 2026 |
| | [ ] Error state shows message |     |                         |
| | [+ Add criterion]             |     | LINKED ITEMS            |
| |                                |     | PR #142 (open)          |
| | Technical Requirements         |     | Note: "Sprint planning" |
| | ```                            |     |                         |
| | Must use React 18 Suspense    |     |                         |
| | ```                            |     |                         |
| +--------------------------------+     |                         |
|                                        |                         |
| Sub-Issues (2)                         |                         |
| [====50%====] 1/2                      |                         |
|  PILOT-43 Setup API endpoint    [Done] |                         |
|  PILOT-44 Add unit tests      [Todo]  |                         |
| [+ Add sub-issue]                      |                         |
|                                        |                         |
| v Activity                             |                         |
| +--------------------------------+     |                         |
| | [TD] Tin Dang  2h ago          |     |                         |
| |   Updated state to In Progress |     |                         |
| |                                |     |                         |
| | [JD] Jane Doe  1d ago          |     |                         |
| |   "Looks good, let's proceed"  |     |                         |
| |                                |     |                         |
| | [Comment input...]             |     |                         |
| +--------------------------------+     |                         |
+----------------------------------------+-------------------------+
```

### 8.2 Desktop -- AI Context Tab (Revised)

```
+-- Header --------------------------------------------------------+
| [<-] PILOT-42  [AI Generated]            [Copy link] [...] menu  |
+------------------------------------------------------------------+
|                                        |                         |
| [Description] [Sparkles AI Context]    | PROPERTIES              |
|                                        | (same as above)         |
| [Sparkles] Full Context for AI         |                         |
|                 [Clone] [Regenerate]   |                         |
| --------------------------------       |                         |
|                                        |                         |
| +-- Summary Card ----------------+     |                         |
| | [FileText] PILOT-42            |     |                         |
| | Implement GraphQL schema       |     |                         |
| | Schema definition for the...   |     |                         |
| | [3 Issues] [11 Tasks]          |  <-- only non-zero pills    |
| +--------------------------------+     |                         |
|                                        |                         |
| --------------------------------       |                         |
| [Link] Related Context                 |                         |
|   PILOT-38: Setup database...          |                         |
|   PILOT-40: API middleware...          |                         |
|                                        |                         |
| --------------------------------       |                         |
| [CheckSquare] AI Tasks                 |                         |
|   [==========------] 3/7              |                         |
|   [Decompose Tasks]                    |                         |
|   ...checklist items...                |                         |
|   ...prompt blocks...                  |                         |
+----------------------------------------+-------------------------+
```

### 8.3 Mobile -- Description Tab

```
+-- Header (compact) ----------------------+
| [<-] PILOT-42         [Copy] [...] menu  |
+------------------------------------------+
| [Description] [Sparkles AI Context]      |
|                                          |
| Issue Title (h1, editable)               |
| ======================================== |
|                                          |
| Description                              |
| (TipTap rich text editor)               |
|                                          |
| +-- Implementation Tasks --------+       |
| | [Sparkles] 3/7 completed       |       |
| | [==========------]   View -->  |       |
| +--------------------------------+       |
|                                          |
| > Specification (2 items)                |
|                                          |
| Sub-Issues (2)                           |
|  PILOT-43 Setup API...          [Done]   |
|  PILOT-44 Add unit tests       [Todo]   |
|                                          |
| v Activity                               |
| ...activity entries...                   |
|                                          |
+------------------------------------------+
                              [FAB button]
                              (Properties)

--- When FAB tapped: ---

+------------------------------------------+
|           Properties                  [X] |
| ---------------------------------------- |
| State      [In Progress]                 |
| Priority   [High]                        |
| Assignee   [Jane D.]                     |
| Labels     [frontend]                    |
| Cycle      [Sprint 12]                   |
| Effort     [5] [pts|hrs]                 |
| ---------------------------------------- |
| Start      [Feb 15]                      |
| Due        [Feb 28]                      |
| ---------------------------------------- |
| Reporter   [TD] Tin Dang                 |
| Created    Feb 10, 2026                  |
| Updated    Feb 20, 2026                  |
+------------------------------------------+
```

### 8.4 Delete Confirmation Dialog

```
+--------------------------------------+
|          [Trash icon - red]          |
|                                      |
|        Delete 1 Issue?               |
|                                      |
| This will permanently delete         |
| "Implement GraphQL schema".          |
|                                      |
| This action cannot be undone. All    |
| issue data including comments,       |
| attachments, and history will be     |
| permanently removed.                 |
|                                      |
|          [Cancel]  [Delete]          |
+--------------------------------------+
```

This is exactly what `DeleteConfirmDialog` already renders. No new component needed.

---

## 9. Implementation Checklist

### Phase 1: Quick Wins (no new components)

- [ ] H-1: Remove `IssueTypeSelect` from `IssuePropertiesPanel` (delete PropertyRow + handler + import)
- [ ] H-2: Wire `DeleteConfirmDialog` in `page.tsx` (replace `window.confirm`)
- [ ] H-3: Conditionally render `StatPill` in `ContextSummaryCard` (hide zero counts)
- [ ] H-4: Fix Hours default value (`issue.estimateHours ? String(...) : ''`, placeholder "Not set")

### Phase 2: New Components

- [ ] H-7: Create mobile `Sheet` sidebar in `page.tsx` (replace `order-first` pattern)
- [ ] H-5: Create `CollapsibleSection` component
- [ ] H-5: Restructure Description tab to use `CollapsibleSection` for Specification and Activity
- [ ] H-6: Create `TaskProgressWidget` component
- [ ] H-6: Add `TaskProgressWidget` to Description tab (reads from `TaskStore`)

### Phase 3: Refinements

- [ ] H-8: Create `FieldSaveIndicator` component
- [ ] H-8: Integrate `FieldSaveIndicator` into `PropertyRow`
- [ ] H-9: Create `EffortField` component with points/hours toggle
- [ ] H-9: Replace Estimate + Hours rows with single Effort row in `IssuePropertiesPanel`

### Phase 4: Tests

- [ ] Unit test: `CollapsibleSection` renders collapsed/open states
- [ ] Unit test: `TaskProgressWidget` hides when totalCount === 0
- [ ] Unit test: `EffortField` toggles between points and hours modes
- [ ] Unit test: `FieldSaveIndicator` renders correct icons per status
- [ ] Unit test: `ContextSummaryCard` hides zero-count pills
- [ ] Unit test: Delete flow uses `DeleteConfirmDialog` (no `window.confirm`)
- [ ] Unit test: Mobile layout renders `Sheet` trigger (not inline panel)
- [ ] Integration test: Properties Sheet opens/closes on mobile viewport
- [ ] Responsive test: Sidebar hidden below md, visible above md

---

## Appendix: Files Changed

| File | Type | Issue(s) |
|------|------|----------|
| `app/.../[issueId]/page.tsx` | Modify | H-2, H-5, H-6, H-7 |
| `features/issues/components/issue-properties-panel.tsx` | Modify | H-1, H-4, H-8, H-9 |
| `features/issues/components/context-summary-card.tsx` | Modify | H-3 |
| `features/issues/components/collapsible-section.tsx` | New | H-5 |
| `features/issues/components/task-progress-widget.tsx` | New | H-6 |
| `features/issues/components/effort-field.tsx` | New | H-9 |
| `features/issues/components/field-save-indicator.tsx` | New | H-8 |
| `features/issues/components/index.ts` | Modify | Export new components |
