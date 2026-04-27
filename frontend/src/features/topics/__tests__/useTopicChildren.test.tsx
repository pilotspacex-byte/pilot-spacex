/**
 * Unit tests for useTopicChildren (Phase 93 Plan 03 Task 2).
 *
 * Coverage:
 *  - For a non-null parentId, hook calls notesApi.listChildren and keys by topicTreeKeys.children.
 *  - For parentId === null (root), hook falls back to notesApi.list (workspace-scoped) and
 *    filters items to those with parentTopicId === null (Decision K — root listing v1).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

const mockListChildren = vi.fn();
const mockList = vi.fn();
const mockListAncestors = vi.fn();
const mockMoveTopic = vi.fn();

vi.mock('@/services/api', () => ({
  notesApi: {
    listChildren: (...args: unknown[]) => mockListChildren(...args),
    list: (...args: unknown[]) => mockList(...args),
    listAncestors: (...args: unknown[]) => mockListAncestors(...args),
    moveTopic: (...args: unknown[]) => mockMoveTopic(...args),
  },
}));

vi.mock('@/lib/supabase', () => ({
  supabase: { auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) } },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

describe('useTopicChildren', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns paginated children for a non-null parentId via listChildren', async () => {
    const { wrapper } = createWrapper();
    const fakePage = {
      items: [{ id: 'c1', title: 'Child 1', parentTopicId: 'p1', topicDepth: 1 }],
      total: 1,
      hasNext: false,
      hasPrev: false,
      pageSize: 20,
      nextCursor: null,
      prevCursor: null,
    };
    mockListChildren.mockResolvedValueOnce(fakePage);

    const { useTopicChildren } = await import('../hooks/useTopicChildren');
    const { result } = renderHook(() => useTopicChildren('ws-1', 'p1', 1, 20), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockListChildren).toHaveBeenCalledWith('ws-1', 'p1', 1, 20);
    expect(mockList).not.toHaveBeenCalled();
    expect(result.current.data).toBe(fakePage);
  });

  it('for parentId === null, fetches workspace list and filters to top-level topics', async () => {
    const { wrapper } = createWrapper();
    const allNotes = {
      items: [
        { id: 'n1', title: 'Root A', parentTopicId: null, topicDepth: 0 },
        { id: 'n2', title: 'Child', parentTopicId: 'n1', topicDepth: 1 },
        { id: 'n3', title: 'Root B', parentTopicId: null, topicDepth: 0 },
      ],
      total: 3,
      hasNext: false,
      hasPrev: false,
      pageSize: 200,
      nextCursor: null,
      prevCursor: null,
    };
    mockList.mockResolvedValueOnce(allNotes);

    const { useTopicChildren } = await import('../hooks/useTopicChildren');
    const { result } = renderHook(() => useTopicChildren('ws-1', null), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockList).toHaveBeenCalled();
    expect(mockListChildren).not.toHaveBeenCalled();
    // Filtered to root-only topics
    expect(result.current.data?.items.map((n) => n.id)).toEqual(['n1', 'n3']);
    expect(result.current.data?.total).toBe(2);
  });

  it('issue #141: root listing requests pageSize within backend cap (<=100)', async () => {
    // Backend `GET /workspaces/{ws}/notes` enforces `Query(ge=1, le=100)` on
    // `page_size`. The previous v1 implementation requested 200 → FastAPI
    // returned 422 → React Query surfaced an error → sidebar tree rendered
    // empty. Lock the upper bound here so future bumps match the backend.
    const { wrapper } = createWrapper();
    mockList.mockResolvedValueOnce({
      items: [],
      total: 0,
      hasNext: false,
      hasPrev: false,
      pageSize: 100,
      nextCursor: null,
      prevCursor: null,
    });

    const { useTopicChildren } = await import('../hooks/useTopicChildren');
    const { result } = renderHook(() => useTopicChildren('ws-1', null), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockList).toHaveBeenCalledTimes(1);
    const call = mockList.mock.calls[0] as [string, unknown, number, number];
    const requestedPageSize = call[3];
    expect(requestedPageSize).toBeGreaterThanOrEqual(1);
    expect(requestedPageSize).toBeLessThanOrEqual(100);
  });
});
