# Implementation Plan: Compact Layout Redesign

**Feature**: Compact Layout Redesign
**Branch**: `009-compact-layout-redesign`
**Created**: 2026-02-04
**Spec**: `specs/009-compact-layout-redesign/spec.md`
**Author**: Tin Dang

---

## Summary

Reorganize the app shell by moving notification + user controls from the header to the sidebar bottom, stripping the header to breadcrumb-only at 40px height, removing search bar / AI button / +New dropdown from the header, and applying aggressive -2px font size + spacing compaction globally.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | TypeScript 5.3+ / Next.js 14+ (App Router) + React 18 |
| **Primary Dependencies** | MobX 6+, TailwindCSS 3.4+, shadcn/ui, lucide-react, motion/react |
| **Storage** | N/A (frontend-only; no backend changes) |
| **Testing** | Vitest (unit) |
| **Target Platform** | Browser (desktop 1280px+) |
| **Project Type** | Frontend-only |
| **Performance Goals** | No render regressions; layout paint < 16ms |
| **Constraints** | 700 lines max per file; WCAG 2.2 AA |
| **Scale/Scope** | 4 files modified |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (TypeScript, Next.js, TailwindCSS)
- [x] Database choice N/A (no backend changes)
- [x] Auth approach N/A (no auth changes)
- [x] Architecture patterns match (MobX observer components, feature-folder structure)

### Simplicity Gate

- [x] Using minimum number of projects/services (4 files modified, 0 new files)
- [x] No future-proofing or speculative features
- [x] No premature abstractions

### Quality Gate

- [x] Test strategy defined with coverage target (>80%)
- [x] Type checking enforced (TypeScript strict)
- [x] File size limits respected (700 lines max)
- [x] Linting configured (ESLint via `pnpm lint`)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement | Technical Approach | Components |
|-------|------------|-------------------|------------|
| FR-001 | Notification controls in sidebar bottom | Move `<DropdownMenu>` for notifications from `header.tsx` to `sidebar.tsx` bottom section | sidebar.tsx |
| FR-002 | User avatar in sidebar bottom | Move `<DropdownMenu>` for user avatar from `header.tsx` to `sidebar.tsx` bottom section | sidebar.tsx |
| FR-003 | Collapsed sidebar: icons with tooltips | Wrap notification + avatar buttons in `<Tooltip>` with `side="right"` when `collapsed` | sidebar.tsx |
| FR-004 | Expanded sidebar: horizontal row layout | Use `flex items-center gap-2` container in sidebar bottom | sidebar.tsx |
| FR-005 | Header 40px, breadcrumb only | Change `h-14` → `h-10`, remove all children except left breadcrumb slot | header.tsx |
| FR-006 | Remove search bar | Delete search `<Button>` and `<Tooltip>` block (lines 62-86 of header.tsx) | header.tsx |
| FR-007 | Remove AI Assistant button | Delete AI `<Button>` block (lines 91-107 of header.tsx) | header.tsx |
| FR-008 | Remove +New dropdown | Delete `<DropdownMenu>` block (lines 110-154 of header.tsx) | header.tsx |
| FR-009 | Body text 14px → 12px | Override Tailwind `text-sm` base via globals.css `@theme` or per-component class changes | globals.css |
| FR-010 | Label/meta text 12px → 10px | Override `text-xs` and `text-[10px]` sizes; add compact utility classes | globals.css |
| FR-011 | Navigation text 14px → 12px | Change nav item `text-sm` → `text-xs` in sidebar.tsx | sidebar.tsx |
| FR-012 | Proportional padding/gap reduction | Reduce `p-3` → `p-2`, `gap-3` → `gap-2`, `py-2` → `py-1.5` across layout components | sidebar.tsx, header.tsx |
| FR-013 | Keyboard shortcuts preserved | No code changes needed — shortcuts are in UIStore and global handlers, not header components | N/A |
| FR-014 | Dropdown overflow prevention | Use `side="right"` + `align="start"` on sidebar dropdown menus; `side="top"` for avatar | sidebar.tsx |
| FR-015 | Sidebar +New Note remains note-only | No change to existing sidebar +New Note button | sidebar.tsx |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Data Entities |
|------------|-------------------|--------------------|--------------  |
| US1: Consolidated Sidebar Controls | N/A | sidebar.tsx (add notification + user controls) | N/A |
| US2: Minimal Header Bar | N/A | header.tsx (strip to breadcrumb), globals.css (--header-height) | N/A |
| US3: Font & Spacing Compaction | N/A | globals.css (font overrides), sidebar.tsx, header.tsx (class adjustments) | N/A |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| How to reduce font sizes globally? | A) Override Tailwind theme `fontSize` in tailwind config, B) Add CSS custom properties and utility classes in globals.css, C) Change classes per-component | C) Per-component class changes + CSS variable for header height | FR-009/010/011: Per-component gives precise control without risk of breaking unrelated pages. Only layout components need changes. Tailwind theme override would affect all pages including settings pages we don't want to touch. |
| Where to position sidebar notification/user dropdowns? | A) Dropdown opens to the right (side="right"), B) Dropdown opens upward (side="top"), C) Popover instead of dropdown | A) side="right" for both, align="start" | FR-014: Right-side opening avoids bottom viewport overflow since controls are at sidebar bottom. Consistent with collapsed sidebar tooltip pattern. |
| How to handle sidebar bottom section layout? | A) Single `<div>` with flex-wrap, B) Separate rows for [New Note] and [controls], C) Grid layout | B) Separate bordered rows | FR-001/004: Keeps visual separation between creation action and utility controls. Matches existing sidebar section pattern (border-t separators). |

