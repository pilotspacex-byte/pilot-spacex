'use client';

/**
 * useDocumentIngest — TanStack mutation hook for POST /ai/attachments/{id}/ingest.
 *
 * Sends adjusted chunk configuration to the backend to trigger Knowledge Graph
 * ingestion. Shows toast feedback on success or error.
 *
 * Feature 044: Artifact UI Enhancements (AUI-05)
 */
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { attachmentsApi } from '@/services/api/attachments';
import type { ChunkAdjustment, DocumentIngestRequest } from '@/types/attachments';

export interface UseDocumentIngestOptions {
  artifactId: string;
  workspaceId: string;
  projectId: string;
}

/**
 * Mutation hook to trigger KG ingestion for an attachment.
 *
 * Call `mutate(adjustments)` with the list of ChunkAdjustment objects.
 * Pass an empty array to use the server's default chunking.
 *
 * Returns standard TanStack useMutation result.
 */
export function useDocumentIngest({ artifactId, workspaceId, projectId }: UseDocumentIngestOptions) {
  return useMutation({
    mutationFn: (adjustments: ChunkAdjustment[]) => {
      const request: DocumentIngestRequest = {
        workspaceId,
        projectId,
        chunkAdjustments: adjustments,
      };
      return attachmentsApi.ingestDocument(artifactId, request);
    },
    onSuccess: () => {
      toast.success('Document queued for Knowledge Graph ingestion.');
    },
    onError: () => {
      toast.error('Failed to queue document. Please try again.');
    },
  });
}
