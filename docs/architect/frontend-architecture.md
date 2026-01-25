# Frontend Architecture

**Framework**: Next.js 14+ (App Router)
**UI Library**: React 18 + TypeScript 5.3+
**State Management**: MobX + TanStack Query
**Styling**: TailwindCSS + shadcn/ui patterns

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  app/                │  components/          │  layouts/              │  │
│  │  (Next.js pages)     │  (React components)   │  (App shells)          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                               STATE LAYER                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  stores/             │  hooks/               │  contexts/             │  │
│  │  (MobX stores)       │  (React Query, custom)│  (React Context)       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              SERVICE LAYER                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  services/api/       │  services/ai/         │  services/auth/        │  │
│  │  (API clients)       │  (SSE streaming)      │  (Supabase Auth)       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                               SHARED LAYER                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  lib/                │  types/               │  utils/                │  │
│  │  (Utilities)         │  (TypeScript types)   │  (Pure functions)      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Next.js App Router Structure

### Route Groups

| Route Group | Purpose | Layout |
|-------------|---------|--------|
| `(auth)` | Authentication pages | Centered, minimal |
| `(workspace)` | Authenticated workspace views | Sidebar + Header |
| `(public)` | Public read-only views | Minimal public layout |
| `api` | BFF API routes | N/A |

### Page Organization

```
app/
├── layout.tsx                    # Root layout (providers, fonts)
├── page.tsx                      # Landing → redirect to workspace
├── globals.css
│
├── (auth)/                       # Auth routes (no sidebar)
│   ├── layout.tsx                # Centered auth layout
│   ├── login/page.tsx
│   ├── callback/page.tsx         # OAuth callback handler
│   └── logout/page.tsx
│
├── (workspace)/                  # Authenticated routes
│   ├── layout.tsx                # Sidebar + Header layout
│   └── [workspaceSlug]/
│       ├── page.tsx              # Workspace home (Note Canvas)
│       ├── notes/
│       │   ├── page.tsx          # Notes list
│       │   ├── [noteId]/page.tsx # Note editor
│       │   └── new/page.tsx      # New note with AI
│       ├── projects/
│       │   └── [projectId]/
│       │       ├── page.tsx      # Project overview
│       │       ├── issues/
│       │       │   ├── page.tsx  # Issue board/list
│       │       │   └── [issueId]/page.tsx
│       │       ├── cycles/
│       │       ├── modules/
│       │       └── pages/
│       ├── settings/
│       │   ├── page.tsx          # Workspace settings
│       │   ├── members/page.tsx
│       │   ├── ai/page.tsx       # AI provider config
│       │   └── integrations/page.tsx
│       └── search/page.tsx
│
├── (public)/                     # Public views
│   ├── layout.tsx
│   └── [workspaceSlug]/
│       └── [projectSlug]/
│           └── issues/[issueId]/page.tsx
│
└── api/                          # API routes (BFF)
    ├── auth/
    │   ├── login/route.ts
    │   ├── callback/route.ts
    │   └── refresh/route.ts
    └── ai/
        └── ghost-text/route.ts   # SSE proxy if needed
```

---

## Component Architecture

### Component Categories

| Category | Location | Purpose |
|----------|----------|---------|
| UI Components | `components/ui/` | Base building blocks (shadcn/ui style) |
| Editor Components | `components/editor/` | TipTap note canvas |
| Feature Components | `components/{feature}/` | Domain-specific UI |
| Layout Components | `components/layouts/` | Page shells |
| Navigation | `components/navigation/` | Sidebar, header, modals |
| AI Components | `components/ai/` | AI-specific UI elements |

### Component Patterns

#### 1. Server Components (Default)

