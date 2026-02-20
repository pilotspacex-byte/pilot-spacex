/**
 * useProjects hook tests.
 *
 * Verifies TanStack Query integration for fetching projects list.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useProjects, projectsKeys, selectAllProjects } from '../useProjects';
import type { Project } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';

vi.mock('@/services/api', () => ({
  projectsApi: {
    list: vi.fn(),
  },
}));

import { projectsApi } from '@/services/api';

const mockProject: Project = {
  id: 'proj-1',
  name: 'Test Project',
  description: 'A test project',
  identifier: 'TP',
  workspaceId: 'ws-1',
  leadId: 'user-1',
  lead: { id: 'user-1', email: 'lead@test.com', displayName: 'Lead User' },
  icon: '🚀',
  issueCount: 10,
  openIssueCount: 3,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
};

const mockPaginatedResponse: PaginatedResponse<Project> = {
  items: [mockProject],
  total: 1,
  page: 1,
  pageSize: 50,
  hasMore: false,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches projects list when workspaceId is provided', async () => {
    vi.mocked(projectsApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useProjects({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(projectsApi.list).toHaveBeenCalledWith('ws-1');
    expect(result.current.data).toEqual(mockPaginatedResponse);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useProjects({ workspaceId: '' }), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(projectsApi.list).not.toHaveBeenCalled();
  });

  it('is disabled when enabled option is false', () => {
    const { result } = renderHook(
      () => useProjects({ workspaceId: 'ws-1', enabled: false }),
      { wrapper: createWrapper() },
    );

    expect(result.current.fetchStatus).toBe('idle');
    expect(projectsApi.list).not.toHaveBeenCalled();
  });

  it('returns error state when API call fails', async () => {
    vi.mocked(projectsApi.list).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useProjects({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });

  it('uses correct query key structure', () => {
    expect(projectsKeys.list('ws-1')).toEqual(['projects', 'list', 'ws-1']);
    expect(projectsKeys.detail('proj-1')).toEqual(['projects', 'detail', 'proj-1']);
    expect(projectsKeys.all).toEqual(['projects']);
  });
});

describe('selectAllProjects', () => {
  it('returns items from paginated response', () => {
    const result = selectAllProjects(mockPaginatedResponse);
    expect(result).toEqual([mockProject]);
  });

  it('returns empty array when data is undefined', () => {
    const result = selectAllProjects(undefined);
    expect(result).toEqual([]);
  });

  it('returns empty array when items is empty', () => {
    const result = selectAllProjects({ items: [], total: 0, page: 1, pageSize: 50, hasMore: false });
    expect(result).toEqual([]);
  });
});
