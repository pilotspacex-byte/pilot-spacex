/**
 * useBatchRunStream - SSE EventSource hook for real-time batch run updates.
 *
 * Connects to /api/v1/batch-runs/{id}/stream and invalidates TanStack Query
 * caches on batch_status_update events.
 *
 * Phase 76: Sprint Batch Implementation
 */

import { useEffect, useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { batchRunKeys } from './use-batch-run';

interface BatchStatusUpdatePayload {
  batch_run_issue_id: string;
  issue_id?: string;
  status: string;
  stage?: string;
  pr_url?: string;
  error?: string;
  ts: string;
}

export interface UseBatchRunStreamResult {
  connectionError: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

/**
 * Opens an SSE connection to the batch run stream endpoint.
 * Automatically invalidates TanStack Query caches on status updates.
 * Cleans up EventSource on unmount or batchRunId change.
 */
export function useBatchRunStream(batchRunId: string | null): UseBatchRunStreamResult {
  const queryClient = useQueryClient();
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!batchRunId) return;

    // Clear any previous error when reconnecting
    setConnectionError(null);

    const url = `${API_BASE}/batch-runs/${batchRunId}/stream`;
    const eventSource = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('batch_status_update', (event: MessageEvent) => {
      try {
        const payload: BatchStatusUpdatePayload = JSON.parse(event.data as string);

        // Always invalidate the batch run detail query
        queryClient.invalidateQueries({ queryKey: batchRunKeys.detail(batchRunId) });

        // If a PR was created, also invalidate the issue query
        if (payload.pr_url && payload.issue_id) {
          queryClient.invalidateQueries({ queryKey: ['issue', payload.issue_id] });
        }

        // Invalidate issues sub-list
        queryClient.invalidateQueries({ queryKey: batchRunKeys.issues(batchRunId) });
      } catch {
        // Malformed JSON — ignore
      }
    });

    eventSource.onerror = () => {
      setConnectionError('Live updates paused. Refresh to reconnect.');
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [batchRunId, queryClient]);

  return { connectionError };
}
