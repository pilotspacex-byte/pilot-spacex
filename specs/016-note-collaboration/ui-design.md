# UI Design Specification: Feature 016 — Note Collaboration & Density

**Version**: 1.0.0
**Created**: 2026-02-19
**Status**: Draft
**Author**: Designer Agent
**Extends**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 (Section 9 — Note Canvas)
**Target**: `frontend/src/features/notes/editor/extensions/` + Note Canvas UI

---

## Overview

Feature 016 adds three visual systems to the Note Canvas: (1) real-time presence cursors for humans and AI skills (M6a), (2) block-level ownership indicators with edit guards (M6b), and (3) density controls to manage AI content volume (M8).

**Design Principle**: Human content is sovereign. AI content is clearly labeled, collapsible, and dismissable. The canvas never feels overwhelmed.

---

## Component Hierarchy

```
NoteEditor (existing)
├── EditorToolbar (existing)
│   └── DensityControls (NEW — M8)
│       ├── FocusModeToggle
│       └── DensityDropdown
├── TipTap Editor (existing)
│   ├── OwnershipExtension (NEW — M6b)
│   │   ├── OwnershipGutter (left-side indicators)
│   │   └── EditGuardToast (blocked action feedback)
│   ├── PresenceExtension (NEW — M6a)
│   │   ├── PresenceCursor (per-user caret + label)
│   │   └── PresenceSelection (per-user selection highlight)
│   └── DensityExtension (NEW — M8)
│       ├── AIBlockGroupHeader (collapsible group)
│       └── CollapsedBlockSummary (single-line placeholder)
├── PresenceBar (NEW — M6a, above editor)
└── SidebarPanels (existing right margin)
    ├── AnnotationPanel (existing)
    ├── PresencePanel (NEW — M6a)
    └── ConversationPanel (NEW — M8)
```

---

## 1. Presence Cursors (M6a)

Real-time collaborative cursors and selections using Yjs awareness protocol.

### Cursor Display

```
        ┌──────────┐
        │ Sarah K. │     <- name label
        └────┬─────┘
             |           <- 2px cursor line
             |
   The quick | brown fox jumps over the lazy dog
```

### Specifications

| Property | Value |
|----------|-------|
| Cursor Line | 2px width, full line height, user-assigned color |
| Name Label | `text-xs` (11px), `font-medium`, white text on colored background |
| Label Position | Above cursor, left-aligned to cursor position |
| Label Shape | `rounded-sm` (6px), `px-1.5`, `py-0.5` |
| Label Shadow | `shadow-sm` for readability over content |
| Visibility | Fade in 150ms on appear, fade out 300ms on leave |
| Idle Timeout | Label hides after 5s of inactivity, cursor remains (dimmed to 40% opacity) |

### Color Assignment

Users are assigned colors from a predefined palette (up to 8 distinct colors). Colors cycle for additional users.

| Slot | Color | Name |
|------|-------|------|
| 1 | `#E06560` | Coral |
| 2 | `#5B8FC9` | Blue |
| 3 | `#8B7EC8` | Purple |
| 4 | `#D9853F` | Amber |
| 5 | `#29A386` | Teal |
| 6 | `#C4A035` | Gold |
| 7 | `#D96BA0` | Pink |
| 8 | `#6B8FAD` | Slate |

### Selection Highlight

When a remote user selects text, highlight the range with their assigned color at 15% opacity.

| Property | Value |
|----------|-------|
| Background | User color at 15% opacity |
| Border | None (background only) |
| Blend Mode | Normal |
| Z-index | Below local selection |

### AI Skill Presence

AI skills use the same cursor system but with distinct visual treatment (FR-031, FR-032).

```
        ┌──────────────────┐
        │ [cpu] create-spec │     <- skill name with icon
        └────────┬─────────┘
                 ┆                <- dashed cursor line (vs solid for humans)
                 ┆
   The quick brown┆fox jumps over the lazy dog
```

| Property | Value |
|----------|-------|
| Cursor Line | 2px dashed (vs solid for humans), `--ai` color |
| Name Label | `--ai` background, white text, `Cpu` icon (12px) prefix |
| Label Shape | Same as human but with `border` (`--ai-border`, 1px) |
| Appear/Disappear | Fade in < 2s (FR-033), fade out < 5s (FR-033) |
| Activity Indicator | Subtle pulse on label when actively writing |

### Accessibility

- Cursors: `aria-hidden="true"` (decorative, screen readers use collaboration announcements)
- Screen reader announcement: `aria-live="polite"` region announces "{name} joined" / "{name} left"
- Selection highlights: decorative only, `aria-hidden="true"`

---

## 2. Presence Bar

Compact bar above the editor showing all active collaborators.

### Layout

```
+----------------------------------------------------------+
| [avatar] [avatar] [avatar]  +2  |  [cpu] create-spec     |
| Sarah    Mike     You           |  Writing blocks 4-7     |
+----------------------------------------------------------+
```

### Specifications

| Property | Value |
|----------|-------|
| Position | Below note header, above editor content |
| Container | `px-4`, `py-2`, `bg-background-subtle`, `border-b` (`--border`), flex row |
| Human Avatars | 28px circles, stacked with -4px overlap, colored border matching cursor color |
| Overflow | "+N" badge when >5 humans visible |
| AI Section | Separated by vertical divider (`--border`, 1px), `--ai` accent |
| AI Skill Entry | `Cpu` icon (14px) + skill name (`text-xs`, `font-mono`), status text |
| Visibility | Hidden when solo editing (no remote users/skills) |
| Transition | Slide down 200ms when first remote user joins, slide up when last leaves |