---

## Data Model

N/A — No data entities. This is a frontend-only layout change.

---

## API Contracts

N/A — No API endpoints. This is a frontend-only layout change.

---

## Project Structure

```text
specs/009-compact-layout-redesign/
├── spec.md                          # Feature specification
├── plan.md                          # This file
├── checklists/requirements.md       # Requirements validation
├── quickstart.md                    # Smoke test scenarios
└── tasks.md                         # Task breakdown (next phase)

frontend/src/
├── components/layout/
│   ├── header.tsx                   # MODIFY: Strip to breadcrumb-only, h-10
│   ├── sidebar.tsx                  # MODIFY: Add notification + user controls to bottom
│   └── app-shell.tsx                # MODIFY: Update sidebar header height alignment
└── app/
    └── globals.css                  # MODIFY: Update --header-height, font compaction
```

**Structure Decision**: No new files created. All changes are modifications to existing layout components, following the constitution rule: "Prefer editing existing files to creating new ones."

---

## Detailed File Changes

### 1. `header.tsx` (232 → ~40 lines)

**Current state**: Contains search bar, AI button, +New dropdown, notifications, user avatar.
**Target state**: Breadcrumb-only bar at 40px height.

**Changes**:
- Line 58: `h-14` → `h-10`, remove `justify-between`
- Delete lines 60-86: Search bar (entire left section)
- Delete lines 89-228: All right-side actions (AI, +New, Notifications, User)
- Remove unused imports: `Search`, `Bell`, `Plus`, `Command`, `Sparkles`, `Loader2`, `Avatar`, `AvatarFallback`, `AvatarImage`, `Badge`, `DropdownMenu*`, `useCreateNote`, `createNoteDefaults`, `useNotificationStore`
- Keep: `observer`, `useUIStore` (for potential breadcrumb context)
- Header becomes a simple `<header>` with breadcrumb children slot

**Post-change imports**:
```
observer, cn
```

**Post-change JSX** (conceptual):
```tsx
<header className="flex h-10 shrink-0 items-center border-b border-border bg-background px-4">
  {/* Breadcrumb slot — pages inject their own breadcrumb via context or children */}
</header>
```

### 2. `sidebar.tsx` (301 → ~350 lines)

**Current state**: Logo, nav, notes, +New Note, collapse toggle, settings.
**Target state**: Same + notification bell + user avatar added between +New Note and collapse toggle.

**Changes**:

