'use client';

/**
 * useArtifactSignedUrl — On-demand signed URL fetcher for artifact preview/download.
 *
 * CRITICAL timing constraints (Supabase Storage signed URLs expire at 60 minutes):
 * - staleTime: 55 minutes — re-fetch before URL expiry
 * - gcTime: 1 hour — retain in cache while modal may still be open
 *
 * Enabled only when:
 * - artifactId is non-null and non-empty (user has selected a file)
 * - workspaceId is non-empty
 *
 * NOT auto-fetched on mount — only fires when user explicitly selects an artifact.
 */

import { useQuery } from '@tanstack/react-query';
import { artifactsApi } from '@/services/api/artifacts';
import type { ArtifactSignedUrlResponse } from '@/types/artifact';
import { artifactsKeys } from './use-project-artifacts';

export function useArtifactSignedUrl(
  workspaceId: string,
  projectId: string,
  artifactId: string | null
): ReturnType<typeof useQuery<ArtifactSignedUrlResponse>> {
  return useQuery({
    queryKey: artifactsKeys.signedUrl(artifactId ?? ''),
    queryFn: () => artifactsApi.getSignedUrl(workspaceId, projectId, artifactId!),
    enabled: !!artifactId && !!workspaceId && !!projectId,
    staleTime: 55 * 60 * 1000, // 55 minutes — below 1hr Supabase signed URL expiry
    gcTime: 60 * 60 * 1000, // 1 hour — retain while preview modal may be open
  });
}
