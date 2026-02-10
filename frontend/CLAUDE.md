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

## Frontend Architecture Overview

### Technology Stack

| Component    | Technology              | Version | Decision                 |
| ------------ | ----------------------- | ------- | ------------------------ |
| Framework    | Next.js (App Router)    | 14+     | --                       |
| UI State     | MobX                    | 6+      | DD-065 (clear ownership) |
| Server State | TanStack Query          | 5+      | DD-065 (caching + sync)  |
| Styling      | TailwindCSS + shadcn/ui | 3.4+    | --                       |
| Rich Text    | TipTap/ProseMirror      | 2+      | --                       |
| Language     | TypeScript              | 5.3+    | --                       |

### Project Structure

```
frontend/src/
├── app/                    # Next.js App Router (pages, layouts)
│   ├── (auth)/            # Login, password reset flows
│   ├── (workspace)/       # Main app routes under workspace
│   ├── (public)/          # Public pages
│   ├── api/               # API routes (health check only)
│   └── layout.tsx         # Root layout
├── features/              # Domain-driven modules (feature folders)
│   ├── notes/             # Canvas editor + 13 TipTap extensions + ghost text
│   ├── issues/            # Issue detail + AI context + duplicate detection
│   ├── ai/                # ChatView (25-component tree) + skill system
│   ├── approvals/         # Approval queue + modal workflows
│   ├── cycles/            # Cycle management + burndown/velocity charts
│   ├── github/            # GitHub integration + PR review streaming
│   ├── costs/             # Cost tracking dashboard
│   ├── settings/          # Workspace/profile/AI settings
│   ├── onboarding/        # Role + skill setup wizard
│   ├── homepage/          # Note canvas home view
│   └── integrations/      # GitHub + Slack connections
├── components/            # Shared UI components
│   ├── ui/                # 25 shadcn/ui primitives
│   ├── editor/            # Canvas + toolbar + annotations + TOC
│   ├── layout/            # Shell + sidebar + header
│   ├── navigation/        # Outline tree, pinned notes list
│   ├── issues/            # Issue cards, boards, modals
│   ├── cycles/            # Burndown, velocity charts
│   ├── ai/                # Chat components, approval dialogs
│   └── role-skill/        # Role cards, skill displays
├── stores/                # MobX stores (UI + AI state)
│   ├── RootStore.ts       # Root: aggregates all domain stores
│   ├── AuthStore.ts       # Auth state (user, workspace, role)
│   ├── UIStore.ts         # Global UI state (theme, modals, etc.)
│   ├── WorkspaceStore.ts  # Current workspace context
│   ├── NotificationStore.ts # Toast/notifications
│   ├── OnboardingStore.ts # Onboarding state
│   ├── RoleSkillStore.ts  # Role/skill assignments
│   ├── features/          # Domain stores (NoteStore, IssueStore, CycleStore)
│   └── ai/                # AI stores (PilotSpaceStore, GhostTextStore, etc.)
├── services/              # API clients
│   └── api/               # 9 typed API clients (notes, issues, ai, etc.)
├── hooks/                 # Shared custom hooks
│   └── Organized by concern (useQuery, animations, SSE, etc.)
├── lib/                   # Utilities
│   ├── supabase.ts        # Supabase client
│   ├── sse-client.ts      # SSE streaming client
│   ├── queryClient.ts     # TanStack Query configuration
│   ├── utils.ts           # General utilities
│   └── issue-helpers.ts   # Issue-specific formatters
└── types/                 # Global type definitions

```

### 5-Tier Request Flow

```
User Browser
    ↓ User interaction (click, type, etc.)
Next.js Page/Component
    ↓ Server component fetches initial data, client component renders interactive UI
Feature Component (observer-wrapped, TanStack Query)
    ↓ useQuery/useMutation for server data, observer() for MobX UI state
MobX Store (PilotSpaceStore, IssueStore, etc.)
    ↓ @action methods update observable state, trigger reactions
API Services (issuesApi, notesApi, etc.)
    ↓ Axios-based HTTP (RFC 7807 error handling)
Backend API (FastAPI on :8000)
```

---

## MobX State Management

### State Split: MobX (UI) vs TanStack Query (Server)

**Golden Rule**: Store API responses in TanStack Query. Store UI state in MobX.

**MobX** (`@observable`, `@action`, `@computed`):

