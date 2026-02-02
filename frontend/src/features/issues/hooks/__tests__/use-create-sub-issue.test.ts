/**
 * useCreateSubIssue hook tests.
 *
 * T015: Verifies sub-issue creation with parentId and cache invalidation.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useCreateSubIssue } from '../use-create-sub-issue';
import { issueDetailKeys } from '../use-issue-detail';
import type { Issue } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    create: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

const mockCreatedIssue: Issue = {
  id: 'sub-issue-1',
  identifier: 'PS-2',
  name: 'Sub Task',
  title: 'Sub Task',
  state: { id: 'state-1', name: 'Todo', color: '#5B8FC9', group: 'unstarted' },
  priority: 'medium',
  type: 'task',
  projectId: 'proj-1',
  workspaceId: 'ws-1',
  sequenceId: 2,
  sortOrder: 0,
  reporterId: 'user-1',
  reporter: { id: 'user-1', email: 'test@test.com', displayName: 'Test User' },
  labels: [],
  subIssueCount: 0,
  parentId: 'parent-1',
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

describe('useCreateSubIssue', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  it('calls issuesApi.create with parentId merged into data', async () => {
    vi.mocked(issuesApi.create).mockResolvedValue(mockCreatedIssue);

    const { result } = renderHook(() => useCreateSubIssue('ws-1', 'parent-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Sub Task', projectId: 'proj-1' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.create).toHaveBeenCalledWith('ws-1', {
      name: 'Sub Task',
      projectId: 'proj-1',
      parentId: 'parent-1',
    });
  });

  it('invalidates parent issue detail cache on success', async () => {
    vi.mocked(issuesApi.create).mockResolvedValue(mockCreatedIssue);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateSubIssue('ws-1', 'parent-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Sub Task' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: issueDetailKeys.detail('parent-1'),
    });
  });

  it('invalidates all issues cache on success', async () => {
    vi.mocked(issuesApi.create).mockResolvedValue(mockCreatedIssue);
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateSubIssue('ws-1', 'parent-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: 'Sub Task' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: issueDetailKeys.all,
    });
  });

  it('reports error state when creation fails', async () => {
    vi.mocked(issuesApi.create).mockRejectedValue(new Error('Validation error'));

    const { result } = renderHook(() => useCreateSubIssue('ws-1', 'parent-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({ name: '' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
