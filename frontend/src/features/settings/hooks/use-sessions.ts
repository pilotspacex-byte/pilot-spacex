/**
 * useSessions - TanStack Query hooks for workspace session management.
 *
 * AUTH-06: Session visibility and termination for workspace admins.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface Session {
  id: string;
  user_id: string;
  user_display_name: string | null;
  user_avatar_url: string | null;
  ip_address: string | null;
  browser: string | null;
  os: string | null;
  device: string | null;
  last_seen_at: string;
  created_at: string;
  is_current: boolean;
}

// ---- Query Keys ----

export const sessionKeys = {
  list: (workspaceSlug: string) => ['workspace-sessions', workspaceSlug] as const,
};

// ---- Hooks ----

export function useSessions(workspaceSlug: string) {
  return useQuery<Session[]>({
    queryKey: sessionKeys.list(workspaceSlug),
    queryFn: () => apiClient.get<Session[]>(`/workspaces/${workspaceSlug}/sessions`),
    enabled: !!workspaceSlug,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}

export function useTerminateSession(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiClient.delete(`/workspaces/${workspaceSlug}/sessions/${sessionId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.list(workspaceSlug) });
    },
  });
}

export function useTerminateAllUserSessions(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      apiClient.delete(`/workspaces/${workspaceSlug}/sessions/users/${userId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.list(workspaceSlug) });
    },
  });
}
