/**
 * SSO login hooks — AUTH-01, AUTH-02, AUTH-03
 *
 * useWorkspaceSsoStatus: check if a workspace has SSO configured
 * useSsoLogin:           initiate SAML redirect or Supabase OIDC sign-in
 * useApplyClaimsRole:    apply IdP role claims after OIDC login
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { useCallback } from 'react';
import { apiClient } from '@/services/api';
import { supabase } from '@/lib/supabase';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkspaceSsoStatus {
  has_saml: boolean;
  has_oidc: boolean;
  sso_required: boolean;
  oidc_provider: 'google' | 'azure' | 'okta' | null;
}

export type OidcProvider = 'google' | 'azure' | 'okta';

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const ssoLoginKeys = {
  status: (workspaceId: string) => ['sso-status', workspaceId] as const,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Fetch SSO configuration status for a workspace.
 * No auth required — called before login to decide whether to show SSO button.
 * Returns all-false gracefully when workspace is unknown.
 */
export function useWorkspaceSsoStatus(workspaceId: string | null) {
  return useQuery<WorkspaceSsoStatus>({
    queryKey: ssoLoginKeys.status(workspaceId ?? ''),
    queryFn: () =>
      apiClient.get<WorkspaceSsoStatus>(`/auth/sso/status?workspace_id=${workspaceId}`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

/**
 * Returns a callback that initiates SSO login.
 *
 * OIDC path: delegates to Supabase auth.signInWithOAuth (handles PKCE, redirects).
 * SAML path: fetches the SP-initiated redirect URL from backend then hard-navigates.
 */
export function useSsoLogin() {
  return useCallback(
    async (workspaceId: string, method: 'saml' | 'oidc', oidcProvider?: string): Promise<void> => {
      if (method === 'oidc' && oidcProvider) {
        await supabase.auth.signInWithOAuth({
          // Supabase accepts any string for custom OIDC providers
          provider: oidcProvider as Parameters<typeof supabase.auth.signInWithOAuth>[0]['provider'],
          options: {
            redirectTo: `${window.location.origin}/auth/callback?workspace_id=${workspaceId}`,
          },
        });
        return;
      }

      if (method === 'saml') {
        const { redirect_url } = await apiClient.get<{ redirect_url: string }>(
          `/auth/sso/saml/initiate?workspace_id=${workspaceId}`
        );
        window.location.href = redirect_url;
      }
    },
    []
  );
}

/**
 * Mutation to apply workspace role from SSO JWT claims after OIDC login.
 * Called in the auth callback after session is established.
 * Graceful degradation: callers should catch and ignore failures
 * (unmapped claims default to "member" on the backend).
 */
export function useApplyClaimsRole() {
  return useMutation({
    mutationFn: ({
      workspaceId,
      jwtClaims,
    }: {
      workspaceId: string;
      jwtClaims: Record<string, unknown>;
    }) =>
      apiClient.post<{ role: string }>('/auth/sso/claim-role', {
        workspace_id: workspaceId,
        jwt_claims: jwtClaims,
      }),
  });
}
