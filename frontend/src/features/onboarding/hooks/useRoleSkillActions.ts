'use client';

/**
 * useRoleSkillActions - TanStack Query hooks for skill operations.
 *
 * Migrated from legacy roleSkillsApi to unified skill-templates API.
 * Source: FR-001, FR-002, FR-003, FR-004, FR-009, FR-018, US1, US2, US6
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  skillTemplatesApi,
  useSkillTemplates,
  type SkillTemplate,
  type SkillTemplateCreate,
} from '@/services/api/skill-templates';
import { onboardingKeys } from './useOnboardingState';

/**
 * Query keys for skill data.
 */
export const roleSkillKeys = {
  all: ['skill-templates'] as const,
  templates: (workspaceSlug: string) => [...roleSkillKeys.all, workspaceSlug] as const,
};

/**
 * Hook for fetching skill templates (replaces useRoleTemplates).
 * Re-exports useSkillTemplates for backward compat.
 */
export function useRoleTemplates(workspaceSlug?: string) {
  return useSkillTemplates(workspaceSlug ?? '');
}

/**
 * Hook for fetching user's skills in a workspace.
 * Delegates to skill-templates API.
 */
export function useRoleSkills(workspaceSlug: string) {
  return useSkillTemplates(workspaceSlug);
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
    mutationFn: (payload: { roleType: string; experienceDescription: string; roleName?: string }) =>
      skillTemplatesApi.createTemplate(workspaceId, {
        name: payload.roleName ?? payload.roleType,
        description: payload.experienceDescription,
        skill_content: '',
        role_type: payload.roleType,
      }),
    onSuccess: (result) => {
      // Map response to legacy shape for consumers
      return {
        skillContent: result.skill_content,
        suggestedRoleName: result.name,
        suggestedTags: [] as string[],
        suggestedUsage: result.description,
        wordCount: result.skill_content.split(/\s+/).length,
        generationModel: 'skill-templates',
        generationTimeMs: 0,
      };
    },
    onError: (error: Error) => {
      toast.error('Skill generation failed', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for saving a skill template (create).
 * FR-002, FR-018: Save generated/default skill to workspace.
 */
export function useCreateRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SkillTemplateCreate & { roleType?: string; roleName?: string; isPrimary?: boolean }) =>
      skillTemplatesApi.createTemplate(workspaceId, {
        name: payload.roleName ?? payload.name,
        description: payload.description,
        skill_content: payload.skill_content,
        role_type: payload.roleType ?? payload.role_type,
      }),
    onSuccess: () => {
      toast.success('Skill saved and active');
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.all });
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
 * Hook for deleting a skill template.
 * FR-009: Remove skill from workspace.
 */
export function useDeleteRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (skillId: string) => skillTemplatesApi.deleteTemplate(workspaceId, skillId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.all });
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
 * Hook for updating an existing skill template.
 * FR-009, FR-010: Edit skill content, name.
 */
export function useUpdateRoleSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ skillId, payload }: { skillId: string; payload: { name?: string; skill_content?: string; is_active?: boolean } }) =>
      skillTemplatesApi.updateTemplate(workspaceId, skillId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleSkillKeys.all });
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
 * FR-003, FR-015: Regenerate skill.
 */
export function useRegenerateSkill({ workspaceId }: UseRoleSkillMutationsOptions) {
  return useMutation({
    mutationFn: ({ skillId, payload }: { skillId: string; payload: { experienceDescription: string } }) =>
      skillTemplatesApi.updateTemplate(workspaceId, skillId, {
        description: payload.experienceDescription,
      }),
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
export type { SkillTemplate };
