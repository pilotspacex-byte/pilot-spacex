/**
 * useWorkspaceHooks -- TanStack Query hooks for workspace hook rules CRUD (Phase 83).
 *
 * Backend endpoints (mounted under /api/v1/workspaces/{workspaceId}/hooks):
 *   GET    ""              list all hook rules (member)
 *   POST   ""              create hook rule (admin)
 *   PUT    "/{hookId}"     update hook rule (admin)
 *   DELETE "/{hookId}"     delete hook rule (admin)
 *
 * Note: workspaceId here is the UUID, NOT the slug.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import type {
  CreateHookRuleInput,
  HookRule,
  HookRuleListResponse,
  UpdateHookRuleInput,
} from '../types/hook-rules';

// ---- Query keys ----

export const hookRulesKeys = {
  list: (workspaceId: string) => ['hook-rules', workspaceId] as const,
};

// ---- Hooks ----

export function useWorkspaceHooks(workspaceId: string | undefined) {
  return useQuery<HookRuleListResponse>({
    queryKey: hookRulesKeys.list(workspaceId ?? ''),
    queryFn: () =>
      apiClient.get<HookRuleListResponse>(`/workspaces/${workspaceId}/hooks`),
    enabled: Boolean(workspaceId),
    staleTime: 30_000,
  });
}

export function useCreateHookRule(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateHookRuleInput) =>
      apiClient.post<HookRule>(`/workspaces/${workspaceId}/hooks`, input),
    onSuccess: () => {
      toast.success('Hook rule created');
      void queryClient.invalidateQueries({
        queryKey: hookRulesKeys.list(workspaceId ?? ''),
      });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : 'Failed to create hook rule';
      toast.error(msg);
    },
  });
}

export function useUpdateHookRule(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ hookId, ...input }: UpdateHookRuleInput & { hookId: string }) =>
      apiClient.put<HookRule>(
        `/workspaces/${workspaceId}/hooks/${hookId}`,
        input
      ),
    onSuccess: () => {
      toast.success('Hook rule updated');
      void queryClient.invalidateQueries({
        queryKey: hookRulesKeys.list(workspaceId ?? ''),
      });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : 'Failed to update hook rule';
      toast.error(msg);
    },
  });
}

export function useDeleteHookRule(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (hookId: string) =>
      apiClient.delete(`/workspaces/${workspaceId}/hooks/${hookId}`),
    onSuccess: () => {
      toast.success('Hook rule deleted');
      void queryClient.invalidateQueries({
        queryKey: hookRulesKeys.list(workspaceId ?? ''),
      });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : 'Failed to delete hook rule';
      toast.error(msg);
    },
  });
}

export function useToggleHookRule(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ hookId, isEnabled }: { hookId: string; isEnabled: boolean }) =>
      apiClient.put<HookRule>(
        `/workspaces/${workspaceId}/hooks/${hookId}`,
        { isEnabled }
      ),
    onMutate: async ({ hookId, isEnabled }) => {
      const key = hookRulesKeys.list(workspaceId ?? '');
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<HookRuleListResponse>(key);
      queryClient.setQueryData<HookRuleListResponse>(key, (old) => {
        if (!old) return old;
        return {
          ...old,
          rules: old.rules.map((r) =>
            r.id === hookId ? { ...r, isEnabled } : r
          ),
        };
      });
      return { previous };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(
          hookRulesKeys.list(workspaceId ?? ''),
          ctx.previous
        );
      }
      const msg = err instanceof Error ? err.message : 'Failed to toggle hook rule';
      toast.error(msg);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: hookRulesKeys.list(workspaceId ?? ''),
      });
    },
  });
}
