/**
 * useDeleteArtifact hook tests.
 *
 * Covers: MGMT-04 — optimistic delete with cache restore on error and
 * invalidation on settlement. Toast message must be exact.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useDeleteArtifact } from '../use-delete-artifact';
import { artifactsKeys } from '../use-project-artifacts';
import type { Artifact } from '@/types/artifact';

vi.mock('@/services/api/artifacts', () => ({
  artifactsApi: {
    list: vi.fn(),
    delete: vi.fn(),
    getSignedUrl: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { artifactsApi } from '@/services/api/artifacts';
import { toast } from 'sonner';

const mockArtifacts: Artifact[] = [
  {
    id: 'artifact-1',
    filename: 'spec.pdf',
    mimeType: 'application/pdf',
    sizeBytes: 102400,
    status: 'ready',
    uploaderId: 'user-1',
    projectId: 'proj-1',
    workspaceId: 'ws-1',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
  {
    id: 'artifact-2',
    filename: 'design.png',
    mimeType: 'image/png',
    sizeBytes: 204800,
    status: 'ready',
    uploaderId: 'user-1',
    projectId: 'proj-1',
    workspaceId: 'ws-1',
    createdAt: '2026-01-02T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
  },
];

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

describe('useDeleteArtifact', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  it('onMutate removes artifact from cache at artifactsKeys.list(ws, proj)', async () => {
    // Delay API resolution to observe optimistic update
    let resolveDelete: () => void;
    const deletePromise = new Promise<void>((resolve) => {
      resolveDelete = resolve;
    });
    vi.mocked(artifactsApi.delete).mockReturnValue(deletePromise);

    const listKey = artifactsKeys.list('ws-1', 'proj-1');
    queryClient.setQueryData<Artifact[]>(listKey, mockArtifacts);

    const { result } = renderHook(() => useDeleteArtifact('ws-1', 'proj-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('artifact-1');
    });

    // Cache should be optimistically filtered before API resolves
    await waitFor(() => {
      const cached = queryClient.getQueryData<Artifact[]>(listKey) ?? [];
      expect(cached).toHaveLength(1);
      expect(cached.at(0)?.id).toBe('artifact-2');
    });

    // Resolve the API
    await act(async () => {
      resolveDelete!();
    });
  });

  it('onError restores previous cache and calls toast.error with exact message', async () => {
    vi.mocked(artifactsApi.delete).mockRejectedValue(new Error('Server error'));

    const listKey = artifactsKeys.list('ws-1', 'proj-1');
    queryClient.setQueryData<Artifact[]>(listKey, mockArtifacts);

    const { result } = renderHook(() => useDeleteArtifact('ws-1', 'proj-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('artifact-1');
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Cache should be restored to original 2 items
    const cached = queryClient.getQueryData<Artifact[]>(listKey) ?? [];
    expect(cached).toHaveLength(2);
    expect(cached.at(0)?.id).toBe('artifact-1');

    // Toast must use exact message from the plan
    expect(toast.error).toHaveBeenCalledWith('Delete failed. Please try again.');
  });

  it('onSettled calls queryClient.invalidateQueries with artifactsKeys.list(ws, proj)', async () => {
    vi.mocked(artifactsApi.delete).mockResolvedValue(undefined);

    const listKey = artifactsKeys.list('ws-1', 'proj-1');
    queryClient.setQueryData<Artifact[]>(listKey, mockArtifacts);

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useDeleteArtifact('ws-1', 'proj-1'), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('artifact-1');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: listKey }));
  });
});