```tsx
// app/(workspace)/[workspaceSlug]/projects/[projectId]/issues/page.tsx

import { getIssues } from '@/services/api/issues';
import { IssueBoard } from '@/components/issues/IssueBoard';

// Server Component - fetches data on server
export default async function IssuesPage({
  params,
  searchParams,
}: {
  params: Promise<{ workspaceSlug: string; projectId: string }>;
  searchParams: Promise<{ view?: 'board' | 'list'; state?: string }>;
}) {
  const { projectId } = await params;
  const { view = 'board', state } = await searchParams;

  // Server-side data fetching
  const issues = await getIssues(projectId, { state });

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-semibold mb-4">Issues</h1>
      {/* Client component receives server data */}
      <IssueBoard initialIssues={issues} view={view} />
    </div>
  );
}
```

#### 2. Client Components (Interactive)

```tsx
// components/issues/IssueBoard.tsx
'use client';

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useIssues } from '@/hooks/useIssues';
import { useIssueStore } from '@/stores/context';
import { IssueCard } from './IssueCard';
import { DndContext, DragEndEvent } from '@dnd-kit/core';

interface IssueBoardProps {
  initialIssues: Issue[];
  view: 'board' | 'list';
}

export const IssueBoard = observer(function IssueBoard({
  initialIssues,
  view,
}: IssueBoardProps) {
  const issueStore = useIssueStore();
  const { issues, moveIssue, isLoading } = useIssues(initialIssues);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const issueId = active.id as string;
    const newState = over.id as string;

    // Optimistic update
    issueStore.optimisticUpdateState(issueId, newState);

    try {
      await moveIssue(issueId, newState);
    } catch (error) {
      // Rollback on failure
      issueStore.rollbackState(issueId);
    }
  };

  if (view === 'list') {
    return <IssueList issues={issues} />;
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STATE_COLUMNS.map((state) => (
          <StateColumn
            key={state.id}
            state={state}
            issues={issues.filter((i) => i.state === state.id)}
          />
        ))}
      </div>
    </DndContext>
  );
});
```

#### 3. Compound Components (Complex UI)

```tsx
// components/ui/command.tsx
'use client';

import * as React from 'react';
import { Command as CommandPrimitive } from 'cmdk';
import { cn } from '@/lib/cn';

const Command = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive>
>(({ className, ...props }, ref) => (
  <CommandPrimitive
    ref={ref}
    className={cn(
      'flex h-full w-full flex-col overflow-hidden rounded-md bg-white',
      className
    )}
    {...props}
  />
));
Command.displayName = 'Command';

const CommandInput = React.forwardRef<...>(...);
const CommandList = React.forwardRef<...>(...);
const CommandItem = React.forwardRef<...>(...);
const CommandGroup = React.forwardRef<...>(...);

export { Command, CommandInput, CommandList, CommandItem, CommandGroup };
```

---

## State Management

### State Responsibility Split

**IMPORTANT**: MobX and TanStack Query have distinct responsibilities:

| State Type | Owner | Examples |
|------------|-------|----------|
| **Server Data** | TanStack Query | Issues, notes, projects, user data |
| **UI State** | MobX | Selection, filters, modals, drag state |
| **Form State** | React Hook Form | Form inputs, validation |
| **URL State** | Next.js Router | Current route, query params |

**Anti-Pattern**: Do NOT store server data in MobX stores. The `issues: Map` pattern below is for *optimistic update tracking only*, not as the source of truth.

### MobX Stores

Use MobX for complex client-side UI state that requires fine-grained reactivity:

