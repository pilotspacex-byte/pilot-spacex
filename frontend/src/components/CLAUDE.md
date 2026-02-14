# Shared Components

**Scope**: `frontend/src/components/` (95 files, 9 subdirectories)
**Standards**: TypeScript strict, WCAG 2.2 AA, MobX + TanStack Query, TailwindCSS + shadcn/ui, 700-line limit

---

## Submodule Documentation

| Module                | Doc                                    | Covers                                             |
| --------------------- | -------------------------------------- | -------------------------------------------------- |
| **Editor Components** | [`editor/CLAUDE.md`](editor/CLAUDE.md) | NoteCanvas, 13 TipTap extensions, auto-save, layout |

---

## Directory Structure

```
frontend/src/components/
├── ui/                          # 25 shadcn/ui primitives + custom components
├── editor/                      # TipTap note canvas + 13 extensions
├── layout/                      # App shell, sidebar, header, notifications
├── issues/                      # 14 issue selectors, cards, modals
├── ai/                          # Chat, approvals, confidence tags
├── integrations/                # GitHub, PR linking
├── cycles/                      # Burndown, velocity charts
├── navigation/                  # Outline tree, pinned notes
├── role-skill/                  # Role cards, icons
├── workspace-guard.tsx          # Auth boundary
├── workspace-selector.tsx       # Workspace switcher
└── providers.tsx                # Client-side providers
```

---

## UI Primitives (shadcn/ui)

Extend via Tailwind classes, CSS variables, or composition (not direct modification). Use `cn()` utility to merge classNames.

**Custom Additions**: Button (6 variants, 5 sizes), Card (header/content/footer), FAB (floating action, Escape to close), SaveStatus (idle/saving/saved/error), TokenBudgetRing (circular progress 0-100%), ConfidenceTagBadge (color-coded 0-1).

**Color System**: Use CSS variables for automatic theme support. Key tokens: `--background`, `--foreground`, `--primary`, `--ai`, `--destructive`, `--border`. Apply via Tailwind: `bg-background`, `text-foreground`, `border-border`.

---

## Layout Components

- **AppShell**: Responsive shell with mobile-aware sidebar. Skip-to-main-content link (accessibility).
- **Sidebar**: Observer-wrapped navigation (Home, Notes, Issues, Projects, AI Chat, Approvals, Costs, Settings) + user controls.
- **Header**: Breadcrumb injection point per page.
- **NotificationPanel**: Dropdown with unread count badge.

---

## Issue Components

- **IssueCard/IssueBoard/IssueModal**: Card view, Kanban board (6 columns), create/edit modal.
- **14 Selectors**: All follow `{ value, onChange, options, isLoading, error, placeholder, disabled }` pattern. Types: IssueTypeSelect, IssueStateSelect (state machine), IssuePrioritySelect, CycleSelector, EstimateSelector (Fibonacci 1-21), LabelSelector (multi-select), AssigneeSelector (with AI recommendations), DuplicateWarning (70%+ similarity).
- **AI Context**: AIContext, ContextItemList, ContextChat, TaskChecklist, ClaudeCodePrompt.

---

## AI Components

- **ApprovalDialog**: Non-dismissable modal for destructive AI actions. 24h countdown, Approve/Reject.
- **CountdownTimer**: Color-coded expiry (green >4h, yellow 1-4h, red <1h).
- **AIConfidenceTag**: Color-coded score (green 0.8-1.0, yellow 0.5-0.8, red 0-0.5).

---

## Accessibility (WCAG 2.2 AA)

1. **Keyboard**: All interactive elements support Tab, Enter, Space, Escape, Arrow keys
2. **ARIA**: Form inputs require `aria-label` or `aria-describedby`. Icon buttons need `aria-label` + `title`
3. **Focus**: Trap in modals. Autoref to close button on open. Escape to close
4. **Contrast**: Minimum 4.5:1 ratio. Use design system tokens
5. **Motion**: Use `motion-safe:animate-*` and `motion-reduce:transition-none`
6. **Skip Links**: Invisible link to `#main-content`, visible on focus. Place in AppShell

---

## Anti-Patterns

| Anti-Pattern               | Fix                                               |
| -------------------------- | ------------------------------------------------- |
| Storing API data in MobX   | Use `useQuery()` instead                          |
| Inline styles              | Use Tailwind classes                              |
| Hardcoded colors           | Use CSS variables (e.g., `bg-primary`)            |
| Missing ARIA labels        | Add `aria-label` + `title` to icon buttons        |
| No focus trap in modals    | Trap Tab key within modal, focus on open          |

---

## Import Pattern

Import via barrel exports: `import { Button, Card, NoteCanvas } from '@/components'`.

---

## Related Documentation

- **Editor Components**: [`editor/CLAUDE.md`](editor/CLAUDE.md)
- **AI Stores**: [`../stores/ai/CLAUDE.md`](../stores/ai/CLAUDE.md)
- **Design System**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0
