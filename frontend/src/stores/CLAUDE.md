# MobX Stores Architecture

**File**: `frontend/src/stores/CLAUDE.md`
**Scope**: Complete MobX state management system
**Last Updated**: 2026-02-10

## Overview

This directory contains MobX stores that manage **UI state only** (per DD-065). Server state is managed exclusively by TanStack Query.

**Core Philosophy**:
- **MobX = UI State**: Local UI interactions, modals, theme, sidebar collapsed, etc.
- **TanStack Query = Server State**: Notes, issues, cycles, workspace members, etc.
- **Never mix**: Do not store API responses in MobX. Do not fetch in TanStack Query selectors.

**Store Hierarchy**:

```
RootStore
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

## RootStore

**File**: `frontend/src/stores/RootStore.ts`

Central hub that coordinates all stores with cross-store references.

### Structure

```tsx
export class RootStore {
  auth: AuthStore;
  ui: UIStore;
  workspace: WorkspaceStore;
  notifications: NotificationStore;
  notes: NoteStore;
  issues: IssueStore;
  cycles: CycleStore;
  ai: AIStore;
  onboarding: OnboardingStore;
  roleSkill: RoleSkillStore;
  homepage: HomepageUIStore;

  constructor() {
    // Initialize all stores
    this.auth = new AuthStore();
    this.ui = new UIStore();
    // ...
    // Wire cross-store references
    this.workspace.setAuthStore(this.auth);
  }

  reset(): void {
    // Reset all stores on logout
  }

  dispose(): void {
    // Clean up subscriptions
  }
}
```

### Hooks

Use these hooks to access stores in components. **Always use hooks, never access `rootStore` directly**.

```tsx
// Single store hook
const { noteStore } = useStore();
const noteStore = useNoteStore();

// Multiple stores
const { noteStore, issueStore, cycleStore } = useStore();

// Root store (rarely needed)
const root = useStores();
```

### Error Handling

```tsx
// ❌ Wrong - accessing outside provider
const store = rootStore.notes;

// ✅ Correct - use hook
function MyComponent() {
  const noteStore = useNoteStore();
  // ...
}
```

---

## Core Stores

### AuthStore

**File**: `frontend/src/stores/AuthStore.ts` (359 lines)

Manages Supabase authentication with session lifecycle.

**Observable Properties**:

```tsx
class AuthStore {
  // Auth state
  user: AuthUser | null = null;           // Current user
  session: Session | null = null;         // Supabase session
  isLoading = true;                       // Loading initial state
  error: string | null = null;

  // Computed
  get isAuthenticated(): boolean;         // user !== null && session !== null
  get userDisplayName(): string;          // name or email prefix
  get userInitials(): string;             // 1-2 letter initials (e.g., "TD")
}
```

**Actions**:

```tsx
// Login/signup
async login(email: string, password: string): Promise<boolean>;
async loginWithOAuth(provider: 'github' | 'google'): Promise<void>;
async signup(email: string, password: string, name: string): Promise<boolean>;
async logout(): Promise<void>;

// Profile updates
async updateProfile(data: { name?: string; avatarUrl?: string }): Promise<boolean>;
async resetPassword(email: string): Promise<boolean>;
async refreshSession(): Promise<boolean>;

// Error handling
clearError(): void;
```

**Patterns**:

```tsx
// Subscription to auth changes
private subscribeToAuthChanges(): void {
  const { data } = supabase.auth.onAuthStateChange((event, session) => {
    runInAction(() => {
      this.session = session;
      this.user = session ? this.mapSupabaseUser(session.user) : null;
    });
  });
  this.authSubscription = data.subscription;
}

// Cleanup on dispose
dispose(): void {
  if (this.authSubscription) {
    this.authSubscription.unsubscribe();
  }
}
```

**Usage**:

```tsx
export default function LoginForm() {
  const authStore = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await authStore.login(email, password);
    if (success) {
      // AuthStore subscription redirects on success
    }
  };

  return (
    <div>
      {authStore.error && <Alert>{authStore.error}</Alert>}
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button disabled={authStore.isLoading} onClick={handleSubmit}>
        Sign In
      </button>
    </div>
  );
}
```

### UIStore

**File**: `frontend/src/stores/UIStore.ts` (282 lines)

UI layout state with localStorage persistence and theme management.

**Observable Properties**:

```tsx
class UIStore {
  // Layout
  sidebarCollapsed = false;               // Sidebar toggle
  sidebarWidth = 260;                     // Resizable width
  marginPanelWidth = 200;                 // Annotations panel width

  // Theme
  theme: Theme = 'system';                // 'light' | 'dark' | 'system'
  hydrated = false;                       // SSR-safe hydration flag

  // Modals & Overlays
  commandPaletteOpen = false;
  searchModalOpen = false;
  modals: Map<string, ModalState> = new Map();  // Named modals
  toasts: Toast[] = [];                   // Toast notifications (max 5 visible)

  // Computed
  get activeToasts(): Toast[];            // First 5 toasts
  get resolvedTheme(): 'light' | 'dark'; // Computed from system preference
  get hasOpenModal(): boolean;            // Any modal open?
}
```

**Actions - Layout**:

```tsx
toggleSidebar(): void;                    // Toggle collapsed state
setSidebarCollapsed(collapsed: boolean): void;
setSidebarWidth(width: number): void;     // Clamped 220-400px
setMarginPanelWidth(width: number): void; // Clamped 150-350px
```

**Actions - Theme**:

```tsx
setTheme(theme: Theme): void;

