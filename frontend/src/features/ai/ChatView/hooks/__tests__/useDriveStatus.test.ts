/**
 * useDriveStatus hook tests (T042 — TDD).
 *
 * Verifies TanStack Query integration for Google Drive connection status.
 * Tests: query disabled when workspaceId is absent, connected=false state,
 * and connected=true state with email.
 *
 * @module features/ai/ChatView/hooks/__tests__/useDriveStatus
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useDriveStatus } from '../useDriveStatus';
import type { DriveStatusResponse } from '@/types/attachments';

// ── Module mocks ────────────────────────────────────────────────────────────

vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: {
    getDriveStatus: vi.fn(),
    getDriveAuthUrl: vi.fn(),
    getDriveFiles: vi.fn(),
    importDriveFile: vi.fn(),
    revokeDriveCredentials: vi.fn(),
  },
}));

import { attachmentsApi } from '@/services/api/attachments';

// ── Helpers ─────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('useDriveStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns_disconnected_when_no_workspace_id', () => {
    const { result } = renderHook(() => useDriveStatus(undefined), {
      wrapper: createWrapper(),
    });

    // Query disabled — stays idle, never fetches
    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
    expect(attachmentsApi.getDriveStatus).not.toHaveBeenCalled();
  });

  it('returns_connected_false_initially', async () => {
    const mockResponse: DriveStatusResponse = {
      connected: false,
      googleEmail: null,
      connectedAt: null,
    };
    vi.mocked(attachmentsApi.getDriveStatus).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDriveStatus('ws-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(attachmentsApi.getDriveStatus).toHaveBeenCalledWith('ws-1');
    expect(result.current.data).toEqual({
      connected: false,
      googleEmail: null,
      connectedAt: null,
    });
  });

  it('returns_connected_true_with_email', async () => {
    const mockResponse: DriveStatusResponse = {
      connected: true,
      googleEmail: 'alice@example.com',
      connectedAt: '2026-01-01T00:00:00Z',
    };
    vi.mocked(attachmentsApi.getDriveStatus).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDriveStatus('ws-2'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(attachmentsApi.getDriveStatus).toHaveBeenCalledWith('ws-2');
    expect(result.current.data).toEqual({
      connected: true,
      googleEmail: 'alice@example.com',
      connectedAt: '2026-01-01T00:00:00Z',
    });
  });
});