```tsx
// stores/IssueUIStore.ts
import { makeAutoObservable, runInAction } from 'mobx';

// NOTE: This store holds UI state only. Server data comes from TanStack Query.
export class IssueUIStore {
  // UI state only - NOT server data
  selectedIssueId: string | null = null;
  isCreating = false;
  filterState: string | null = null;
  filterAssignee: string | null = null;
  sortBy: 'created' | 'updated' | 'priority' = 'updated';

  // Optimistic update tracking (temporary, cleared after server confirms)
  pendingUpdates: Map<string, { field: string; originalValue: unknown }> = new Map();

  constructor() {
    makeAutoObservable(this);
  }

  // Computed - for UI state only
  get hasActiveFilters(): boolean {
    return this.filterState !== null || this.filterAssignee !== null;
  }

  // Actions - UI state management
  selectIssue(id: string | null) {
    this.selectedIssueId = id;
  }

  setFilter(state: string | null, assignee: string | null) {
    this.filterState = state;
    this.filterAssignee = assignee;
  }

  clearFilters() {
    this.filterState = null;
    this.filterAssignee = null;
  }

  // Optimistic update tracking (used with TanStack Query mutations)
  trackPendingUpdate(issueId: string, field: string, originalValue: unknown) {
    this.pendingUpdates.set(issueId, { field, originalValue });
  }

  clearPendingUpdate(issueId: string) {
    this.pendingUpdates.delete(issueId);
  }

  hasPendingUpdate(issueId: string): boolean {
    return this.pendingUpdates.has(issueId);
  }
}

// CORRECT: Server data from TanStack Query, UI state from MobX
// See useIssues hook below for the proper integration pattern
```

### Integrating MobX with TanStack Query

```tsx
// hooks/useIssues.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useStore } from '@/stores/context';
import { issuesApi } from '@/services/api';

export function useIssues(projectId: string) {
  const { issueUIStore } = useStore();
  const queryClient = useQueryClient();

  // Server data from TanStack Query (source of truth)
  const { data: issues = [], isLoading } = useQuery({
    queryKey: ['issues', projectId],
    queryFn: () => issuesApi.getByProject(projectId),
  });

  // Apply MobX filters to server data
  const filteredIssues = issues.filter((issue) => {
    if (issueUIStore.filterState && issue.state !== issueUIStore.filterState) {
      return false;
    }
    if (issueUIStore.filterAssignee && issue.assigneeId !== issueUIStore.filterAssignee) {
      return false;
    }
    return true;
  });

  // Mutation with optimistic updates
  const updateStateMutation = useMutation({
    mutationFn: ({ issueId, newState }: { issueId: string; newState: string }) =>
      issuesApi.updateState(issueId, newState),
    onMutate: async ({ issueId, newState }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['issues', projectId] });

      // Snapshot previous value
      const previousIssues = queryClient.getQueryData(['issues', projectId]);

      // Track in MobX for UI indicators
      const issue = issues.find((i) => i.id === issueId);
      if (issue) {
        issueUIStore.trackPendingUpdate(issueId, 'state', issue.state);
      }

      // Optimistically update cache
      queryClient.setQueryData(['issues', projectId], (old: Issue[]) =>
        old.map((i) => (i.id === issueId ? { ...i, state: newState } : i))
      );

      return { previousIssues };
    },
    onError: (_err, { issueId }, context) => {
      // Rollback on error
      queryClient.setQueryData(['issues', projectId], context?.previousIssues);
      issueUIStore.clearPendingUpdate(issueId);
    },
    onSettled: (_data, _err, { issueId }) => {
      issueUIStore.clearPendingUpdate(issueId);
      queryClient.invalidateQueries({ queryKey: ['issues', projectId] });
    },
  });

  return {
    issues: filteredIssues,
    isLoading,
    updateState: updateStateMutation.mutate,
    selectedIssue: issues.find((i) => i.id === issueUIStore.selectedIssueId),
  };
}
```

### Store Provider

