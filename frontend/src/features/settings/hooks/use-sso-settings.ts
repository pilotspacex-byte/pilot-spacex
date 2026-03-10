/**
 * useSSoSettings - TanStack Query hooks for SSO configuration.
 *
 * AUTH-01, AUTH-02: SAML 2.0 and OIDC/OAuth 2.0 configuration API operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

// ---- Types ----

export interface SamlConfig {
  entity_id: string;
  sso_url: string;
  acs_url: string;
  metadata_url: string | null;
  certificate: string | null;
  sso_required: boolean;
}

export interface UpdateSamlConfigInput {
  entity_id?: string;
  sso_url?: string;
  certificate?: string;
  metadata_url?: string;
}

export interface OidcConfig {
  provider: 'google' | 'azure' | 'okta';
  client_id: string;
  client_secret?: string;
  issuer_url?: string;
  enabled: boolean;
}

export interface UpdateOidcConfigInput {
  provider: 'google' | 'azure' | 'okta';
  client_id: string;
  client_secret?: string;
  issuer_url?: string;
}

export interface RoleClaimMapping {
  claim_key: string;
  mappings: Array<{
    claim_value: string;
    role_id: string;
  }>;
}

export interface UpdateRoleClaimMappingInput {
  claim_key: string;
  mappings: Array<{
    claim_value: string;
    role_id: string;
  }>;
}

// ---- Query Keys ----

export const ssoKeys = {
  saml: (workspaceSlug: string) => ['sso', workspaceSlug, 'saml'] as const,
  oidc: (workspaceSlug: string) => ['sso', workspaceSlug, 'oidc'] as const,
  roleMapping: (workspaceSlug: string) => ['sso', workspaceSlug, 'role-mapping'] as const,
};

// ---- SAML Hooks ----

export function useSamlConfig(workspaceSlug: string) {
  return useQuery<SamlConfig | null>({
    queryKey: ssoKeys.saml(workspaceSlug),
    queryFn: () =>
      apiClient.get<SamlConfig | null>(`/auth/sso/saml/config?workspace_slug=${workspaceSlug}`),
    enabled: !!workspaceSlug,
    staleTime: 60_000,
  });
}

export function useUpdateSamlConfig(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateSamlConfigInput) =>
      apiClient.put<SamlConfig>('/auth/sso/saml/config', {
        ...data,
        workspace_slug: workspaceSlug,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(ssoKeys.saml(workspaceSlug), updated);
    },
  });
}

// ---- OIDC Hooks ----

export function useOidcConfig(workspaceSlug: string) {
  return useQuery<OidcConfig | null>({
    queryKey: ssoKeys.oidc(workspaceSlug),
    queryFn: () =>
      apiClient.get<OidcConfig | null>(`/auth/sso/oidc/config?workspace_slug=${workspaceSlug}`),
    enabled: !!workspaceSlug,
    staleTime: 60_000,
  });
}

export function useUpdateOidcConfig(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateOidcConfigInput) =>
      apiClient.put<OidcConfig>('/auth/sso/oidc/config', {
        ...data,
        workspace_slug: workspaceSlug,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(ssoKeys.oidc(workspaceSlug), updated);
    },
  });
}

// ---- SSO Enforcement Hook ----

export function useSetSsoRequired(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sso_required: boolean) =>
      apiClient.patch('/auth/sso/enforcement', { workspace_slug: workspaceSlug, sso_required }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ssoKeys.saml(workspaceSlug) });
    },
  });
}

// ---- Role Claim Mapping Hooks ----

export function useRoleClaimMapping(workspaceSlug: string) {
  return useQuery<RoleClaimMapping | null>({
    queryKey: ssoKeys.roleMapping(workspaceSlug),
    queryFn: () =>
      apiClient.get<RoleClaimMapping | null>(
        `/auth/sso/role-mapping?workspace_slug=${workspaceSlug}`
      ),
    enabled: !!workspaceSlug,
    staleTime: 60_000,
  });
}

export function useUpdateRoleClaimMapping(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateRoleClaimMappingInput) =>
      apiClient.put<RoleClaimMapping>('/auth/sso/role-mapping', {
        ...data,
        workspace_slug: workspaceSlug,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(ssoKeys.roleMapping(workspaceSlug), updated);
    },
  });
}
