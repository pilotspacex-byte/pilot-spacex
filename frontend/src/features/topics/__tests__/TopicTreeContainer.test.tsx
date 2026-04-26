/**
 * Unit tests for TopicTreeContainer (Phase 93 Plan 04 Task 2).
 *
 * Verifies the DndContext wiring + lazy-fetch behaviour + drag-end → mutation
 * routing. We mock the topic hooks directly so the test exercises the
 * container's logic without spinning up TanStack against a fake API.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Note } from '@/types';
import { topicTreeStore } from '../stores/TopicTreeStore';

vi.mock('next/navigation', () => ({
  usePathname: () => '/workspace/topics',
  useParams: () => ({ workspaceSlug: 'workspace' }),
}));

// Hook mocks --------------------------------------------------------------

const mockUseTopicChildren = vi.fn();
const mockMutate = vi.fn();
const mockUseMoveTopic = vi.fn();

vi.mock('../hooks', () => ({
  useTopicChildren: (...args: unknown[]) => mockUseTopicChildren(...args),
  useMoveTopic: (...args: unknown[]) => mockUseMoveTopic(...args),
}));

const toastError = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: unknown[]) => toastError(...args) },
}));

// Test fixtures -----------------------------------------------------------

function makeNote(over: Partial<Note> & { id: string; title: string; topicDepth?: number }): Note {
  return {
    workspaceId: 'ws-1',
    wordCount: 0,
    isPinned: false,
    linkedIssues: [],
    parentTopicId: over.parentTopicId ?? null,
    topicDepth: over.topicDepth ?? 0,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
    ...over,
  } as Note;
}

function makeChildrenResult(items: Note[]) {
  return { data: { items, total: items.length, page: 1, pageSize: 20 } };
}

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

// Lazy import after mocks are wired.
async function mountContainer() {
  const { TopicTreeContainer } = await import('../components/TopicTreeContainer');
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <TopicTreeContainer workspaceId="ws-1" />
    </Wrapper>,
  );
}

// Tests -------------------------------------------------------------------

describe('TopicTreeContainer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    topicTreeStore.expanded.clear();
    topicTreeStore.endDrag();
    mockUseMoveTopic.mockReturnValue({ mutate: mockMutate, isPending: false });
  });

  it('renders root rows from useTopicChildren(workspaceId, null)', async () => {
    const root = [
      makeNote({ id: 'root-1', title: 'Alpha', topicDepth: 0 }),
      makeNote({ id: 'root-2', title: 'Beta', topicDepth: 0 }),
    ];
    mockUseTopicChildren.mockImplementation((_ws: string, parentId: string | null) => {
      if (parentId === null) return makeChildrenResult(root);
      return makeChildrenResult([]);
    });

    await mountContainer();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('does NOT call useTopicChildren for collapsed children (lazy expansion)', async () => {
    const root = [makeNote({ id: 'root-1', title: 'Alpha' })];
    mockUseTopicChildren.mockImplementation((_ws: string, parentId: string | null) => {
      if (parentId === null) return makeChildrenResult(root);
      return makeChildrenResult([]);
    });

    await mountContainer();
    // Collapsed root: hook should be called for null only — never for 'root-1'
    // with `enabled: true`. We assert by inspecting the calls.
    const calledForRoot1Enabled = mockUseTopicChildren.mock.calls.some((args) => {
      const [, parentId, , , options] = args as [string, string | null, number?, number?, { enabled?: boolean }?];
      return parentId === 'root-1' && (options?.enabled ?? true) === true;
    });
    expect(calledForRoot1Enabled).toBe(false);
  });

  it('expands a row and fetches its children when the chevron is clicked', async () => {
    const root = [makeNote({ id: 'root-1', title: 'Alpha' })];
    const children = [makeNote({ id: 'c-1', title: 'Child', parentTopicId: 'root-1', topicDepth: 1 })];
    mockUseTopicChildren.mockImplementation((_ws: string, parentId: string | null) => {
      if (parentId === null) return makeChildrenResult(root);
      if (parentId === 'root-1') return makeChildrenResult(children);
      return makeChildrenResult([]);
    });

    await mountContainer();
    act(() => {
      topicTreeStore.expand('root-1');
    });
    expect(await screen.findByText('Child')).toBeInTheDocument();
  });

  it('renders the role="application" wrapper with aria-label "Topic tree"', async () => {
    mockUseTopicChildren.mockReturnValue(makeChildrenResult([]));
    await mountContainer();
    const wrap = screen.getByRole('application', { name: 'Topic tree' });
    expect(wrap).toBeInTheDocument();
  });

  it('renders aria-live status region for drop announcements (sr-only)', async () => {
    mockUseTopicChildren.mockReturnValue(makeChildrenResult([]));
    await mountContainer();
    // @dnd-kit injects its own DndLiveRegion role="status"; we look up our
    // status via testid to avoid that ambiguity.
    const status = screen.getByTestId('topic-tree-aria-live');
    expect(status).toBeInTheDocument();
    expect(status.getAttribute('role')).toBe('status');
    expect(status.getAttribute('aria-live')).toBe('polite');
    expect(status.className).toMatch(/sr-only/);
  });

  it('routes drag-end → useMoveTopic.mutate with derived parentId and surfaces typed error toasts', async () => {
    const root = [
      makeNote({ id: 'root-1', title: 'Alpha' }),
      makeNote({ id: 'root-2', title: 'Beta' }),
    ];
    mockUseTopicChildren.mockImplementation((_ws: string, parentId: string | null) => {
      if (parentId === null) return makeChildrenResult(root);
      return makeChildrenResult([]);
    });

    const { TopicTreeContainer, __testHooks } = await import('../components/TopicTreeContainer');
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <TopicTreeContainer workspaceId="ws-1" />
      </Wrapper>,
    );

    expect(__testHooks).toBeTruthy();

    // Simulate "drop on row-2" by invoking the test-only handler
    act(() => {
      __testHooks.handleDragEnd({
        active: { id: 'root-1', data: { current: { note: root[0] } } },
        over: { id: 'root-2', data: { current: {} } },
        collisions: [{ id: 'root-2', data: { dropMode: 'on' } }],
      });
    });

    expect(mockMutate).toHaveBeenCalledWith(
      { noteId: 'root-1', parentId: 'root-2', oldParentId: null },
      expect.objectContaining({ onError: expect.any(Function) }),
    );

    // Capture the onError from the most recent mutate call and fire it with
    // a synthetic maxDepth error — assert toast copy.
    const onError = mockMutate.mock.calls.at(-1)?.[1]?.onError as
      | ((err: { kind: string }) => void)
      | undefined;
    expect(onError).toBeTypeOf('function');

    act(() => {
      onError?.({ kind: 'maxDepth' });
    });
    expect(toastError).toHaveBeenLastCalledWith(
      'Couldn\'t move "Alpha".',
      expect.objectContaining({
        description: 'This would exceed the 5-level depth limit.',
      }),
    );

    act(() => {
      onError?.({ kind: 'cycle' });
    });
    expect(toastError).toHaveBeenLastCalledWith(
      'Couldn\'t move "Alpha".',
      expect.objectContaining({
        description: "A topic can't be moved into its own subtree.",
      }),
    );
  });

  it('drag-end with dropMode "between-after" derives parentId from the target row\'s parent', async () => {
    const root = [
      makeNote({ id: 'root-1', title: 'Alpha' }),
      makeNote({ id: 'root-2', title: 'Beta' }),
    ];
    const children = [
      makeNote({ id: 'c-1', title: 'Child', parentTopicId: 'root-2', topicDepth: 1 }),
    ];
    mockUseTopicChildren.mockImplementation((_ws: string, parentId: string | null) => {
      if (parentId === null) return makeChildrenResult(root);
      if (parentId === 'root-2') return makeChildrenResult(children);
      return makeChildrenResult([]);
    });

    topicTreeStore.expand('root-2');

    const { TopicTreeContainer, __testHooks } = await import('../components/TopicTreeContainer');
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <TopicTreeContainer workspaceId="ws-1" />
      </Wrapper>,
    );

    // Drop "root-1" between siblings of "c-1" → newParentId = c-1.parentTopicId = "root-2"
    act(() => {
      __testHooks.handleDragEnd({
        active: { id: 'root-1', data: { current: { note: root[0] } } },
        over: { id: 'c-1', data: { current: {} } },
        collisions: [{ id: 'c-1', data: { dropMode: 'between-after' } }],
      });
    });

    expect(mockMutate).toHaveBeenCalledWith(
      { noteId: 'root-1', parentId: 'root-2', oldParentId: null },
      expect.any(Object),
    );
  });

  it('drag-cancel clears the store without firing a mutation', async () => {
    mockUseTopicChildren.mockReturnValue(makeChildrenResult([]));
    const { __testHooks } = await import('../components/TopicTreeContainer');
    await mountContainer();

    topicTreeStore.beginDrag('root-1');
    topicTreeStore.setDropTarget('root-2', 'on');

    act(() => {
      __testHooks.handleDragCancel();
    });

    expect(topicTreeStore.dragSourceId).toBeNull();
    expect(topicTreeStore.dropTargetId).toBeNull();
    expect(mockMutate).not.toHaveBeenCalled();
  });
});
