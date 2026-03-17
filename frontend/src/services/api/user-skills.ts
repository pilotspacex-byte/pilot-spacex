/**
 * User Skills API client.
 * Owner-only CRUD for personalized user skills.
 * Source: Phase 20, P20-09, P20-10
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserSkill {
  id: string;
  user_id: string;
  workspace_id: string;
  template_id: string | null;
  skill_content: string;
  experience_description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  template_name: string | null;
  skill_name: string | null;
}

export interface UserSkillCreate {
  template_id?: string;
  skill_content?: string;
  experience_description?: string;
  skill_name?: string;
}

export interface UserSkillUpdate {
  is_active?: boolean;
  experience_description?: string;
  skill_content?: string;
  skill_name?: string;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export const userSkillsApi = {
  getUserSkills(workspaceSlug: string): Promise<UserSkill[]> {
    return apiClient.get<UserSkill[]>(`/workspaces/${workspaceSlug}/user-skills`);
  },

  createUserSkill(workspaceSlug: string, data: UserSkillCreate): Promise<UserSkill> {
    return apiClient.post<UserSkill>(`/workspaces/${workspaceSlug}/user-skills`, data);
  },

  updateUserSkill(workspaceSlug: string, id: string, data: UserSkillUpdate): Promise<UserSkill> {
    return apiClient.patch<UserSkill>(`/workspaces/${workspaceSlug}/user-skills/${id}`, data);
  },

  deleteUserSkill(workspaceSlug: string, id: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceSlug}/user-skills/${id}`);
  },
};

// ---------------------------------------------------------------------------
// TanStack Query Hooks
// ---------------------------------------------------------------------------

export function useUserSkills(workspaceSlug: string) {
  return useQuery({
    queryKey: ['user-skills', workspaceSlug],
    queryFn: () => userSkillsApi.getUserSkills(workspaceSlug),
    staleTime: 60_000,
    enabled: !!workspaceSlug,
  });
}

export function useCreateUserSkill(workspaceSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UserSkillCreate) => userSkillsApi.createUserSkill(workspaceSlug, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-skills', workspaceSlug] }),
  });
}

export function useUpdateUserSkill(workspaceSlug: string) {
  const qc = useQueryClient();
  const queryKey = ['user-skills', workspaceSlug];
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserSkillUpdate }) =>
      userSkillsApi.updateUserSkill(workspaceSlug, id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<UserSkill[]>(queryKey);
      qc.setQueryData<UserSkill[]>(queryKey, (old) =>
        old?.map((s) => (s.id === id ? { ...s, ...data } : s))
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(queryKey, context.previous);
    },
    onSettled: () => qc.invalidateQueries({ queryKey }),
  });
}

export function useDeleteUserSkill(workspaceSlug: string) {
  const qc = useQueryClient();
  const queryKey = ['user-skills', workspaceSlug];
  return useMutation({
    mutationFn: (id: string) => userSkillsApi.deleteUserSkill(workspaceSlug, id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey });
      const previous = qc.getQueryData<UserSkill[]>(queryKey);
      qc.setQueryData<UserSkill[]>(queryKey, (old) => old?.filter((s) => s.id !== id));
      return { previous };
    },
    onError: (_err, _id, context) => {
      if (context?.previous) qc.setQueryData(queryKey, context.previous);
    },
    onSettled: () => qc.invalidateQueries({ queryKey }),
  });
}
