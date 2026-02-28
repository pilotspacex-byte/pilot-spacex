/**
 * useIssueRelations hook tests.
 *
 * Verifies TanStack Query integration for fetching issue-to-issue relations.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useIssueRelations, issueRelationsKeys } from '../use-issue-relations';
import type { IssueRelation } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    getRelations: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

const mockRelations: IssueRelation[] = [
  {
    id: 'link-1',
    linkType: 'blocks',
    direction: 'outbound',
    relatedIssue: {
      id: 'issue-2',
      identifier: 'PS-2',
      name: 'Blocked issue',
      priority: 'high',
      state: { id: 'state-1', name: 'Todo', color: '#60a5fa', group: 'unstarted' },
    },
  },
  {
    id: 'link-2',
    linkType: 'related',
    direction: 'inbound',
    relatedIssue: {
      id: 'issue-3',
      identifier: 'PS-3',
      name: 'Related issue',
      priority: 'low',
      state: { id: 'state-2', name: 'Done', color: '#22c55e', group: 'completed' },
    },
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useIssueRelations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches relations when workspaceId and issueId are provided', async () => {
    vi.mocked(issuesApi.getRelations).mockResolvedValue(mockRelations);

    const { result } = renderHook(() => useIssueRelations('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.getRelations).toHaveBeenCalledWith('ws-1', 'issue-1');
    expect(result.current.data).toEqual(mockRelations);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useIssueRelations('', 'issue-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.getRelations).not.toHaveBeenCalled();
  });

  it('is disabled when issueId is empty', () => {
    const { result } = renderHook(() => useIssueRelations('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.getRelations).not.toHaveBeenCalled();
  });

  it('returns error state when API call fails', async () => {
    vi.mocked(issuesApi.getRelations).mockRejectedValue(new Error('Unauthorized'));

    const { result } = renderHook(() => useIssueRelations('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it('returns empty array when API returns no relations', async () => {
    vi.mocked(issuesApi.getRelations).mockResolvedValue([]);

    const { result } = renderHook(() => useIssueRelations('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });

  it('uses correct query key', () => {
    expect(issueRelationsKeys.detail('ws-1', 'issue-1')).toEqual([
      'issues',
      'issue-1',
      'relations',
      'ws-1',
    ]);
  });
});
