'use client';

/**
 * useExtractionResult - TanStack Query hook for artifact extraction data.
 *
 * Fetches extraction metadata, full text, chunks, and tables for an
 * attachment. Polls every 5 seconds while extraction is still in progress
 * (extractionSource === "none"), then stops once extraction completes.
 *
 * Feature 044: Artifact UI Enhancements (AUI-01, AUI-02, AUI-03, AUI-04)
 */
import { useQuery } from '@tanstack/react-query';
import { attachmentsApi } from '@/services/api/attachments';
import type { AttachmentExtractionResult } from '@/types/attachments';

export const extractionKeys = {
  all: ['artifacts', 'extraction'] as const,
  result: (artifactId: string) => [...extractionKeys.all, artifactId] as const,
};

export interface UseExtractionResultOptions {
  /** Server-assigned attachment UUID */
  artifactId: string;
  /** Whether the containing modal is open - gates the query */
  open: boolean;
}

/**
 * Fetch extraction result for an attachment.
 *
 * Polls every 5 seconds when extraction_source is "none" (extraction still
 * running). Stops polling when a real source ("office" | "ocr" | "raw") is
 * returned.
 *
 * Returns standard TanStack Query result object.
 */
export function useExtractionResult({ artifactId, open }: UseExtractionResultOptions) {
  return useQuery<AttachmentExtractionResult>({
    queryKey: extractionKeys.result(artifactId),
    queryFn: () => attachmentsApi.getExtraction(artifactId),
    enabled: open && !!artifactId,
    staleTime: 1000 * 60 * 5, // 5 minutes - extraction results are stable once complete
    retry: false,
    // Poll while extraction is still running
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      return data.metadata.extractionSource === 'none' ? 5000 : false;
    },
  });
}