### Presence Panel (Sidebar)

Accessible via density controls or sidebar tab. Full list of collaborators.

```
+-------------------------------+
| Collaborators (5)             |
|-------------------------------|
| HUMANS                        |
| [avatar] Sarah K.  Editing    |
| [avatar] Mike R.   Idle 2m    |
| [avatar] You       Active     |
|                               |
| AI SKILLS                     |
| [cpu] create-spec  Running    |
|   Intent: Auth spec           |
|   Blocks 4-7                  |
| [cpu] review-code  Queued     |
+-------------------------------+
```

| Property | Value |
|----------|-------|
| Panel Width | 280px (matches existing annotation panel) |
| Section Headers | `text-xs`, `uppercase`, `tracking-wider`, `--foreground-muted` |
| User Row | 36px height, avatar (24px) + name (`text-sm`) + status (`text-xs`, `--foreground-muted`) |
| AI Row | 36px height + optional 20px sub-row for intent reference |
| Status Colors | Active: `--primary`, Idle: `--foreground-muted`, Running: `--ai` |

### Accessibility

- Presence bar: `role="status"`, `aria-label="{N} collaborators active"`
- Avatar group: `role="group"`, `aria-label="Active collaborators"`
- Panel: `role="complementary"`, `aria-label="Collaborator list"`

---

## 3. Ownership Indicators (M6b)

Visual block-level ownership markers in the left gutter.

### Gutter Display

```
    ┌─ GUTTER ─┐
    │          │
    │  [user]  │  # Authentication Refactor        <- human block
    │  [user]  │                                    <- human block
    │  [user]  │  We need to rethink how users...   <- human block
    │          │
    │  [ai]    │  ## AI Analysis                    <- ai:create-spec
    │  [ai]    │  Based on the requirements...      <- ai:create-spec
    │  [ai]    │  - Consider OAuth PKCE flow        <- ai:create-spec
    │          │
    │  [share] │  ## Decision Log                   <- shared block
    │  [share] │  Both human and AI can edit here   <- shared block
    │          │
```

### Specifications

| Owner Type | Gutter Icon | Gutter Color | Block Style |
|------------|-------------|--------------|-------------|
| `human` | None (clean) | None | Default editor styling, no decoration |
| `ai:{skill}` | `Bot` (12px) | 3px left border, `--ai` | `bg` (`--ai-muted`), `border-l-3` (`--ai`) |
| `shared` | `Users` (12px) | 3px left border, `--primary` at 50% | `bg` (`--primary-muted`), `border-l-3` (`--primary` at 50%) |

### Gutter Specifications

| Property | Value |
|----------|-------|
| Gutter Width | 24px (left of editor content area) |
| Icon Size | 12px, centered in gutter |
| Icon Color | `--foreground-muted` (40% opacity for human, full for AI/shared) |
| Hover | Tooltip with full ownership info: "AI block (create-spec)" or "Shared block" |
| Click | Opens ownership popover (see below) |

### Ownership Popover (on gutter click)

```
+-------------------------------+
| Block Ownership               |
|-------------------------------|
| Owner: AI (create-spec)       |
| Created: 2 min ago            |
| Intent: Auth feature spec     |
|                               |
| [Approve] [Reject] [Convert] |
+-------------------------------+
```

| Property | Value |
|----------|-------|
| Width | 240px |
| Position | Left of gutter, aligned to block |
| Background | `bg-background`, frosted glass effect |
| Border | `--border`, `rounded-lg` (14px) |

| Button | Behavior |
|--------|----------|
| Approve | For AI blocks: accepts content, keeps AI ownership label |
| Reject | For AI blocks: removes block content (with undo toast) |
| Convert to Shared | Changes ownership to "shared", unlocks editing |

### Edit Guard Toast

When a user attempts to edit a protected block (FR-008):

```
+----------------------------------------------------------+
| [lock]  This block is owned by AI (create-spec).          |
|         You can approve, reject, or convert to shared.    |
+----------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Position | Bottom-center of editor, above ChatInput area |
| Duration | 3 seconds, dismissable |
| Style | `rounded-lg`, `bg-foreground`, `text-background` (inverted), `shadow-lg` |
| Icon | Lucide `Lock` (16px) |

### AI Block Visual Treatment

AI-owned blocks have a distinct visual style to clearly separate them from human content:

| Property | Value |
|----------|-------|
| Background | `--ai-muted` (#6B8FAD at 8% opacity) |
| Left Border | 3px solid `--ai` |
| Text Style | Same font/size as human blocks (no italic — readable) |
| Skill Label | Top-right corner of first block in group: `text-xs`, `--ai`, `font-mono` (e.g., "create-spec") |
| Selection | Users can select/copy AI block text but cannot modify |

### Focus Mode (M8)

When Focus Mode is active, all `ai:*` owned blocks are hidden:

| Property | Value |
|----------|-------|
| Hidden Blocks | `display: none` with smooth height collapse (200ms) |
| Placeholder | Single-line summary per AI group: "[N AI blocks hidden]" in `--foreground-muted` |
| Toggle | Appears in toolbar as eye icon toggle |

### Accessibility

- Gutter icons: `role="img"`, `aria-label="Human block"` / `"AI block from {skill}"` / `"Shared block"`
- Edit guard toast: `role="alert"`, `aria-live="assertive"`
- Focus mode: `aria-live="polite"` announcement: "{N} AI blocks hidden" / "All blocks visible"
- Ownership popover: `role="dialog"`, focus trapped

---

## 4. Density Controls (M8)

Toolbar controls for managing AI content density in notes.

### Toolbar Integration

```
[B] [I] [U] [S] | [H1] [H2] | [bullet] [number] | ... | [eye] [layers ▾]
                                                          Focus  Density
