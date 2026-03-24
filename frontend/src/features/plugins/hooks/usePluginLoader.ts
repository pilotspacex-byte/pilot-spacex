/**
 * usePluginLoader
 *
 * Fetches enabled plugins for a workspace and lazily loads their JS bundles.
 * Uses TanStack Query with a 5-minute stale time. Plugin bundles are fetched
 * only after the plugin list resolves (dependent query pattern).
 */

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/services/api/client';

import type { PluginManifest } from '../registry/PluginRegistry';

// ---------------------------------------------------------------------------
// API types
// ---------------------------------------------------------------------------

interface EnabledPluginDTO {
  name: string;
  version: string;
  display_name: string;
  description: string;
  permissions: string[];
  icon?: string;
  storage_path: string;
}

interface LoadedPlugin {
  manifest: PluginManifest;
  jsContent: string;
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

async function fetchEnabledPlugins(workspaceId: string): Promise<EnabledPluginDTO[]> {
  return apiClient.get<EnabledPluginDTO[]>(`/workspaces/${workspaceId}/plugins/enabled`);
}

async function fetchPluginBundle(storagePath: string): Promise<string> {
  const res = await fetch(storagePath);
  if (!res.ok) throw new Error(`Failed to fetch plugin bundle: ${res.status}`);
  return res.text();
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePluginLoader(workspaceId: string) {
  // Step 1: Fetch the list of enabled plugins
  const pluginListQuery = useQuery({
    queryKey: ['workspace-plugins', workspaceId],
    queryFn: () => fetchEnabledPlugins(workspaceId),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(workspaceId),
  });

  // Step 2: Fetch JS bundles for each enabled plugin (dependent query)
  const bundlesQuery = useQuery({
    queryKey: ['workspace-plugin-bundles', workspaceId, pluginListQuery.data?.length ?? 0],
    queryFn: async (): Promise<LoadedPlugin[]> => {
      const dtos = pluginListQuery.data ?? [];
      const results = await Promise.allSettled(
        dtos.map(async (dto): Promise<LoadedPlugin> => {
          const jsContent = await fetchPluginBundle(dto.storage_path);
          return {
            manifest: {
              name: dto.name,
              version: dto.version,
              displayName: dto.display_name,
              description: dto.description,
              permissions: dto.permissions as PluginManifest['permissions'],
              icon: dto.icon,
              storagePath: dto.storage_path,
            },
            jsContent,
          };
        })
      );

      // Only return successfully loaded plugins
      return results
        .filter((r): r is PromiseFulfilledResult<LoadedPlugin> => r.status === 'fulfilled')
        .map((r) => r.value);
    },
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(pluginListQuery.data && pluginListQuery.data.length > 0),
  });

  const isLoading = pluginListQuery.isLoading || bundlesQuery.isLoading;
  const error = pluginListQuery.error?.message ?? bundlesQuery.error?.message ?? null;

  return {
    plugins: bundlesQuery.data ?? [],
    isLoading,
    error,
  };
}
