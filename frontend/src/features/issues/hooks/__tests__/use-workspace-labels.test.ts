/**
 * useWorkspaceLabels hook tests.
 *
 * T015: Verifies workspace label fetching via apiClient.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceLabels } from '../use-workspace-labels';
import type { Label } from '@/types';

vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/services/api';

const mockLabels: Label[] = [
  { id: 'label-1', name: 'Bug', color: '#D9534F', projectId: 'proj-1' },
  { id: 'label-2', name: 'Feature', color: '#29A386', projectId: 'proj-1' },
  { id: 'label-3', name: 'Docs', color: '#6B8FAD', projectId: 'proj-1' },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useWorkspaceLabels', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches workspace labels', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockLabels);

    const { result } = renderHook(() => useWorkspaceLabels('ws-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/workspaces/ws-1/labels');
    expect(result.current.data).toHaveLength(3);
    expect(result.current.data?.[0]!.name).toBe('Bug');
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useWorkspaceLabels(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('returns error when API fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useWorkspaceLabels('ws-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