```

### Focus Mode Toggle

| Property | Value |
|----------|-------|
| Icon | Lucide `Eye` (active) / `EyeOff` (Focus Mode on) |
| Button | `ghost` variant, `icon-sm` (32px) |
| Tooltip | "Focus Mode: Show only human content" / "Focus Mode: Showing all content" |
| Keyboard Shortcut | `Cmd+Shift+F` (Mac) / `Ctrl+Shift+F` (Windows) |
| Active Indicator | `--primary` dot (4px) below icon when active |

### Density Dropdown

| Property | Value |
|----------|-------|
| Trigger | Lucide `Layers` icon, `ghost` variant, `icon-sm` |
| Dropdown | `rounded-lg`, `shadow-md`, `bg-background`, `border`, 200px width |
| Position | Below trigger, right-aligned |

#### Dropdown Items

```
+-------------------------------+
| Density Controls              |
|-------------------------------|
| [v] Collapse intent blocks    |
| [v] Collapse progress blocks  |
| [ ] Collapse all AI blocks    |
|-------------------------------|
| Sidebar Panels                |
| [>] Versions                  |
| [>] Presence                  |
| [>] Conversations             |
+-------------------------------+
```

| Item | Behavior |
|------|----------|
| Collapse intent blocks | Collapses IntentCard-type blocks to single-line summary (FR-095) |
| Collapse progress blocks | Collapses progress-type blocks to status summary (FR-096) |
| Collapse all AI blocks | Collapses all AI-owned blocks to group summaries |
| Sidebar panels | Opens corresponding sidebar panel (FR-097) |

### AI Block Group Header

When AI blocks are collapsed, a group header replaces them:

```
+----------------------------------------------------------+
| [chevron-right] [bot] create-spec  |  12 blocks  |  Expand|
|  "Feature specification for user authentication flow"    |
+----------------------------------------------------------+
```

### Group Header Specifications

| Property | Value |
|----------|-------|
| Container | `rounded` (10px), `bg-background-subtle`, `border` (`--ai-border`), `px-3`, `py-2` |
| Chevron | 14px, rotates 90deg on expand (200ms transition) |
| Skill Icon | `Bot` (14px), `--ai` color |
| Skill Name | `text-xs`, `font-mono`, `font-medium` |
| Block Count | `text-xs`, `--foreground-muted`, `tabular-nums` |
| Summary | `text-sm`, `--foreground-muted`, single line, truncated |
| Expand Button | `ghost` variant, `text-xs`, "Expand" / "Collapse" text |
| Hover | `bg-background-subtle` darker (interactive card pattern) |

### Expand/Collapse Animation

| Property | Value |
|----------|-------|
| Collapse | Content height animates to 0, 200ms ease-in |
| Expand | Content height animates from 0, 200ms ease-out |
| Group header | Slides into place, 200ms |
| Reduced motion | Instant show/hide (no height animation) |

### Accessibility

- Focus Mode toggle: `aria-pressed="true/false"`, `aria-label="Toggle Focus Mode"`
- Density dropdown: `role="menu"`, items `role="menuitemcheckbox"` with `aria-checked`
- AI group header: `role="button"`, `aria-expanded="true/false"`, `aria-label="AI block group: {summary}"`
- Collapse/expand: `aria-live="polite"` announcement

---

## 5. Templates (FR-063–065)

Four SDLC templates accessible from the "New Note" flow.

### Template Picker

```
+----------------------------------------------------------+
| Create New Note                                          |
|----------------------------------------------------------|
|                                                          |
| [Blank Note]  Start from scratch                         |
|                                                          |
| SDLC TEMPLATES                                           |
| +----------+  +----------+  +----------+  +----------+   |
| | Sprint   |  | Design   |  | Post-    |  | Release  |   |
| | Planning |  | Review   |  | mortem   |  | Planning |   |
| |          |  |          |  |          |  |          |   |
| | [sprint] |  | [pencil] |  | [alert]  |  | [rocket] |  |
| +----------+  +----------+  +----------+  +----------+   |
|                                                          |
| CUSTOM TEMPLATES (admin)                                  |
| +----------+  +----------+                                |
| | My Custom|  | + Create |                                |
| | Template |  | Template |                                |
| +----------+  +----------+                                |
+----------------------------------------------------------+
```

### Template Card Specifications

| Property | Value |
|----------|-------|
| Card Size | 120px x 140px |
| Card Style | `rounded-lg`, `border`, `bg-background`, `shadow-sm`, interactive hover |
| Icon | 32px Lucide icon, centered, `--primary` color |
| Title | `text-sm`, `font-medium`, centered below icon |
| Hover | Scale 1%, elevated shadow (interactive card pattern) |
| Selection | `border-primary`, `ring-2 ring-primary/20` |

### Template Icons

| Template | Icon |
|----------|------|
| Sprint Planning | `LayoutDashboard` |
| Design Review | `PenTool` |
| Postmortem | `AlertTriangle` |
| Release Planning | `Rocket` |
| Custom | `FileText` |
| Create Template | `Plus` |

### Accessibility

- Template grid: `role="radiogroup"`, `aria-label="Note template selection"`
- Template cards: `role="radio"`, `aria-checked`, keyboard arrow navigation
- Template description read by screen reader on focus

---

## Responsive Behavior

### Presence Cursors

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Full cursor labels visible |
| Tablet (768–1279px) | Labels show initials only (e.g., "SK" instead of "Sarah K.") |
| Mobile (<768px) | Cursors visible, labels hidden (avatar dot only at cursor position) |

### Ownership Gutter

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Full 24px gutter with icons |
| Tablet (768–1279px) | 16px gutter, icons only (no tooltips on hover — tap instead) |
| Mobile (<768px) | Gutter hidden, ownership shown via block background color only |

### Density Controls

| Breakpoint | Behavior |
|------------|----------|
| Desktop (>1280px) | Both Focus Mode and Density in toolbar |
| Tablet (768–1279px) | Combined into single density button with dropdown |
| Mobile (<768px) | Moved to note header menu (three-dot) |

---

## Animation & Transitions

| Animation | Duration | Easing | Trigger |
|-----------|----------|--------|---------|
| Cursor appear/move | 150ms | ease-out | Remote user movement |
| Cursor label fade out (idle) | 300ms | ease-in | 5s inactivity |
| Selection highlight | 100ms | ease-out | Remote selection change |
| AI block collapse | 200ms | ease-in | Density control toggle |
| AI block expand | 200ms | ease-out | Density control toggle |
| Presence bar slide | 200ms | ease-out | First/last collaborator |
| Edit guard toast | 200ms in, 200ms out | ease | Blocked edit attempt |
| Ownership popover | 150ms | ease-out | Gutter click |
| Focus Mode transition | 300ms | ease-in-out | All AI blocks simultaneously |

### Reduced Motion

- Cursor movements: instant position changes (no interpolation)
- Collapse/expand: instant show/hide
- Fade transitions: instant opacity changes
- Toast: instant appear, 3s display, instant disappear

---

## Dark Mode

All components use CSS custom properties. Dark mode adjustments:

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| AI block background | `--ai-muted` (8% opacity) | `--ai-muted` (12% opacity for visibility) |
| Cursor label shadow | `shadow-sm` | `shadow-md` (stronger for dark bg contrast) |
| Gutter icon opacity | 40% (human) / 100% (AI) | 50% (human) / 100% (AI) |
| Presence bar bg | `--background-subtle` | `--background-subtle` |
| Edit guard toast | Inverted colors | Inverted colors (auto from variables) |

---

## Implementation Notes

### File Organization

```
features/notes/editor/extensions/
├── OwnershipExtension.ts          (NEW — M6b)
├── PresenceExtension.ts           (NEW — M6a, Yjs awareness)
├── DensityExtension.ts            (NEW — M8)
features/notes/components/
├── PresenceBar.tsx                 (NEW)
├── PresenceCursor.tsx              (NEW)
├── PresencePanel.tsx               (NEW)
├── OwnershipGutter.tsx             (NEW)
├── OwnershipPopover.tsx            (NEW)
├── EditGuardToast.tsx              (NEW)
├── AIBlockGroupHeader.tsx          (NEW)
├── DensityControls.tsx             (NEW)
├── FocusModeToggle.tsx             (NEW)
├── TemplatePicker.tsx              (NEW)
```

### Store Integration

| Component | Store | Observable |
|-----------|-------|-----------|
| PresenceBar | CollabStore (new) | `activeCollaborators`, `aiSkillPresence` |
| PresenceCursor | CollabStore | `cursorPositions` (Map<userId, position>) |
| OwnershipGutter | OwnershipStore (new) | `blockOwnership` (Map<blockId, owner>) |
| DensityControls | DensityStore (new) | `focusMode`, `collapsedGroups`, `sidebarPanel` |
| FocusModeToggle | DensityStore | `focusMode` (boolean) |
| AIBlockGroupHeader | DensityStore | `collapsedGroups` (Set<groupId>) |

### TipTap Extension Integration

- `OwnershipExtension`: ProseMirror plugin that reads `owner` attribute from block nodes, filters transactions that modify protected blocks
- `PresenceExtension`: Wraps `@tiptap/extension-collaboration-cursor` with custom renderer for AI skill presence
- `DensityExtension`: ProseMirror decoration plugin that adds/removes NodeView decorations for collapsed groups

### Dependencies

- `yjs` + `@tiptap/extension-collaboration` + `@tiptap/extension-collaboration-cursor` (M6a)
- `y-supabase` or `y-websocket` (M6a, dependent on Sprint 1a gate result)
- No new backend dependencies for M6b/M8 (frontend-only ownership enforcement)

---

## Detailed Component Specs (T-123, T-124, T-133, T-145)

**Added**: 2026-02-19 | **Author**: Designer Agent
**Context**: Concrete implementation specs for fullstack-2 (T-123, T-124, T-133, T-145)

---

## T-123: PresenceBar Component

Compact bar above the editor showing all active collaborators. Humans as circles, AI skills as squares with teal border.

### Layout Dimensions

```
Full width of editor content area (not including ChatView panel)
Height: 36px (py-2 = 8px + 20px content)
Position: sticky top, below note header, above EditorContent
z-index: 10 (above editor content, below modals)
```

```
+------------------------------------------------------------------------+
| [●S] [●M] [●A]  +2  │  [■] create-spec  Writing 4-7  │  [■] review   |
|  Sarah Mike Alex    |                                  |               |
+------------------------------------------------------------------------+
  <-- human group -->   <-------- AI skill group -------->
