/**
 * use-sso-login hooks tests.
 *
 * Tests for useWorkspaceSsoStatus, useSsoLogin, and useApplyClaimsRole.
 * Uses TanStack Query + vitest-mock patterns.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, type ReactNode } from 'react';

// ---- Module mocks ----

vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn(),
    },
  },
}));

// ---- Imports after mocks ----

import { apiClient } from '@/services/api';
import { supabase } from '@/lib/supabase';
import { useWorkspaceSsoStatus, useSsoLogin, useApplyClaimsRole } from '../use-sso-login';

// ---- Helpers ----

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ---- Tests ----

describe('useWorkspaceSsoStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not fetch when workspaceId is null', () => {
    const { result } = renderHook(() => useWorkspaceSsoStatus(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
    expect(result.current.isFetchedAfterMount).toBe(false);
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('fetches SSO status when workspaceId is provided', async () => {
    const mockStatus = {
      has_saml: true,
      has_oidc: false,
      sso_required: false,
      oidc_provider: null,
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useWorkspaceSsoStatus('workspace-uuid-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/auth/sso/status?workspace_id=workspace-uuid-123');
    expect(result.current.data).toEqual(mockStatus);
  });

  it('returns correct shape when SSO is not configured', async () => {
    const mockStatus = {
      has_saml: false,
      has_oidc: false,
      sso_required: false,
      oidc_provider: null,
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useWorkspaceSsoStatus('workspace-uuid-456'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.has_saml).toBe(false);
    expect(result.current.data?.has_oidc).toBe(false);
    expect(result.current.data?.sso_required).toBe(false);
  });
});

describe('useSsoLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location.href setter
    Object.defineProperty(window, 'location', {
      value: { ...window.location, href: '' },
      writable: true,
    });
  });

  it('calls supabase.auth.signInWithOAuth for OIDC login', async () => {
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValueOnce({
      data: { provider: 'google', url: 'https://accounts.google.com/oauth' },
      error: null,
    });

    const { result } = renderHook(() => useSsoLogin(), {
      wrapper: createWrapper(),
    });

    await result.current('workspace-123', 'oidc', 'google');

    expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'google',
        options: expect.objectContaining({
          redirectTo: expect.stringContaining('/auth/callback'),
        }),
      })
    );
  });

  it('fetches SAML redirect URL and redirects for SAML login', async () => {
    const mockRedirectUrl = 'https://idp.okta.com/sso/saml?SAMLRequest=abc123';
    vi.mocked(apiClient.get).mockResolvedValueOnce({ redirect_url: mockRedirectUrl });

    const { result } = renderHook(() => useSsoLogin(), {
      wrapper: createWrapper(),
    });

    await result.current('workspace-456', 'saml');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/auth/sso/saml/initiate?workspace_id=workspace-456'
    );
    expect(window.location.href).toBe(mockRedirectUrl);
  });

  it('includes workspace_id in OIDC redirectTo URL', async () => {
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValueOnce({
      data: { provider: 'google', url: '' },
      error: null,
    });

    const { result } = renderHook(() => useSsoLogin(), {
      wrapper: createWrapper(),
    });

    await result.current('my-workspace-id', 'oidc', 'google');

    expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
      expect.objectContaining({
        options: expect.objectContaining({
          redirectTo: expect.stringContaining('workspace_id=my-workspace-id'),
        }),
      })
    );
  });
});

describe('useApplyClaimsRole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POSTs to /auth/sso/claim-role with workspace_id and jwt_claims', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ role: 'admin' });

    const { result } = renderHook(() => useApplyClaimsRole(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      workspaceId: 'workspace-789',
      jwtClaims: { groups: ['admin-group'] },
    });

    expect(apiClient.post).toHaveBeenCalledWith('/auth/sso/claim-role', {
      workspace_id: 'workspace-789',
      jwt_claims: { groups: ['admin-group'] },
    });
  });

  it('succeeds when claim-role returns the applied role', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ role: 'member' });

    const { result } = renderHook(() => useApplyClaimsRole(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.mutateAsync({
      workspaceId: 'workspace-abc',
      jwtClaims: {},
    });

    expect(response).toEqual({ role: 'member' });
  });
});