- UI state: modal visibility, selected items, editing mode, form inputs
- App state: current user, workspace, theme, sidebar collapsed
- Derived state: active tasks, pending approvals, completion percentage

**TanStack Query** (`useQuery`, `useMutation`):

- Server data: notes, issues, cycles, members
- Caching, background sync, stale time management
- Optimistic updates with rollback

**Anti-Pattern**: Storing API data in MobX

```tsx
// ❌ WRONG - API data in MobX
class EditorStore {
  @observable note: Note | null = null; // ❌ Use TanStack Query instead
  @observable issues: Issue[] = []; // ❌ Use TanStack Query instead
}

// ✅ CORRECT - UI state in MobX
class EditorStore {
  @observable isEditing = false;
  @observable selectedBlockId: string | null = null;
  @observable isLoading = false;
}

// ✅ CORRECT - Server data in TanStack Query
function useNote(noteId: string) {
  return useQuery({
    queryKey: ['notes', noteId],
    queryFn: () => notesApi.get(noteId),
    staleTime: 5 * 60 * 1000,
  });
}
```

### Store Organization

**RootStore** (singleton, created at app startup):

```typescript
export class RootStore {
  auth: AuthStore;
  ui: UIStore;
  workspace: WorkspaceStore;
  notes: NoteStore;
  issues: IssueStore;
  cycles: CycleStore;
  ai: AIStore;
  onboarding: OnboardingStore;
  roleSkill: RoleSkillStore;
  homepage: HomepageUIStore;
  notifications: NotificationStore;
}
```

Access via hooks: `useStore()` returns RootStore, then access specific stores.

```typescript
function MyComponent() {
  const { issueStore, workspaceStore } = useStores();
  return <div>{issueStore.selectedIssueId}</div>;
}
```

### AI Store Organization (11 Stores)

**Root**: `AIStore` (singleton, aggregates all AI feature stores)

**Feature Stores**:

1. **PilotSpaceStore**: Central orchestrator for all conversational AI (note sync, skill routing, approvals)
2. **GhostTextStore**: Inline autocomplete state (suggestion, loading, position)
3. **AIContextStore**: Issue context aggregation (related issues, notes, docs, dependencies)
4. **ApprovalStore**: Pending approvals queue (24h countdown, content diffs, approval history)
5. **MarginAnnotationStore**: Margin annotations per block (annotation types, colors, visibility)
6. **PRReviewStore**: GitHub PR review results (severity, aspect findings, cost tracking)
7. **CostStore**: Cost tracking per agent (per-request tokens, monthly trends, budget alerts)
8. **AISettingsStore**: User AI preferences (enabled features, model selection, approval rules)
9. **SessionListStore**: Chat session management (session list, current session, history)
10. **ConversationStore**: Multi-turn conversation state (messages, tool calls, context)
11. **AnnotationStore**: Margin annotation UI state (expanded annotations, scroll sync)

**Access Pattern**:

```typescript
const { pilotSpaceStore, ghostTextStore, approvalStore } = useStore().ai;
```

### Observable Patterns

**Making Stores**:

```typescript
import { makeAutoObservable } from 'mobx';
import { observer } from 'mobx-react-lite';

class IssueStore {
  selectedIssueId: string | null = null;
  filters: IssueFilters = {};
  isLoading = false;

  constructor() {
    makeAutoObservable(this, {
      // Skip observing these (e.g., large computed properties)
      computedValue: false,
    });
  }

  @action
  setSelectedIssueId(id: string | null) {
    this.selectedIssueId = id;
  }

  @computed
  get activeIssueCount() {
    return this.issues.filter(i => i.state !== 'done').length;
  }
}

// Using in components
export const IssueDetail = observer(function IssueDetail() {
  const { issueStore } = useStores();
  return <div>{issueStore.selectedIssueId}</div>;
});
```

**Reactions (Side Effects)**:

```typescript
import { reaction } from 'mobx';

useEffect(() => {
  const dispose = reaction(
    () => editorStore.isDirty,
    (isDirty) => {
      if (isDirty) {
        // Trigger auto-save after 2s debounce
        saveNote();
      }
    },
    { delay: 2000 }
  );

  return () => dispose();
}, []);
```

---

## TipTap Editor Extensions (13 Total)

All extensions live in `frontend/src/features/notes/editor/extensions/`. Each extension is independently testable.

