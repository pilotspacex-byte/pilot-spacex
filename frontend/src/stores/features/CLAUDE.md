# Core Feature Stores

**Scope**: Domain-specific MobX stores (Auth, UI, Workspace, Note, Issue, Cycle, Notification)
**Parent**: [`../CLAUDE.md`](../CLAUDE.md)
**Rule**: MobX for UI state only. TanStack Query for server state (DD-065).

---

## Store Overview

| Store              | File                                    | Purpose                              |
| ------------------ | --------------------------------------- | ------------------------------------ |
| **AuthStore**      | `stores/AuthStore.ts`                   | Supabase auth + session lifecycle    |
| **UIStore**        | `stores/UIStore.ts`                     | Theme, layout, modals, toasts        |
| **WorkspaceStore** | `stores/WorkspaceStore.ts`              | Current workspace + members + roles  |
| **NoteStore**      | `stores/features/notes/NoteStore.ts`    | Editor state, auto-save, annotations |
| **IssueStore**     | `stores/features/issues/IssueStore.ts`  | Filters, sorting, AI suggestions     |
| **CycleStore**     | `stores/features/cycles/CycleStore.ts`  | Cycle CRUD, burndown, velocity       |
| **NotificationStore** | `stores/NotificationStore.ts`        | Notification inbox                   |

All stores are initialized by RootStore and accessed via hooks.

---

## AuthStore

**Implementation**: `AuthStore.ts` (359 lines)

Manages Supabase authentication with session lifecycle.

**Key Observables**: `user: AuthUser | null`, `session: Session | null`, `isLoading`, `error`

**Key Computed**: `isAuthenticated`, `userDisplayName`, `userInitials`

**Key Actions**:
- `login(email, password)`, `loginWithOAuth(provider)`, `signup(email, password, name)`, `logout()`
- `updateProfile(data)`, `resetPassword(email)`, `refreshSession()`

Subscribes to `supabase.auth.onAuthStateChange()` internally. Cleans up subscription in `dispose()`.

---

## UIStore

**Implementation**: `UIStore.ts` (282 lines)

UI layout state with localStorage persistence and theme management.

**Key Observables**:
- Layout: `sidebarCollapsed`, `sidebarWidth` (220-400px), `marginPanelWidth` (150-350px)
- Theme: `theme` ('light'|'dark'|'system'), `hydrated` (SSR-safe flag)
- Modals: `commandPaletteOpen`, `searchModalOpen`, `modals: Map<string, ModalState>`
- Toasts: `toasts: Toast[]` (max 5 visible)

**Key Computed**: `activeToasts`, `resolvedTheme`, `hasOpenModal`

**Key Actions**:
- Layout: `toggleSidebar()`, `setSidebarWidth()`, `setMarginPanelWidth()`
- Theme: `setTheme()` -- auto-persists to localStorage, updates DOM classList
- Modals: `openModal(id, data?)`, `closeModal(id)`, `closeAllModals()`
- Toasts: `showToast()`, `success()`, `error()` (8s auto-dismiss), `warning()`, `info()`

Uses MobX reactions for localStorage persistence. Disposers cleaned in `dispose()`.

---

## WorkspaceStore

**Implementation**: `WorkspaceStore.ts` (200+ lines)

Current workspace and members state.

**Key Observables**: `workspaces: Map`, `currentWorkspaceId`, `members: Map`, `isLoading`, `isSaving`, `error`

**Key Computed**: `currentWorkspace`, `workspaceList` (sorted), `currentMembers`, `memberCount`, `currentUserRole`, `isAdmin`, `isOwner`

**Key Actions**:
- CRUD: `loadWorkspaces()`, `createWorkspace()`, `updateWorkspace()`, `deleteWorkspace()`
- Members: `loadMembers()`, `inviteMember()`, `removeMember()`, `updateMemberRole()`
- Selection: `setCurrentWorkspace(id)`

Cross-store: `setAuthStore()` wires AuthStore for `currentUserRole` computed.

---

## NoteStore

**Implementation**: `features/notes/NoteStore.ts` (300+ lines)

Note editor state with auto-save and dirty tracking (NOT server data).