```

### Human Avatar Spec

| Property | Value |
|----------|-------|
| Shape | Circle (`rounded-full`) |
| Size | 28px × 28px |
| Border | 2px solid, user-assigned presence color |
| Stack overlap | `-ml-1.5` (−6px) on 2nd+ avatars |
| Max visible | 5 humans (then "+N more" badge) |
| Background | User avatar image; fallback = initials, `bg` = presence color at 20% opacity |
| Initials | `text-[10px]`, `font-medium`, presence color |
| Hover | `scale-110` (110%), `z-10`, shows tooltip: full name + status |
| Tooltip | `text-xs`, "Sarah K. — Editing" / "Mike R. — Idle 2m" |

### AI Skill Avatar Spec

| Property | Value |
|----------|-------|
| Shape | Square with `rounded-sm` (6px) — distinct from human circles |
| Size | 28px × 28px |
| Border | 2px solid `--ai` (`#6B8FAD`) |
| Background | `--ai-muted` (`#6B8FAD15`) |
| Icon | Lucide `Cpu` (14px), `--ai` color, centered |
| Activity pulse | `ring-2 ring-ai/30 animate-pulse` while actively writing |
| Hover | Shows tooltip: skill name + current operation (e.g., "create-spec — Writing blocks 4-7") |
| Max visible | 3 AI skill avatars (then "+N more" badge) |

