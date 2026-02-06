/**
 * Hook tests for useRoleSkillActions.
 *
 * T023: Tests for TanStack Query hooks for role skill operations.
 * Source: FR-001, FR-002, FR-003, FR-004, FR-009, FR-018, US1, US2, US6
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import {
  useRoleTemplates,
  useRoleSkills,
  useGenerateSkill,
  useCreateRoleSkill,
  useDeleteRoleSkill,
} from '../useRoleSkillActions';
import { roleSkillsApi } from '@/services/api/role-skills';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/services/api/role-skills', () => ({
  roleSkillsApi: {
    getTemplates: vi.fn(),
    getRoleSkills: vi.fn(),
    generateSkill: vi.fn(),
    createRoleSkill: vi.fn(),
    deleteRoleSkill: vi.fn(),
  },
}));

const mockTemplates = [
  {
    id: '1',
    roleType: 'developer' as const,
    displayName: 'Developer',
    description: 'Code & architecture',
    icon: 'Code',
    sortOrder: 3,
    version: 1,
    defaultSkillContent: '# Developer',
  },
];

const mockSkills = [
  {
    id: 'skill-1',
    roleType: 'developer' as const,
    roleName: 'Developer',
    skillContent: '# Developer',
    experienceDescription: null,
    isPrimary: true,
    templateVersion: 1,
    templateUpdateAvailable: false,
    wordCount: 5,
    createdAt: '2026-02-06T00:00:00Z',
    updatedAt: '2026-02-06T00:00:00Z',
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useRoleTemplates', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch and return templates', async () => {
    vi.mocked(roleSkillsApi.getTemplates).mockResolvedValue({ templates: mockTemplates });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useRoleTemplates(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockTemplates);
    expect(roleSkillsApi.getTemplates).toHaveBeenCalledOnce();
  });

  it('should handle fetch error', async () => {
    vi.mocked(roleSkillsApi.getTemplates).mockRejectedValue(new Error('Network error'));

    const wrapper = createWrapper();
    const { result } = renderHook(() => useRoleTemplates(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

describe('useRoleSkills', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch skills for a workspace', async () => {
    vi.mocked(roleSkillsApi.getRoleSkills).mockResolvedValue({ skills: mockSkills });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useRoleSkills('ws-123'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockSkills);
    expect(roleSkillsApi.getRoleSkills).toHaveBeenCalledWith('ws-123');
  });

  it('should not fetch when workspaceId is empty', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useRoleSkills(''), { wrapper });

    expect(result.current.isFetching).toBe(false);
  });
});

describe('useGenerateSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call generateSkill API with correct params', async () => {
    const mockResponse = {
      skillContent: '# Generated',
      suggestedRoleName: 'Senior Dev',
      wordCount: 50,
      generationModel: 'claude-sonnet',
      generationTimeMs: 2000,
    };
    vi.mocked(roleSkillsApi.generateSkill).mockResolvedValue(mockResponse);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useGenerateSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate({
      roleType: 'developer',
      experienceDescription: 'Full-stack TypeScript dev',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(roleSkillsApi.generateSkill).toHaveBeenCalledWith('ws-123', {
      roleType: 'developer',
      experienceDescription: 'Full-stack TypeScript dev',
    });
    expect(result.current.data).toEqual(mockResponse);
  });

  it('should handle generation error', async () => {
    vi.mocked(roleSkillsApi.generateSkill).mockRejectedValue(new Error('Provider unavailable'));

    const wrapper = createWrapper();
    const { result } = renderHook(() => useGenerateSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate({
      roleType: 'developer',
      experienceDescription: 'Full-stack TypeScript dev',
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useCreateRoleSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call createRoleSkill API', async () => {
    vi.mocked(roleSkillsApi.createRoleSkill).mockResolvedValue(mockSkills[0]!);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useCreateRoleSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate({
      roleType: 'developer',
      roleName: 'Developer',
      skillContent: '# Developer',
      isPrimary: true,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(roleSkillsApi.createRoleSkill).toHaveBeenCalledWith('ws-123', {
      roleType: 'developer',
      roleName: 'Developer',
      skillContent: '# Developer',
      isPrimary: true,
    });
  });
});

describe('useDeleteRoleSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call deleteRoleSkill API', async () => {
    vi.mocked(roleSkillsApi.deleteRoleSkill).mockResolvedValue(undefined);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDeleteRoleSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate('skill-1');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(roleSkillsApi.deleteRoleSkill).toHaveBeenCalledWith('ws-123', 'skill-1');
  });
});
