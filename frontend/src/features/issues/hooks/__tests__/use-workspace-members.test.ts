/**
 * useWorkspaceMembers hook tests.
 *
 * T015: Verifies workspace member fetching via apiClient.
 * A4-E05: Updated for PaginatedWorkspaceMembers return type.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceMembers, type WorkspaceMember } from '../use-workspace-members';

vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/services/api';

const mockMembers: WorkspaceMember[] = [
  {
    userId: 'user-1',
    email: 'owner@test.com',
    fullName: 'Owner',
    avatarUrl: null,
    role: 'owner',
    joinedAt: '2025-01-01T00:00:00Z',
    weeklyAvailableHours: 40,
  },
  {
    userId: 'user-2',
    email: 'member@test.com',
    fullName: 'Member',
    avatarUrl: null,
    role: 'member',
    joinedAt: '2025-01-02T00:00:00Z',
    weeklyAvailableHours: 40,
  },
];

const mockPaginatedResponse = {
  items: mockMembers,
  total: 2,
  has_next: false,
  has_prev: false,
  page_size: 20,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useWorkspaceMembers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches workspace members', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useWorkspaceMembers('ws-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining('/workspaces/ws-1/members'));
    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items[0]!.role).toBe('owner');
    expect(result.current.data?.total).toBe(2);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useWorkspaceMembers(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('returns error when API fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Unauthorized'));

    const { result } = renderHook(() => useWorkspaceMembers('ws-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
