/**
 * useAuditLog - TanStack Query hooks for workspace audit log.
 *
 * AUDIT-03: Filtered, paginated audit log retrieval.
 * AUDIT-04: Export audit log as JSON or CSV.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface AuditLogEntry {
  id: string;
  actorId: string | null;
  actorType: 'USER' | 'SYSTEM' | 'AI';
  action: string;
  resourceType: string;
  resourceId: string | null;
  payload: {
    before: Record<string, unknown>;
    after: Record<string, unknown>;
  } | null;
  aiModel: string | null;
  aiTokenCost: number | null;
  aiRationale: string | null;
  approvalRequestId: string | null;
  ipAddress: string | null;
  createdAt: string;
}

export interface AuditFilters {
  actor_id?: string;
  actor_type?: 'AI' | 'USER' | 'SYSTEM';
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

export interface PaginatedAuditResponse {
  items: AuditLogEntry[];
  hasNext: boolean;
  nextCursor: string | null;
  pageSize: number;
}

// ---- Query Keys ----

export const auditLogKeys = {
  list: (workspaceSlug: string, filters: AuditFilters, cursor?: string | null) =>
    ['audit-log', workspaceSlug, filters, cursor] as const,
};

// ---- Helpers ----

function buildAuditParams(
  filters: AuditFilters,
  cursor?: string | null,
  pageSize = 50
): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.actor_id) params.set('actor_id', filters.actor_id);
  if (filters.actor_type) params.set('actor_type', filters.actor_type);
  if (filters.action) params.set('action', filters.action);
  if (filters.resource_type) params.set('resource_type', filters.resource_type);
  if (filters.start_date) params.set('start_date', filters.start_date);
  if (filters.end_date) params.set('end_date', filters.end_date);
  if (cursor) params.set('cursor', cursor);
  params.set('page_size', String(pageSize));
  return params;
}

// ---- Hooks ----

export function useAuditLog(
  workspaceSlug: string,
  filters: AuditFilters = {},
  cursor?: string | null
) {
  const params = buildAuditParams(filters, cursor);

  return useQuery<PaginatedAuditResponse>({
    queryKey: auditLogKeys.list(workspaceSlug, filters, cursor),
    queryFn: () =>
      apiClient.get<PaginatedAuditResponse>(
        `/workspaces/${workspaceSlug}/audit?${params.toString()}`
      ),
    enabled: !!workspaceSlug,
    staleTime: 30_000,
  });
}

export function useRollbackAIArtifact(workspaceSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (entryId: string) => {
      await apiClient.post(`/workspaces/${workspaceSlug}/audit/${entryId}/rollback`);
    },
    onSuccess: () => {
      // Invalidate audit log so the new ai.rollback entry appears
      void queryClient.invalidateQueries({
        queryKey: ['audit-log', workspaceSlug],
      });
    },
  });
}

export function useExportAuditLog(workspaceSlug: string) {
  let isExporting = false;

  const triggerExport = async (
    format: 'json' | 'csv',
    filters: AuditFilters = {}
  ): Promise<void> => {
    if (isExporting) return;
    isExporting = true;

    try {
      const params = new URLSearchParams({ format });
      if (filters.actor_id) params.set('actor_id', filters.actor_id);
      if (filters.actor_type) params.set('actor_type', filters.actor_type);
      if (filters.action) params.set('action', filters.action);
      if (filters.resource_type) params.set('resource_type', filters.resource_type);
      if (filters.start_date) params.set('start_date', filters.start_date);
      if (filters.end_date) params.set('end_date', filters.end_date);

      const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? '').replace(/\/$/, '');
      const url = `${apiBase}/api/v1/workspaces/${workspaceSlug}/audit/export?${params.toString()}`;

      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = `audit-log-${workspaceSlug}-${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(objectUrl);
    } finally {
      isExporting = false;
    }
  };

  return { triggerExport, isExporting };
}
