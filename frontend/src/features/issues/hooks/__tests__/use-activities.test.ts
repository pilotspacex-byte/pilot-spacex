/**
 * useActivities hook tests.
 *
 * T015: Verifies infinite query pagination for activity timeline.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useActivities } from '../use-activities';
import type { ActivityTimelineResponse } from '@/types';

vi.mock('@/services/api', () => ({
  issuesApi: {
    listActivities: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

function makeActivitiesPage(total: number, count: number): ActivityTimelineResponse {
  return {
    activities: Array.from({ length: count }, (_, i) => ({
      id: `act-${i}`,
      activityType: 'comment',
      field: null,
      oldValue: null,
      newValue: null,
      comment: `Comment ${i}`,
      metadata: null,
      createdAt: '2025-01-01T00:00:00Z',
      actor: { id: 'user-1', email: 'test@test.com', displayName: 'Test' },
    })),
    total,
  };
}

describe('useActivities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches first page of activities', async () => {
    const page = makeActivitiesPage(100, 50);
    vi.mocked(issuesApi.listActivities).mockResolvedValue(page);

    const { result } = renderHook(() => useActivities('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(issuesApi.listActivities).toHaveBeenCalledWith('ws-1', 'issue-1', {
      limit: 50,
      offset: 0,
    });
    expect(result.current.data?.pages).toHaveLength(1);
    expect(result.current.data?.pages[0]!.activities).toHaveLength(50);
  });

  it('computes next page offset when more data exists', async () => {
    const page = makeActivitiesPage(120, 50);
    vi.mocked(issuesApi.listActivities).mockResolvedValue(page);

    const { result } = renderHook(() => useActivities('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.hasNextPage).toBe(true);
  });

  it('stops pagination when all activities are loaded', async () => {
    const page = makeActivitiesPage(30, 30);
    vi.mocked(issuesApi.listActivities).mockResolvedValue(page);

    const { result } = renderHook(() => useActivities('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // total (30) <= offset of next page (50), so no next page
    expect(result.current.hasNextPage).toBe(false);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useActivities('', 'issue-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.listActivities).not.toHaveBeenCalled();
  });

  it('is disabled when issueId is empty', () => {
    const { result } = renderHook(() => useActivities('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(issuesApi.listActivities).not.toHaveBeenCalled();
  });
});
