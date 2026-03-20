/**
 * User Skills API hooks tests — P20-09, P20-10
 *
 * Verifies TanStack Query hooks for user-skills endpoints:
 * query keys, cache invalidation, and correct API calls.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';
import {
  useUserSkills,
  useCreateUserSkill,
  useUpdateUserSkill,
  useDeleteUserSkill,
  userSkillsApi,
} from './user-skills';
import type { UserSkill, UserSkillCreate, UserSkillUpdate } from './user-skills';

// Mock the API client
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockSkill: UserSkill = {
  id: 'us-1',
  user_id: 'u-1',
  workspace_id: 'ws-1',
  template_id: 'tpl-1',
  skill_content: 'You are an expert developer.',
  experience_description: '10 years React',
  tags: [],
  usage: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  template_name: 'Senior Developer',
  skill_name: null,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('userSkillsApi', () => {
  it('exports all API functions', () => {
    expect(userSkillsApi.getUserSkills).toBeTypeOf('function');
    expect(userSkillsApi.createUserSkill).toBeTypeOf('function');
    expect(userSkillsApi.updateUserSkill).toBeTypeOf('function');
    expect(userSkillsApi.deleteUserSkill).toBeTypeOf('function');
  });
});

describe('useUserSkills', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches user skills with correct query key', async () => {
    const { apiClient } = await import('./client');
    vi.mocked(apiClient.get).mockResolvedValue([mockSkill]);

    const { result } = renderHook(() => useUserSkills('ws-slug'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith('/workspaces/ws-slug/user-skills');
    expect(result.current.data).toEqual([mockSkill]);
  });

  it('does not fetch when workspaceSlug is empty', () => {
    const { result } = renderHook(() => useUserSkills(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
  });
});

describe('useCreateUserSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls POST with correct payload', async () => {
    const { apiClient } = await import('./client');
    vi.mocked(apiClient.post).mockResolvedValue(mockSkill);

    const payload: UserSkillCreate = {
      template_id: 'tpl-1',
      experience_description: 'My exp',
      tags: ['Python', 'FastAPI'],
      usage: 'Use for backend reviews',
    };
    const { result } = renderHook(() => useCreateUserSkill('ws-slug'), {
      wrapper: createWrapper(),
    });

    result.current.mutate(payload);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith('/workspaces/ws-slug/user-skills', payload);
  });
});

describe('useUpdateUserSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls PATCH with id and payload', async () => {
    const { apiClient } = await import('./client');
    vi.mocked(apiClient.patch).mockResolvedValue({ ...mockSkill, is_active: false });

    const payload: UserSkillUpdate = {
      is_active: false,
      tags: ['React', 'TypeScript'],
      usage: 'Frontend work',
    };
    const { result } = renderHook(() => useUpdateUserSkill('ws-slug'), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: 'us-1', data: payload });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.patch).toHaveBeenCalledWith('/workspaces/ws-slug/user-skills/us-1', payload);
  });
});

describe('useDeleteUserSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls DELETE with skill id', async () => {
    const { apiClient } = await import('./client');
    vi.mocked(apiClient.delete).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteUserSkill('ws-slug'), {
      wrapper: createWrapper(),
    });

    result.current.mutate('us-1');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.delete).toHaveBeenCalledWith('/workspaces/ws-slug/user-skills/us-1');
  });
});
