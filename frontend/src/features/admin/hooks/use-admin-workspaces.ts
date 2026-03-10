'use client';

import { useQuery } from '@tanstack/react-query';

// ---- Token helpers ----

function getAdminToken(): string {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem('admin_token') ?? '';
}

// ---- Types ----

export interface AdminWorkspace {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  member_count: number;
  owner_email: string | null;
  last_active: string | null;
  storage_used_bytes: number;
  ai_action_count: number;
  rate_limit_violation_count: number;
}

export interface AdminWorkspaceDetail extends AdminWorkspace {
  top_members: Array<{ user_id: string; email: string; action_count: number }>;
  recent_ai_actions: Array<{ actor: string; action: string; created_at: string }>;
  quota_config: {
    rate_limit_standard_rpm: number | null;
    rate_limit_ai_rpm: number | null;
    storage_quota_mb: number | null;
  };
}

// ---- Fetchers ----

async function fetchAdminWorkspaces(token: string): Promise<AdminWorkspace[]> {
  const res = await fetch('/api/v1/admin/workspaces', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) throw new Error('Invalid or missing admin token');
  if (!res.ok) throw new Error(`Failed to fetch workspaces: ${res.status}`);
  return res.json() as Promise<AdminWorkspace[]>;
}

async function fetchAdminWorkspaceDetail(
  token: string,
  slug: string
): Promise<AdminWorkspaceDetail> {
  const res = await fetch(`/api/v1/admin/workspaces/${slug}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) throw new Error('Invalid admin token');
  if (!res.ok) throw new Error(`Failed to fetch workspace detail: ${res.status}`);
  return res.json() as Promise<AdminWorkspaceDetail>;
}

// ---- Hooks ----

/**
 * Fetch all workspace health summaries using the provided admin bearer token.
 * Token is passed explicitly (not read from sessionStorage) so the hook re-runs
 * when the token state changes in the parent component.
 */
export function useAdminWorkspaces(token: string) {
  return useQuery({
    queryKey: ['admin', 'workspaces', token],
    queryFn: () => fetchAdminWorkspaces(token),
    enabled: !!token,
    retry: false,
    staleTime: 60_000, // 60s — operator view is not real-time
  });
}

/**
 * Fetch detail for a single workspace (top members, recent AI actions, quota config).
 * Only fetches when both token and slug are truthy (i.e. a row is expanded).
 */
export function useAdminWorkspaceDetail(token: string, slug: string | null) {
  return useQuery({
    queryKey: ['admin', 'workspace', slug, token],
    queryFn: () => fetchAdminWorkspaceDetail(token, slug!),
    enabled: !!token && !!slug,
    retry: false,
    staleTime: 60_000,
  });
}

// Re-export helper for components that need to read token outside React render
export { getAdminToken };
