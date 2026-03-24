/**
 * TanStack Query hooks for workspace plugin CRUD.
 *
 * Phase 45-04: Provides usePlugins (list), useUploadPlugin, useTogglePlugin,
 * and useDeletePlugin with optimistic updates and toast notifications.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import type { WorkspacePlugin, PluginStatus } from '../types';
import { listPlugins, uploadPlugin, togglePlugin, deletePlugin } from '../api/plugin-api';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

const pluginKeys = {
  all: (workspaceId: string) => ['workspace-plugins', workspaceId] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Fetch all plugins (enabled + disabled) for a workspace.
 */
export function usePlugins(workspaceId: string) {
  return useQuery({
    queryKey: pluginKeys.all(workspaceId),
    queryFn: () => listPlugins(workspaceId),
    staleTime: 60_000,
    enabled: Boolean(workspaceId),
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Upload a new plugin zip file.
 * Invalidates the plugin list on success; shows toast on success/error.
 */
export function useUploadPlugin(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadPlugin(workspaceId, file),
    onSuccess: (plugin) => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.all(workspaceId) });
      toast.success(`Plugin "${plugin.displayName}" installed`);
    },
    onError: (error: Error) => {
      toast.error('Failed to upload plugin', {
        description: error.message,
      });
    },
  });
}

/**
 * Toggle a plugin between enabled and disabled.
 * Uses optimistic update for instant UI feedback; rolls back on error.
 */
export function useTogglePlugin(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ pluginId, status }: { pluginId: string; status: PluginStatus }) =>
      togglePlugin(workspaceId, pluginId, status),

    onMutate: async ({ pluginId, status }) => {
      // Cancel outgoing queries so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: pluginKeys.all(workspaceId) });

      const previous = queryClient.getQueryData<WorkspacePlugin[]>(pluginKeys.all(workspaceId));

      // Optimistically toggle the status in-place
      queryClient.setQueryData<WorkspacePlugin[]>(pluginKeys.all(workspaceId), (old) =>
        old?.map((p) => (p.id === pluginId ? { ...p, status } : p))
      );

      return { previous };
    },

    onError: (_error, _vars, context) => {
      // Rollback to previous state
      if (context?.previous) {
        queryClient.setQueryData(pluginKeys.all(workspaceId), context.previous);
      }
      toast.error('Failed to update plugin status');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.all(workspaceId) });
    },
  });
}

/**
 * Delete a plugin from the workspace.
 * Invalidates the plugin list on success; shows confirmation toast.
 */
export function useDeletePlugin(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (pluginId: string) => deletePlugin(workspaceId, pluginId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.all(workspaceId) });
      toast.success('Plugin deleted');
    },
    onError: (error: Error) => {
      toast.error('Failed to delete plugin', {
        description: error.message,
      });
    },
  });
}
