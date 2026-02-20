# Issue Detail Page -- Note-First Redesign Specification

**Version**: 2.0.0
**Created**: 2026-02-20
**Status**: Draft
**Parent**: `ui-design-spec.md` v4.0, `issue-detail-page-redesign.md` v1.0
**Supersedes**: The v1 targeted-fix spec for layout structure (v1 field-level fixes H-1 through H-9 remain valid)
**Branch**: `feat/issue-note`

---

## Table of Contents

1. [Design Brief](#1-design-brief)
2. [Layout Architecture](#2-layout-architecture)
3. [Minimal Header](#3-minimal-header)
4. [Property Block Node](#4-property-block-node)
5. [Issue Title](#5-issue-title)
6. [Note Editor Body](#6-note-editor-body)
7. [Sub-issues Section](#7-sub-issues-section)
8. [Activity Section](#8-activity-section)
9. [AI Chat Panel](#9-ai-chat-panel)
10. [Mobile Responsive Design](#10-mobile-responsive-design)
11. [Interaction Patterns](#11-interaction-patterns)
12. [Keyboard Shortcuts](#12-keyboard-shortcuts)
13. [Transitions and Animation](#13-transitions-and-animation)
14. [Design Tokens Reference](#14-design-tokens-reference)
15. [Component Hierarchy](#15-component-hierarchy)
16. [Accessibility](#16-accessibility)
17. [ASCII Wireframes](#17-ascii-wireframes)
18. [Implementation Checklist](#18-implementation-checklist)

---

## 1. Design Brief

### Problem

The current issue detail page uses a traditional form-tracker pattern: properties sidebar on the right, tabbed content (Description | AI Context) on the left. This breaks Pilot Space's core "note-first" paradigm where users should feel like they are working in a note that happens to have issue metadata, not filling out a form.

### Solution

Replace the two-column form layout with a note canvas layout identical to `NoteCanvasLayout.tsx`. The issue detail page becomes a note editor with:

- An **inline property block** (custom TipTap node) at document position 0
- A seamless **H1 title** immediately after the property block
- A full **TipTap note editor** with all 13+ extensions (ghost text, slash commands, margin annotations, note links, inline issues, code blocks, etc.)
- An **AI Chat panel** on the right (same `ChatView` component used in notes)
- **Sub-issues** and **Activity** below the editor as scrollable sections

### Emotional Goal

The page should feel like editing a note in Craft or Apple Notes. The metadata is there but recedes. The writing surface dominates. The AI co-pilot is always available but never intrusive.

### Persona Fit

| Persona | How This Serves Them |
|---------|---------------------|
| **Architect** | Full editor with code blocks, tech spec sections, AI chat for architecture review |
| **Tech Lead** | Inline property editing without context-switching; sub-issue decomposition below |
| **PM** | Natural prose-first writing; properties visible but secondary; AI enhancement via /commands |
| **Junior Dev** | Familiar note-editing UX; less intimidating than a form; AI chat for context generation |

---

## 2. Layout Architecture

### Desktop (lg and above, >= 1024px)

Two-panel resizable layout using `ResizablePanelGroup` from `react-resizable-panels`.

```
┌──────────────────────────────────────────────────────────────┐
│ Minimal Header: ← | PS-42 Bug | save status | chat | ...    │  h-12  (48px)
├──────────────────────────────────────────┬───────────────────┤
│ Note Editor Panel (60-65%)               │ AI Chat (35-40%)  │
│                                          │                   │
│  ┌─ Scrollable Document ──────────────┐  │  ┌─ ChatView ──┐ │
│  │ [Property Block Node]              │  │  │ ChatHeader  │ │
│  │ # Issue Title (H1)                 │  │  │ MessageList │ │
│  │                                    │  │  │             │ │
│  │ Description content...             │  │  │             │ │
│  │ (full TipTap editor)               │  │  │             │ │
│  │                                    │  │  │             │ │
│  │ ─── Sub-issues ─────────────────── │  │  │             │ │
│  │ (SubIssuesList)                    │  │  │             │ │
│  │                                    │  │  ├─────────────┤ │
│  │ ─── Activity ───────────────────── │  │  │ ChatInput   │ │
│  │ (ActivityTimeline)                 │  │  │ /commands   │ │
│  └────────────────────────────────────┘  │  └─────────────┘ │
│                                          │                   │
└──────────────────────────────────────────┴───────────────────┘
```

### Measurements

| Element | Value | Rationale |
|---------|-------|-----------|
| Header height | 48px (`h-12`) | Compact; matches NoteCanvas InlineNoteHeader |
| Editor panel default | 62% | Matches NoteCanvasLayout editor panel |
| Editor panel min | 50% | Ensures readable content width |
| Chat panel default | 38% | Matches NoteCanvasLayout chat panel |
| Chat panel min | 30% | Minimum for readable chat messages |
| Chat panel max | 50% | Prevents editor from becoming too narrow |
| Editor content max-width | 720px (lg), 760px (xl), 800px (2xl) | Optimal reading width (50-75 chars) |
| Editor horizontal padding | `px-8 lg:px-12 xl:px-16 2xl:px-20` | Breathing room, matches NoteCanvas |
| Editor vertical padding | `py-4 lg:py-6 2xl:py-8` | Generous top/bottom spacing |
| Document canvas centering | `mx-auto` | Centers content in wide panels |

### Chat Panel Collapsed State

When chat is closed, show `CollapsedChatStrip` (reuse existing component from `components/editor/CollapsedChatStrip.tsx`):

```
┌──────────────────────────────────────────────────────┬────┐
│ Note Editor (100% minus strip)                       │ ▸  │  w-10 strip
│                                                      │ P  │
│                                                      │ i  │
│                                                      │ l  │
│                                                      │ o  │
│                                                      │ t  │
└──────────────────────────────────────────────────────┴────┘
```

### Tablet (md to lg, 768px-1023px)

Full-width editor. Chat panel is a slide-over overlay (reuse `NoteCanvasMobileLayout` pattern).

### Mobile (below md, < 768px)

Full-width editor. Chat panel is a bottom sheet. Property block collapses to single-line mode. Mobile FAB for chat toggle.

---

## 3. Minimal Header

### Design

Strip the header to bare essentials. Match the `InlineNoteHeader` density from note canvas.

```
┌─────────────────────────────────────────────────────────────┐
│  ←  │  PS-42  Bug  [AI]  │           Saved ✓  │  💬  ···   │
└─────────────────────────────────────────────────────────────┘
```

### Structure

```
<header class="flex items-center h-12 px-4 border-b border-border bg-background">
  <!-- Left cluster -->
  <div class="flex items-center gap-2">
    <BackButton />                        <!-- ghost icon-sm, ArrowLeft -->
    <span class="text-sm font-medium text-muted-foreground font-mono">
      PS-42
    </span>
    <IssueTypeBadge type="bug" />         <!-- badge variant="secondary" -->
    {aiGenerated && <AIBadge />}          <!-- badge variant="ai" -->
  </div>

  <!-- Spacer -->
  <div class="flex-1" />

  <!-- Right cluster -->
  <div class="flex items-center gap-1.5">
    <SaveStatus status={aggregateSaveStatus} />
    <ChatToggleButton />                  <!-- ghost icon-sm, MessageSquare, ai color -->
    <MoreMenu />                          <!-- ghost icon-sm, MoreHorizontal -->
  </div>
</header>
```

### Component: `IssueNoteHeader`

| Prop | Type | Description |
|------|------|-------------|
| `identifier` | `string` | Issue identifier (e.g., "PS-42") |
| `issueType` | `'bug' \| 'feature' \| 'improvement' \| 'task'` | Issue type for badge |
| `aiGenerated` | `boolean` | Show AI badge |
| `saveStatus` | `SaveStatusType` | Aggregate save status |
| `isChatOpen` | `boolean` | Chat panel open state |
| `onBack` | `() => void` | Navigate back |
| `onToggleChat` | `() => void` | Toggle chat panel |
| `onCopyLink` | `() => void` | Copy issue URL |
| `onDelete` | `() => void` | Open delete confirmation |

### Reused Components

- `SaveStatus` from `@/components/ui/save-status`
- `Badge` from `@/components/ui/badge`
- `Button` from `@/components/ui/button`
- `DropdownMenu` from `@/components/ui/dropdown-menu`

### Chat Toggle Button Spec

```tsx
<Button
  variant="ghost"
  size="icon-sm"
  onClick={onToggleChat}
  className={cn(
    isChatOpen && 'bg-ai-muted text-ai'
  )}
  aria-label={isChatOpen ? 'Close AI chat' : 'Open AI chat'}
  aria-pressed={isChatOpen}
>
  <MessageSquare className="size-4" />
</Button>
```

---

## 4. Property Block Node

### Concept

A custom TipTap NodeView rendered as the first node in the document. It is **non-deletable** (ProseMirror schema constraint), always at document position 0, and shows all issue properties in a compact grid.

### Visual Design -- Expanded State (default)

```
┌─────────────────────────────────────────────────────────────┐
│  ● In Progress    ▲▲▲ High    @Tin Dang    Sprint 3        │
│  Feb 28           [frontend] [ux]           ⊕ Add label     │
│  ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── │
│  Start: Feb 15    Due: Feb 28    Effort: 5 pts    ☰        │
└─────────────────────────────────────────────────────────────┘
```

### Visual Design -- Collapsed State

```
┌─────────────────────────────────────────────────────────────┐
│  ● In Progress  ▲▲▲ High  @Tin  Sprint 3  Feb 28  [2] ▾   │
└─────────────────────────────────────────────────────────────┘
```

### Layout Grid

The expanded property block uses a CSS Grid layout:

```
Row 1:  [State]  [Priority]  [Assignee]  [Cycle]        -- 4 columns, equal flex
Row 2:  [Due date]  [Labels ...]  [+ Add label]         -- labels wrap
Row 3:  [Start]  [Due]  [Effort]  [Collapse toggle]     -- supplementary row
```

### Styling

| Property | Value |
|----------|-------|
| Background | `bg-[#F8F6F3]` (warm surface, slightly darker than `--background-subtle`) |
| Border | `border border-[#E5E2DD]` (matches `--border`) |
| Border radius | `rounded-[12px]` (card-level squircle) |
| Padding | `px-4 py-3` (16px / 12px) |
| Inner gap | `gap-x-4 gap-y-2` (16px horizontal, 8px vertical) |
| Margin bottom | `mb-4` (16px space before title) |
| Transition | `motion-safe:transition-all duration-200` for collapse |

### Property Chips

Each property is rendered as a clickable chip that opens an inline dropdown:

```
┌──────────────────┐
│ ● In Progress  ▾ │   <-- state chip
└──────────────────┘
```

| Chip State | Style |
|------------|-------|
| Default | `bg-transparent text-sm text-foreground cursor-pointer rounded-[8px] px-2 py-1` |
| Hover | `bg-muted/50` |
| Active/Editing | `bg-background ring-1 ring-primary/30 shadow-sm` |
| Empty | `text-muted-foreground italic` ("Not set") |

### Inline Dropdowns

When a chip is clicked, it opens a popover (using Radix `Popover`) anchored to the chip. Reuse existing selector components:

| Property | Selector Component | Notes |
|----------|--------------------|-------|
| State | `IssueStateSelect` | Already exists in `@/components/issues` |
| Priority | `IssuePrioritySelect` | Already exists |
| Assignee | `AssigneeSelector` | Already exists |
| Cycle | `CycleSelector` | Already exists |
| Labels | `LabelSelector` | Already exists, multi-select |
| Due date | `Calendar` popover | Already exists in `IssuePropertiesPanel` |
| Start date | `Calendar` popover | Already exists |
| Effort | `EffortField` | Already exists |

### Collapse/Expand Toggle

- Bottom-right of the expanded block: a ghost button with `ChevronUp` icon
- Collapsed state shows single-line summary: `[State] [Priority] [Assignee] [Cycle] [Due] [label count] [ChevronDown]`
- Toggle persisted in `localStorage` keyed by `issue-property-block-collapsed`
- Keyboard: `Ctrl+Shift+P` toggles collapse

### TipTap Node Configuration

```typescript
// PropertyBlockNode -- custom TipTap Node extension
{
  name: 'propertyBlock',
  group: 'block',
  atom: true,         // non-editable text content
  draggable: false,
  selectable: true,
  isolating: true,     // prevents deletion via backspace
  defining: true,      // required at position 0

  addAttributes() {
    return {
      issueId: { default: null },
      collapsed: { default: false },
    };
  },

  // Rendered via ReactNodeViewRenderer
  addNodeView() {
    return ReactNodeViewRenderer(PropertyBlockView);
  },

  // Schema: exactly one at position 0, cannot be deleted
  // Enforced via appendTransaction plugin
}
```

### Data Flow

The PropertyBlockView receives issue data via React context (not TipTap attributes) to avoid serialization overhead:

```
IssueDetailPage (observer)
  └─ IssueNoteContext.Provider value={{ issue, onUpdate, members, labels, cycles }}
       └─ TipTap Editor
            └─ PropertyBlockView (reads from IssueNoteContext)
```

### States

| State | Behavior |
|-------|----------|
| Loading | Skeleton pulse: 3 rows of rounded rectangles at property block dimensions |
| Editing (dropdown open) | Active chip highlighted; popover open; clicking outside closes |
| Saving | Per-field `FieldSaveIndicator` dot appears next to the changed chip |
| Error | Red dot + tooltip on the chip that failed to save |
| Read-only | All chips show as static text, no hover state, no cursor pointer |
| Collapsed | Single-line summary with label count badge |

---

## 5. Issue Title

### Design

A seamless H1 heading directly after the property block. No border, no container -- just text.

```
# Redesign the issue detail page for note-first experience
```

### Styling

| Property | Value |
|----------|-------|
| Element | `<h1>` |
| Font size | `text-2xl` (24px) |
| Font weight | `font-semibold` (600) |
| Line height | 32px |
| Color | `text-foreground` (#171717) |
| Margin top | `mt-2` (8px, tight coupling to property block) |
| Margin bottom | `mb-4` (16px, generous space before body) |
| Placeholder | `text-muted-foreground/50` "Issue title..." |
| Editing | `contenteditable`, no border, focus ring on container only |

### Reuse

Refactor existing `IssueTitle` component (`features/issues/components/issue-title.tsx`) to work in this context. It already handles inline editing with debounced save.

---

## 6. Note Editor Body

### Extension Set

The issue note editor uses the **full note canvas extension set** (same as `NoteCanvasEditor.tsx`), not the limited `createIssueEditorExtensions()` set currently used.

Full extensions to enable:

| Extension | Purpose |
|-----------|---------|
| StarterKit | Basic formatting (bold, italic, lists, etc.) |
| Placeholder | "Start writing..." placeholder |
| Typography | Smart quotes, em dashes |
| TaskList + TaskItem | Checkbox lists (acceptance criteria) |
| CodeBlock (lowlight) | Syntax-highlighted code blocks |
| Table | Tabular data |
| Image | Embedded images |
| Link | Hyperlinks |
| Highlight | Text highlighting |
| Underline | Underline formatting |
| TextAlign | Text alignment |
| Markdown | Markdown input/output |
| SlashCommand | `/` trigger for block insertion menu |
| GhostText | AI inline completions (500ms trigger) |
| MarginAnnotation | AI margin annotations |
| NoteLink | `[[note-name]]` cross-linking |
| InlineIssue | `[PS-42]` inline issue references |
| PMBlock | ProseMirror block-level elements |
| MentionUser | `@user` mentions |

### Editor Content Area

The description field currently in `IssueDescriptionEditor` is replaced by this full editor. The editor content maps to `issue.descriptionHtml` and `issue.description` (markdown) fields.

### Auto-save

- 2-second debounce (unchanged from current)
- Save triggers: content change, blur, `Cmd+S`
- Visual feedback: `SaveStatus` in the header

### Sections Below Editor

After the note editor content, two persistent sections appear in the scrollable area (not inside the TipTap editor):

1. **Sub-issues** (always visible)
2. **Activity** (collapsible, default open)

These are rendered outside the editor but within the same scroll container.

---

## 7. Sub-issues Section

### Design

A section divider + the existing `SubIssuesList` component:

```
─────────────── Sub-issues (3) ───────────────
[progress bar: 1/3 completed]
┌──────────────────────────────────────────┐
│ PS-43  Set up new layout components  ● Todo         @Alex │
│ PS-44  Implement property block node ● In Progress  @Tin  │
│ PS-45  Write unit tests              ✓ Done         @Mai  │
└──────────────────────────────────────────┘
[+ Add sub-issue]
```

### Section Divider Component

```tsx
<div className="flex items-center gap-3 pt-8 pb-4">
  <div className="h-px flex-1 bg-border" />
  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
    Sub-issues
    {count > 0 && (
      <span className="ml-1.5 tabular-nums">({count})</span>
    )}
  </span>
  <div className="h-px flex-1 bg-border" />
</div>
```

### Reuse

`SubIssuesList` from `features/issues/components/sub-issues-list.tsx` -- no changes needed.

---

## 8. Activity Section

### Design

Collapsible section below sub-issues. Uses existing `CollapsibleSection` + `ActivityTimeline`.

```
▶ Activity (12)
  ┌─────────────────────────────────────────┐
  │ @Tin changed state to In Progress  2h   │
  │ @AI enhanced description            1h   │
  │ @Mai commented: "Looks good"       30m   │
  │ ...                                      │
  ├─────────────────────────────────────────┤
  │ [Comment input]                    Send  │
  └─────────────────────────────────────────┘
```

### Reuse

- `CollapsibleSection` from `features/issues/components/collapsible-section.tsx`
- `ActivityTimeline` from `features/issues/components/activity-timeline.tsx`
- Both unchanged.

---

## 9. AI Chat Panel

### Design

Identical to the note canvas ChatView integration. Reuse `ChatView` from `features/ai/ChatView/ChatView.tsx` with issue-specific context.

### Context Binding

When the chat panel opens on an issue detail page, the `PilotSpaceStore` is configured with:

```typescript
store.setIssueContext({
  issueId: issue.id,
  projectId: issue.project?.id ?? '',
  issueTitle: issue.name,
  issueIdentifier: issue.identifier,
});
```

### Issue-Specific Slash Commands

The `/` menu in `ChatInput` already shows skills from the `SKILLS` constant. Issue-specific skills are already defined:

| Skill | Command | Description |
|-------|---------|-------------|
| Enhance Issue | `/enhance` | Improve description, add details |
| Decompose Tasks | `/decompose` | Break into sub-issues |
| Find Duplicates | `/find-duplicates` | Search for similar issues |
| Recommend Assignee | `/assign` | Suggest best assignee |
| Generate Context | `/generate-context` | Build AI context for coding |
| Review Spec | `/review-spec` | Review acceptance criteria |
| Suggest Labels | `/suggest-labels` | Auto-label based on content |

No new components needed. The `SkillMenu` already renders these.

### Panel Integration

```tsx
// In IssueDetailPage layout:
{isChatOpen ? (
  <ResizablePanelGroup orientation="horizontal" id="issue-editor-layout">
    <ResizablePanel id="editor-panel" defaultSize="62%" minSize="50%">
      {editorContent}
    </ResizablePanel>
    <ResizableHandle withHandle toggleState={chatPanelState} onToggle={handleChatPanelToggle} />
    <ResizablePanel id="chat-panel" defaultSize="38%" minSize="30%" maxSize="50%">
      <motion.aside
        aria-label="AI Chat Assistant"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="h-full w-full overflow-hidden border-l border-border"
      >
        <ChatView store={aiStore.pilotSpace} autoFocus onClose={() => setIsChatOpen(false)} />
      </motion.aside>
    </ResizablePanel>
  </ResizablePanelGroup>
) : (
  <>
    <div className="flex-1 min-w-0">{editorContent}</div>
    <CollapsedChatStrip onClick={() => setIsChatOpen(true)} />
  </>
)}
```

### Suggested Prompts (Empty State)

When the chat has no history for this issue, show issue-specific suggested prompts:

```typescript
const ISSUE_SUGGESTED_PROMPTS = [
  'Enhance this issue description',
  'Break this into sub-tasks',
  'Find duplicate issues',
  'Generate AI context for coding',
  'Review the acceptance criteria',
] as const;
```

Pass as `suggestedPrompts` prop to `ChatView`.

---

## 10. Mobile Responsive Design

### Breakpoint Behavior

| Breakpoint | Layout |
|------------|--------|
| `2xl` (>= 1536px) | Editor 62% / Chat 38%, max-w-[800px] content, `px-20 py-8` |
| `xl` (>= 1280px) | Editor 62% / Chat 38%, max-w-[760px] content, `px-16 py-6` |
| `lg` (>= 1024px) | Editor 62% / Chat 38%, max-w-[720px] content, `px-12 py-6` |
| `md` (>= 768px) | Full-width editor, chat slide-over overlay, `px-8 py-4` |
| `sm` (>= 640px) | Full-width editor, chat bottom sheet, `px-6 py-3` |
| `< 640px` | Full-width editor, chat bottom sheet, `px-4 py-3` |

### Property Block -- Mobile Adaptations

| Breakpoint | Property Block Behavior |
|------------|------------------------|
| `lg+` | Full expanded grid: 4 columns |
| `md` | 2-column grid: State+Priority row, Assignee+Cycle row, Labels row |
| `< md` | Auto-collapsed to single-line summary; tap to expand as bottom sheet |

### Mobile Chat Panel

Reuse `NoteCanvasMobileLayout` pattern:

```tsx
// Mobile: slide-over chat panel (same as note canvas)
<NoteCanvasMobileLayout
  editorContent={editorContent}
  chatViewContent={chatViewContent}
  isChatViewOpen={isChatOpen}
  onClose={() => setIsChatOpen(false)}
  onOpen={() => setIsChatOpen(true)}
/>
```

### Mobile Property Sheet

On mobile (< md), tapping the collapsed property line opens a `Sheet` (bottom drawer) with the full `IssuePropertiesPanel`:

```tsx
<Sheet open={mobilePropertiesOpen} onOpenChange={setMobilePropertiesOpen}>
  <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
    <SheetHeader>
      <SheetTitle>Properties</SheetTitle>
    </SheetHeader>
    <IssuePropertiesPanel ... />
  </SheetContent>
</Sheet>
```

### Mobile FAB

A floating action button for chat (bottom-right, above safe area):

```tsx
<div className="fixed bottom-6 right-6 z-40 md:hidden lg:hidden">
  <Button
    size="icon"
    className="size-12 rounded-full shadow-lg bg-ai text-white"
    onClick={() => setIsChatOpen(true)}
    aria-label="Open AI chat"
  >
    <MessageSquare className="size-5" />
  </Button>
</div>
```

---

## 11. Interaction Patterns

### Property Editing Flow

1. User clicks a property chip in the property block
2. Popover opens anchored to the chip (Radix Popover, `align="start"`)
3. User selects new value
4. Popover closes
5. Optimistic update: chip immediately shows new value
6. Background mutation fires with `wrapMutation` for save status
7. `FieldSaveIndicator` dot appears during save, then fades

### Title Editing Flow

1. User clicks the H1 title
2. Cursor appears (already editable, `contenteditable`)
3. On blur or 2s debounce, title saves
4. `SaveStatus` in header reflects save state

### Description Editing Flow

1. User clicks anywhere in the editor body
2. Cursor appears, full TipTap toolbar available
3. Ghost text triggers after 500ms pause
4. Slash commands available via `/`
5. Auto-save at 2s debounce
6. `Cmd+S` forces immediate save

### Chat Panel Toggle

1. User clicks chat icon in header OR presses `Cmd+Shift+P`
2. Panel slides in from right (200ms ease-in-out)
3. Chat input auto-focuses
4. Existing session auto-resumes if available for this issue context
5. Clicking chat icon again or pressing `Cmd+Shift+P` collapses panel
6. Collapsed strip appears on right edge

### Delete Flow

Unchanged from v1 spec: `MoreMenu` > "Delete issue" > `DeleteConfirmDialog` (AlertDialog).

---

## 12. Keyboard Shortcuts

| Shortcut | Action | Scope |
|----------|--------|-------|
| `Cmd+Shift+P` / `Ctrl+Shift+P` | Toggle AI chat panel | Page-level |
| `Cmd+S` / `Ctrl+S` | Force save all fields | Page-level |
| `Cmd+Shift+.` / `Ctrl+Shift+.` | Toggle property block collapse | Page-level |
| `Escape` | Close active popover/dropdown; then close chat panel | Contextual |
| `Tab` | Accept ghost text suggestion | Editor-level |
| `/` | Open slash command menu | Editor-level |
| `[[` | Open note link search | Editor-level |
| `@` | Open mention menu | Editor-level |

### Implementation

Extend `useIssueKeyboardShortcuts` hook to add the new shortcuts:

```typescript
useIssueKeyboardShortcuts({
  onForceSave: handleForceSave,
  onToggleChat: handleToggleChat,          // NEW
  onTogglePropertyBlock: handleTogglePropertyBlock,  // NEW
});
```

---

## 13. Transitions and Animation

All transitions follow the existing motion system from `ui-design-spec.md`.

| Element | Trigger | Duration | Easing | Property |
|---------|---------|----------|--------|----------|
| Chat panel open/close | Toggle | 200ms | ease-in-out | opacity |
| Property block collapse | Toggle | 200ms | ease-in-out | height, opacity |
| Property chip hover | Pointer enter | 100ms | ease | background-color |
| Property dropdown open | Click | 150ms | ease-out | opacity, transform (scale) |
| Save status indicator | Save start/end | 150ms | ease | opacity |
| Section divider | Scroll into view | -- | -- | No animation (static) |
| Collapsed chat strip | Chat close | 150ms | ease-out | opacity |

### Reduced Motion

All animations gated behind `motion-safe:` prefix or `useReducedMotion()` check. When reduced motion is preferred:
- Chat panel: instant show/hide (opacity only, 0ms)
- Property block: instant collapse (no height animation)
- All others: instant transitions

---

## 14. Design Tokens Reference

All tokens from the existing Pilot Space design system. No new tokens introduced.

### Colors Used

```css
--background:          #FDFCFA;     /* page background */
--background-subtle:   #F7F5F2;     /* property block bg fallback */
--foreground:          #171717;     /* primary text */
--foreground-muted:    #737373;     /* secondary text */
--border:              #E5E2DD;     /* borders */
--border-subtle:       #EBE8E4;     /* subtle borders */
--primary:             #29A386;     /* teal-green actions */
--primary-hover:       #238F74;     /* teal-green hover */
--primary-muted:       #29A38615;   /* teal-green subtle bg */
--ai:                  #6B8FAD;     /* dusty blue AI elements */
--ai-muted:            #6B8FAD15;   /* AI background */
--ai-border:           #6B8FAD30;   /* AI border */

/* Property block warm surface (custom, derived from palette) */
--property-block-bg:   #F8F6F3;     /* between --background and --background-subtle */
```

### Typography

```css
--font-family-primary: 'Geist', system-ui, -apple-system, sans-serif;
--font-family-mono:    'Geist Mono', 'SF Mono', Monaco, monospace;
```

| Usage | Size | Weight | Class |
|-------|------|--------|-------|
| Property chip text | 13px | 400 | `text-sm` |
| Property chip label | 11px | 500 | `text-xs font-medium` |
| Issue title (H1) | 24px | 600 | `text-2xl font-semibold` |
| Editor body | 15px | 400 | `text-base` (prose) |
| Section divider label | 11px | 600 | `text-xs font-semibold uppercase tracking-wider` |
| Header identifier | 13px | 500 | `text-sm font-medium font-mono` |

### Spacing

4px grid. Key values:

```css
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-6:  24px;
--space-8:  32px;
```

### Border Radius

```css
--radius-sm:  6px;   /* badges, chips */
--radius:     10px;  /* buttons, inputs */
--radius-lg:  14px;  /* cards */
--radius-xl:  18px;  /* modals */
```

Property block: `rounded-[12px]` (between card and button).

---

## 15. Component Hierarchy

### New Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| `IssueNoteHeader` | `features/issues/components/issue-note-header.tsx` | Minimal header with back, identifier, save status, chat toggle |
| `PropertyBlockView` | `features/issues/components/property-block-view.tsx` | TipTap NodeView for inline properties |
| `PropertyBlockNode` | `features/issues/editor/property-block-extension.ts` | TipTap Node extension definition |
| `PropertyChip` | `features/issues/components/property-chip.tsx` | Clickable chip for a single property |
| `PropertyBlockCollapsed` | `features/issues/components/property-block-collapsed.tsx` | Single-line collapsed summary |
| `IssueNoteContext` | `features/issues/contexts/issue-note-context.ts` | React context for passing issue data to NodeView |
| `IssueNoteLayout` | `features/issues/components/issue-note-layout.tsx` | Resizable panel layout (editor + chat) |
| `IssueSectionDivider` | `features/issues/components/issue-section-divider.tsx` | Centered divider with label |

### Modified Components

| Component | Change |
|-----------|--------|
| `IssueDetailPage` (page.tsx) | Full rewrite: replace tab layout with note canvas layout |
| `useIssueKeyboardShortcuts` | Add chat toggle and property block toggle shortcuts |

### Reused Components (unchanged)

| Component | Source |
|-----------|--------|
| `ChatView` | `features/ai/ChatView/ChatView.tsx` |
| `CollapsedChatStrip` | `components/editor/CollapsedChatStrip.tsx` |
| `NoteCanvasMobileLayout` | `components/editor/NoteCanvasMobileLayout.tsx` |
| `SubIssuesList` | `features/issues/components/sub-issues-list.tsx` |
| `ActivityTimeline` | `features/issues/components/activity-timeline.tsx` |
| `CollapsibleSection` | `features/issues/components/collapsible-section.tsx` |
| `IssueTitle` | `features/issues/components/issue-title.tsx` |
| `IssueStateSelect` | `@/components/issues` |
| `IssuePrioritySelect` | `@/components/issues` |
| `AssigneeSelector` | `@/components/issues` |
| `CycleSelector` | `@/components/issues` |
| `LabelSelector` | `@/components/issues` |
| `EffortField` | `features/issues/components/effort-field.tsx` |
| `FieldSaveIndicator` | `features/issues/components/field-save-indicator.tsx` |
| `SaveStatus` | `@/components/ui/save-status` |
| `DeleteConfirmDialog` | `@/components/issues/DeleteConfirmDialog` |
| `ResizablePanelGroup/Panel/Handle` | `@/components/ui/resizable` |
| `SelectionToolbar` | `components/editor/SelectionToolbar.tsx` |

### Deprecated Components (to be removed after migration)

| Component | Reason |
|-----------|--------|
| `IssueHeader` | Replaced by `IssueNoteHeader` |
| `IssueDescriptionEditor` | Replaced by full TipTap editor in note layout |
| `IssuePropertiesPanel` | Replaced by inline `PropertyBlockView` (kept for mobile Sheet fallback) |
| `ai-panel-with-chat.tsx` | Redundant; ChatView used directly |

---

## 16. Accessibility

### WCAG 2.2 AA Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Color contrast** | All text meets 4.5:1 ratio. Property chip text (#171717 on #F8F6F3) = 11.2:1. Muted text (#737373 on #FDFCFA) = 4.8:1. |
| **Touch targets** | All clickable chips: min 44x44px touch target (achieved via `min-h-[44px]` on mobile, `min-h-[36px] py-1` on desktop with 44px tap area via padding). |
| **Focus management** | Property chips: `focus-visible:ring-2 focus-visible:ring-ring`. Editor: standard TipTap focus. Chat input: auto-focus on panel open. |
| **Focus order** | Header > Property block (L-to-R, T-to-B) > Title > Editor > Sub-issues > Activity > Chat (when open) |
| **Screen reader** | Property block: `role="region" aria-label="Issue properties"`. Each chip: `aria-label="Priority: High"` + `aria-haspopup="listbox"`. Chat panel: `aria-label="AI Chat Assistant"`. |
| **Keyboard nav** | Arrow keys navigate between property chips. Enter/Space opens dropdown. Escape closes. Tab moves to next section. |
| **Reduced motion** | All animations gated. See section 13. |
| **Text resize** | Layout uses rem/em units. Content reflows at 200% zoom. Property block wraps to 2-column at narrow widths. |

### Landmarks

```html
<header> <!-- IssueNoteHeader -->
<main>
  <section aria-label="Issue properties"> <!-- PropertyBlockView -->
  <section aria-label="Issue content">    <!-- TipTap editor -->
  <section aria-label="Sub-issues">       <!-- SubIssuesList -->
  <section aria-label="Activity">         <!-- ActivityTimeline -->
</main>
<aside aria-label="AI Chat Assistant">    <!-- ChatView panel -->
```

### Property Block Keyboard Navigation

Within the property block, chips are navigable via arrow keys:

```
[State] → [Priority] → [Assignee] → [Cycle]     (Row 1)
   ↓                                    ↓
[Due]   → [Labels]   → [+ Add]   → [Effort]      (Row 2)
```

Implementation: `role="toolbar"` on the property block container, `roving tabindex` pattern on chips.

---

## 17. ASCII Wireframes

### Desktop -- Chat Open, Property Block Expanded

```
┌─────────────────────────────────────────────────────────────────────┐
│  ←  PS-42  [Bug] [AI]                    Saved ✓  💬(on)  ···     │
├─────────────────────────────────────────┬───────────────────────────┤
│                                         │                           │
│    ┌─ Property Block ────────────────┐  │  PilotSpace Agent    [x]  │
│    │ ● In Progress  ▲▲▲ High        │  │  ─────────────────────── │
│    │ @Tin Dang      Sprint 3        │  │                           │
│    │ Feb 28   [frontend] [ux]       │  │  You: Enhance this issue  │
│    │ Start: Feb 15  Due: Feb 28     │  │                           │
│    │ Effort: 5 pts            [▲]   │  │  AI: I'll improve the     │
│    └─────────────────────────────────┘  │  description with more    │
│                                         │  context and acceptance   │
│    # Redesign issue detail page         │  criteria...              │
│                                         │                           │
│    The current issue detail page        │                           │
│    uses a traditional form layout       │                           │
│    that breaks the note-first           │                           │
│    paradigm. We need to...              │                           │
│                                         │                           │
│    ## Acceptance Criteria               │                           │
│    - [ ] Property block inline          │                           │
│    - [ ] Full TipTap editor             │                           │
│    - [x] AI chat panel                  │                           │
│                                         │                           │
│    ## Technical Requirements            │                           │
│    - Custom TipTap NodeView             │                           │
│    - ResizablePanel layout              │                           │
│                                         │  ─────────────────────── │
│    ─────── Sub-issues (3) ──────────    │                           │
│    [======----] 1/3 completed           │  ┌───────────────────┐   │
│    ┌─────────────────────────────────┐  │  │ /enhance          │   │
│    │ PS-43  Layout components  ●Todo │  │  │ Ask PilotSpace... │   │
│    │ PS-44  Property block   ●InProg │  │  └───────────────────┘   │
│    │ PS-45  Unit tests       ✓ Done  │  │                           │
│    └─────────────────────────────────┘  │                           │
│    [+ Add sub-issue]                    │                           │
│                                         │                           │
│    ▶ Activity (12)                      │                           │
│      @Tin changed state       2h ago    │                           │
│      @AI enhanced desc        1h ago    │                           │
│      [Comment input]          [Send]    │                           │
│                                         │                           │
└─────────────────────────────────────────┴───────────────────────────┘
```

### Desktop -- Chat Closed, Property Block Collapsed

```
┌─────────────────────────────────────────────────────────────────┬────┐
│  ←  PS-42  [Bug] [AI]                     Saved ✓  💬(off) ··· │ ▸  │
├─────────────────────────────────────────────────────────────────│ P  │
│                                                                 │ i  │
│    ┌─ Property Block (collapsed) ────────────────────────────┐  │ l  │
│    │ ● In Progress  ▲▲▲ High  @Tin  Sprint 3  Feb 28  [2] ▾ │  │ o  │
│    └─────────────────────────────────────────────────────────┘  │ t  │
│                                                                 │    │
│    # Redesign issue detail page                                 │ S  │
│                                                                 │ p  │
│    The current issue detail page uses a traditional form        │ a  │
│    layout that breaks the note-first paradigm...                │ c  │
│                                                                 │ e  │
│    ...                                                          │    │
│                                                                 │    │
└─────────────────────────────────────────────────────────────────┴────┘
```

### Mobile (< 768px) -- Property Block Collapsed

```
┌──────────────────────────────────┐
│  ←  PS-42 [Bug]    Saved ✓  ··· │
├──────────────────────────────────┤
│                                  │
│  ● InProg ▲▲▲ @Tin Sprint3 ▾    │  <-- tap to open Sheet
│                                  │
│  # Redesign issue detail page    │
│                                  │
│  The current issue detail page   │
│  uses a traditional form layout  │
│  that breaks the note-first...   │
│                                  │
│  ## Acceptance Criteria          │
│  - [ ] Property block inline     │
│  - [x] AI chat panel             │
│                                  │
│  ────── Sub-issues (3) ──────    │
│  [======----] 1/3                │
│  PS-43  Layout components  ●Todo │
│  PS-44  Property block   ●InProg │
│  PS-45  Unit tests       ✓Done   │
│  [+ Add sub-issue]               │
│                                  │
│  ▶ Activity (12)                 │
│                                  │
│                            [💬]  │  <-- FAB for AI chat
│                                  │
└──────────────────────────────────┘
```

### Mobile -- Properties Sheet Open

```
┌──────────────────────────────────┐
│  (dimmed editor behind)          │
│                                  │
│                                  │
├──────────────────────────────────┤  <-- bottom sheet
│  ──── Properties ────      [x]   │
│                                  │
│  State      [● In Progress  ▾]  │
│  Priority   [▲▲▲ High      ▾]  │
│  Assignee   [@Tin Dang      ▾]  │
│  Labels     [frontend] [ux]     │
│  Cycle      [Sprint 3       ▾]  │
│  Effort     [5 pts]             │
│  ────────────────────────────── │
│  Start date [Feb 15]            │
│  Due date   [Feb 28]            │
│  ────────────────────────────── │
│  Reporter   Tin Dang            │
│  Created    Feb 15, 2026        │
└──────────────────────────────────┘
```

---

## 18. Implementation Checklist

### Phase 1: Foundation (estimated: 3-4 days)

- [ ] P1-1: Create `IssueNoteContext` (React context for issue data)
- [ ] P1-2: Create `PropertyBlockNode` TipTap extension (`property-block-extension.ts`)
- [ ] P1-3: Create `PropertyChip` component with hover/active/editing states
- [ ] P1-4: Create `PropertyBlockView` TipTap NodeView (expanded + collapsed)
- [ ] P1-5: Create `PropertyBlockCollapsed` single-line summary variant
- [ ] P1-6: Write unit tests for PropertyBlockView (all states: loading, editing, saving, error, read-only, collapsed)
- [ ] P1-7: Write unit tests for PropertyChip (click, keyboard nav, dropdown open/close)

### Phase 2: Layout (estimated: 2-3 days)

- [ ] P2-1: Create `IssueNoteHeader` component
- [ ] P2-2: Create `IssueNoteLayout` with ResizablePanelGroup
- [ ] P2-3: Create `IssueSectionDivider` component
- [ ] P2-4: Integrate ChatView with issue context binding
- [ ] P2-5: Integrate CollapsedChatStrip for closed state
- [ ] P2-6: Wire mobile layout (NoteCanvasMobileLayout reuse)
- [ ] P2-7: Wire mobile property Sheet fallback
- [ ] P2-8: Write unit tests for IssueNoteHeader
- [ ] P2-9: Write responsive layout test (breakpoint assertions)

### Phase 3: Editor Integration (estimated: 2-3 days)

- [ ] P3-1: Create full TipTap extension set for issue editor (reuse note canvas extensions)
- [ ] P3-2: Wire PropertyBlockNode as mandatory first node (appendTransaction enforcement)
- [ ] P3-3: Refactor IssueTitle for seamless H1 in new layout
- [ ] P3-4: Wire auto-save (2s debounce) for description content
- [ ] P3-5: Wire ghost text and slash commands in issue editor
- [ ] P3-6: Add sub-issues section below editor with IssueSectionDivider
- [ ] P3-7: Add collapsible Activity section below sub-issues
- [ ] P3-8: Write integration test: property block + editor + save cycle

### Phase 4: Keyboard & Polish (estimated: 1-2 days)

- [ ] P4-1: Extend `useIssueKeyboardShortcuts` with chat toggle and property collapse
- [ ] P4-2: Implement property block keyboard navigation (roving tabindex)
- [ ] P4-3: Add suggested prompts for issue context in ChatView
- [ ] P4-4: Verify all transitions respect `prefers-reduced-motion`
- [ ] P4-5: Accessibility audit (focus order, ARIA labels, contrast)
- [ ] P4-6: Remove deprecated components (IssueHeader, IssueDescriptionEditor wrapper)

### Quality Gates

After each phase:
- [ ] `pnpm lint` passes
- [ ] `pnpm type-check` passes
- [ ] `pnpm test` passes with > 80% coverage on new files
- [ ] Manual test on Chrome, Safari, Firefox
- [ ] Manual test at 320px, 768px, 1024px, 1440px, 1920px widths

---

## Appendix A: Migration Path

### Before (current)

```
IssueDetailPage
  ├─ IssueHeader
  ├─ Tabs (Description | AI Context)
  │   ├─ Description tab
  │   │   ├─ IssueTitle
  │   │   ├─ IssueDescriptionEditor (limited TipTap)
  │   │   ├─ TaskProgressWidget
  │   │   ├─ CollapsibleSection (Specification)
  │   │   ├─ SubIssuesList
  │   │   └─ CollapsibleSection (Activity)
  │   └─ AI Context tab
  │       └─ AIContextTab
  └─ IssuePropertiesPanel (right sidebar)
```

### After (note-first)

```
IssueDetailPage
  ├─ IssueNoteContext.Provider
  ├─ IssueNoteHeader
  └─ IssueNoteLayout (ResizablePanelGroup)
      ├─ Editor Panel
      │   ├─ Scrollable Document
      │   │   ├─ PropertyBlockView (TipTap NodeView, position 0)
      │   │   ├─ IssueTitle (H1, position 1)
      │   │   ├─ TipTap EditorContent (full extensions)
      │   │   ├─ IssueSectionDivider ("Sub-issues")
      │   │   ├─ SubIssuesList
      │   │   └─ CollapsibleSection ("Activity")
      │   │       └─ ActivityTimeline
      │   └─ SelectionToolbar (floating)
      └─ Chat Panel
          └─ ChatView (with issue context)
```

### Data Flow Changes

| Before | After |
|--------|-------|
| `IssuePropertiesPanel` receives props directly | `PropertyBlockView` reads from `IssueNoteContext` |
| `IssueDescriptionEditor` uses `createIssueEditorExtensions()` | Full editor uses note canvas extension set + `PropertyBlockNode` |
| AI Context is a separate tab | AI Chat is a persistent side panel |
| Properties sidebar takes 30-35% width | Property block is inline, 0% width overhead |

---

## Appendix B: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PropertyBlockNode deletion by user | Medium | High | `appendTransaction` plugin re-inserts if removed; `isolating: true` in schema |
| TipTap extension conflicts between note and issue | Low | Medium | Issue editor uses same extension set as note; tested in note canvas already |
| Performance with full extension set on issue page | Low | Medium | Lazy-load extensions; profile with React DevTools |
| Mobile property sheet UX regression | Medium | Medium | Keep `IssuePropertiesPanel` as fallback; user-test at 320px |
| Chat context collision (note vs issue) | Low | High | Clear previous context before setting issue context in `PilotSpaceStore` |

---

*End of specification.*