### Click-to-Scroll Behavior (T-123 requirement)

| Interaction | Behavior |
|-------------|----------|
| Click human avatar | Smooth scroll editor to that user's cursor position; 300ms ease-out |
| Click AI skill avatar | Smooth scroll editor to that skill's active cursor position |
| Click "+N more" badge | Opens PresencePanel sidebar (see Section 2 above) |
| Keyboard: Tab + Enter | Same as click — navigable via keyboard |

Click-to-scroll implementation note: read `cursorPositions` from CollabStore, use `editor.commands.scrollIntoView()` after setting selection to the user's cursor anchor position.

### Overflow Badge ("+N more")

| Property | Value |
|----------|-------|
| Shape | `rounded-full` |
| Size | 28px × 28px |
| Background | `--background-subtle` |
| Border | `--border` |
| Text | `text-[10px]`, `font-medium`, `--foreground-muted`, e.g., "+2" |
| Click | Opens PresencePanel |

### Divider Between Humans and AI Skills

| Property | Value |
|----------|-------|
| Style | 1px vertical `--border` |
| Height | 20px, vertically centered |
| Margin | `mx-3` (12px each side) |
| Visibility | Only shown when both humans and AI skills are present |

### Container Spec

| Property | Value |
|----------|-------|
| Background | `--background-subtle` |
| Border-bottom | `--border`, 1px |
| Padding | `px-4 py-2` |
| Layout | `flex items-center gap-1` |
| Visibility | `hidden` when solo editing (no remote users/skills active). Slide-down 200ms when first remote presence joins. Slide-up 200ms when last leaves. |
| Transition | `max-h` animation: `max-h-0 overflow-hidden` → `max-h-[36px]` (200ms ease-out) for smooth appear/disappear without layout shift |

### Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| Desktop > 1280px | Full presence bar as above |
| Tablet 768–1279px | Avatar labels (tooltips) only on tap; initials only visible (no text labels adjacent to avatars) |
| Mobile < 768px | PresenceBar collapsed to a single avatar stack in the note header row (shares row with breadcrumb); no separate bar |

### Accessibility

```html
<div
  role="status"
  aria-label="{N} collaborators active: {names}"
  aria-live="polite"
>
  <div role="group" aria-label="Active collaborators">
    <!-- human avatars -->
  </div>
  <div role="group" aria-label="Active AI skills">
    <!-- AI skill avatars -->
  </div>
</div>
```

- Each avatar button: `aria-label="{name} — {status}"`, `title="{name}"`.
- AI skill button: `aria-label="{skill-name} — {operation}"`.
- Overflow badge: `aria-label="Show all {N} collaborators"`.
- `aria-live="polite"` region in AppShell announces "{name} joined" / "{name} left" when CollabStore updates.
- All avatar buttons: minimum 44×44px touch target (avatar is 28px; add `p-2` invisible padding around each).

