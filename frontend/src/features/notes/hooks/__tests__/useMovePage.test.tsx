/**
 * Unit tests for useMovePage mutation hook.
 *
 * Tests that:
 * - mutationFn calls notesApi.movePage with correct arguments
 * - onSuccess invalidates the project tree cache
 * - onError shows error toast via sonner
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMovePage = vi.fn();

vi.mock('@/services/api', () => ({
  notesApi: {
    movePage: (...args: unknown[]) => mockMovePage(...args),
  },
}));

const mockToastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useMovePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Test 1: mutate calls notesApi.movePage with correct workspaceId, noteId, and newParentId', async () => {
    const { wrapper } = createWrapper();
    mockMovePage.mockResolvedValue({ id: 'note-1', title: 'Test' });

    const { useMovePage } = await import('../useMovePage');
    const { result } = renderHook(() => useMovePage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', newParentId: 'parent-2' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockMovePage).toHaveBeenCalledWith('ws-1', 'note-1', 'parent-2');
  });

  it('Test 3: onSuccess invalidates projectPageTree query cache', async () => {
    const { wrapper, queryClient } = createWrapper();
    mockMovePage.mockResolvedValue({ id: 'note-1', title: 'Test' });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { useMovePage } = await import('../useMovePage');
    const { result } = renderHook(() => useMovePage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', newParentId: null });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining(['notes', 'project-tree', 'ws-1', 'proj-1']),
      })
    );
  });

  it('Test 5: shows error toast on mutation failure', async () => {
    const { wrapper } = createWrapper();
    mockMovePage.mockRejectedValue(new Error('Network error'));

    const { useMovePage } = await import('../useMovePage');
    const { result } = renderHook(() => useMovePage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', newParentId: 'parent-2' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(mockToastError).toHaveBeenCalledWith('Failed to move page');
  });
});
