/**
 * useUpdateIssue hook tests.
 *
 * T015: Verifies optimistic update, rollback on error, and cache invalidation.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useUpdateIssue } from '../use-update-issue';
import { issueDetailKeys } from '../use-issue-detail';
import type { Issue } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    update: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

const mockIssue: Issue = {
  id: 'issue-1',
  identifier: 'PS-1',
  name: 'Original Title',
  title: 'Original Title',
  state: { id: 'state-1', name: 'Todo', color: '#5B8FC9', group: 'unstarted' },
  priority: 'medium',
  type: 'task',
  projectId: 'proj-1',
  workspaceId: 'ws-1',
  sequenceId: 1,
  sortOrder: 0,
  reporterId: 'user-1',
  reporter: { id: 'user-1', email: 'test@test.com', displayName: 'Test User' },
  labels: [],
  subIssueCount: 0,
  project: { id: 'proj-1', name: 'Test Project', identifier: 'PS' },
  aiGenerated: false,
  hasAiEnhancements: false,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
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

describe('useUpdateIssue', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  it('calls issuesApi.update with correct arguments', async () => {
    const updatedIssue = { ...mockIssue, name: 'Updated Title' };
    vi.mocked(issuesApi.update).mockResolvedValue(updatedIssue);

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Updated Title' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.update).toHaveBeenCalledWith('ws-1', 'issue-1', {
      name: 'Updated Title',
    });
  });

  it('optimistically updates cache before API responds', async () => {
    let resolveUpdate: (value: Issue) => void;
    const updatePromise = new Promise<Issue>((resolve) => {
      resolveUpdate = resolve;
    });
    vi.mocked(issuesApi.update).mockReturnValue(updatePromise);

    const queryKey = issueDetailKeys.detail('issue-1');
    queryClient.setQueryData<Issue>(queryKey, mockIssue);

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Optimistic Title' });
    });

    // Cache should be updated optimistically before API responds
    await waitFor(() => {
      const cached = queryClient.getQueryData<Issue>(queryKey);
      expect(cached?.name).toBe('Optimistic Title');
    });

    // Now resolve the API call
    const serverIssue = { ...mockIssue, name: 'Optimistic Title' };
    await act(async () => {
      resolveUpdate!(serverIssue);
    });
  });

  it('rolls back cache on API error', async () => {
    vi.mocked(issuesApi.update).mockRejectedValue(new Error('Server error'));

    const queryKey = issueDetailKeys.detail('issue-1');
    queryClient.setQueryData<Issue>(queryKey, mockIssue);

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Will Fail' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Cache should be rolled back to original
    const cached = queryClient.getQueryData<Issue>(queryKey);
    expect(cached?.name).toBe('Original Title');
  });

  it('invalidates query cache on settlement', async () => {
    const updatedIssue = { ...mockIssue, priority: 'high' as const };
    vi.mocked(issuesApi.update).mockResolvedValue(updatedIssue);

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ priority: 'high' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: issueDetailKeys.detail('issue-1'),
    });
  });
});
