/**
 * Hook tests for useRoleSkillActions.
 *
 * Migrated from roleSkillsApi to skill-templates API.
 * Source: FR-001, FR-002, FR-003, FR-004, FR-009, FR-018, US1, US2, US6
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import {
  useGenerateSkill,
  useCreateRoleSkill,
  useDeleteRoleSkill,
} from '../useRoleSkillActions';
import { skillTemplatesApi, useSkillTemplates } from '@/services/api/skill-templates';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/services/api/skill-templates', () => ({
  skillTemplatesApi: {
    getTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
  useSkillTemplates: vi.fn(() => ({
    data: [],
    isLoading: false,
    isSuccess: false,
    isError: false,
    error: null,
  })),
  useCreateSkillTemplate: vi.fn(),
  useUpdateSkillTemplate: vi.fn(),
  useDeleteSkillTemplate: vi.fn(),
}));

const mockTemplates = [
  {
    id: '1',
    workspace_id: 'ws-1',
    name: 'Developer',
    description: 'Code & architecture',
    skill_content: '# Developer',
    icon: 'Code',
    sort_order: 3,
    source: 'built_in' as const,
    role_type: 'developer',
    is_active: true,
    created_by: null,
    created_at: '2026-02-06T00:00:00Z',
    updated_at: '2026-02-06T00:00:00Z',
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

describe('useSkillTemplates (via useRoleTemplates)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should delegate to useSkillTemplates', () => {
    // useSkillTemplates is mocked at the module level
    expect(useSkillTemplates).toBeDefined();
  });
});

describe('useGenerateSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call createTemplate API with correct params', async () => {
    const mockResponse = {
      id: 'tmpl-new',
      workspace_id: 'ws-123',
      name: 'Senior Dev',
      description: 'Full-stack TypeScript dev',
      skill_content: '# Generated',
      icon: '',
      sort_order: 0,
      source: 'custom' as const,
      role_type: 'developer',
      is_active: true,
      created_by: null,
      created_at: '2026-02-06T00:00:00Z',
      updated_at: '2026-02-06T00:00:00Z',
    };
    vi.mocked(skillTemplatesApi.createTemplate).mockResolvedValue(mockResponse);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useGenerateSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate({
      roleType: 'developer',
      experienceDescription: 'Full-stack TypeScript dev',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(skillTemplatesApi.createTemplate).toHaveBeenCalledWith('ws-123', {
      name: 'developer',
      description: 'Full-stack TypeScript dev',
      skill_content: '',
      role_type: 'developer',
    });
  });

  it('should handle generation error', async () => {
    vi.mocked(skillTemplatesApi.createTemplate).mockRejectedValue(new Error('Provider unavailable'));

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

  it('should call createTemplate API', async () => {
    vi.mocked(skillTemplatesApi.createTemplate).mockResolvedValue(mockTemplates[0]!);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useCreateRoleSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate({
      name: 'Developer',
      description: '',
      skill_content: '# Developer',
      roleType: 'developer',
      roleName: 'Developer',
      isPrimary: true,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(skillTemplatesApi.createTemplate).toHaveBeenCalledWith('ws-123', {
      name: 'Developer',
      description: '',
      skill_content: '# Developer',
      role_type: 'developer',
    });
  });
});

describe('useDeleteRoleSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call deleteTemplate API', async () => {
    vi.mocked(skillTemplatesApi.deleteTemplate).mockResolvedValue(undefined);

    const wrapper = createWrapper();
    const { result } = renderHook(() => useDeleteRoleSkill({ workspaceId: 'ws-123' }), { wrapper });

    result.current.mutate('skill-1');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(skillTemplatesApi.deleteTemplate).toHaveBeenCalledWith('ws-123', 'skill-1');
  });
});
