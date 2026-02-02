/**
 * useAddComment hook tests.
 *
 * T015: Verifies comment creation and cache invalidation on settle.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useAddComment } from '../use-add-comment';
import type { Activity } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    addComment: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

const mockComment: Activity = {
  id: 'act-1',
  activityType: 'comment',
  field: null,
  oldValue: null,
  newValue: null,
  comment: 'New comment content',
  metadata: null,
  createdAt: '2025-01-01T00:00:00Z',
  actor: { id: 'user-1', email: 'test@test.com', displayName: 'Test User' },
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useAddComment', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  it('calls issuesApi.addComment with workspace, issue, and content', async () => {
    vi.mocked(issuesApi.addComment).mockResolvedValue(mockComment);

    const { result } = renderHook(() => useAddComment('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('New comment content');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.addComment).toHaveBeenCalledWith('ws-1', 'issue-1', {
      content: 'New comment content',
    });
  });

  it('invalidates activities cache on settlement', async () => {
    vi.mocked(issuesApi.addComment).mockResolvedValue(mockComment);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useAddComment('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('Test comment');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['issues', 'issue-1', 'activities'],
    });
  });

  it('invalidates issue detail cache on settlement', async () => {
    vi.mocked(issuesApi.addComment).mockResolvedValue(mockComment);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useAddComment('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('Another comment');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['issues', 'issue-1'],
    });
  });

  it('reports error state when API fails', async () => {
    vi.mocked(issuesApi.addComment).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAddComment('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('Will fail');
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
