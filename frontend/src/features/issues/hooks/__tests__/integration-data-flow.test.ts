/**
 * Data flow integration tests for TanStack Query hooks.
 *
 * T047a: Tests hook wiring for issue detail fetching, optimistic updates,
 * rollback, comment cache invalidation, and save-status lifecycle.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { Issue } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('@/services/api', () => ({
  issuesApi: {
    get: vi.fn(),
    update: vi.fn(),
    listActivities: vi.fn(),
    addComment: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';
import { useIssueDetail, issueDetailKeys } from '../use-issue-detail';
import { useUpdateIssue } from '../use-update-issue';
import { useAddComment } from '../use-add-comment';
import { activitiesKeys } from '../use-activities';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Issue Detail data flow integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  it('useIssueDetail fetches issue data and caches it', async () => {
    vi.mocked(issuesApi.get).mockResolvedValue(mockIssue);

    const { result } = renderHook(() => useIssueDetail('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockIssue);

    // Verify it is cached
    const cached = queryClient.getQueryData(issueDetailKeys.detail('issue-1'));
    expect(cached).toEqual(mockIssue);
  });

  it('useUpdateIssue optimistically updates the issue cache', async () => {
    // Seed cache
    const queryKey = issueDetailKeys.detail('issue-1');
    queryClient.setQueryData<Issue>(queryKey, mockIssue);

    // Hold the API call pending so we can observe optimistic state
    let resolveUpdate!: (value: Issue) => void;
    vi.mocked(issuesApi.update).mockReturnValue(
      new Promise<Issue>((resolve) => {
        resolveUpdate = resolve;
      })
    );

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Optimistic Name' });
    });

    // Cache should reflect the optimistic value before API settles
    await waitFor(() => {
      const cached = queryClient.getQueryData<Issue>(queryKey);
      expect(cached?.name).toBe('Optimistic Name');
    });

    // Resolve API
    await act(async () => {
      resolveUpdate({ ...mockIssue, name: 'Optimistic Name' });
    });
  });

  it('useUpdateIssue rollbacks on error', async () => {
    const queryKey = issueDetailKeys.detail('issue-1');
    queryClient.setQueryData<Issue>(queryKey, mockIssue);

    vi.mocked(issuesApi.update).mockRejectedValue(new Error('Server error'));

    const { result } = renderHook(() => useUpdateIssue('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Will Fail' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Should rollback to original
    const cached = queryClient.getQueryData<Issue>(queryKey);
    expect(cached?.name).toBe('Original Title');
  });

  it('useAddComment invalidates activity cache on settlement', async () => {
    vi.mocked(issuesApi.addComment).mockResolvedValue({
      id: 'act-1',
      activityType: 'comment',
      field: null,
      oldValue: null,
      newValue: null,
      comment: 'Test comment',
      metadata: null,
      createdAt: '2025-01-01T00:00:00Z',
      actor: { id: 'user-1', email: 'test@test.com', displayName: 'Test User' },
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useAddComment('ws-1', 'issue-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('Test comment');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activitiesKeys.all('issue-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: issueDetailKeys.detail('issue-1'),
    });
  });
});