// Reactions automatically:
// 1. Persist to localStorage
// 2. Update DOM classList (light/dark)
// 3. Trigger re-render via MobX
```

**Actions - Modals**:

```tsx
openModal(id: string, data?: unknown): void;   // Set isOpen=true, optional data
closeModal(id: string): void;                  // Set isOpen=false
getModalState(id: string): ModalState | undefined;
isModalOpen(id: string): boolean;
closeAllModals(): void;
```

**Actions - Toasts**:

```tsx
showToast(toast: Omit<Toast, 'id'>): string;   // Returns toast ID
dismissToast(id: string): void;                 // Remove immediately
success(title: string, description?: string): string;
error(title: string, description?: string): string;  // Auto-dismiss 8s
warning(title: string, description?: string): string;
info(title: string, description?: string): string;
clearAllToasts(): void;
```

**Persistence with Reactions**:

```tsx
constructor() {
  makeAutoObservable(this, {
    activeToasts: computed,
    resolvedTheme: computed,
    hasOpenModal: computed,
  });
  this.setupPersistence();
}

private setupPersistence(): void {
  // Save layout to localStorage on change
  const persistDisposer = reaction(
    () => ({
      sidebarCollapsed: this.sidebarCollapsed,
      sidebarWidth: this.sidebarWidth,
      marginPanelWidth: this.marginPanelWidth,
      theme: this.theme,
    }),
    (state) => {
      localStorage.setItem(UI_STORAGE_KEY, JSON.stringify(state));
    }
  );

  // Apply resolved theme to DOM
  const themeDisposer = reaction(
    () => this.resolvedTheme,
    (theme) => {
      document.documentElement.classList.remove('light', 'dark');
      document.documentElement.classList.add(theme);
    },
    { fireImmediately: true }
  );

  this.reactionDisposers.push(persistDisposer, themeDisposer);
}

dispose(): void {
  for (const disposer of this.reactionDisposers) {
    disposer();
  }
}
```

**Usage**:

```tsx
import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';

export const Sidebar = observer(function Sidebar() {
  const { uiStore } = useStore();

  return (
    <aside
      className={uiStore.sidebarCollapsed ? 'w-0' : 'w-60'}
      style={{ width: uiStore.sidebarWidth }}
    >
      {/* Sidebar content */}
    </aside>
  );
});

