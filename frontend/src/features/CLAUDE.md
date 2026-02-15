# Frontend Features

**Scope**: `frontend/src/features/` (10 feature modules)
**Architecture**: Feature-folder pattern with colocated components, hooks, stores

---

## Module Index

### Core Modules

| Module        | Purpose                                            | Docs                                         |
| ------------- | -------------------------------------------------- | -------------------------------------------- |
| **Notes**     | Block-based editor, ghost text, issue extraction   | [`notes/CLAUDE.md`](notes/CLAUDE.md)         |
| **Issues**    | Issue CRUD, AI context, activity tracking          | [`issues/CLAUDE.md`](issues/CLAUDE.md)       |
| **AI**        | Conversational interface, SSE streaming, approvals | [`ai/CLAUDE.md`](ai/CLAUDE.md)               |
| **Approvals** | Human-in-the-loop workflow (DD-003)                | [`approvals/CLAUDE.md`](approvals/CLAUDE.md) |
| **Cycles**    | Sprint management, burndown charts                 | [`cycles/CLAUDE.md`](cycles/CLAUDE.md)       |
| **Homepage**  | Landing page (Note-First), activity feed, digest   | [`homepage/CLAUDE.md`](homepage/CLAUDE.md)   |

### Integration Modules

| Module           | Purpose                               | Docs                                   |
| ---------------- | ------------------------------------- | -------------------------------------- |
| **GitHub**       | PR review, linking, OAuth             | [`github/CLAUDE.md`](github/CLAUDE.md) |
| **Integrations** | PR review hooks (future integrations) | --                                     |

### Configuration Modules

| Module       | Purpose                                           | Docs                                       |
| ------------ | ------------------------------------------------- | ------------------------------------------ |
| **Settings** | Workspace, members, AI providers, profile, skills | [`settings/CLAUDE.md`](settings/CLAUDE.md) |
| **Costs**    | AI cost tracking by agent/user/day                | [`costs/CLAUDE.md`](costs/CLAUDE.md)       |

### Onboarding

| Module         | Purpose                |
| -------------- | ---------------------- |
| **Onboarding** | 3-step workspace setup |

---

## Shared Patterns

### Feature Module Structure

```
Feature Module/
├── components/               # UI (wrapped with observer() if MobX)
├── hooks/                    # TanStack Query + MobX reactions
├── pages/                    # Next.js app router pages (optional)
├── editor/                   # TipTap extensions (notes only)
├── services/                 # Business logic (optional)
└── CLAUDE.md                 # Feature-specific documentation
```

### State Management (DD-065)

MobX for UI state. TanStack Query for server data. Never store API data in MobX. Wrap MobX-consuming components with `observer()` using named function expressions.

### Optimistic Updates with Rollback

All mutations that update cached data follow the snapshot + rollback pattern: onMutate (cancel queries, snapshot, optimistic patch) -> onError (rollback to snapshot) -> onSettled (invalidate). See `docs/dev-pattern/45-pilot-space-patterns.md` for details.

### Barrel Exports

Every module exposes via `index.ts`: `import { useNotes } from '@/features/notes';`

### File Size Limit

700 lines max (enforced by pre-commit hook). Extract sub-components, hooks, or services when exceeding.

---

## Troubleshooting

| Issue                               | Cause                | Fix                                                  |
| ----------------------------------- | -------------------- | ---------------------------------------------------- |
| Component not re-rendering          | Missing `observer()` | Wrap with `observer(function Component() { ... })`   |
| Query not refetching after mutation | Key mismatch         | Ensure invalidation key matches query key            |
| Infinite scroll not triggering      | Sentinel not visible | Verify sentinel ref + observer threshold             |
| SSE connection dropping             | Token expiration     | Refresh token before connect, exponential backoff    |
| Ghost text not triggering           | Config missing       | Check `debounceMs: 500`, verify `onTrigger` callback |
| Block IDs lost after AI edit        | Extension order      | BlockIdExtension must be last in array               |