### Animation: Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  .presence-bar { transition: none; max-height: auto; }
  .avatar-pulse { animation: none; }
  .avatar-hover { transform: none; }
}
```

---

## T-124: Soft Editor Limit UI (50 Concurrent Users)

Warning state at 50 concurrent editors; read-only lock beyond 50.

### Warning State (50th user joins)

Display a dismissable warning banner below the PresenceBar when the 50th simultaneous editor joins.

```
+------------------------------------------------------------------------+
| [users]  50 people are editing this note. Performance may be affected. |
|          [Dismiss]                                                      |
+------------------------------------------------------------------------+
```

#### Warning Banner Spec

| Property | Value |
|----------|-------|
| Position | Below PresenceBar, above EditorContent, sticky |
| Container | `bg-amber-50 dark:bg-amber-950/30`, `border-b border-amber-200 dark:border-amber-800` |
| Padding | `px-4 py-2` |
| Icon | Lucide `Users` (16px), `text-amber-600 dark:text-amber-400` |
| Text | `text-sm text-amber-700 dark:text-amber-300` |
| Dismiss | `ghost` variant, `text-xs`, right-aligned, persists dismissal in localStorage key: `note-limit-warning-dismissed-{noteId}` |
| Animation | Slide down 200ms ease-out on appear |

#### Accessibility

```html
<div role="alert" aria-live="assertive" aria-label="Editor limit warning">
  <Users /> 50 people are editing this note. Performance may be affected.
  <button aria-label="Dismiss editor limit warning">Dismiss</button>
</div>
```

- `role="alert"` ensures screen readers announce immediately (assertive).
- Do NOT use `aria-live="polite"` — this is a capacity warning that needs immediate attention.

### Read-Only State (> 50 users)

When the user count exceeds 50 and the current user cannot obtain a write token, show the read-only lock state.

```
+------------------------------------------------------------------------+
| [lock]  This note has reached the maximum of 50 concurrent editors.   |
|         You are in read-only mode. You can view but not edit.         |
|         [Try Again]   Editors online: 51                               |
+------------------------------------------------------------------------+
```

#### Read-Only Banner Spec

| Property | Value |
|----------|-------|
| Position | Below PresenceBar, full width, sticky |
| Container | `bg-red-50 dark:bg-red-950/30`, `border-b border-red-200 dark:border-red-800` |
| Padding | `px-4 py-2` |
| Icon | Lucide `Lock` (16px), `text-red-600 dark:text-red-400` |
| Primary text | `text-sm font-medium text-red-700 dark:text-red-300` |
| Secondary text | `text-xs text-red-600 dark:text-red-400` |
| "Try Again" button | `outline` variant, `text-xs`, re-attempts write token acquisition |
| Editor count | `text-xs text-red-500`, right-aligned, `tabular-nums`, live count from CollabStore |

#### Editor Lock Visual Effect

When read-only lock is active:

| Property | Value |
|----------|-------|
| Editor opacity | `opacity-75` on `EditorContent` wrapper |
| Cursor | `cursor-default` on EditorContent (overrides TipTap default pointer) |
| Toolbar | All formatting buttons `disabled`, `opacity-50`, `pointer-events-none` |
| Selection | Still allowed (can select and copy text) |
| Indicator | "Read-only" badge in note header, `secondary` variant, right of title |

#### "Try Again" behavior

1. Click → button shows spinner, polling CollabStore for available write slot.
2. If slot becomes available (user count drops below 50): banner animates out, editor re-enables, spinner stops.
3. If no slot after 5s: button resets to "Try Again", shows secondary text "Still full — {N} editors online."

#### Accessibility

```html
<div role="alert" aria-live="assertive" aria-label="Note is read-only">
  <Lock /> This note has reached the maximum of 50 concurrent editors.
  <p>You are in read-only mode.</p>
  <button aria-label="Try to gain edit access">Try Again</button>
  <span aria-live="polite" aria-atomic="true">Editors online: {N}</span>
</div>
```

- The editor count `<span>` uses `aria-live="polite"` (separate from the alert container) to avoid re-announcing on every count change.
- TipTap `editable={false}` must be set — this disables all keyboard editing input, not just visual cues.

### State Transition Matrix

| CollabStore `editorCount` | User is writer? | Banner shown |
|---------------------------|-----------------|--------------|
| 0–49 | Yes | None |
| 50 | Yes | Warning banner (50th editor) |
| 50 | No | Read-only banner + lock |
| > 50 | Yes (existing writer) | Warning banner (persists) |
| > 50 | No | Read-only banner + lock |

---

## T-133: Focus Mode Toggle

Toolbar button controlling Focus Mode (hide all AI-owned blocks). State persisted to localStorage.

### Toolbar Placement

```
[B] [I] [U] [S] | [H1] [H2] [H3] | [bullet][number] | ... | [Focus Mode] [layers▾]
                                                               ^^^^^^^^^^^^
                                                               T-133 toggle
```

The Focus Mode toggle is the second-to-last item in the toolbar, before the density dropdown. It appears as a button with both an icon AND a text label (not icon-only) to maximize discoverability (per CX review recommendation R-06).

### Button Spec (Off State)

| Property | Value |
|----------|-------|
| Variant | `ghost` |
| Size | `sm` (height 32px) |
| Icon | Lucide `Eye` (16px) |
| Label | `text-xs`, "Focus Mode" |
| Layout | `flex items-center gap-1.5` |
| Color | `--foreground-muted` (default inactive) |
| Border | None |

### Button Spec (On State)

| Property | Value |
|----------|-------|
| Variant | `secondary` (uses `--background-subtle` bg) |
| Icon | Lucide `EyeOff` (16px), `--primary` color |
| Label | `text-xs`, "Focus Mode", `--primary` color, `font-medium` |
| Active indicator | 3px `--primary` underline below button (not a dot — text button needs line) |
| Background | `--primary-muted` (`#29A38615`) |
| Border | 1px `--primary` at 30% opacity |

### Keyboard Shortcut

| Platform | Shortcut |
|----------|----------|
| macOS | `Cmd+Shift+F` |
| Windows/Linux | `Ctrl+Shift+F` |