```tsx
// stores/context.tsx
'use client';

import { createContext, useContext, useRef } from 'react';
import { IssueUIStore } from './IssueUIStore';
import { NoteUIStore } from './NoteUIStore';
import { GlobalUIStore } from './GlobalUIStore';

// UI stores only - server data handled by TanStack Query
interface RootStore {
  issueUIStore: IssueUIStore;
  noteUIStore: NoteUIStore;
  globalUIStore: GlobalUIStore;
}

const StoreContext = createContext<RootStore | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const storeRef = useRef<RootStore>();

  if (!storeRef.current) {
    storeRef.current = {
      issueUIStore: new IssueUIStore(),
      noteStore: new NoteStore(),
      uiStore: new UIStore(),
    };
  }

  return (
    <StoreContext.Provider value={storeRef.current}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStores() {
  const stores = useContext(StoreContext);
  if (!stores) {
    throw new Error('useStores must be used within StoreProvider');
  }
  return stores;
}

export function useIssueStore() {
  return useStores().issueStore;
}

export function useNoteStore() {
  return useStores().noteStore;
}
```

### TanStack Query for Server State

```tsx
// hooks/useIssues.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api/issues';

export function useIssues(projectId: string, initialData?: Issue[]) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['issues', projectId],
    queryFn: () => issuesApi.getByProject(projectId),
    initialData,
    staleTime: 30_000, // 30 seconds
  });

  const createMutation = useMutation({
    mutationFn: issuesApi.create,
    onSuccess: (newIssue) => {
      queryClient.setQueryData(['issues', projectId], (old: Issue[] = []) => [
        newIssue,
        ...old,
      ]);
    },
  });

  const updateStateMutation = useMutation({
    mutationFn: ({ issueId, state }: { issueId: string; state: string }) =>
      issuesApi.updateState(issueId, state),
    onMutate: async ({ issueId, state }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['issues', projectId] });

      // Snapshot previous value
      const previous = queryClient.getQueryData(['issues', projectId]);

      // Optimistic update
      queryClient.setQueryData(['issues', projectId], (old: Issue[] = []) =>
        old.map((issue) =>
          issue.id === issueId ? { ...issue, state } : issue
        )
      );

      return { previous };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(['issues', projectId], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['issues', projectId] });
    },
  });

  return {
    issues: query.data ?? [],
    isLoading: query.isLoading,
    createIssue: createMutation.mutateAsync,
    moveIssue: (issueId: string, state: string) =>
      updateStateMutation.mutateAsync({ issueId, state }),
  };
}
```

---

## TipTap Editor Integration

### Note Canvas Architecture

```tsx
// components/editor/NoteCanvas.tsx
'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { GhostText } from './extensions/ghost-text';
import { BlockId } from './extensions/block-id';
import { SlashCommands } from './extensions/slash-commands';
import { useGhostText } from '@/hooks/useGhostText';
import { useAutosave } from '@/hooks/useAutosave';
import { GhostTextOverlay } from './GhostTextOverlay';
import { MarginAnnotations } from './MarginAnnotations';
import { SelectionToolbar } from './SelectionToolbar';

interface NoteCanvasProps {
  noteId: string;
  initialContent: JSONContent;
  annotations: Annotation[];
}

export function NoteCanvas({
  noteId,
  initialContent,
  annotations,
}: NoteCanvasProps) {
  const { suggestion, requestSuggestion, acceptSuggestion, dismissSuggestion } =
    useGhostText(noteId);

  const editor = useEditor({
    extensions: [
      StarterKit,
      BlockId,
      GhostText.configure({
        suggestion,
        onAccept: () => {
          const text = acceptSuggestion();
          if (text) {
            editor?.commands.insertContent(text);
          }
        },
        onDismiss: dismissSuggestion,
      }),
      SlashCommands,
    ],
    content: initialContent,
    onUpdate: ({ editor }) => {
      triggerSave(editor.getJSON());
    },
  });

  const { saveStatus, triggerSave } = useAutosave(noteId, () =>
    editor?.getJSON()
  );

  // Request ghost text after typing pause
  useEffect(() => {
    if (!editor) return;

    const timeout = setTimeout(() => {
      const { from } = editor.state.selection;
      const context = editor.state.doc.textBetween(
        Math.max(0, from - 500),
        from
      );
      requestSuggestion(context, from);
    }, 500); // 500ms pause per spec

    return () => clearTimeout(timeout);
  }, [editor?.state.doc]);

  return (
    <div className="flex h-full">
      {/* Main Editor (65%) */}
      <div className="flex-1 max-w-[65%] relative">
        <EditorContent editor={editor} className="prose prose-lg max-w-none" />
        {suggestion && <GhostTextOverlay suggestion={suggestion} />}
        {editor && <SelectionToolbar editor={editor} />}
        <SaveIndicator status={saveStatus} />
      </div>

      {/* Margin Annotations (35%) */}
      <MarginAnnotations
        editor={editor}
        annotations={annotations}
        className="w-[35%] min-w-[150px] max-w-[350px]"
      />
    </div>
  );
}
```

