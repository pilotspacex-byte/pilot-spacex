/**
 * useProjectCycles hook tests.
 *
 * T015: Verifies cycle list fetching with stale time and enabled logic.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useProjectCycles } from '../use-project-cycles';
import type { CycleListResponse } from '@/services/api';

vi.mock('@/services/api', () => ({
  cyclesApi: {
    list: vi.fn(),
  },
}));

import { cyclesApi } from '@/services/api';

const mockCycleListResponse: CycleListResponse = {
  items: [
    {
      id: 'cycle-1',
      workspaceId: 'ws-1',
      name: 'Sprint 1',
      status: 'active',
      sequence: 1,
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
      project: { id: 'proj-1', name: 'Test', identifier: 'PS' },
      issueCount: 10,
    },
  ],
  total: 1,
  nextCursor: null,
  prevCursor: null,
  hasNext: false,
  hasPrev: false,
  pageSize: 25,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useProjectCycles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches cycles for a given project', async () => {
    vi.mocked(cyclesApi.list).mockResolvedValue(mockCycleListResponse);

    const { result } = renderHook(() => useProjectCycles('ws-1', 'proj-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cyclesApi.list).toHaveBeenCalledWith('ws-1', { projectId: 'proj-1' });
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]!.name).toBe('Sprint 1');
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useProjectCycles('', 'proj-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(cyclesApi.list).not.toHaveBeenCalled();
  });

  it('is disabled when projectId is empty', () => {
    const { result } = renderHook(() => useProjectCycles('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(cyclesApi.list).not.toHaveBeenCalled();
  });

  it('returns error when API fails', async () => {
    vi.mocked(cyclesApi.list).mockRejectedValue(new Error('Forbidden'));

    const { result } = renderHook(() => useProjectCycles('ws-1', 'proj-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