Register via `useEffect` + `keydown` listener in the toolbar component. Show shortcut in tooltip.

### Tooltip

```
Focus Mode
Hide AI-generated content — show only what you wrote.
Cmd+Shift+F
```

Tooltip: `text-xs`, max-width 200px, shows on hover after 400ms delay. Uses shadcn/ui `<Tooltip>`.

### localStorage Persistence

```typescript
const FOCUS_MODE_KEY = 'pilot-space:focus-mode';

// Read on mount
const stored = localStorage.getItem(FOCUS_MODE_KEY);
const initial = stored === 'true';

// Write on toggle
localStorage.setItem(FOCUS_MODE_KEY, String(newValue));
```

- Key is global (not per-note). Focus Mode is a user preference, not a note setting.
- `DensityStore.focusMode` is initialized from localStorage on store construction.
- SSR-safe: read localStorage in `useEffect`, not during render.

### Focus Mode Active Visual Effect

When Focus Mode is on:

| Effect | Implementation |
|--------|----------------|
| All `ai:*` owned blocks | `display: none` via `DensityExtension` decoration (not CSS `visibility: hidden` — must not take up space) |
| Collapsed AI block placeholder | Single-line `<div class="ai-hidden-placeholder">` per AI group: "N AI blocks hidden — [Show]" in `--foreground-muted`, `text-xs`, `italic`, `py-1` |
| Note header tint | `--background` changes to `#29A38608` (primary at 3% opacity) — subtle reinforcement that a filter is active |
| PresenceBar | AI skill avatars remain visible (they are people/processes, not content) |
| Transition | All AI blocks collapse simultaneously with `height: 0, opacity: 0` (200ms ease-in). Reduced motion: instant. |

### Accessibility

```html
<button
  aria-pressed="true|false"
  aria-label="Focus Mode: {on|off}. Show only human content."
  title="Focus Mode (Cmd+Shift+F)"
>
  <EyeOff /> Focus Mode
</button>
```

- `aria-pressed` changes with state. Screen reader announces "Focus Mode, toggle button, pressed" / "not pressed".
- When activated: `aria-live="polite"` region announces "Focus Mode on — {N} AI blocks hidden".
- When deactivated: "Focus Mode off — all content visible".

### Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| Desktop > 1280px | Full button: icon + "Focus Mode" text label in toolbar |
| Tablet 768–1279px | Icon-only button in toolbar; text label in tooltip |
| Mobile < 768px | Moved to note header three-dot menu as "Focus Mode" menu item with toggle switch |

---

## T-145: Template Picker Modal

Modal for selecting a note template when creating a new note. "Blank" first, then SDLC templates, then admin custom templates.

### Trigger

The modal opens from the "New Note" button (or keyboard shortcut `Cmd+N` / `Ctrl+N`). It is NOT shown when auto-creating notes from other flows (e.g., extracting issues from an existing note).

### Modal Dimensions

| Property | Value |
|----------|-------|
| Width | 560px (desktop), full-width with `mx-4` margin (mobile) |
| Max height | 80vh with `overflow-y: auto` |
| Background | `bg-background` |
| Border radius | `rounded-xl` (18px) — modal-level squircle |
| Shadow | `shadow-xl` |
| Overlay | `bg-black/40` backdrop, `backdrop-blur-sm` |

### Modal Layout

```
+---------------------------------------------------------------+
| Create New Note                                     [×]       |
|---------------------------------------------------------------|
|                                                               |
|  [Blank Note ✓]   Start from scratch                          |
|                                                               |
|  SDLC TEMPLATES                                               |
|  +----------+  +----------+  +----------+  +----------+      |
|  |          |  |          |  |          |  |          |      |
|  | Sprint   |  | Design   |  | Post-    |  | Release  |      |
|  | Planning |  | Review   |  | mortem   |  | Planning |      |
|  | [icon]   |  | [icon]   |  | [icon]   |  | [icon]   |      |
|  +----------+  +----------+  +----------+  +----------+      |
|                                                               |
|  MY TEMPLATES (admin only — hidden if no custom templates)    |
|  +----------+  +----------+                                   |
|  | Custom 1 |  | + Create |                                   |
|  | Template |  |          |                                   |
|  +----------+  +----------+                                   |
|                                                               |
|---------------------------------------------------------------|
|  [Cancel]                              [Create Note →]        |
+---------------------------------------------------------------+
```

### Blank Note Row (First Option)

| Property | Value |
|----------|-------|
| Layout | Full-width row, `flex items-center gap-3`, `p-3`, `rounded-lg` |
| Selected state (default) | `bg-primary/5 border border-primary/30 rounded-lg` |
| Icon | Lucide `FileText` (20px), `--primary` when selected, `--foreground-muted` otherwise |
| Title | `text-sm font-medium` |
| Subtitle | `text-xs text-foreground-muted`, "Start from scratch" |
| Check indicator | Lucide `Check` (16px), `--primary`, right-aligned, only when selected |
| Keyboard | Pre-selected on modal open; Enter immediately creates blank note |

This "Blank Note" is a wide row — not a card — to visually separate it from the template grid below.

### Template Card Grid

| Property | Value |
|----------|-------|
| Grid | CSS Grid, `grid-cols-4` desktop, `grid-cols-2` tablet/mobile |
| Gap | `gap-3` (12px) |
| Card size | 120px × 140px, `flex flex-col items-center justify-center` |