### Extension Catalog with Line Counts

| #   | Extension                                | Lines | Purpose                             | Key Features                                          |
| --- | ---------------------------------------- | ----- | ----------------------------------- | ----------------------------------------------------- |
| 1   | **BlockIdExtension**                     | 203   | Assign unique IDs to blocks         | UUID generation, AI edit guard, navigation key bypass |
| 2   | **GhostTextExtension**                   | 519   | Inline autocomplete on 500ms pause  | Debounce, context capture, Tab/Right/Escape handling  |
| 3   | **AnnotationMark**                       | 149   | Mark wrapper for margin annotations | CSS Anchor Positioning, hover effects                 |
| 4   | **MarginAnnotationExtension**            | 395   | Visual indicators in left gutter    | Color-coded by annotation type, click to expand       |
| 5   | **MarginAnnotationAutoTriggerExtension** | 220   | Auto-trigger AI annotations         | Debounce, context blocks, SSE integration             |
| 6   | **IssueLinkExtension**                   | 458   | Auto-detect PS-123 syntax           | Hover preview card, state colors, keyboard nav        |
| 7   | **InlineIssueExtension**                 | 410   | Inline PS-123 rendering as badge    | State colors, priority indicators, click navigation   |
| 8   | **CodeBlockExtension**                   | 444   | Syntax-highlighted code blocks      | lowlight integration, line numbers, copy button       |
| 9   | **SlashCommandExtension**                | 392   | `/slash` commands for formatting    | Command menu, AI commands, keyboard nav               |
| 10  | **MentionExtension**                     | 418   | `@mention` for notes/issues/agents  | Autocomplete popup, click navigation                  |
| 11  | **LineGutterExtension**                  | 427   | Line numbers + fold buttons         | Nested indentation, collapse/expand logic             |
| 12  | **ParagraphSplitExtension**              | 330   | Double-newline → new paragraph      | Paste transformation, hard break conversion           |
| 13  | **AIBlockProcessingExtension**           | 81    | Track blocks being processed by AI  | CSS class application, highlight pending blocks       |

**Note**: Total extension code ~4,800 lines. Individually testable via `createEditorExtensions()` factory.

### Extension Examples

**BlockIdExtension**: Ensures every block has a unique UUID for AI tool targeting and scroll sync.

```typescript
// From BlockIdExtension.ts
const BLOCK_ID_PLUGIN_KEY = new PluginKey('blockId');
const AI_EDIT_GUARD_KEY = new PluginKey('aiEditGuard');

export const BlockIdExtension = Extension.create<BlockIdOptions>({
  name: 'blockId',

  addGlobalAttributes() {
    return [
      {
        types: ['paragraph', 'heading', 'codeBlock', 'bulletList'],
        attributes: {
          blockId: {
            default: null,
            parseHTML: (element) => element.getAttribute('data-block-id'),
            renderHTML: (attributes) => ({
              'data-block-id': attributes.blockId,
            }),
          },
        },
      },
    ];
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: BLOCK_ID_PLUGIN_KEY,
        appendTransaction(transactions, oldState, newState) {
          // Auto-assign block IDs to new blocks
          // Guard against user edits in AI-pending blocks
        },
      }),
    ];
  },
});
```

**GhostTextExtension**: Triggers on 500ms typing pause, streams completions at 50 tokens max.

```typescript
// From GhostTextExtension.ts
export interface GhostTextOptions {
  debounceMs: number; // 500ms default
  minChars: number;
  className: string;
  enabled: boolean;
  onTrigger?: (context: GhostTextContext) => void;
  onAccept?: (text: string, acceptType: 'full' | 'word') => void;
  onDismiss?: () => void;
}

export const GhostTextExtension = Extension.create<GhostTextOptions>({
  name: 'ghostText',

  addOptions() {
    return {
      debounceMs: 500,
      minChars: 3,
      className: 'ghost-text',
      enabled: true,
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: GHOST_TEXT_PLUGIN_KEY,
        state: {
          init: () => ({
            text: null,
            position: null,
            isLoading: false,
            decorations: DecorationSet.empty,
          }),
        },

        props: {
          decorations(state) {
            return this.getState(state).decorations;
          },

          handleKeyDown: (view, event) => {
            // Tab, Right Arrow, or Escape to accept/dismiss
            if (event.key === 'Tab' || event.key === 'ArrowRight') {
              // Apply ghost text
            }
            if (event.key === 'Escape') {
              // Dismiss ghost text
            }
            return false;
          },
        },
      }),
    ];
  },
});
```

