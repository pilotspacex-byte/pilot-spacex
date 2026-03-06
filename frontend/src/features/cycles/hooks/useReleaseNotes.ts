'use client';

/**
 * useReleaseNotes - TanStack Query hook for fetching cycle release notes.
 *
 * T-026/T-027: Release notes tab in cycle detail.
 */
import { useQuery } from '@tanstack/react-query';
import { pmBlocksApi, type ReleaseNotesData } from '@/services/api';
import { cyclesKeys } from './useCycles';

export interface UseReleaseNotesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID (required) */
  cycleId: string;
  /** Enable query */
  enabled?: boolean;
}

export function useReleaseNotes({ workspaceId, cycleId, enabled = true }: UseReleaseNotesOptions) {
  return useQuery<ReleaseNotesData>({
    queryKey: [...cyclesKeys.detail(workspaceId, cycleId), 'release-notes'],
    queryFn: () => pmBlocksApi.getReleaseNotes(workspaceId, cycleId),
    enabled: enabled && !!workspaceId && !!cycleId,
    staleTime: 2 * 60 * 1000,
  });
}