**Key Observables**:
- `notes: Map` (cache only -- primary in TanStack Query), `currentNoteId`, `isLoading`, `isSaving`
- Auto-save: `lastSavedAt`, `_originalContent` (private, for dirty tracking)
- Editor: `ghostTextSuggestion`, `isGhostTextLoading`
- Annotations: `annotationsMap: Map<string, NoteAnnotation[]>`, `selectedAnnotationId`
- Filters: `pinnedOnly`, `searchQuery`

**Key Computed**: `currentNote`, `notesList`, `filteredNotes`, `hasUnsavedChanges`

**Key Actions**:
- `setCurrentNote(id)`, `loadNote(id)`, `loadNotes()`
- `setSearchQuery()`, `setPinnedOnly()`
- Annotations: `addAnnotation()`, `updateAnnotation()`, `removeAnnotation()`, `selectAnnotation()`

Auto-save uses MobX reaction with 2s debounce on content changes. Tracks dirty state via `hasUnsavedChanges` comparing current vs `_originalContent`.

---

## IssueStore

**Implementation**: `features/issues/IssueStore.ts` (250+ lines)

Issue filtering, sorting, and AI suggestions (NOT server data).

**Key Observables**:
- `issues: Map` (cache only), `currentIssueId`, `isLoading`, `isSaving`
- AI: `aiContext`, `enhancementSuggestion`, `duplicateCheckResult`, `assigneeRecommendations`
- Filters: `filters: IssueFilters`, `groupBy`, `sortBy`, `sortOrder`, `searchQuery`, `viewMode` ('board'|'list'|'table')
- Inline editing: `saveStatus: Map<string, 'idle'|'saving'|'saved'|'error'>`

**Key Actions**:
- Selection: `setCurrentIssue(id)`, `loadIssues()`, `loadIssueDetail(id)`
- Filters: `setFilter()`, `setGroupBy()`, `setSortBy()`, `setSearchQuery()`, `setViewMode()`
- AI: `loadAIContext()`, `enhanceIssue()`, `checkDuplicates()`, `getAssigneeRecommendations()`
- Inline: `updateIssueField(issueId, field, value)` with per-field status

AI suggestion types: `EnhancementSuggestion`, `DuplicateCandidate`, `AssigneeRecommendation` -- see types file.

---

## CycleStore

**Implementation**: `features/cycles/CycleStore.ts` (300+ lines)

Sprint/cycle management with burndown and velocity tracking.

**Key Observables**:
- `cycles: Map`, `currentCycleId`, `cycleIssues: Map`
- Charts: `burndownData`, `velocityData`
- Loading: `isLoading`, `isSaving`, `isLoadingIssues`, `isLoadingBurndown`, `isLoadingVelocity`
- Filters: `filters: CycleFilters`, `sortBy`, `sortOrder`, `currentProjectId`, `currentWorkspaceId`
- Pagination: `nextCursor`, `hasMore`

**Key Computed**: `activeCycle`, `cycleList`, `filteredCycles`

**Key Actions**:
- CRUD: `loadCycles()`, `createCycle()`, `updateCycle()`, `deleteCycle()`, `rolloverCycle()`
- Issues: `loadCycleIssues()`, `assignIssueToCycle()`, `removeIssueFromCycle()`
- Metrics: `loadBurndown()`, `loadVelocity()`
- Filters: `setFilter()`, `setSortBy()`

---

## NotificationStore

**Implementation**: `NotificationStore.ts` (78 lines)

Simple notification inbox (independent of UIStore toast notifications).

**Key Observables**: `notifications: Notification[]`

**Key Computed**: `unreadCount`, `unreadNotifications`, `sortedNotifications`

**Key Actions**: `addNotification()`, `markAsRead()`, `markAllAsRead()`, `removeNotification()`, `clearAll()`

---

## Related Documentation

- **Parent Store Architecture**: [`../CLAUDE.md`](../CLAUDE.md)
- **AI Stores**: [`../ai/CLAUDE.md`](../ai/CLAUDE.md)
- **MobX Patterns**: `docs/dev-pattern/21c-frontend-mobx-state.md`
