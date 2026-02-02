/**
 * useIssueDetail hook tests.
 *
 * T015: Verifies TanStack Query integration for fetching a single issue.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useIssueDetail } from '../use-issue-detail';
import type { Issue } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    get: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

const mockIssue: Issue = {
  id: 'issue-1',
  identifier: 'PS-1',
  name: 'Test Issue',
  title: 'Test Issue',
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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useIssueDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches issue detail when workspaceId and issueId are provided', async () => {
    vi.mocked(issuesApi.get).mockResolvedValue(mockIssue);

    const { result } = renderHook(() => useIssueDetail('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.get).toHaveBeenCalledWith('ws-1', 'issue-1');
    expect(result.current.data).toEqual(mockIssue);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useIssueDetail('', 'issue-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.get).not.toHaveBeenCalled();
  });

  it('is disabled when issueId is empty', () => {
    const { result } = renderHook(() => useIssueDetail('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.get).not.toHaveBeenCalled();
  });

  it('returns error state when API call fails', async () => {
    vi.mocked(issuesApi.get).mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useIssueDetail('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
