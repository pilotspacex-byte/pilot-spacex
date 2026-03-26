/**
 * useDocumentIngest tests — AUI-05
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';

// Mock attachmentsApi before import
vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: {
    ingestDocument: vi.fn().mockResolvedValue({ status: 'queued', attachmentId: 'test-id' }),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { useDocumentIngest } from '../useDocumentIngest';
import { attachmentsApi } from '@/services/api/attachments';
import { toast } from 'sonner';

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  }
  return Wrapper;
}

describe('useDocumentIngest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls attachmentsApi.ingestDocument with artifactId and adjustments', async () => {
    const { result } = renderHook(
      () => useDocumentIngest({ artifactId: 'art-1', workspaceId: 'ws-1', projectId: 'proj-1' }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      await result.current.mutateAsync([{ chunkIndex: 0, excluded: true }]);
    });

    expect(attachmentsApi.ingestDocument).toHaveBeenCalledWith('art-1', {
      workspaceId: 'ws-1',
      projectId: 'proj-1',
      chunkAdjustments: [{ chunkIndex: 0, excluded: true }],
    });
  });

  it('shows success toast on successful ingest', async () => {
    const { result } = renderHook(
      () => useDocumentIngest({ artifactId: 'art-1', workspaceId: 'ws-1', projectId: 'proj-1' }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      await result.current.mutateAsync([]);
    });

    expect(toast.success).toHaveBeenCalledWith('Document queued for Knowledge Graph ingestion.');
  });

  it('shows error toast on failure', async () => {
    vi.mocked(attachmentsApi.ingestDocument).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(
      () => useDocumentIngest({ artifactId: 'art-1', workspaceId: 'ws-1', projectId: 'proj-1' }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      result.current.mutate([]);
    });
    // Wait for mutation to settle
    await act(async () => {});

    expect(toast.error).toHaveBeenCalledWith('Failed to queue document. Please try again.');
  });
});
