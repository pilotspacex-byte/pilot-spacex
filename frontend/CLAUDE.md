# Frontend Development Guide - Pilot Space

**For project overview and general context, see main CLAUDE.md at project root.**

---

## Quick Reference

### Quality Gates (Run Before Every Commit)

```bash
pnpm lint && pnpm type-check && pnpm test
```

All three gates must PASS. **80% test coverage requirement** catches 85% of regressions before deployment.

### Critical Constants

| Constraint         | Value                | Rationale                                                                                     |
| ------------------ | -------------------- | --------------------------------------------------------------------------------------------- |
| File size limit    | 700 lines            | Component files >700 lines become unmaintainable. Split by feature or extract sub-components. |
| Accessibility      | WCAG 2.2 AA          | 4.5:1 contrast, keyboard nav, ARIA labels required. Inclusive design benefits all users.      |
| Performance        | FCP <1.5s, LCP <2.5s | Core Web Vitals directly impact user retention and SEO rankings.                              |
| Auto-save debounce | 2s (fixed)           | Frontend constant. Not configurable. Prevents excessive API calls.                            |
| Ghost text trigger | 500ms pause          | GhostTextExtension constant. Balances responsiveness with cost.                               |

### Development Commands

**Setup**: `cd frontend && pnpm install`
**Dev server**: `pnpm dev` (runs on http://localhost:3000)
**Quality gates**: `pnpm lint && pnpm type-check && pnpm test`
**E2E tests**: `pnpm test:e2e`
**Build**: `pnpm build`

---

## Architecture & Structure

Next.js 14+ App Router, TypeScript 5.3+, MobX 6+ (UI state), TanStack Query 5+ (server state), TailwindCSS + shadcn/ui, TipTap/ProseMirror for rich text. Feature-based folder structure under `src/features/`.

5-tier request flow: Browser -> Next.js Page -> Feature Component (observer + TanStack Query) -> MobX Store -> API Service -> Backend.

**Full structure and feature modules**: See [`src/features/CLAUDE.md`](src/features/CLAUDE.md)

---

## State Management

**Golden Rule**: Store API responses in TanStack Query. Store UI state in MobX. Never store API data in MobX stores.

RootStore aggregates domain stores (auth, ui, workspace, notes, issues, cycles, ai, onboarding, roleSkill, homepage, notifications). AIStore aggregates 11 AI feature stores (PilotSpaceStore, GhostTextStore, ApprovalStore, etc.).

**Full store architecture, patterns, and anti-patterns**: See [`src/stores/CLAUDE.md`](src/stores/CLAUDE.md)

---

## TipTap Editor

16 extensions in `src/features/notes/editor/extensions/`. Key extensions: BlockIdExtension (UUID per block), GhostTextExtension (500ms debounce, Tab/Escape), IssueLinkExtension (PS-123 auto-detection), SlashCommandExtension, MentionExtension. All instantiated via `createEditorExtensions()` factory.

**Full extension catalog and editor setup**: See [`src/features/notes/CLAUDE.md`](src/features/notes/CLAUDE.md)

---

## API & SSE

9 typed API clients with RFC 7807 error handling. TanStack Query keys organized hierarchically. Optimistic updates use snapshot + rollback pattern.

**Full API client patterns and query key factories**: See [`src/services/CLAUDE.md`](src/services/CLAUDE.md)

Custom SSE client for POST requests. 8 event types: `message_start`, `text_delta`, `tool_use`, `tool_result`, `content_update`, `approval_request`, `task_progress`, `message_stop`. Route via `PilotSpaceStore.sendMessage()` -> SSEClient -> event handlers -> MobX updates.

**Full SSE patterns and AI streaming**: See [`src/features/ai/CLAUDE.md`](src/features/ai/CLAUDE.md)

---

## Components

25 shadcn/ui primitives in `src/components/ui/`. Feature-specific components colocated under `src/features/*/components/`. Observer pattern required for all MobX-consuming components. WCAG 2.2 AA compliance mandatory (keyboard nav, ARIA labels, focus management, reduced motion).

**Full component patterns and accessibility requirements**: See [`src/components/CLAUDE.md`](src/components/CLAUDE.md)

---

## AI Integration

All user-facing AI goes through `PilotSpaceStore` (not siloed stores). Skills are YAML files in `.claude/skills/` invoked via slash commands. Approval flow: non-dismissable modal, 24h countdown, content diff, approve/reject.

**Full AI integration patterns and PilotSpaceStore API**: See [`src/features/ai/CLAUDE.md`](src/features/ai/CLAUDE.md)

---

## Design System

**Philosophy**: Warm, Capable, Collaborative (inspired by Craft, Apple, Things 3).

| Token         | Light   | Dark    | Usage                  |
| ------------- | ------- | ------- | ---------------------- |
| --background  | #FDFCFA | #1A1A1A | Primary surface        |
| --primary     | #29A386 | #34B896 | Teal-green actions     |
| --ai          | #6B8FAD | #7DA4C4 | Dusty blue AI elements |
| --destructive | #D9534F | #E06560 | Delete/remove          |

**Typography**: Geist font, text-xs (11px) to text-2xl (24px). **Spacing**: 4px grid. **Radius**: squircle 6-18px.

**Full color system, component specs, page catalog**: See [`specs/001-pilot-space-mvp/ui-design-spec.md`](../specs/001-pilot-space-mvp/ui-design-spec.md) v4.0

---

## Standards

### DO

- Use `'use client'` for interactive components
- Wrap MobX components with `observer()`
- Use TanStack Query for server data, MobX for UI state
- Add ARIA labels to interactive elements
- Use Tailwind classes (no inline styles), shadcn/ui as base
- Preserve block IDs through editor operations
- Handle errors with RFC 7807 ApiError class

### DON'T

- Store API data in MobX (use TanStack Query)
- Use `any` types (TypeScript strict mode)
- Hardcode colors (use CSS variables)
- Use generic component names (NoteView not View)
- Leave TODOs in code (resolve or create issue)
- Commit console.log/debugger statements
- Forget to wrap with `observer()` when using MobX

---

## Pre-Submission Checklist

Rate confidence (0-1) before submitting PR. **If any score <0.9, refine before submitting.**

- [ ] MobX (UI) vs TanStack Query (server) separation correct
- [ ] observer() on all MobX-consuming components
- [ ] Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- [ ] ARIA labels for interactive elements
- [ ] Dynamic imports for code-split components
- [ ] File stays under 700 lines
- [ ] TypeScript strict mode passes, no `any` types
- [ ] Tests cover happy path + error cases
- [ ] Block IDs preserved through edits (TipTap)
- [ ] AI interactions through PilotSpaceStore only
- [ ] SSE events mapped per event catalog
- [ ] Approval flow for destructive actions (DD-003)

---

## File Size Audit

**At 700-line limit**: SkillGenerationWizard.tsx (645 lines) -- extract sub-components.
**Medium size** (300-500): GhostTextExtension (519), PilotSpaceStore (500+), IssueLinkExtension (458). Monitor.

---

## Key Files & Load Order

### Load Order for New Features

1. `docs/architect/feature-story-mapping.md` -> Find US-XX and affected components
2. `docs/dev-pattern/45-pilot-space-patterns.md` -> Project-specific overrides
3. This file -> Frontend-specific patterns
4. `specs/001-pilot-space-mvp/ui-design-spec.md` -> Design system

### Key Files

| Topic                | File                                               |
| -------------------- | -------------------------------------------------- |
| State management     | `src/stores/RootStore.ts`, `stores/ai/AIStore.ts`  |
| API clients          | `src/services/api/index.ts`                        |
| SSE streaming        | `src/lib/sse-client.ts`                            |
| Editor extensions    | `src/features/notes/editor/extensions/`            |
| TanStack Query setup | `src/lib/queryClient.ts`                           |
| UI design tokens     | `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 |
| Feature components   | `src/features/*/components/`                       |

---

## Quick Debugging

**Observer not re-rendering**: Wrap with `observer()`. Property must be `@observable`.
**Infinite TanStack Query loops**: Use stable queryKey with `as const`.
**Ghost text not triggering**: Verify 500ms debounce, `enabled: true`, `onTrigger` callback defined.
**Block IDs lost after AI edit**: BlockIdExtension must run last in extension array.
**Performance**: React DevTools Profiler. Target: <100ms keystroke, 60fps scroll, <150ms modal.

---

## Submodule Documentation Index

| Module       | Doc                                                            | Covers                                             |
| ------------ | -------------------------------------------------------------- | -------------------------------------------------- |
| Features     | [`src/features/CLAUDE.md`](src/features/CLAUDE.md)             | Feature modules, folder structure, domain overview |
| Stores       | [`src/stores/CLAUDE.md`](src/stores/CLAUDE.md)                 | MobX stores, AI stores, state patterns             |
| Notes/Editor | [`src/features/notes/CLAUDE.md`](src/features/notes/CLAUDE.md) | TipTap extensions, editor setup, ghost text        |
| AI           | [`src/features/ai/CLAUDE.md`](src/features/ai/CLAUDE.md)       | AI integration, SSE streaming, PilotSpaceStore     |
| Services     | [`src/services/CLAUDE.md`](src/services/CLAUDE.md)             | API clients, RFC 7807, query patterns              |
| Components   | [`src/components/CLAUDE.md`](src/components/CLAUDE.md)         | Shared UI, shadcn/ui, accessibility                |
