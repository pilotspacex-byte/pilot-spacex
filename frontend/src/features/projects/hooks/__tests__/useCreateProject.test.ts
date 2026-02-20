/**
 * useCreateProject hook tests.
 *
 * Verifies TanStack Query mutation integration for project CRUD operations.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useCreateProject, useUpdateProject, useDeleteProject } from '../useCreateProject';
import type { Project } from '@/types';

vi.mock('@/services/api', () => ({
  projectsApi: {
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { projectsApi } from '@/services/api';
import { toast } from 'sonner';

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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useCreateProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates project and shows success toast', async () => {
    vi.mocked(projectsApi.create).mockResolvedValue(mockProject);

    const { result } = renderHook(
      () => useCreateProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ name: 'Test Project', identifier: 'TP' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(projectsApi.create).toHaveBeenCalledWith('ws-1', {
      name: 'Test Project',
      identifier: 'TP',
    });
    expect(toast.success).toHaveBeenCalledWith('Project created', {
      description: '"Test Project" has been created.',
    });
  });

  it('calls onSuccess callback with created project', async () => {
    vi.mocked(projectsApi.create).mockResolvedValue(mockProject);
    const onSuccess = vi.fn();

    const { result } = renderHook(
      () => useCreateProject({ workspaceId: 'ws-1', onSuccess }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ name: 'Test Project', identifier: 'TP' });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(onSuccess).toHaveBeenCalledWith(mockProject);
  });

  it('handles API error and shows error toast', async () => {
    const error = new Error('Duplicate identifier');
    vi.mocked(projectsApi.create).mockRejectedValue(error);

    const { result } = renderHook(
      () => useCreateProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ name: 'Test Project', identifier: 'TP' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalledWith('Failed to create project', {
      description: 'Duplicate identifier',
    });
  });

  it('calls onError callback when API fails', async () => {
    const error = new Error('Server error');
    vi.mocked(projectsApi.create).mockRejectedValue(error);
    const onError = vi.fn();

    const { result } = renderHook(
      () => useCreateProject({ workspaceId: 'ws-1', onError }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ name: 'Test Project', identifier: 'TP' });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(onError).toHaveBeenCalledWith(error);
  });
});

describe('useUpdateProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates project and shows success toast', async () => {
    const updatedProject = { ...mockProject, name: 'Updated Project' };
    vi.mocked(projectsApi.update).mockResolvedValue(updatedProject);

    const { result } = renderHook(
      () => useUpdateProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ projectId: 'proj-1', data: { name: 'Updated Project' } });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(projectsApi.update).toHaveBeenCalledWith('proj-1', { name: 'Updated Project' });
    expect(toast.success).toHaveBeenCalledWith('Project updated', {
      description: '"Updated Project" has been updated.',
    });
  });

  it('handles update error and shows error toast', async () => {
    const error = new Error('Not found');
    vi.mocked(projectsApi.update).mockRejectedValue(error);

    const { result } = renderHook(
      () => useUpdateProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({ projectId: 'proj-1', data: { name: 'Updated' } });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalledWith('Failed to update project', {
      description: 'Not found',
    });
  });
});

describe('useDeleteProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deletes project and shows success toast', async () => {
    vi.mocked(projectsApi.delete).mockResolvedValue(undefined);

    const { result } = renderHook(
      () => useDeleteProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate('proj-1');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(projectsApi.delete).toHaveBeenCalledWith('proj-1');
    expect(toast.success).toHaveBeenCalledWith('Project deleted');
  });

  it('calls onSuccess callback after deletion', async () => {
    vi.mocked(projectsApi.delete).mockResolvedValue(undefined);
    const onSuccess = vi.fn();

    const { result } = renderHook(
      () => useDeleteProject({ workspaceId: 'ws-1', onSuccess }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate('proj-1');
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(onSuccess).toHaveBeenCalled();
  });

  it('handles delete error and shows error toast', async () => {
    const error = new Error('Forbidden');
    vi.mocked(projectsApi.delete).mockRejectedValue(error);

    const { result } = renderHook(
      () => useDeleteProject({ workspaceId: 'ws-1' }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate('proj-1');
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(toast.error).toHaveBeenCalledWith('Failed to delete project', {
      description: 'Forbidden',
    });
  });
});
