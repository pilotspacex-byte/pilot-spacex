/**
 * useAIMemory — TanStack Query hooks for AI long-term memory (Phase 69).
 *
 * Endpoints (all under /api/v1/workspaces/{workspaceId}/ai/memory):
 *   POST   /recall                    semantic recall (member)
 *   POST   /{memory_id}/pin           pin a memory (admin)
 *   DELETE /{memory_id}               forget / soft delete (admin)
 *   POST   /gdpr-forget-user          GDPR hard delete by user_id (admin)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface MemoryItem {
  id: string;
  type: string;
  score: number;
  content: string;
  sourceId?: string | null;
  sourceType?: string | null;
}

export interface MemoryRecallRequest {
  query: string;
  k?: number;
  types?: string[];
  minScore?: number;
}

export interface MemoryRecallResponse {
  items: MemoryItem[];
  cacheHit: boolean;
  elapsedMs: number;
}

// ---- Hooks ----

export function useMemoryRecall(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: (body: MemoryRecallRequest) =>
      apiClient.post<MemoryRecallResponse>(
        `/workspaces/${workspaceId}/ai/memory/recall`,
        body
      ),
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Memory recall failed');
    },
  });
}

export function usePinMemory(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: (memoryId: string) =>
      apiClient.post<{ pinned: boolean }>(
        `/workspaces/${workspaceId}/ai/memory/${memoryId}/pin`,
        {}
      ),
    onSuccess: () => toast.success('Memory pinned'),
    onError: (err) => toast.error(err instanceof Error ? err.message : 'Failed to pin memory'),
  });
}

export function useForgetMemory(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: (memoryId: string) =>
      apiClient.delete(`/workspaces/${workspaceId}/ai/memory/${memoryId}`),
    onSuccess: () => toast.success('Memory forgotten'),
    onError: (err) => toast.error(err instanceof Error ? err.message : 'Failed to forget memory'),
  });
}

export function useGdprForgetUser(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: (userId: string) =>
      apiClient.post<{ deleted: number }>(
        `/workspaces/${workspaceId}/ai/memory/gdpr-forget-user`,
        { user_id: userId }
      ),
    onSuccess: (data) =>
      toast.success(`Erased ${data?.deleted ?? 0} memories for user (GDPR)`),
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'GDPR forget failed'),
  });
}

// ---------------------------------------------------------------------------
// Phase 71 — Memory Browse Types & Hooks
// ---------------------------------------------------------------------------

export interface MemoryListItem {
  id: string;
  nodeType: string;
  kind: string | null;
  label: string;
  contentSnippet: string;
  pinned: boolean;
  score: number | null;
  sourceType: string | null;
  sourceId: string | null;
  createdAt: string;
}

export interface MemoryListParams {
  offset?: number;
  limit?: number;
  type?: string[];
  kind?: string;
  pinned?: boolean;
  q?: string;
}

export interface MemoryListResponse {
  items: MemoryListItem[];
  total: number;
  offset: number;
  limit: number;
  hasNext: boolean;
}

export interface MemoryStatsResponse {
  total: number;
  byType: Record<string, number>;
  pinnedCount: number;
  lastIngestion: string | null;
}

export interface MemoryDetailResponse {
  id: string;
  nodeType: string;
  kind: string | null;
  label: string;
  content: string;
  properties: Record<string, unknown>;
  pinned: boolean;
  sourceType: string | null;
  sourceId: string | null;
  sourceLabel: string | null;
  sourceUrl: string | null;
  embeddingDim: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface BulkMemoryResponse {
  succeeded: string[];
  failed: Array<{ id: string; error: string }>;
  totalProcessed: number;
}

export function useMemoryList(
  workspaceId: string | undefined,
  params: MemoryListParams,
) {
  return useQuery({
    queryKey: ['memory-list', workspaceId, params],
    queryFn: () =>
      apiClient.get<MemoryListResponse>(
        `/workspaces/${workspaceId}/ai/memory`,
        { params },
      ),
    enabled: !!workspaceId,
    placeholderData: (prev) => prev,
  });
}

export function useMemoryStats(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['memory-stats', workspaceId],
    queryFn: () =>
      apiClient.get<MemoryStatsResponse>(
        `/workspaces/${workspaceId}/ai/memory/stats`,
      ),
    enabled: !!workspaceId,
  });
}

export function useMemoryDetail(
  workspaceId: string | undefined,
  nodeId: string | null,
) {
  return useQuery({
    queryKey: ['memory-detail', workspaceId, nodeId],
    queryFn: () =>
      apiClient.get<MemoryDetailResponse>(
        `/workspaces/${workspaceId}/ai/memory/${nodeId}`,
      ),
    enabled: !!workspaceId && !!nodeId,
  });
}

export function useBulkMemoryAction(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { action: 'pin' | 'forget'; memoryIds: string[] }) =>
      apiClient.post<BulkMemoryResponse>(
        `/workspaces/${workspaceId}/ai/memory/bulk`,
        body,
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memory-list'] });
      queryClient.invalidateQueries({ queryKey: ['memory-stats'] });
      queryClient.invalidateQueries({ queryKey: ['memory-detail'] });
      const verb = variables.action === 'pin' ? 'pinned' : 'forgotten';
      toast.success(`Successfully ${verb} ${variables.memoryIds.length} memories`);
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Bulk action failed'),
  });
}