**IssueLinkExtension**: Auto-detects issue patterns (PS-123) and creates clickable links with hover previews.

```typescript
// From IssueLinkExtension.ts
const DEFAULT_ISSUE_PATTERN = /\b([A-Z][A-Z0-9]*)-(\\d+)\b/g;

const STATE_COLORS: Record<string, string> = {
  backlog: '#6b7280',
  todo: '#3b82f6',
  in_progress: '#f59e0b',
  in_review: '#8b5cf6',
  done: '#10b981',
  cancelled: '#ef4444',
};

export const IssueLinkExtension = Extension.create<IssueLinkOptions>({
  name: 'issueLink',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: ISSUE_LINK_PLUGIN_KEY,
        state: {
          init: (config, state) => {
            return { decorations: DecorationSet.empty };
          },
          apply: (tr, value) => {
            // Find all PS-123 matches, create decorations with hover cards
          },
        },
        props: {
          decorations(state) {
            return this.getState(state).decorations;
          },
        },
      }),
    ];
  },
});
```

### Editor Setup Factory

All extensions are instantiated via `createEditorExtensions()`:

```typescript
// From createEditorExtensions.ts
export interface EditorExtensionConfig {
  placeholder?: string;
  enableSlashCommands?: boolean;
  enableMentions?: boolean;
  enableInlineIssues?: boolean;
  enableGhostText?: boolean;
  enableMarginAnnotations?: boolean;
}

export function createEditorExtensions(config: EditorExtensionConfig) {
  const extensions: Extension[] = [
    StarterKit,
    BlockIdExtension.configure({
      generateId: () => crypto.randomUUID(),
      attributeName: 'data-block-id',
      types: null, // All block types
    }),
    GhostTextExtension.configure({
      debounceMs: 500,
      minChars: 3,
      enabled: config.enableGhostText ?? true,
      onTrigger: (context) => {
        // Trigger SSE for ghost text
      },
    }),
    // ... 11 more extensions
  ];

  return extensions;
}
```

---

## API Client Patterns

### RFC 7807 Problem Details

All API errors conform to RFC 7807 standard. Retryable statuses: 500-599 (except 501), 429 (rate limit), 408 (timeout).

### Typed API Clients (9 Total)

Each client exports typed queries + mutations. Example: `notesApi.list()`, `notesApi.get()`, `notesApi.create()`, `notesApi.update()`, `notesApi.delete()`. Full API specs in `/frontend/src/services/CLAUDE.md`.

### Query Key Factories

TanStack Query keys organized hierarchically: `notesKeys.all`, `notesKeys.list(workspaceId)`, `notesKeys.detail(workspaceId, noteId)`. Pattern: `['notes', 'list', workspaceId, filters]`.

### Hook Pattern: useNote

```typescript
export function useNote({ workspaceId, noteId, enabled = true }: UseNoteOptions) {
  return useQuery({
    queryKey: notesKeys.detail(workspaceId, noteId),
    queryFn: () => notesApi.get(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}
```

### Optimistic Updates Pattern

```typescript
const updateIssueMutation = useMutation({
  mutationFn: (data: UpdateIssueData) => issuesApi.update(workspaceId, issueId, data),
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: issueDetailKeys.detail(issueId) });
    const previous = queryClient.getQueryData<Issue>(issueDetailKeys.detail(issueId));
    queryClient.setQueryData<Issue>(issueDetailKeys.detail(issueId), (old) => ({
      ...old,
      ...newData,
    }));
    return { previous };
  },
  onError: (err, _, context) => {
    queryClient.setQueryData(issueDetailKeys.detail(issueId), context?.previous);
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: issueDetailKeys.detail(issueId) }),
});
```

---

## SSE (Server-Sent Events) Streaming

### SSEClient Utility

Custom SSE client for POST requests (EventSource only supports GET). Supports streaming via `fetch` ReadableStream with automatic line parsing and retry logic.

### Usage in PilotSpaceStore

SSE events handled: `message_start`, `text_delta`, `tool_use`, `tool_result`, `content_update`, `approval_request`, `task_progress`, `message_stop`, `error`. Route via `PilotSpaceStore.sendMessage()` → SSEClient → event handlers → MobX updates.

