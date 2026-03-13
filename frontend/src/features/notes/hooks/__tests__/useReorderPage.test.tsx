/**
 * Unit tests for useReorderPage mutation hook.
 *
 * Tests that:
 * - mutationFn calls notesApi.reorderPage with correct arguments
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

const mockReorderPage = vi.fn();

vi.mock('@/services/api', () => ({
  notesApi: {
    reorderPage: (...args: unknown[]) => mockReorderPage(...args),
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

describe('useReorderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Test 2: mutate calls notesApi.reorderPage with correct workspaceId, noteId, and insertAfterId', async () => {
    const { wrapper } = createWrapper();
    mockReorderPage.mockResolvedValue({ id: 'note-1', title: 'Test' });

    const { useReorderPage } = await import('../useReorderPage');
    const { result } = renderHook(() => useReorderPage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', insertAfterId: 'note-sibling' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockReorderPage).toHaveBeenCalledWith('ws-1', 'note-1', 'note-sibling');
  });

  it('Test 4: onSuccess invalidates projectPageTree query cache', async () => {
    const { wrapper, queryClient } = createWrapper();
    mockReorderPage.mockResolvedValue({ id: 'note-1', title: 'Test' });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { useReorderPage } = await import('../useReorderPage');
    const { result } = renderHook(() => useReorderPage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', insertAfterId: null });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining(['notes', 'project-tree', 'ws-1', 'proj-1']),
      })
    );
  });

  it('Test 6: shows error toast on mutation failure', async () => {
    const { wrapper } = createWrapper();
    mockReorderPage.mockRejectedValue(new Error('Network error'));

    const { useReorderPage } = await import('../useReorderPage');
    const { result } = renderHook(() => useReorderPage('ws-1', 'proj-1'), { wrapper });

    await act(async () => {
      result.current.mutate({ noteId: 'note-1', insertAfterId: null });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(mockToastError).toHaveBeenCalledWith('Failed to reorder page');
  });
});