export const Toast = observer(function Toast() {
  const { uiStore } = useStore();

  return (
    <div className="toast-stack">
      {uiStore.activeToasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.variant}`}>
          {toast.title}
          <button onClick={() => uiStore.dismissToast(toast.id)}>×</button>
        </div>
      ))}
    </div>
  );
});
```

### WorkspaceStore

**File**: `frontend/src/stores/WorkspaceStore.ts` (200+ lines)

Current workspace and members state.

**Observable Properties**:

```tsx
class WorkspaceStore {
  workspaces: Map<string, Workspace> = new Map();  // All workspaces user can access
  currentWorkspaceId: string | null = null;        // Currently selected workspace
  members: Map<string, WorkspaceMember[]> = new Map();
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  // Computed
  get currentWorkspace(): Workspace | null;
  get workspaceList(): Workspace[];               // Sorted by name
  get currentMembers(): WorkspaceMember[];
  get memberCount(): number;
  get currentUserRole(): WorkspaceRole | null;    // From AuthStore + members
  get isAdmin(): boolean;                         // role === 'admin' || 'owner'
  get isOwner(): boolean;                         // role === 'owner'
}
```

**Actions**:

```tsx
// CRUD
async loadWorkspaces(): Promise<void>;
async createWorkspace(data: CreateWorkspaceData): Promise<Workspace>;
async updateWorkspace(id: string, data: UpdateWorkspaceData): Promise<Workspace>;
async deleteWorkspace(id: string): Promise<void>;

// Members
async loadMembers(workspaceId: string): Promise<void>;
async inviteMember(workspaceId: string, data: InviteMemberData): Promise<WorkspaceMember>;
async removeMember(workspaceId: string, memberId: string): Promise<void>;
async updateMemberRole(workspaceId: string, memberId: string, role: WorkspaceRole): Promise<void>;

// Selection
setCurrentWorkspace(id: string): void;

// Lifecycle
reset(): void;
```

**Cross-Store Reference**:

```tsx
constructor() {
  makeAutoObservable(this, { currentWorkspace: computed, /* ... */ });
  this.loadFromStorage(); // Restore last workspace
}

setAuthStore(authStore: AuthStore): void {
  this.authStore = authStore;
}

get currentUserRole(): WorkspaceRole | null {
  const userId = this.authStore?.user?.id;  // Cross-store reference
  if (!userId || !this.currentWorkspaceId) return null;
  const members = this.members.get(this.currentWorkspaceId);
  const member = members?.find((m) => m.userId === userId);
  return member?.role ?? null;
}
```

### NotificationStore

**File**: `frontend/src/stores/NotificationStore.ts` (78 lines)

Simple notification inbox (independent of toast notifications).

**Observable Properties**:

```tsx
class NotificationStore {
  notifications: Notification[] = [];

  // Computed
  get unreadCount(): number;
  get unreadNotifications(): Notification[];
  get sortedNotifications(): Notification[];  // By createdAt descending
}
```

**Actions**:

```tsx
addNotification(notification: Omit<Notification, 'id' | 'createdAt' | 'read'>): void;
markAsRead(id: string): void;
markAllAsRead(): void;
removeNotification(id: string): void;
clearAll(): void;
```

---

## Domain Stores (Feature-Based)

### NoteStore

**File**: `frontend/src/stores/features/notes/NoteStore.ts` (300+ lines)

Note editor state with auto-save and dirty tracking (but NOT server data).

**Observable Properties**:

```tsx
class NoteStore {
  // Core state
  notes: Map<string, Note> = new Map();      // Cache only (primary in TanStack Query)
  currentNoteId: string | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  // Auto-save tracking
  lastSavedAt: Date | null = null;
  private _originalContent: string | null = null;

  // Editor state
  ghostTextSuggestion: GhostTextSuggestion | null = null;
  isGhostTextLoading = false;

  // Annotations (per note)
  annotationsMap: Map<string, NoteAnnotation[]> = new Map();
  selectedAnnotationId: string | null = null;

  // Filters
  pinnedOnly = false;
  searchQuery = '';

  // Computed
  get currentNote(): Note | null;
  get notesList(): Note[];
  get filteredNotes(): Note[];  // Apply pinnedOnly + searchQuery filters
  get hasUnsavedChanges(): boolean;
}
```

**Auto-Save Pattern with Reactions**:

```tsx
constructor() {
  makeAutoObservable(this, {}, { autoBind: true });

  // Set up auto-save reaction
  this._disposers.push(
    reaction(
      () => this.currentNote?.content,  // Track content changes
      () => {
        if (this.hasUnsavedChanges) {
          this._scheduleAutoSave();
        }
      },
      { delay: AUTO_SAVE_DEBOUNCE_MS }  // 2000ms debounce
    )
  );
}

private _scheduleAutoSave(): void {
  if (this._autoSaveTimer) clearTimeout(this._autoSaveTimer);

  this._autoSaveTimer = setTimeout(() => {
    this.saveCurrentNote();  // Triggers TanStack mutation
  }, AUTO_SAVE_DEBOUNCE_MS);
}

get hasUnsavedChanges(): boolean {
  const current = this.currentNote?.content;
  return current !== this._originalContent;
}
```

**Actions**:

```tsx
// Selection
setCurrentNote(id: string): void;

// Fetching (delegates to TanStack Query, updates cache)
async loadNote(id: string): Promise<void>;
async loadNotes(): Promise<void>;

// Saving
private async saveCurrentNote(): Promise<void>;

// Filtering/Search
setSearchQuery(query: string): void;
setPinnedOnly(pinned: boolean): void;

// Annotations
addAnnotation(noteId: string, annotation: NoteAnnotation): void;
updateAnnotation(noteId: string, annotationId: string, updates: Partial<NoteAnnotation>): void;
removeAnnotation(noteId: string, annotationId: string): void;
selectAnnotation(id: string | null): void;

// Cleanup
reset(): void;
```

**Key Insight: Separation of Concerns**:

```tsx
// ❌ Wrong - full server response in MobX
class BadStore {
  note: Note | null = null;  // API response stored in MobX
  saveNote() {
    this.note = await noteApi.update(this.note);  // Direct mutation
  }
}

// ✅ Correct - UI state in MobX, server state in TanStack
class GoodStore {
  currentNoteId: string | null = null;  // Only ID in MobX
  isSaving = false;                     // UI state

  // Component uses TanStack Query separately:
  // const { data: note } = useQuery(['notes', noteId], ...)
  // const saveMutation = useMutation(noteApi.update, ...)
}
```

### IssueStore

**File**: `frontend/src/stores/features/issues/IssueStore.ts` (250+ lines)

Issue filtering, sorting, and AI suggestions (but NOT server data).

**Observable Properties**:

```tsx
class IssueStore {
  issues: Map<string, Issue> = new Map();   // Cache only
  currentIssueId: string | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  // AI Context (aggregated via AIContextStore)
  aiContext: AIContext | null = null;
  isLoadingAIContext = false;

  // AI Enhancement suggestions
  enhancementSuggestion: EnhancementSuggestion | null = null;
  isLoadingEnhancement = false;
  duplicateCheckResult: DuplicateCheckResult | null = null;
  isCheckingDuplicates = false;
  assigneeRecommendations: AssigneeRecommendation[] = [];

  // Filters & Sorting
  filters: IssueFilters = {};     // state, priority, type, assignee, project
  groupBy: GroupBy = 'state';     // 'state' | 'priority' | 'assignee' | 'project'
  sortBy: SortBy = 'updated';     // 'created' | 'updated' | 'priority' | 'title'
  sortOrder: SortOrder = 'desc';
  searchQuery = '';
  viewMode: 'board' | 'list' | 'table' = 'board';

  // Per-field save status for inline editing
  saveStatus: Map<string, 'idle' | 'saving' | 'saved' | 'error'> = new Map();
}
```

**AI Suggestion Types**:

```tsx
export interface EnhancementSuggestion {
  enhancedTitle: string;
  enhancedDescription: string | null;
  suggestedLabels: LabelSuggestion[];
  suggestedPriority: PrioritySuggestion | null;
  titleEnhanced: boolean;
  descriptionExpanded: boolean;
}

export interface DuplicateCandidate {
  issueId: string;
  identifier: string;
  title: string;
  similarity: number;        // 0-1, threshold: 0.7
  explanation: string | null;
}
```

**Actions**:

```tsx
// Selection & Fetching
setCurrentIssue(id: string): void;
async loadIssues(filters?: IssueFilters): Promise<void>;
async loadIssueDetail(id: string): Promise<void>;

// Filtering & Sorting
setFilter(key: keyof IssueFilters, value: any): void;
setGroupBy(groupBy: GroupBy): void;
setSortBy(sortBy: SortBy, order?: SortOrder): void;
setSearchQuery(query: string): void;
setViewMode(mode: 'board' | 'list' | 'table'): void;

// AI Enhancement (delegates to AIContextStore)
async loadAIContext(issueId: string): Promise<void>;
async enhanceIssue(issueId: string, title: string, description?: string): Promise<void>;
async checkDuplicates(issueId: string): Promise<void>;
async getAssigneeRecommendations(issueId: string): Promise<void>;

// Inline editing with per-field status
async updateIssueField(issueId: string, field: string, value: any): Promise<void>;

// Cleanup
reset(): void;
```

### CycleStore

**File**: `frontend/src/stores/features/cycles/CycleStore.ts` (300+ lines)

Sprint/cycle management with burndown and velocity tracking.

**Observable Properties**:

```tsx
class CycleStore {
  // Cycle state
  cycles: Map<string, Cycle> = new Map();
  currentCycleId: string | null = null;
  cycleIssues: Map<string, CycleIssue> = new Map();

  // Chart data
  burndownData: BurndownChartData | null = null;
  velocityData: VelocityChartData | null = null;

  // Loading states
  isLoading = false;
  isSaving = false;
  isLoadingIssues = false;
  isLoadingBurndown = false;
  isLoadingVelocity = false;
  error: string | null = null;

  // Filters & Pagination
  filters: CycleFilters = {};
  sortBy: SortBy = 'sequence';
  sortOrder: SortOrder = 'desc';
  currentProjectId: string | null = null;
  currentWorkspaceId: string | null = null;
  nextCursor: string | null = null;
  hasMore = false;

  // Computed
  get activeCycle(): Cycle | null;
  get cycleList(): Cycle[];
  get filteredCycles(): Cycle[];
}
```

**Actions**:

```tsx
// CRUD
async loadCycles(workspaceId: string, projectId: string): Promise<void>;
async createCycle(data: CreateCycleData): Promise<Cycle>;
async updateCycle(id: string, data: UpdateCycleData): Promise<Cycle>;
async deleteCycle(id: string): Promise<void>;
async rolloverCycle(cycleId: string, data: RolloverCycleData): Promise<RolloverCycleResult>;

// Selection
setCurrentCycle(id: string | null): void;

// Issues
async loadCycleIssues(cycleId: string): Promise<void>;
async assignIssueToCycle(issueId: string, cycleId: string): Promise<void>;
async removeIssueFromCycle(issueId: string): Promise<void>;

// Metrics
async loadBurndown(cycleId: string): Promise<void>;
async loadVelocity(projectId: string): Promise<void>;

// Filters
setFilter(key: keyof CycleFilters, value: any): void;
setSortBy(sortBy: SortBy, order?: SortOrder): void;

// Cleanup
reset(): void;
```

---

## AI Stores (AIStore Hub)

**File**: `frontend/src/stores/ai/` (Directory with 12+ files)

All AI-related state management centralized under `AIStore` root.

### AIStore (Root)

**File**: `frontend/src/stores/ai/AIStore.ts` (85 lines)

Container and lifecycle manager for all AI feature stores.

```tsx
export class AIStore {
  ghostText: GhostTextStore;
  aiContext: AIContextStore;
  approval: ApprovalStore;
  settings: AISettingsStore;
  prReview: PRReviewStore;
  conversation: ConversationStore;    // Deprecated
  cost: CostStore;
  marginAnnotation: MarginAnnotationStore;
  pilotSpace: PilotSpaceStore;         // Unified agent

  isGloballyEnabled = true;             // Master switch
  globalError: string | null = null;

  constructor() {
    makeAutoObservable(this);
    this.ghostText = new GhostTextStore(this);
    this.aiContext = new AIContextStore(this);
    // ... initialize all sub-stores
  }

  async loadWorkspaceSettings(workspaceId: string): Promise<void> {
    await this.settings.loadSettings(workspaceId);
    // Update feature availability
    this.ghostText.setEnabled(this.settings.ghostTextEnabled);
    this.aiContext.setEnabled(this.settings.aiContextEnabled);
  }

  abortAllStreams(): void {
    this.ghostText.abort();
    this.aiContext.abort();
    this.prReview.abort();
    this.pilotSpace.abort();
    // Abort all active SSE streams
  }

  reset(): void {
    // Reset all sub-stores
  }
}
```

### GhostTextStore

**File**: `frontend/src/stores/ai/GhostTextStore.ts` (155 lines)

Inline text suggestions with debouncing and caching (per DD-067: Gemini Flash, <2s).

**Observable Properties**:

```tsx
class GhostTextStore {
  suggestion = '';               // Suggested text
  isLoading = false;             // Fetching state
  isEnabled = true;              // Toggle
  error: string | null = null;

  private abortController: AbortController | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private cache = new Map<string, string>();  // LRU cache (max 10 items)
}
```

**Actions**:

```tsx
requestSuggestion(
  noteId: string,
  context: string,     // Last 500 chars of note
  prefix: string,      // What user just typed (last 200 chars)
  workspaceId: string
): void;

clearSuggestion(): void;
abort(): void;         // Cancel in-flight request
setEnabled(enabled: boolean): void;
```

**Pattern: Debounced + Cached**:

```tsx
requestSuggestion(noteId: string, context: string, prefix: string, workspaceId: string): void {
  if (!this.isEnabled || !this.rootStore.isGloballyEnabled) return;

  // Check cache first
  const cacheKey = `${noteId}:${context.slice(-100)}:${prefix.slice(-50)}`;
  const cached = this.cache.get(cacheKey);
  if (cached) {
    this.suggestion = cached;
    return;
  }

  // Debounce - GhostTextExtension already debounces 500ms
  if (this.debounceTimer) clearTimeout(this.debounceTimer);
  this.debounceTimer = setTimeout(() => {
    this.fetchSuggestion(context, prefix, workspaceId, cacheKey);
  }, 0);  // No additional delay
}

private async fetchSuggestion(...): Promise<void> {
  this.abortController = new AbortController();
  try {
    const response = await fetch(aiApi.getGhostTextUrl(''), {
      method: 'POST',
      body: JSON.stringify({ context, prefix, workspace_id: workspaceId }),
      signal: this.abortController.signal,
    });

    if (!response.ok && response.status === 429) {
      // Rate limited - silently ignore, don't show error
      return;
    }

    const data = await response.json();
    runInAction(() => {
      this.suggestion = data.suggestion ?? '';
      // Add to cache (LRU: drop oldest if >10)
      this.cache.set(cacheKey, this.suggestion);
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      // User continued typing, request was aborted - not an error
      return;
    }
    runInAction(() => {
      this.error = err.message;
    });
  }
}
```

### ApprovalStore

**File**: `frontend/src/stores/ai/ApprovalStore.ts` (150+ lines)

Human-in-the-loop approval workflow (DD-003).

**Observable Properties**:

```tsx
class ApprovalStore {
  requests: ApprovalRequest[] = [];
  pendingCount = 0;
  isLoading = false;
  error: string | null = null;
  selectedRequest: ApprovalRequest | null = null;
  filter: 'pending' | 'approved' | 'rejected' | 'expired' | undefined = 'pending';

  // Computed
  get groupedByAgent(): Record<string, ApprovalRequest[]>;
}
```

**Actions**:

```tsx
async loadPending(): Promise<void>;
async loadAll(status?: ApprovalStatus): Promise<void>;
async approveRequest(requestId: string): Promise<void>;
async rejectRequest(requestId: string, reason?: string): Promise<void>;
selectRequest(request: ApprovalRequest | null): void;
setFilter(filter: ApprovalFilter): void;
```

### AIContextStore

**File**: `frontend/src/stores/ai/AIContextStore.ts` (200+ lines)

Issue context aggregation with SSE streaming and structured sections.

**Observable Properties**:

```tsx
class AIContextStore {
  isLoading = false;
  isEnabled = true;
  error: string | null = null;
  currentIssueId: string | null = null;
  phases: AIContextPhase[] = [];      // Legacy
  result: AIContextResult | null = null;
  sectionErrors: Map<string, string> = new Map();

  private client: SSEClient | null = null;
  private cache = new Map<string, AIContextResult>();  // Max 20 items
}
```

**Result Structure**:

```tsx
export interface AIContextResult {
  summary: ContextSummary | null;        // Issue title + description
  relatedIssues: ContextRelatedIssue[]; // Blocking/blocked_by/relates
  relatedDocs: ContextRelatedDoc[];     // API docs, ADRs
  tasks: ContextTask[];                 // Subtasks with estimates
  prompts: ContextPrompt[];             // Claude Code prompts
}
```

**Actions**:

```tsx
async generateContext(issueId: string): Promise<void>;
  // Stream SSE from /api/v1/ai/context/{issueId}
  // Populate sections as they arrive

abort(): void;
setEnabled(enabled: boolean): void;
getContextForIssue(issueId: string): AIContextResult | null;  // Cached
```

### PilotSpaceStore (Unified Agent)

**File**: `frontend/src/stores/ai/PilotSpaceStore.ts` (581 lines)

Central orchestration for all user-facing AI conversations per DD-086.

**Observable Properties** (Categories):

```tsx
class PilotSpaceStore {
  // ====== Messages & Streaming ======
  messages: ChatMessage[] = [];           // Full conversation history
  streamingState: StreamingState = {
    isStreaming: false,
    streamContent: '',                    // Accumulated text delta
    currentMessageId: null,
    thinkingContent: '',
    isThinking: false,
    thinkingStartedAt: null,
    activeToolName: null,
    interrupted: false,
    wordCount: 0,
  };

  // ====== Session Management ======
  sessionId: string | null = null;
  sessionState: SessionState = {
    sessionId: null,
    isActive: false,
    createdAt: null,
    lastActivityAt: null,
  };
  forkSessionId: string | null = null;   // For "what-if" branches

  // ====== Message Pagination (Scroll-Up Loading) ======
  totalMessages: number = 0;
  hasMoreMessages: boolean = false;
  isLoadingMoreMessages: boolean = false;

  // ====== Tasks & Approvals ======
  tasks = new Map<string, TaskState>();
  pendingApprovals: ApprovalRequest[] = [];
  pendingContentUpdates: ContentUpdateEvent['data'][] = [];

  // ====== Context ======
  noteContext: NoteContext | null = null;        // Selected text/blocks
  issueContext: IssueContext | null = null;
  projectContext: { projectId: string; name?: string; slug?: string } | null = null;
  workspaceId: string | null = null;

  // ====== Pending Operations ======
  activeSkill: { name: string; args?: string } | null = null;
  mentionedAgents: string[] = [];
  pendingAIBlockIds: string[] = [];
  pendingNoteEndScroll = false;

  // ====== Skill Registry ======
  skills: SkillDefinition[] = [];

  // ====== Error State ======
  error: string | null = null;

  // ====== Delegates ======
  private readonly streamHandler: PilotSpaceStreamHandler;
  private readonly actions: PilotSpaceActions;

  // ====== Computed ======
  get isStreaming(): boolean;
  get streamContent(): string;
  get pendingToolCalls(): ToolCall[];
  get hasUnresolvedApprovals(): boolean;
  get activeTasks(): TaskState[];       // filter status === 'pending' || 'in_progress'
  get completedTasks(): TaskState[];    // filter status === 'completed'
  get conversationContext(): ConversationContext | null;  // Composite context
  get tokenBudgetPercent(): number;     // (sessionState.totalTokens / 8000) * 100
}
```

**Task State**:

```tsx
export interface TaskState {
  id: string;
  subject: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;                     // 0-100%
  description?: string;
  currentStep?: string;
  totalSteps?: number;
  estimatedSecondsRemaining?: number;
  agentName?: string;                   // Subagent executing task
  model?: string;                       // Claude Opus, Sonnet, etc.
  createdAt: Date;
  updatedAt: Date;
}
```

**Approval Request**:

```tsx
export interface ApprovalRequest {
  requestId: string;
  actionType: string;                   // 'delete_issue', 'merge_pr', etc.
  description: string;
  consequences?: string;
  affectedEntities: Array<{
    type: string;
    id: string;
    name: string;
    preview?: unknown;
  }>;
  urgency: 'low' | 'medium' | 'high';
  proposedContent?: unknown;
  expiresAt: Date;                      // 24h TTL
  confidenceTag?: ConfidenceTag;
  createdAt: Date;
}
```

**Actions - Message Management**:

```tsx
addMessage(message: ChatMessage): void;
prependMessages(messages: ChatMessage[]): void;  // Scroll-up loading
setMessagePaginationState(hasMore: boolean, total: number): void;
setIsLoadingMoreMessages(loading: boolean): void;
updateStreamingState(state: Partial<StreamingState>): void;
```

**Actions - Task Management**:

```tsx
addTask(taskId: string, update: Partial<Omit<TaskState, 'id'>>): void;
updateTaskStatus(taskId: string, status: TaskStatus): void;
removeTask(taskId: string): void;
```

**Actions - Approval Management**:

```tsx
addApproval(request: ApprovalRequest): void;
async approveRequest(requestId: string): Promise<void>;
async rejectRequest(requestId: string, reason?: string): Promise<void>;
async approveAction(id: string, modifications?: Record<string, unknown>): Promise<void>;
async rejectAction(id: string, reason: string): Promise<void>;
```

**Actions - Context Management**:

```tsx
setWorkspaceId(workspaceId: string | null): void;
setNoteContext(context: NoteContext | null): void;
setIssueContext(context: IssueContext | null): void;
setProjectContext(context: { projectId: string; name?: string; slug?: string } | null): void;
clearContext(): void;
setActiveSkill(skill: string, args?: string): void;
addMentionedAgent(agent: string): void;
```

**Actions - Delegated to PilotSpaceActions**:

```tsx
/**
 * Send message to AI and stream response via SSE.
 * Handles:
 * - Session resumption (forkSessionId consumed)
 * - Skill activation (activeSkill consumed)
 * - Context injection (noteContext, issueContext, etc.)
 * - Token budget tracking (8K limit)
 */
async sendMessage(content: string, metadata?: Partial<MessageMetadata>): Promise<void>;

/**
 * Submit answer to pending agent question.
 */
async submitQuestionAnswer(questionId: string, answer: string): Promise<void>;

/**
 * Abort current streaming response.
 */
abort(): void;

/**
 * Clear all messages.
 */
clearConversation(): void;

/**
 * Full reset (logout/workspace change).
 */
reset(): void;
```

**Buffering Patterns (T63, T64)**:

During SSE streaming, events may arrive before `message_stop`:

```tsx
// Pending tool calls (buffered during streaming)
private _pendingToolCalls: ToolCall[] = [];

addPendingToolCall(tc: ToolCall): void;
findPendingToolCall(toolUseId: string): ToolCall | undefined;
consumePendingToolCalls(): ToolCall[] | undefined;  // Called on message_stop

// Pending citations (buffered during streaming)
private _pendingCitations: ChatMessage['citations'] = [];

addPendingCitations(citations: NonNullable<ChatMessage['citations']>): void;
consumePendingCitations(): ChatMessage['citations'] | undefined;
```

**Content Update Handling**:

```tsx
// Buffer content updates (up to 100)
pendingContentUpdates: ContentUpdateEvent['data'][] = [];

handleContentUpdate(event: ContentUpdateEvent): void {
  runInAction(() => {
    if (this.pendingContentUpdates.length >= 100) {
      this.pendingContentUpdates.shift();  // FIFO overflow
    }
    this.pendingContentUpdates.push(event.data);
  });
}

// Consume by note ID
consumeContentUpdate(noteId: string): ContentUpdateEvent['data'] | undefined {
  return runInAction(() => {
    const idx = this.pendingContentUpdates.findIndex((u) => u.noteId === noteId);
    if (idx >= 0) {
      return this.pendingContentUpdates.splice(idx, 1)[0];
    }
    return undefined;
  });
}
```

### MarginAnnotationStore

**File**: `frontend/src/stores/ai/MarginAnnotationStore.ts`

Margin annotations (inline AI suggestions) per block.

```tsx
class MarginAnnotationStore {
  annotations: Map<string, NoteAnnotation[]> = new Map();  // noteId -> annotations
  isLoading = false;
  isEnabled = true;
  error: string | null = null;

  async generateAnnotations(noteId: string, content: string): Promise<void>;
  acceptAnnotation(noteId: string, annotationId: string): void;
  rejectAnnotation(noteId: string, annotationId: string): void;
  clearAnnotations(noteId: string): void;
}
```

### CostStore

**File**: `frontend/src/stores/ai/CostStore.ts`

Token usage and cost tracking.

```tsx
class CostStore {
  costs: AICost[] = [];
  isLoading = false;

  async loadCosts(workspaceId: string, dateRange: DateRange): Promise<void>;
  getCostByAgent(): Record<string, number>;
  getCostTrend(days: number): CostTrendData[];
  getTotalCost(dateRange?: DateRange): number;
}
```

### Other AI Stores

- **AISettingsStore**: Workspace AI feature flags
- **PRReviewStore**: PR review state (legacy)
- **ConversationStore**: Legacy (replaced by PilotSpaceStore)

---

## MobX Patterns & Best Practices

**Core Pattern**: Use `makeAutoObservable(this)` to automatically track observables and actions.

```tsx
export class IssueStore {
  issues: Map<string, Issue> = new Map();
  selectedId: string | null = null;
  filters: IssueFilters = {};
  isLoading = false;

  constructor() {
    makeAutoObservable(this, { filteredIssues: computed });
  }

  // Computed: auto-memoized, runs only if dependencies change
  get filteredIssues(): Issue[] {
    return Array.from(this.issues.values()).filter((i) => {
      if (this.filters.state && i.state !== this.filters.state) return false;
      if (this.filters.priority && i.priority !== this.filters.priority) return false;
      return true;
    });
  }

  // Action: automatic mutation tracking
  setSelectedId(id: string | null): void {
    this.selectedId = id;
  }
}

// Observer: wrap components to subscribe to observable changes
export const IssueList = observer(function IssueList() {
  const { issueStore } = useStore();
  return (
    <ul>
      {issueStore.filteredIssues.map((i) => (
        <li key={i.id}>{i.title}</li>
      ))}
    </ul>
  );
});
```

**Key Patterns**:
- **makeAutoObservable**: Enable automatic tracking. Declare expensive computed properties in second arg.
- **Computed**: Auto-memoized, runs only if dependencies change (fast).
- **Reactions**: Side effects (auto-save, localStorage, fetches). Set up in constructor, store disposers, clean up in `dispose()`.
- **runInAction**: Wrap mutations after `await`. Required in strict mode.
- **observer()**: Wrap all components reading observables. Use named function expressions for stack traces.
- **autoBind: true**: Auto-bind methods so `onClick={store.action}` works without `() =>`.
- **Cross-store references**: RootStore wires stores in constructor (e.g., `workspace.setAuthStore(auth)`).
- **Cleanup**: Dispose reactions on logout via `dispose()` method.

---

## Integration with TanStack Query

**Golden Rule**: MobX = UI state (selectedId, filters, modals). TanStack Query = server state (notes, issues, cycles).

**Correct Pattern**:
- MobX stores: Visibility, selection, form inputs, editing mode
- TanStack hooks: useQuery for fetches, useMutation for updates with optimistic updates + rollback
- Never store API responses in MobX

**Anti-Pattern**: ❌ Storing API data in MobX
```tsx
class BadStore {
  issue: Issue | null = null;  // ❌ No caching, manual sync, no refetch
}

class GoodStore {
  selectedIssueId: string | null = null;  // ✅ Only ID, let TanStack manage data
}
// Component: const { data: issue } = useQuery(['issues', selectedIssueId], ...)
```

---

## Common Gotchas & Solutions

| Issue | Problem | Solution |
|-------|---------|----------|
| Forgot `observer()` | Component won't re-render on observable changes | Wrap with `observer(function Name() {...})` |
| Missing `runInAction` | Mutations after `await` trigger warnings in strict mode | Wrap post-async mutations: `runInAction(() => { this.data = x; })` |
| Storing API data | No caching, manual sync, no refetch | Keep only IDs in MobX; store responses in TanStack Query |
| Computed with unstable deps | Infinite loops or stale computed values | Ensure computed depends only on stable observables |
| Forgetting dispose | Memory leaks from reaction subscriptions | Store disposers, call in `dispose()` on logout |

---

---

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
│   ├── notes/
│   │   ├── NoteStore.ts         # Note editor state
│   │   └── index.ts
│   ├── issues/
│   │   ├── IssueStore.ts        # Issue filters & state
│   │   └── index.ts
│   ├── cycles/
│   │   ├── CycleStore.ts        # Cycle management
│   │   ├── cycle-store-types.ts # Types
│   │   ├── cycle-store-actions.ts # Data loading actions
│   │   └── index.ts
│   └── index.ts
└── ai/
    ├── AIStore.ts               # Root AI store
    ├── PilotSpaceStore.ts       # Unified agent orchestration
    ├── GhostTextStore.ts        # Inline suggestions
    ├── AIContextStore.ts        # Issue context aggregation
    ├── ApprovalStore.ts         # Human-in-the-loop approvals
    ├── AISettingsStore.ts       # Feature flags
    ├── PRReviewStore.ts         # PR review (legacy)
    ├── MarginAnnotationStore.ts # Margin annotations
    ├── CostStore.ts             # Cost tracking
    ├── ConversationStore.ts     # Legacy
    ├── SessionListStore.ts      # Session list
    ├── PilotSpaceStreamHandler.ts   # SSE stream handling
    ├── PilotSpaceActions.ts         # Async actions
    ├── PilotSpaceSSEParser.ts       # Event parsing
    ├── PilotSpaceToolCallHandler.ts # Tool call processing
    ├── PilotSpaceApprovals.ts       # Approval delegation
    ├── types/
    │   ├── conversation.ts      # ChatMessage, ToolCall, etc.
    │   ├── events.ts            # SSE event types
    │   ├── skills.ts            # Skill definitions
    │   └── index.ts
    ├── __tests__/
    │   └── *.test.ts            # AI store tests
    ├── PILOTSPACE_STORE_USAGE.md # Usage guide
    └── index.ts
└── __tests__/
    └── *.test.ts                # Unit tests
```

---

## Generation Metadata

**Refactoring Summary**:
- **Original**: 1,954 lines | **After**: 1,469 lines | **Reduction**: -25% (485 lines)
- **Changes**: Removed all testing sections (150+ lines). Reduced code examples to single concise pattern. Removed performance optimization section. Compressed gotchas to table format.

- **Preserved**:
  - Store catalog (17+ stores with full responsibilities)
  - Core patterns (makeAutoObservable, computed, reactions, observer, runInAction)
  - File organization (complete directory tree)
  - Quick reference table (when to use which store)
  - Related documentation links

- **Patterns Detected**:
  - MobX state management (makeAutoObservable, computed, reactions, observer)
  - UI/Server state split (MobX vs TanStack Query)
  - Async actions (runInAction after await)
  - Persistence (localStorage via reactions)
  - SSE integration (GhostTextStore, AIContextStore, PilotSpaceStore)
  - Cross-store references (RootStore wiring)
  - Disposal & cleanup (reaction disposers)

- **Next Steps**:
  - Create `stores/TESTING.md` for test setup + mock patterns
  - Add PilotSpaceStreamHandler event flow details
  - Create store troubleshooting guide (indexed by error type)

---

## Quick Reference: When to Use Which Store

| Use Case | Store | Pattern |
|----------|-------|---------|
| User authentication | AuthStore | Supabase + subscriptions |
| Layout (sidebar, theme) | UIStore | Reactions + localStorage |
| Current workspace selection | WorkspaceStore | Computed properties |
| Note editor dirty state | NoteStore | Auto-save + reactions |
| Issue filters & sorting | IssueStore | Computed filtering |
| Cycle selection | CycleStore | CRUD + state |
| Inline text suggestions | GhostTextStore | Debounced + cached |
| Issue context | AIContextStore | SSE streaming + cache |
| Human-in-the-loop approvals | ApprovalStore + PilotSpaceStore | Queue + UI state |
| AI conversations | PilotSpaceStore | SSE + session mgmt |
| Margin annotations | MarginAnnotationStore | Inline UI state |
| Cost tracking | CostStore | Read-only metrics |

---

## Related Documentation

- **MobX Patterns**: `docs/dev-pattern/21c-frontend-mobx-state.md`
- **Frontend Architecture**: `docs/architect/frontend-architecture.md`
- **AI Agent Architecture**: `docs/architect/pilotspace-agent-architecture.md`
- **Design System**: `specs/001-pilot-space-mvp/ui-design-spec.md`
- **Data Model**: `specs/001-pilot-space-mvp/data-model.md`