### Ghost Text Extension

```typescript
// components/editor/extensions/ghost-text.ts
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface GhostTextOptions {
  suggestion: string | null;
  onAccept: () => void;
  onAcceptWord: () => void;
  onDismiss: () => void;
}

export const GhostText = Extension.create<GhostTextOptions>({
  name: 'ghostText',

  addOptions() {
    return {
      suggestion: null,
      onAccept: () => {},
      onAcceptWord: () => {},
      onDismiss: () => {},
    };
  },

  addProseMirrorPlugins() {
    const { suggestion, onAccept, onAcceptWord, onDismiss } = this.options;

    return [
      new Plugin({
        key: new PluginKey('ghostText'),
        props: {
          decorations: (state) => {
            if (!suggestion) return DecorationSet.empty;
            if (!state.selection.empty) return DecorationSet.empty;

            const { from } = state.selection;

            const widget = Decoration.widget(
              from,
              () => {
                const span = document.createElement('span');
                span.className = 'ghost-text text-gray-400 opacity-50';
                span.textContent = suggestion;
                return span;
              },
              { side: 1 }
            );

            return DecorationSet.create(state.doc, [widget]);
          },

          handleKeyDown: (view, event) => {
            if (!suggestion) return false;

            // Tab: Accept full suggestion
            if (event.key === 'Tab') {
              event.preventDefault();
              onAccept();
              return true;
            }

            // Shift+Right: Accept word
            if (event.key === 'ArrowRight' && event.shiftKey) {
              event.preventDefault();
              onAcceptWord();
              return true;
            }

            // Escape: Dismiss
            if (event.key === 'Escape') {
              onDismiss();
              return true;
            }

            return false;
          },
        },
      }),
    ];
  },
});
```

---

## SSE Streaming for AI

```typescript
// hooks/useGhostText.ts
import { useState, useEffect, useCallback, useRef } from 'react';

export function useGhostText(noteId: string) {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const requestSuggestion = useCallback(
    async (context: string, cursorPosition: number) => {
      // Cancel previous request
      eventSourceRef.current?.close();

      setIsLoading(true);
      setSuggestion(null);

      const url = new URL(
        `/api/v1/notes/${noteId}/ghost-text`,
        window.location.origin
      );
      url.searchParams.set('context', context);
      url.searchParams.set('cursor_position', cursorPosition.toString());

      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      let accumulated = '';

      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          eventSource.close();
          setIsLoading(false);
          return;
        }

        try {
          const { text } = JSON.parse(event.data);
          accumulated += text;
          setSuggestion(accumulated);
        } catch {
          // Ignore parse errors
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setIsLoading(false);
        setSuggestion(null);
      };
    },
    [noteId]
  );

  const acceptSuggestion = useCallback(() => {
    const current = suggestion;
    setSuggestion(null);
    return current;
  }, [suggestion]);

  const acceptWord = useCallback(() => {
    if (!suggestion) return null;

    const words = suggestion.split(/\s+/);
    const firstWord = words[0] + (words.length > 1 ? ' ' : '');
    const remaining = words.slice(1).join(' ');

    setSuggestion(remaining || null);
    return firstWord;
  }, [suggestion]);

  const dismissSuggestion = useCallback(() => {
    eventSourceRef.current?.close();
    setSuggestion(null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  return {
    suggestion,
    isLoading,
    requestSuggestion,
    acceptSuggestion,
    acceptWord,
    dismissSuggestion,
  };
}
```

