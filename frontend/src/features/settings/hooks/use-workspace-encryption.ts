/**
 * useWorkspaceEncryption - TanStack Query hooks for workspace encryption management.
 *
 * TENANT-02: Bring-your-own-key encryption configuration for workspace owners.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface EncryptionStatus {
  enabled: boolean;
  key_hint: string | null;
  key_version: number | null;
  last_rotated: string | null;
}

export interface UploadEncryptionKeyResponse {
  key_version: number;
  key_hint: string;
}

export interface VerifyEncryptionKeyResponse {
  verified: boolean;
  key_version: number;
}

export interface GenerateEncryptionKeyResponse {
  key: string;
}

// ---- Query Keys ----

export const encryptionKeys = {
  status: (workspaceSlug: string) => ['workspace', workspaceSlug, 'encryption'] as const,
};

// ---- Hooks ----

export function useEncryptionStatus(workspaceSlug: string) {
  return useQuery<EncryptionStatus>({
    queryKey: encryptionKeys.status(workspaceSlug),
    queryFn: () => apiClient.get<EncryptionStatus>(`/workspaces/${workspaceSlug}/encryption`),
    enabled: !!workspaceSlug,
    staleTime: 60_000,
  });
}

export function useUploadEncryptionKey(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (key: string) =>
      apiClient.put<UploadEncryptionKeyResponse>(`/workspaces/${workspaceSlug}/encryption/key`, {
        key,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: encryptionKeys.status(workspaceSlug) });
    },
  });
}

export function useVerifyEncryptionKey(workspaceSlug: string) {
  return useMutation({
    mutationFn: (key: string) =>
      apiClient.post<VerifyEncryptionKeyResponse>(
        `/workspaces/${workspaceSlug}/encryption/verify`,
        { key }
      ),
  });
}

export function useGenerateEncryptionKey(workspaceSlug: string) {
  return useMutation({
    mutationFn: () =>
      apiClient.post<GenerateEncryptionKeyResponse>(
        `/workspaces/${workspaceSlug}/encryption/generate-key`,
        {}
      ),
  });
}
