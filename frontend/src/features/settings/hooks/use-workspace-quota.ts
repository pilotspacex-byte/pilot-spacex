/**
 * useWorkspaceQuota - TanStack Query hooks for workspace quota management.
 *
 * TENANT-03: Storage and rate limit quota display and owner-editable configuration.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface QuotaStatus {
  rate_limit_standard_rpm: number | null;
  rate_limit_ai_rpm: number | null;
  storage_quota_mb: number | null;
  storage_used_bytes: number;
  storage_used_mb: number;
}

export interface UpdateQuotaBody {
  rate_limit_standard_rpm?: number | null;
  rate_limit_ai_rpm?: number | null;
  storage_quota_mb?: number | null;
}

// ---- Query Keys ----

export const quotaKeys = {
  quota: (workspaceSlug: string) => ['workspace', workspaceSlug, 'quota'] as const,
};

// ---- Hooks ----

export function useWorkspaceQuota(workspaceSlug: string) {
  return useQuery<QuotaStatus>({
    queryKey: quotaKeys.quota(workspaceSlug),
    queryFn: () => apiClient.get<QuotaStatus>(`/workspaces/${workspaceSlug}/settings/quota`),
    enabled: !!workspaceSlug,
    staleTime: 30_000,
  });
}

export function useUpdateWorkspaceQuota(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateQuotaBody) =>
      apiClient.patch<QuotaStatus>(`/workspaces/${workspaceSlug}/settings/quota`, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: quotaKeys.quota(workspaceSlug) });
    },
  });
}
