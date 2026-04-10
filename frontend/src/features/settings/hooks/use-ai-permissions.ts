/**
 * useAIPermissions — TanStack Query hooks for granular AI tool permissions (Phase 69 DD-003).
 *
 * Backend endpoints (mounted under /api/v1/workspaces/{workspaceId}/ai/permissions):
 *   GET    ""                        list all tool permissions (member)
 *   PUT    "/{tool_name}"            set tool mode (admin)
 *   POST   "/template/{template}"    apply policy template (admin)
 *   GET    "/audit-log?limit&offset" paginated audit log (admin)
 *
 * Note: workspace_id here is the UUID, NOT the slug.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import type {
  PermissionAuditEntry,
  PolicyTemplate,
  ToolPermission,
  ToolPermissionMode,
} from '../types/ai-permissions';

// ---- Query keys ----

export const aiPermissionsKeys = {
  list: (workspaceId: string) => ['ai-permissions', workspaceId] as const,
  auditLog: (workspaceId: string, limit: number, offset: number) =>
    ['ai-permissions', workspaceId, 'audit-log', limit, offset] as const,
};

// ---- Hooks ----

export function useAIPermissions(workspaceId: string | undefined) {
  return useQuery<ToolPermission[]>({
    queryKey: aiPermissionsKeys.list(workspaceId ?? ''),
    queryFn: () =>
      // FastAPI 307 footgun: collection root MUST be "" not "/"
      apiClient.get<ToolPermission[]>(`/workspaces/${workspaceId}/ai/permissions`),
    enabled: Boolean(workspaceId),
    staleTime: 30_000,
  });
}

export interface SetToolPermissionInput {
  tool_name: string;
  mode: ToolPermissionMode;
}

export function useSetToolPermission(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tool_name, mode }: SetToolPermissionInput) =>
      apiClient.put<ToolPermission>(
        `/workspaces/${workspaceId}/ai/permissions/${encodeURIComponent(tool_name)}`,
        { mode }
      ),
    onMutate: async ({ tool_name, mode }) => {
      await queryClient.cancelQueries({ queryKey: aiPermissionsKeys.list(workspaceId ?? '') });
      const previous = queryClient.getQueryData<ToolPermission[]>(
        aiPermissionsKeys.list(workspaceId ?? '')
      );
      queryClient.setQueryData<ToolPermission[]>(
        aiPermissionsKeys.list(workspaceId ?? ''),
        (old) =>
          old?.map((p) =>
            p.tool_name === tool_name ? { ...p, mode, source: 'db' as const } : p
          ) ?? old
      );
      return { previous };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(aiPermissionsKeys.list(workspaceId ?? ''), ctx.previous);
      }
      const msg = err instanceof Error ? err.message : 'Failed to update permission';
      toast.error(msg);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ai-permissions', workspaceId] });
    },
  });
}

export function useApplyPolicyTemplate(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (template: PolicyTemplate) =>
      apiClient.post<{ applied: number }>(
        `/workspaces/${workspaceId}/ai/permissions/template/${template}`,
        {}
      ),
    onSuccess: (_data, template) => {
      toast.success(`Applied "${template}" policy template`);
      void queryClient.invalidateQueries({ queryKey: ['ai-permissions', workspaceId] });
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : 'Failed to apply template';
      toast.error(msg);
    },
  });
}

export interface AuditLogPagination {
  limit?: number;
  offset?: number;
}

export function useAIPermissionsAuditLog(
  workspaceId: string | undefined,
  { limit = 50, offset = 0 }: AuditLogPagination = {}
) {
  return useQuery<PermissionAuditEntry[]>({
    queryKey: aiPermissionsKeys.auditLog(workspaceId ?? '', limit, offset),
    queryFn: () =>
      apiClient.get<PermissionAuditEntry[]>(
        `/workspaces/${workspaceId}/ai/permissions/audit-log?limit=${limit}&offset=${offset}`
      ),
    enabled: Boolean(workspaceId),
    staleTime: 15_000,
  });
}