### SSE Authentication Strategy

SSE connections can persist for extended periods (5+ minutes for AI operations). Since EventSource doesn't support custom headers, we use cookie-based authentication:

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SSE AUTH FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CLIENT                    SUPABASE AUTH              FASTAPI BACKEND       │
│    │                            │                           │               │
│    ├── Login ──────────────────>│                           │               │
│    │<── Access Token (1h) ──────┤                           │               │
│    │<── Refresh Token (cookie) ─┤                           │               │
│    │                            │                           │               │
│    ├── SSE Request (with cookie) ───────────────────────────>│               │
│    │                            │                           ├── Validate    │
│    │                            │<── Verify JWT ────────────┤   Cookie      │
│    │                            │                           │               │
│    │<── Stream Data ─────────────────────────────────────────┤               │
│    │                            │                           │               │
│    │<── Heartbeat (every 30s) ───────────────────────────────┤               │
│    │                            │                           │               │
│    ├── [On disconnect: auto-reconnect with token refresh] ──>│               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```typescript
// hooks/useSSEWithAuth.ts
import { useSupabaseClient } from '@supabase/auth-helpers-react';

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAY_MS = 1000;
const HEARTBEAT_TIMEOUT_MS = 45000; // Server sends every 30s

export function useSSEWithAuth(url: string) {
  const supabase = useSupabaseClient();
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'error'>('connecting');
  const reconnectAttempts = useRef(0);
  const heartbeatTimer = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(async () => {
    // Ensure fresh access token before connecting
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      setConnectionState('error');
      return;
    }

    // Access token is in cookie (HttpOnly for security)
    // EventSource automatically includes cookies with credentials
    const eventSource = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnectionState('connected');
      reconnectAttempts.current = 0;
      resetHeartbeatTimer();
    };

    eventSource.onmessage = (event) => {
      resetHeartbeatTimer();
      // Handle message...
    };

    eventSource.onerror = async () => {
      eventSource.close();
      clearHeartbeatTimer();

      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts.current++;
        setConnectionState('connecting');

        // Refresh token before reconnecting
        await supabase.auth.refreshSession();

        // Exponential backoff
        const delay = RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts.current - 1);
        setTimeout(connect, delay);
      } else {
        setConnectionState('error');
      }
    };
  }, [url, supabase]);

  const resetHeartbeatTimer = () => {
    clearHeartbeatTimer();
    heartbeatTimer.current = setTimeout(() => {
      // No heartbeat received - connection likely dead
      eventSourceRef.current?.close();
      connect();
    }, HEARTBEAT_TIMEOUT_MS);
  };

  const clearHeartbeatTimer = () => {
    if (heartbeatTimer.current) {
      clearTimeout(heartbeatTimer.current);
    }
  };

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      clearHeartbeatTimer();
    };
  }, [connect]);

  return { connectionState };
}
```

**Backend Heartbeat**:

```python
# Backend sends heartbeat every 30s
async def ghost_text_stream(request: Request, note_id: str):
    async def generate():
        heartbeat_interval = 30
        last_heartbeat = time.time()

        async for chunk in ai_service.stream_ghost_text(context):
            yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Send heartbeat if needed
            if time.time() - last_heartbeat > heartbeat_interval:
                yield f": heartbeat\n\n"  # SSE comment for keepalive
                last_heartbeat = time.time()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Key Considerations**:
- Access token (1 hour): Stored in HttpOnly cookie, included automatically
- Refresh token (7 days): Used to get new access token on reconnection
- Heartbeat: Server sends every 30s, client reconnects if none received for 45s
- Reconnection: Exponential backoff (1s, 2s, 4s) with max 3 attempts
- Token refresh: Triggered before reconnection to ensure fresh credentials

---

## API Service Layer

```typescript
// services/api/client.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { params, ...fetchOptions } = options;

    let url = `${this.baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.message ?? 'Request failed');
    }

    return response.json();
  }

  get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE);
```

