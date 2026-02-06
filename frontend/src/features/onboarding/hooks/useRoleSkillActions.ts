'use client';

/**
 * useRoleSkillActions - TanStack Query mutation hooks for role skill operations.
 *
 * T020: Role skill actions for onboarding and settings.
 * Source: FR-001, FR-002, FR-003, FR-004, FR-009, FR-018, US1, US2, US6
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  roleSkillsApi,
  type RoleTemplate,
  type RoleSkill,
  type CreateRoleSkillPayload,
  type UpdateRoleSkillPayload,
  type GenerateSkillPayload,
  type GenerateSkillResponse,
  type RegenerateSkillPayload,
  type RegenerateSkillResponse,
} from '@/services/api/role-skills';
import { onboardingKeys } from './useOnboardingState';

/**
 * Query keys for role skill data.
 */
export const roleSkillKeys = {
  all: ['role-skills'] as const,
  templates: () => [...roleSkillKeys.all, 'templates'] as const,
  skills: (workspaceId: string) => [...roleSkillKeys.all, 'skills', workspaceId] as const,
};

/**
 * Hook for fetching predefined role templates.
 * Templates are stable seed data, so staleTime is high.
 * FR-001: Display predefined SDLC role options.
 */
export function useRoleTemplates() {
  return useQuery({
    queryKey: roleSkillKeys.templates(),
    queryFn: async () => {
      const response = await roleSkillsApi.getTemplates();
      return response.templates;
    },
    staleTime: 1000 * 60 * 60 * 24, // 24 hours
    gcTime: 1000 * 60 * 60 * 24,
  });
}

/**
 * Hook for fetching user's role skills in a workspace.
 * FR-009: View configured role skills.
 */
export function useRoleSkills(workspaceId: string) {
  return useQuery({
    queryKey: roleSkillKeys.skills(workspaceId),
    queryFn: async () => {
      const response = await roleSkillsApi.getRoleSkills(workspaceId);
      return response.skills;
    },
    enabled: !!workspaceId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export interface UseRoleSkillMutationsOptions {
  workspaceId: string;
}

/**
 * Hook for AI skill generation.
 * FR-003, FR-004, US2: Generate personalized skill via AI.
 */
export function useGenerateSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  return useMutation({
    mutationFn: (payload: GenerateSkillPayload) =>
      roleSkillsApi.generateSkill(workspaceId, payload),
    onError: (error: Error) => {
      toast.error('Skill generation failed', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for saving a role skill (create).
 * FR-002, FR-018: Save generated/default skill to workspace.
 */
export function useCreateRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateRoleSkillPayload) =>
      roleSkillsApi.createRoleSkill(workspaceId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.skills(workspaceId) });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.detail(workspaceId) });
    },
    onError: (error: Error) => {
      toast.error('Failed to save role skill', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for deleting a role skill.
 * FR-009: Remove role from workspace.
 */
export function useDeleteRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (skillId: string) => roleSkillsApi.deleteRoleSkill(workspaceId, skillId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.skills(workspaceId) });
      toast.success('Role removed');
    },
    onError: (error: Error) => {
      toast.error('Failed to remove role', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for updating an existing role skill.
 * FR-009, FR-010: Edit skill content, name, primary status.
 */
export function useUpdateRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ skillId, payload }: { skillId: string; payload: UpdateRoleSkillPayload }) =>
      roleSkillsApi.updateRoleSkill(workspaceId, skillId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.skills(workspaceId) });
      toast.success('Skill updated');
    },
    onError: (error: Error) => {
      toast.error('Failed to update skill', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for regenerating a skill with updated experience description.
 * FR-003, FR-015: Regenerate skill, returns preview with diff.
 */
export function useRegenerateSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  return useMutation({
    mutationFn: ({ skillId, payload }: { skillId: string; payload: RegenerateSkillPayload }) =>
      roleSkillsApi.regenerateSkill(workspaceId, skillId, payload),
    onError: (error: Error) => {
      toast.error('Skill regeneration failed', {
        description: error.message,
      });
    },
  });
}

/**
 * Convenience type re-exports for consumers.
 */
export type { RoleTemplate, RoleSkill, GenerateSkillResponse, RegenerateSkillResponse };
