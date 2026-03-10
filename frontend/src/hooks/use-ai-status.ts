/**
 * useAIStatus - Hook for fetching workspace AI configuration status.
 *
 * Returns BYOK configuration state: whether the workspace has an API key
 * configured and which providers are available.
 *
 * Used by:
 * - AiNotConfiguredBanner (owner-only banner)
 * - AI trigger controls (disable when byok_configured=false)
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api/client';

export interface AIStatusResponse {
  byok_configured: boolean;
  providers: string[];
}

export function useAIStatus(workspaceSlug: string) {
  return useQuery<AIStatusResponse>({
    queryKey: ['ai-status', workspaceSlug],
    queryFn: () =>
      apiClient.get<AIStatusResponse>(`/workspaces/${workspaceSlug}/settings/ai-status`),
    enabled: !!workspaceSlug,
    staleTime: 60 * 1000, // 1 min cache; don't hammer the endpoint
  });
}