a) **Add imports** (from header.tsx):
- `Bell` from lucide-react
- `Avatar`, `AvatarFallback`, `AvatarImage` from ui/avatar
- `Badge` from ui/badge
- `DropdownMenu`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuLabel`, `DropdownMenuSeparator`, `DropdownMenuTrigger` from ui/dropdown-menu
- `useNotificationStore` from stores

b) **Add store usage**:
- `const notificationStore = useNotificationStore();` in component body

c) **Add notification + user section** between `{/* New Note Button */}` and `{/* Collapse Toggle */}`:

```tsx
{/* Notification + User Controls */}
<div className="border-t border-sidebar-border p-2">
  <div className={cn('flex items-center', collapsed ? 'flex-col gap-1' : 'gap-2 px-1')}>
    {/* Notification Bell */}
    <DropdownMenu>
      <Tooltip delayDuration={collapsed ? 0 : 1000}>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-8 w-8 text-muted-foreground">
              <Bell className="h-4 w-4" />
              {notificationStore.unreadCount > 0 && (
                <Badge variant="destructive" className="absolute -right-1 -top-1 h-3.5 min-w-3.5 px-0.5 text-[9px]">
                  {notificationStore.unreadCount > 99 ? '99+' : notificationStore.unreadCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        {collapsed && <TooltipContent side="right">Notifications</TooltipContent>}
      </Tooltip>
      <DropdownMenuContent side="right" align="end" className="w-72">
        {/* ... notification content (moved from header) ... */}
      </DropdownMenuContent>
    </DropdownMenu>

    {/* User Avatar */}
    <DropdownMenu>
      <Tooltip delayDuration={collapsed ? 0 : 1000}>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-7 w-7 border border-border">
                <AvatarImage src="" alt="User" />
                <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">TD</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        {collapsed && <TooltipContent side="right">Account</TooltipContent>}
      </Tooltip>
      <DropdownMenuContent side="right" align="end" className="w-52">
        {/* ... user menu content (moved from header) ... */}
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</div>
```

d) **Compact font/spacing changes**:
- Nav items: `text-sm` → `text-xs`, `gap-3` → `gap-2`, `px-3 py-2` → `px-2.5 py-1.5`
- Logo header: `h-14` → `h-10`, `gap-3` → `gap-2`
- Section labels: `text-[10px]` → `text-[9px]`
- Note items: `text-sm` → `text-xs`, `py-1.5` → `py-1`
- +New Note section: `p-3` → `p-2`
- Collapse toggle section: keep `p-2`

e) **Move Settings into the bottom controls row** instead of separate section.

### 3. `globals.css`

**Changes**:
- Line 181: `--header-height: 56px` → `--header-height: 40px`

### 4. `app-shell.tsx`

**Changes**:
- Sidebar header alignment: If sidebar logo section changes from `h-14` to `h-10`, the sidebar aside element needs no changes since it uses `h-full`.
- No structural changes needed — the composition remains the same.

---

## Quickstart Validation

### Scenario 1: Sidebar Controls Work

1. Start dev server (`pnpm dev`), navigate to a workspace
2. Verify notification bell appears in sidebar bottom
3. Click notification bell — dropdown opens to the right
4. Click user avatar (TD) — dropdown opens with Profile, Settings, Keyboard shortcuts, Sign out
5. **Verify**: All menu items functional, dropdowns positioned correctly

### Scenario 2: Header Is Minimal

1. Navigate to any note page
2. **Verify**: Header shows only breadcrumb (e.g., "Notes > Auth Refactor")
3. **Verify**: No search bar, AI button, +New dropdown, notification bell, or user avatar in header
4. **Verify**: Header height is visually compact (~40px)

### Scenario 3: Collapsed Sidebar

1. Click collapse toggle to collapse sidebar
2. **Verify**: Notification bell shows as icon with tooltip "Notifications"
3. **Verify**: User avatar shows as icon with tooltip "Account"
4. **Verify**: Clicking notification icon opens dropdown to the right
5. **Verify**: Clicking avatar opens dropdown to the right

### Scenario 4: Keyboard Shortcuts

1. Press `Cmd+K` — search modal opens
2. Press `Cmd+N` — new note created
3. **Verify**: Both shortcuts work identically to before

### Scenario 5: Font Compaction

1. Navigate to Notes list
2. **Verify**: Navigation text is smaller (~12px)
3. **Verify**: Note item text is smaller (~12px)
4. **Verify**: All text remains readable on a standard laptop screen

---

## Complexity Tracking

No constitution gate violations. All gates pass.

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping
- [x] Every user story maps to frontend components
- [x] Data model N/A (no entities)
- [x] API contracts N/A (no endpoints)
- [x] Research documents each decision with 2+ alternatives

### Constitution Compliance

- [x] Technology standards gate passed
- [x] Simplicity gate passed
- [x] Quality gate passed
- [x] No violations to document

### Traceability

- [x] Every technical decision references FR-NNN
- [x] Every component change references the user story it serves
- [x] N/A for data entities (frontend-only)
- [x] Project structure matches existing codebase patterns

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining
- [x] Performance constraints defined (layout paint < 16ms)
- [x] Security N/A (no auth/data changes)
- [x] Error handling N/A (no API calls added)
- [x] File modification order specified

---

## Implementation Order

1. **globals.css** — Update `--header-height` CSS variable (foundation change)
2. **header.tsx** — Strip to breadcrumb-only, reduce height (US-2)
3. **sidebar.tsx** — Add notification + user controls, apply compaction (US-1, US-3)
4. **app-shell.tsx** — Verify alignment, minor adjustments if needed

---

## Next Phase

After this plan passes all checklists:

1. **Proceed to task breakdown** — Use `template-tasks.md` to create tasks.md
2. **Implementation** — Execute changes in the order specified above