```typescript
// services/api/issues.ts
import { apiClient } from './client';
import type { Issue, CreateIssueData, UpdateIssueData } from '@/types/issue';

export const issuesApi = {
  getByProject: (projectId: string, params?: { state?: string }) =>
    apiClient.get<Issue[]>(`/projects/${projectId}/issues`, params),

  getById: (issueId: string) =>
    apiClient.get<Issue>(`/issues/${issueId}`),

  create: (data: CreateIssueData) =>
    apiClient.post<Issue>('/issues', data),

  update: (issueId: string, data: UpdateIssueData) =>
    apiClient.put<Issue>(`/issues/${issueId}`, data),

  updateState: (issueId: string, state: string) =>
    apiClient.put<Issue>(`/issues/${issueId}/state`, { state }),

  delete: (issueId: string) =>
    apiClient.delete<void>(`/issues/${issueId}`),

  getAIContext: (issueId: string) =>
    apiClient.get<AIContext>(`/issues/${issueId}/ai-context`),
};
```

---

## Testing Strategy

### Component Tests

```tsx
// tests/components/issues/IssueCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { IssueCard } from '@/components/issues/IssueCard';

const mockIssue = {
  id: '1',
  identifier: 'PS-123',
  title: 'Fix login bug',
  state: 'todo',
  priority: 'high',
  assignee: { name: 'John Doe', avatar: '/john.png' },
};

describe('IssueCard', () => {
  it('renders issue information', () => {
    render(<IssueCard issue={mockIssue} />);

    expect(screen.getByText('PS-123')).toBeInTheDocument();
    expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<IssueCard issue={mockIssue} onClick={handleClick} />);

    fireEvent.click(screen.getByRole('article'));

    expect(handleClick).toHaveBeenCalledWith(mockIssue.id);
  });
});
```

### Hook Tests

```tsx
// tests/hooks/useGhostText.test.ts
import { renderHook, act, waitFor } from '@testing-library/react';
import { useGhostText } from '@/hooks/useGhostText';

// Mock EventSource
const mockEventSource = {
  onmessage: null,
  onerror: null,
  close: jest.fn(),
};

global.EventSource = jest.fn(() => mockEventSource) as any;

describe('useGhostText', () => {
  it('accumulates streamed text', async () => {
    const { result } = renderHook(() => useGhostText('note-1'));

    act(() => {
      result.current.requestSuggestion('Hello ', 6);
    });

    // Simulate SSE messages
    act(() => {
      mockEventSource.onmessage?.({ data: JSON.stringify({ text: 'world' }) });
    });

    expect(result.current.suggestion).toBe('world');

    act(() => {
      mockEventSource.onmessage?.({ data: JSON.stringify({ text: '!' }) });
    });

    expect(result.current.suggestion).toBe('world!');
  });

  it('clears suggestion on accept', () => {
    const { result } = renderHook(() => useGhostText('note-1'));

    act(() => {
      result.current.requestSuggestion('Hello ', 6);
      mockEventSource.onmessage?.({ data: JSON.stringify({ text: 'world' }) });
    });

    let accepted: string | null;
    act(() => {
      accepted = result.current.acceptSuggestion();
    });

    expect(accepted).toBe('world');
    expect(result.current.suggestion).toBeNull();
  });
});
```

---

## Related Documents

- [Project Structure](./project-structure.md) - Full directory layout
- [Design Patterns](./design-patterns.md) - UI patterns and conventions
- [UI Design Spec](../../specs/001-pilot-space-mvp/ui-design-spec.md) - Detailed UI specifications
- [Research](../../specs/001-pilot-space-mvp/research.md) - TipTap research findings
