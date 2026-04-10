/**
 * useAITelemetry — TanStack Query hooks for AI memory telemetry (Phase 70).
 *
 * Endpoints (all under /api/v1/workspaces/{workspaceId}/ai/memory/telemetry):
 *   GET  ""                       — memory stats + producer counters + toggles (admin)
 *   PUT  "/toggles/{producer}"    — set a single producer toggle (admin)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface MemoryTelemetryData {
  memory: {
    hit_rate: number;
    recall_p95_ms: number;
    total_recalls: number;
  };
  producers: {
    enqueued: Record<string, number>;
    dropped: Record<string, number>;
  };
  toggles: {
    agent_turn: boolean;
    user_correction: boolean;
    pr_review_finding: boolean;
    summarizer: boolean;
  };
}

export interface SetProducerToggleInput {
  producer: string;
  enabled: boolean;
}

// ---- Query keys ----

export const aiTelemetryKeys = {
  all: (workspaceId: string) => ['ai-memory-telemetry', workspaceId] as const,
};

// ---- Hooks ----

export function useAITelemetry(workspaceId: string | undefined) {
  return useQuery<MemoryTelemetryData>({
    queryKey: aiTelemetryKeys.all(workspaceId ?? ''),
    queryFn: () =>
      apiClient.get<MemoryTelemetryData>(
        `/workspaces/${workspaceId}/ai/memory/telemetry`
      ),
    enabled: Boolean(workspaceId),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}

export function useSetProducerToggle(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ producer, enabled }: SetProducerToggleInput) =>
      apiClient.put<Record<string, boolean>>(
        `/workspaces/${workspaceId}/ai/memory/telemetry/toggles/${producer}`,
        { enabled }
      ),
    onMutate: async ({ producer, enabled }) => {
      await queryClient.cancelQueries({ queryKey: aiTelemetryKeys.all(workspaceId ?? '') });
      const previous = queryClient.getQueryData<MemoryTelemetryData>(
        aiTelemetryKeys.all(workspaceId ?? '')
      );
      if (previous) {
        queryClient.setQueryData<MemoryTelemetryData>(
          aiTelemetryKeys.all(workspaceId ?? ''),
          {
            ...previous,
            toggles: { ...previous.toggles, [producer]: enabled },
          }
        );
      }
      return { previous };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(aiTelemetryKeys.all(workspaceId ?? ''), ctx.previous);
      }
      const msg = err instanceof Error ? err.message : 'Failed to update toggle';
      toast.error(msg);
    },
    onSuccess: () => {
      toast.success('Producer toggle updated');
      void queryClient.invalidateQueries({ queryKey: aiTelemetryKeys.all(workspaceId ?? '') });
    },
  });
}