#### Template Card Spec

| Property | Value |
|----------|-------|
| Container | `rounded-lg` (14px), `border border-border`, `bg-background`, `p-3`, `cursor-pointer` |
| Hover | `border-primary/40 bg-primary/3 shadow-sm`, `transition-all 150ms` |
| Selected | `border-primary border-2 bg-primary/5`, `ring-2 ring-primary/20` |
| Icon | 32px, centered, `--foreground-muted` default, `--primary` when selected |
| Title | `text-xs font-medium text-center mt-2`, `--foreground` |
| Focus ring | `ring-2 ring-primary/50 ring-offset-2` (keyboard focus) |

#### Template Card Icons

| Template | Lucide Icon | Description shown in tooltip |
|----------|-------------|------------------------------|
| Sprint Planning | `LayoutDashboard` | "Sprint goals, team assignments, and task breakdown" |
| Design Review | `PenTool` | "Design critique structure with feedback and decisions" |
| Postmortem | `AlertTriangle` | "Incident timeline, impact analysis, and action items" |
| Release Planning | `Rocket` | "Feature list, go/no-go criteria, and rollout plan" |

Tooltip appears on hover (400ms delay), `text-xs`, max-width 180px.

### Section Headers

| Property | Value |
|----------|-------|
| Text | `text-xs uppercase tracking-wider --foreground-muted` |
| Margin | `mt-4 mb-2` on the header text |
| "SDLC TEMPLATES" | Always visible when templates exist |
| "MY TEMPLATES" | Only visible when `workspace.customTemplates.length > 0` AND user has `admin` or `owner` role |

### Custom Template Card (Admin Only)

Shares the same 120×140px card spec. Differences:

| Property | Value |
|----------|-------|
| Icon | Lucide `FileText` (32px), `--foreground-muted` |
| Hover badge | Small `[edit]` icon appears top-right on hover (`Settings` 12px, `ghost` style) |
| Edit click | Opens template editor (separate flow, not in this modal) — `e.stopPropagation()` |

### "Create Template" Card (Admin Only)

The last card in the custom templates section:

| Property | Value |
|----------|-------|
| Container | Same size as cards, `border-dashed border-2 border-border`, `bg-background` |
| Icon | Lucide `Plus` (32px), `--foreground-muted` |
| Title | `text-xs text-foreground-muted`, "New Template" |
| Hover | `border-primary/50 text-primary` (icon + text), no scale |
| Click | Navigates to template creator (closes modal) |

### Footer

| Property | Value |
|----------|-------|
| Layout | `flex justify-between items-center`, `pt-4 border-t border-border` |
| Cancel | `ghost` variant, `sm` size |
| "Create Note" | `default` (primary), `sm` size, arrow icon suffix, disabled until a template is selected |
| Button label | "Create Note →" — arrow reinforces forward action |

### Selection State Management

```typescript
// State
const [selected, setSelected] = useState<TemplateId | 'blank'>('blank');

// Keyboard arrow navigation
// Left/Right: navigate within current row
// Up/Down: navigate between rows
// Enter: confirm selection (same as clicking "Create Note")
// Escape: close modal without creating
```

- Default selection: `'blank'` (Blank Note row is pre-selected).
- Arrow key navigation moves through the template grid using `roving tabindex` pattern.
- The "Create Note" button reflects selected template: "Create Blank Note", "Create Sprint Planning Note", etc.

### Keyboard Navigation (Roving Tabindex)

```
Tab → moves to template grid
Arrow keys → navigate within grid (wraps at row ends)
Space/Enter → select focused card
Enter (when "Create Note" button focused) → submit
Escape → close modal
```

### Accessibility

```html
<dialog
  role="dialog"
  aria-modal="true"
  aria-label="Create New Note — choose a template"
>
  <div role="radiogroup" aria-label="Note template selection">
    <!-- Blank Note -->
    <div role="radio" aria-checked="true" tabindex="0" aria-label="Blank Note — start from scratch">
      ...
    </div>
    <!-- SDLC Templates -->
    <div role="radio" aria-checked="false" tabindex="-1" aria-label="Sprint Planning — sprint goals, team assignments, and task breakdown">
      ...
    </div>
    ...
  </div>
</dialog>
```

- Modal uses `<dialog>` element (native focus trap) or `@radix-ui/react-dialog` which provides the same.
- Focus moves to "Blank Note" option on open (pre-selected + focused).
- All template cards: `role="radio"`, `aria-checked`, `tabindex` managed by roving tabindex.
- Template descriptions read on focus via `aria-label` (not tooltip only — screen readers must hear the description without hover).

### Responsive Behavior

| Breakpoint | Grid | Modal Width |
|------------|------|-------------|
| Desktop > 1280px | `grid-cols-4` | 560px |
| Tablet 768–1279px | `grid-cols-3` | 480px |
| Mobile < 768px | `grid-cols-2` | full width, `mx-4` |

On mobile, card size reduces to 100px × 120px with `text-[11px]` titles.

### Empty Custom Templates State

When admin has no custom templates (custom section hidden for non-admins entirely):

For admins, show the "Create Template" card alone under "MY TEMPLATES" heading with descriptive text:

```
MY TEMPLATES
+----------+
| + Create |  No custom templates yet. Create one for your team.
| Template |
+----------+
```

Text: `text-xs text-foreground-muted italic`, adjacent to the card (not inside).