### SSE Event Types (8 Total)

| Event              | Payload                         | Frontend Action                              |
| ------------------ | ------------------------------- | -------------------------------------------- |
| `message_start`    | `{ id, role }`                  | Create new message, show streaming indicator |
| `text_delta`       | `{ delta }`                     | Append to current message content            |
| `tool_use`         | `{ id, name, input }`           | Add tool call card, show tool details        |
| `tool_result`      | `{ id, content }`               | Update tool result display                   |
| `content_update`   | `{ block_id, content }`         | Apply TipTap JSON patch to editor            |
| `approval_request` | `{ request_id, ...details }`    | Show modal overlay (non-dismissable)         |
| `task_progress`    | `{ task_id, status, progress }` | Update task panel progress bar               |
| `message_stop`     | `{}`                            | Hide streaming indicator, commit message     |

---

## Component Patterns

### Feature Folder Structure

Each feature folder follows this pattern:

```
features/notes/
├── components/          # Feature-specific components
│   ├── EditorToolbar.tsx
│   ├── annotation-card.tsx
│   └── __tests__/
├── hooks/               # Feature-specific hooks
│   ├── useNote.ts
│   ├── useAutoSave.ts
│   └── index.ts
├── services/            # Feature-specific API clients
│   └── ghostTextService.ts
├── editor/              # TipTap editor setup
│   ├── extensions/      # 13 extensions
│   ├── hooks/
│   └── config.ts
├── stores/              # Feature-specific stores (if any)
│   └── EditorStore.ts
├── types.ts             # TypeScript interfaces
└── index.ts             # Barrel export
```

### Observer Component Pattern

All MobX-consuming components must be wrapped with `observer()`:

```typescript
'use client';

import { observer } from 'mobx-react-lite';
import { useStores } from '@/stores';

interface NoteCardProps {
  noteId: string;
}

export const NoteCard = observer(function NoteCard({ noteId }: NoteCardProps) {
  const { noteStore } = useStores();

  return (
    <div>
      <h3>{noteStore.getNoteTitle(noteId)}</h3>
      <p>Modified: {noteStore.getLastModified(noteId)}</p>
    </div>
  );
});
```

### Hook Composition Pattern

```typescript
export function useIssueDetail(issueId: string) {
  const workspaceId = useWorkspaceId();
  const { issueStore } = useStores();
  const { data: issue, isLoading } = useQuery({
    queryKey: issueDetailKeys.detail(issueId),
    queryFn: () => issuesApi.get(workspaceId, issueId),
  });
  const updateMutation = useMutation({
    mutationFn: (data: UpdateIssueData) => issuesApi.update(workspaceId, issueId, data),
  });
  return {
    issue,
    isLoading,
    update: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
  };
}
```

### Accessibility Patterns

WCAG 2.2 AA compliance is mandatory. Requirements:

- Keyboard navigation: Enter, Space, Tab, Arrow keys. Use `role="button"` with `onKeyDown` for divs.
- ARIA labels: All interactive elements must have `aria-label` or `aria-labelledby`.
- Focus management: Modal dialogs trap focus. Use `useRef` + `useEffect` for focus restoration.
- Reduced motion: Use Tailwind `motion-reduce:` and `motion-safe:` classes for animations.

---

## AI Integration Patterns

### PilotSpaceStore: Unified AI Orchestrator

All user-facing AI goes through `PilotSpaceStore`, not siloed stores.

**Key Methods**:

