/**
 * useScim - TanStack Query hooks for SCIM directory sync token management.
 *
 * AUTH-07: SCIM token generation for workspace admins.
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface ScimTokenResponse {
  token: string;
  message: string;
}

// ---- Hooks ----

export function useGenerateScimToken(workspaceSlug: string) {
  return useMutation({
    mutationFn: () =>
      apiClient.post<ScimTokenResponse>(`/workspaces/${workspaceSlug}/settings/scim-token`),
  });
}
