/**
 * Plugin API client - CRUD operations for workspace editor plugins.
 *
 * Phase 45-04: Provides typed API functions consumed by TanStack Query hooks
 * in usePlugins.ts. All functions use the shared apiClient singleton which
 * handles auth headers, error transformation, and response unwrapping.
 */

import { apiClient } from '@/services/api/client';
import type { WorkspacePlugin, PluginStatus } from '../types';

/**
 * List all plugins installed in a workspace (enabled + disabled).
 */
export function listPlugins(workspaceId: string): Promise<WorkspacePlugin[]> {
  return apiClient.get<WorkspacePlugin[]>(`/workspaces/${workspaceId}/plugins`);
}

/**
 * List only enabled plugins for a workspace.
 */
export function listEnabledPlugins(workspaceId: string): Promise<WorkspacePlugin[]> {
  return apiClient.get<WorkspacePlugin[]>(`/workspaces/${workspaceId}/plugins/enabled`);
}

/**
 * Upload a plugin zip file containing plugin.json manifest and JS bundle.
 *
 * The backend handles zip extraction, manifest validation, and bundle storage.
 * The zip is sent as multipart/form-data.
 */
export function uploadPlugin(workspaceId: string, file: File): Promise<WorkspacePlugin> {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient.post<WorkspacePlugin>(`/workspaces/${workspaceId}/plugins`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

/**
 * Toggle a plugin's status between enabled and disabled.
 */
export function togglePlugin(
  workspaceId: string,
  pluginId: string,
  status: PluginStatus
): Promise<WorkspacePlugin> {
  return apiClient.patch<WorkspacePlugin>(`/workspaces/${workspaceId}/plugins/${pluginId}/status`, {
    status,
  });
}

/**
 * Permanently delete a plugin from the workspace.
 */
export function deletePlugin(workspaceId: string, pluginId: string): Promise<void> {
  return apiClient.delete(`/workspaces/${workspaceId}/plugins/${pluginId}`);
}