```typescript
class PilotSpaceStore {
  // Session management
  setSessionId(id: string): void
  currentSession: ChatSession | null
  messages: Message[]
  isStreaming: boolean

  // Message handling
  sendMessage(content: string): Promise<void>
  appendMessageDelta(delta: string): void
  addMessage(role: 'user' | 'assistant', content: string): void

  // Context management
  setNoteContext(context: NoteContext): void
  setIssueContext(context: IssueContext): void
  setProjectContext(projectId: string): void
  clearContext(): void

  // Tool calls (MCP tools)
  pendingToolCalls: ToolCall[]
  findPendingToolCall(toolUseId: string): ToolCall | undefined
  addPendingToolCall(call: ToolCall): void

  // Content updates (TipTap patches)
  pendingContentUpdates: ContentUpdate[]
  consumeContentUpdate(blockId: string): ContentUpdate | undefined
  handleContentUpdate(update: ContentUpdate): void

  // Approvals
  pendingApprovals: ApprovalRequest[]
  addApproval(approval: ApprovalRequest): void
  approveApproval(requestId: string): Promise<void>
  rejectApproval(requestId: string): Promise<void>

  // Token budget
  tokenBudgetPercent: number  // 0-100
  messages.reduce((sum, m) => sum + m.tokenUsage.total, 0)

  // Active tasks
  tasks: TaskState[]
  activeTasks: TaskState[]
  completedTasks: TaskState[]
  addTask(task: TaskState): void
  updateTaskStatus(taskId: string, status: TaskStatus): void
}
```

### Skill System

Skills are YAML files in `.claude/skills/` (backend). Frontend invokes via slash commands or intent detection. Interface: `Skill { name, description, args?, tags? }`. Access via `useSkills()` hook returning `{ skills, invokeSkill(), activeSkill }`.

### Approval Flow

Non-dismissable modal. 24h countdown. Content diff display. Implementation: `Dialog open={!!approval} onOpenChange={() => {}}` (no dismiss), `CountdownTimer`, `DiffViewer`, Approve/Reject buttons → `pilotSpaceStore.approveApproval() | rejectApproval()`.

---

## File Size Audit

**At 700-line limit**: SkillGenerationWizard.tsx (645 lines) — extract RoleSelectorStep, SkillEditorStep, ReviewStep into separate files.

**Medium size** (300-500 lines): GhostTextExtension (519), PilotSpaceStore (500+), IssueLinkExtension (458), CodeBlockExtension (444). Monitor for clarity.

---

## Pre-Submission Checklist

Rate confidence (0-1) before submitting PR:

**State Management**:

- [ ] MobX (UI state) vs TanStack Query (server state) separation correct: \_\_\_
- [ ] No API data stored in MobX stores: \_\_\_
- [ ] Optimistic updates use snapshot + rollback pattern: \_\_\_
- [ ] observer() wrapper on all MobX-consuming components: \_\_\_

**Accessibility**:

- [ ] Keyboard navigation functional (Tab, Enter, Escape, Arrow keys): \_\_\_
- [ ] ARIA labels/descriptions for interactive elements: \_\_\_
- [ ] Focus management correct (modals trap focus): \_\_\_
- [ ] Reduced motion support (`motion-reduce:` Tailwind classes): \_\_\_

**Performance**:

- [ ] Dynamic imports for code-split components: \_\_\_
- [ ] Virtual scroll used for lists >500 items: \_\_\_
- [ ] Images optimized (Next.js Image component): \_\_\_
- [ ] No unnecessary re-renders (observer() wrapping, useMemo, useCallback): \_\_\_

**TipTap Editor** (if applicable):

- [ ] Extensions properly typed with Options interface: \_\_\_
- [ ] Block IDs preserved through all edits: \_\_\_
- [ ] Ghost text tested at 500ms debounce: \_\_\_
- [ ] Issue link pattern matching tested (PS-123, PROJECT-999): \_\_\_

**AI Integration** (if applicable):

- [ ] AI interactions through PilotSpaceStore (never siloed stores): \_\_\_
- [ ] SSE events mapped correctly per event catalog: \_\_\_
- [ ] Approval flow implemented for destructive actions (DD-003): \_\_\_
- [ ] Content updates properly parsed from SSE JSON patches: \_\_\_

**Code Quality**:

- [ ] File stays under 700 lines: \_\_\_
- [ ] TypeScript strict mode passes: \_\_\_
- [ ] No `any` types (except approved escape hatches): \_\_\_
- [ ] No console errors/warnings: \_\_\_
- [ ] Tests cover happy path + error cases: \_\_\_

**Testing**:

- [ ] Unit tests for hooks (useNote, useIssue, etc.): \_\_\_
- [ ] Integration tests for mutations (optimistic + rollback): \_\_\_
- [ ] E2E tests for critical paths (note create, issue update): \_\_\_
- [ ] Accessibility tests (axe, ARIA): \_\_\_

**If any score <0.9, refine implementation before submitting.**

---

## Common Patterns Reference

### Load Order for New Features

