# MobX Stores Architecture

**Scope**: Complete MobX state management system
**Rule**: MobX = UI state only. TanStack Query = server state. Never mix (DD-065).

---

## Store Hierarchy

```
RootStore (RootStore.ts)
├── auth: AuthStore              (User authentication + metadata)
├── ui: UIStore                  (Theme, layout, modals, toasts)
├── workspace: WorkspaceStore    (Current workspace + members)
├── notifications: NotificationStore
├── notes: NoteStore             (Editor state, dirty tracking)
├── issues: IssueStore           (Issue filters, sorting, AI suggestions)
├── cycles: CycleStore           (Cycle selection, burndown state)
├── ai: AIStore                  (All AI-related stores)
│   ├── ghostText: GhostTextStore
│   ├── aiContext: AIContextStore
│   ├── approval: ApprovalStore
│   ├── settings: AISettingsStore
│   ├── prReview: PRReviewStore
│   ├── conversation: ConversationStore (Deprecated)
│   ├── cost: CostStore
│   ├── marginAnnotation: MarginAnnotationStore
│   └── pilotSpace: PilotSpaceStore (Unified agent orchestration)
├── onboarding: OnboardingStore  (First-time setup UI)
├── roleSkill: RoleSkillStore    (Role setup wizard UI)
└── homepage: HomepageUIStore    (Home page layout)
```

---

## Submodule Documentation

| Module              | Doc                                        | Covers                                                                |
| ------------------- | ------------------------------------------ | --------------------------------------------------------------------- |
| **AI Stores** (11)  | [`ai/CLAUDE.md`](ai/CLAUDE.md)             | PilotSpaceStore, GhostTextStore, ApprovalStore, AIContextStore, etc.  |
| **Core Stores** (7) | [`features/CLAUDE.md`](features/CLAUDE.md) | AuthStore, UIStore, WorkspaceStore, NoteStore, IssueStore, CycleStore |

---

## RootStore

**Implementation**: `RootStore.ts`

Central hub that coordinates all stores with cross-store references. Initializes all child stores in constructor, wires cross-store dependencies (e.g., `workspace.setAuthStore(auth)`). Provides `reset()` for logout cleanup and `dispose()` for subscription teardown.

**Access via hooks only** (never access `rootStore` directly). See `RootStore.ts` for `useStore()`, `useStores()`, and per-store hooks like `useNoteStore()`.

---

## NotificationStore

**Implementation**: `NotificationStore.ts` (78 lines)

Simple notification inbox (independent of toast notifications). Manages `notifications[]` with `unreadCount`, `markAsRead()`, `markAllAsRead()`, `clearAll()`.

---

## MobX Patterns

- **makeAutoObservable**: Use in constructor. Declare expensive computed properties in second arg.
- **Computed**: Auto-memoized derived values. Depend only on stable observables.
- **Reactions**: Side effects (auto-save, localStorage). Store disposers, clean up in `dispose()`.
- **runInAction**: Required for mutations after `await` in strict mode.
- **observer()**: Wrap all MobX-consuming components. Use named function expressions for stack traces.
- **Cross-store references**: RootStore wires stores in constructor.

See `docs/dev-pattern/21c-frontend-mobx-state.md` for full patterns with examples.

---

## TanStack Query Integration

**Rule**: MobX stores hold selection IDs, filters, modals, editing mode. TanStack Query holds server data via `useQuery`/`useMutation`. Never store API responses in MobX -- keep only IDs and let TanStack manage data lifecycle.

---

## Common Gotchas

| Issue                       | Problem                                         | Solution                                                           |
| --------------------------- | ----------------------------------------------- | ------------------------------------------------------------------ |
| Forgot `observer()`         | Component won't re-render on observable changes | Wrap with `observer(function Name() {...})`                        |
| Missing `runInAction`       | Mutations after `await` trigger warnings        | Wrap post-async mutations: `runInAction(() => { this.data = x; })` |
| Storing API data in MobX    | No caching, manual sync, no refetch            | Keep only IDs in MobX; use TanStack Query for data                 |
| Computed with unstable deps | Infinite loops or stale computed values         | Ensure computed depends only on stable observables                 |
| Forgetting dispose          | Memory leaks from reaction subscriptions        | Store disposers, call in `dispose()` on logout                     |

---

## File Organization

```
frontend/src/stores/
├── RootStore.ts                 # Central hub + hooks
├── AuthStore.ts                 # Authentication
├── UIStore.ts                   # Layout & modals
├── WorkspaceStore.ts            # Workspace & members
├── NotificationStore.ts         # Notifications
├── OnboardingStore.ts           # First-time setup UI
├── RoleSkillStore.ts            # Role setup wizard UI
├── index.ts                     # Barrel exports
├── features/
│   ├── notes/NoteStore.ts
│   ├── issues/IssueStore.ts
│   ├── cycles/CycleStore.ts
│   ├── CLAUDE.md
│   └── index.ts
└── ai/
    ├── AIStore.ts               # Root AI store
    ├── PilotSpaceStore.ts       # Unified agent orchestration
    ├── GhostTextStore.ts        # Inline suggestions
    ├── ... (14 more files)
    ├── CLAUDE.md
    └── index.ts
```

---

## Quick Reference: When to Use Which Store

| Use Case                    | Store                           | Pattern                  |
| --------------------------- | ------------------------------- | ------------------------ |
| User authentication         | AuthStore                       | Supabase + subscriptions |
| Layout (sidebar, theme)     | UIStore                         | Reactions + localStorage |
| Current workspace selection | WorkspaceStore                  | Computed properties      |
| Note editor dirty state     | NoteStore                       | Auto-save + reactions    |
| Issue filters & sorting     | IssueStore                      | Computed filtering       |
| Cycle selection             | CycleStore                      | CRUD + state             |
| Inline text suggestions     | GhostTextStore                  | Debounced + cached       |
| Issue context               | AIContextStore                  | SSE streaming + cache    |
| Human-in-the-loop approvals | ApprovalStore + PilotSpaceStore | Queue + UI state         |
| AI conversations            | PilotSpaceStore                 | SSE + session mgmt       |
| Margin annotations          | MarginAnnotationStore           | Inline UI state          |
| Cost tracking               | CostStore                       | Read-only metrics        |

---

## Related Documentation

- **AI Stores (detailed)**: [`ai/CLAUDE.md`](ai/CLAUDE.md)
- **Core Stores (detailed)**: [`features/CLAUDE.md`](features/CLAUDE.md)
- **MobX Patterns**: `docs/dev-pattern/21c-frontend-mobx-state.md`
- **Frontend Architecture**: `docs/architect/frontend-architecture.md`
