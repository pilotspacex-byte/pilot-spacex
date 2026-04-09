import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock API modules before imports
vi.mock('@/services/api/notes', () => ({
  notesApi: { list: vi.fn() },
}));
vi.mock('@/services/api/issues', () => ({
  issuesApi: { list: vi.fn() },
}));
vi.mock('@/services/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}));

import { notesApi } from '@/services/api/notes';
import { issuesApi } from '@/services/api/issues';
import { projectsApi } from '@/services/api/projects';
import { useEntitySearch } from '../useEntitySearch';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const WORKSPACE = 'ws-test-1';

function mockApiResponses(
  notes: { id: string; title: string }[] = [],
  issues: { id: string; name: string }[] = [],
  projects: { id: string; name: string }[] = []
) {
  vi.mocked(notesApi.list).mockResolvedValue({
    items: notes, total: notes.length, nextCursor: null, prevCursor: null,
    hasNext: false, hasPrev: false, pageSize: 20,
  } as never);
  vi.mocked(issuesApi.list).mockResolvedValue({
    items: issues, total: issues.length, nextCursor: null, prevCursor: null,
    hasNext: false, hasPrev: false, pageSize: 20,
  } as never);
  vi.mocked(projectsApi.list).mockResolvedValue({
    items: projects, total: projects.length, nextCursor: null, prevCursor: null,
    hasNext: false, hasPrev: false, pageSize: 50,
  } as never);
}

describe('useEntitySearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    mockApiResponses();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not call APIs when workspaceId is empty', async () => {
    renderHook(() => useEntitySearch({ query: '', workspaceId: '' }), {
      wrapper: createWrapper(),
    });

    // Advance debounce timer
    act(() => { vi.advanceTimersByTime(200); });

    expect(notesApi.list).not.toHaveBeenCalled();
    expect(issuesApi.list).not.toHaveBeenCalled();
    expect(projectsApi.list).not.toHaveBeenCalled();
  });

  it('calls all three APIs when workspaceId is set and query is empty (browse mode)', async () => {
    mockApiResponses(
      [{ id: 'n1', title: 'Note 1' }],
      [{ id: 'i1', name: 'Issue 1' }],
      [{ id: 'p1', name: 'Project 1' }]
    );

    const { result } = renderHook(
      () => useEntitySearch({ query: '', workspaceId: WORKSPACE }),
      { wrapper: createWrapper() }
    );

    // Advance debounce timer
    act(() => { vi.advanceTimersByTime(200); });

    await waitFor(() => {
      expect(result.current.notes).toHaveLength(1);
    });

    expect(notesApi.list).toHaveBeenCalledWith(WORKSPACE, { search: '' }, 1, 20);
    expect(issuesApi.list).toHaveBeenCalledWith(WORKSPACE, { search: '' }, 1, 20);
    expect(projectsApi.list).toHaveBeenCalledWith(WORKSPACE);
  });

  it('debounces query changes by 150ms', async () => {
    mockApiResponses([{ id: 'n1', title: 'Match' }]);

    const { rerender } = renderHook(
      ({ query }: { query: string }) => useEntitySearch({ query, workspaceId: WORKSPACE }),
      { wrapper: createWrapper(), initialProps: { query: '' } }
    );

    // Initial calls happen for empty query
    act(() => { vi.advanceTimersByTime(200); });
    await waitFor(() => expect(notesApi.list).toHaveBeenCalledTimes(1));
    vi.clearAllMocks();
    mockApiResponses([{ id: 'n1', title: 'Match' }]);

    // Type quickly: 'a', then 'ab' within 150ms — only 'ab' should trigger API call
    rerender({ query: 'a' });
    act(() => { vi.advanceTimersByTime(50); });
    rerender({ query: 'ab' });

    // At 100ms total — debounce not yet fired for 'ab'
    act(() => { vi.advanceTimersByTime(50); });
    expect(notesApi.list).not.toHaveBeenCalled();

    // At 200ms after last change — debounce fires for 'ab'
    act(() => { vi.advanceTimersByTime(100); });
    await waitFor(() => {
      expect(notesApi.list).toHaveBeenCalledWith(WORKSPACE, { search: 'ab' }, 1, 20);
    });
  });

  it('filters projects client-side by name', async () => {
    mockApiResponses(
      [],
      [],
      [
        { id: 'p1', name: 'Frontend App' },
        { id: 'p2', name: 'Backend API' },
        { id: 'p3', name: 'Mobile Frontend' },
      ]
    );

    const { result } = renderHook(
      () => useEntitySearch({ query: 'front', workspaceId: WORKSPACE }),
      { wrapper: createWrapper() }
    );

    act(() => { vi.advanceTimersByTime(200); });

    await waitFor(() => {
      expect(result.current.projects).toHaveLength(2);
    });

    expect(result.current.projects.map((p) => p.id)).toEqual(['p1', 'p3']);
    // projectsApi.list should NOT include query — it's a stable query
    expect(projectsApi.list).toHaveBeenCalledWith(WORKSPACE);
  });

  it('returns empty arrays when APIs return no results', async () => {
    const { result } = renderHook(
      () => useEntitySearch({ query: 'xyz', workspaceId: WORKSPACE }),
      { wrapper: createWrapper() }
    );

    act(() => { vi.advanceTimersByTime(200); });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.notes).toEqual([]);
    expect(result.current.issues).toEqual([]);
    expect(result.current.projects).toEqual([]);
  });

  it('uses correct API signatures — pageSize as 4th positional arg', async () => {
    mockApiResponses();

    renderHook(
      () => useEntitySearch({ query: 'test', workspaceId: WORKSPACE }),
      { wrapper: createWrapper() }
    );

    act(() => { vi.advanceTimersByTime(200); });

    await waitFor(() => {
      expect(notesApi.list).toHaveBeenCalled();
    });

    // Verify exact call signature: (workspaceId, filters, page, pageSize)
    expect(notesApi.list).toHaveBeenCalledWith(WORKSPACE, { search: 'test' }, 1, 20);
    expect(issuesApi.list).toHaveBeenCalledWith(WORKSPACE, { search: 'test' }, 1, 20);
  });
});