1. `docs/architect/feature-story-mapping.md` → Find US-XX and affected components
2. `docs/dev-pattern/45-pilot-space-patterns.md` → Project-specific overrides
3. `frontend/CLAUDE.md` (this file) → Frontend-specific patterns
4. `specs/001-pilot-space-mvp/ui-design-spec.md` → Design system

### Key Files to Reference

| Topic                | File                                                               |
| -------------------- | ------------------------------------------------------------------ |
| State management     | `frontend/src/stores/RootStore.ts`, `stores/ai/PilotSpaceStore.ts` |
| API clients          | `frontend/src/services/api/index.ts`                               |
| SSE streaming        | `frontend/src/lib/sse-client.ts`                                   |
| Editor extensions    | `frontend/src/features/notes/editor/extensions/`                   |
| TanStack Query setup | `frontend/src/lib/queryClient.ts`                                  |
| UI design tokens     | `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0                 |
| Feature components   | `frontend/src/features/*/components/`                              |

---

## Standards Summary

### DO

- **Use `'use client'`** for interactive components
- **Wrap MobX components** with `observer()`
- **Use TanStack Query** for server data (never MobX)
- **Use MobX** for UI state (editing, selection, visibility)
- **Add ARIA labels** to interactive elements
- **Test critical paths** (create, update, delete)
- **Use Tailwind classes** for styling (no inline styles)
- **Use shadcn/ui** as base, extend with variants
- **Preserve block IDs** through editor operations (TipTap)
- **Handle errors** with RFC 7807 ApiError class
- **Write integration tests** for optimistic updates

### DON'T

- **Store API data in MobX** (use TanStack Query)
- **Use `any` types** (TypeScript strict mode)
- **Create components without tests** (>700 lines especially)
- **Disable accessibility** for performance (keyboard nav is a feature)
- **Hardcode colors** (use CSS variables from design spec)
- **Use generic component names** (NoteView not View)
- **Skip error boundaries** for async operations
- **Forget to wrap with `observer()`** when using MobX
- **Leave TODOs in code** (resolve or create issue)
- **Commit console.log/debugger** statements

---

## Design System Quick Reference

### Color Palette

```css
/* Warm Neutrals */
--background: #fdfcfa;
--background-dark: #1a1a1a;
--foreground: #171717;
--foreground-dark: #ededed;
--border: #e5e2dd;

/* Accents */
--primary: #29a386; /* Teal-green */
--primary-hover: #238f74;
--ai: #6b8fad; /* Dusty blue */
--destructive: #d9534f; /* Red */
```

### Issue State Colors

- **Backlog**: `#9C9590` (gray)
- **Todo**: `#5B8FC9` (blue)
- **In Progress**: `#D9853F` (orange)
- **In Review**: `#8B7EC8` (purple)
- **Done**: `#29A386` (teal)
- **Cancelled**: `#D9534F` (red)

### Typography (Geist Font)

- **text-xs**: 11px (labels, badges)
- **text-sm**: 13px (body, descriptions)
- **text-base**: 15px (primary content)
- **text-lg**: 17px (card titles)
- **text-xl**: 20px (section headers)
- **text-2xl**: 24px (page titles)

### Spacing (4px grid)

- space-1 = 4px, space-2 = 8px, space-3 = 12px, space-4 = 16px
- space-6 = 24px, space-8 = 32px, space-12 = 48px

### Border Radius (Squircle)

- rounded-sm = 6px, rounded = 10px, rounded-lg = 14px, rounded-xl = 18px

---

## Quick Debugging

**Observer not re-rendering**: Wrap with `observer()`. Property must be `@observable`.

**Infinite TanStack Query loops**: Use stable queryKey with `as const`.

**Ghost text not triggering**: Verify 500ms debounce, `enabled: true`, `onTrigger` callback defined.

**Block IDs lost after AI edit**: BlockIdExtension must run last in extension array.

**Performance**: Use React DevTools Profiler. Target: <100ms keystroke, 60fps scroll, <150ms modal.

---

## Documentation Status

- **Scope**: 180+ TypeScript/TSX files
- **Patterns**: State split (MobX/TanStack), optimistic updates, SSE streaming, extensible editor
- **Refactoring Candidate**: SkillGenerationWizard.tsx (645 lines—extract sub-components)
- **See also**: `/frontend/src/services/CLAUDE.md` for detailed API client patterns
