/**
 * Editor Plugin type contracts.
 *
 * Shared type definitions for the editor plugin system (Phase 45).
 * PluginManifest is the single source of truth for plugin shape -- both
 * frontend and backend validate against this schema.
 */

/** Permissions a plugin can request from the host editor. */
export type PluginPermission =
  | 'editor:read'
  | 'editor:write'
  | 'git:read'
  | 'storage:read'
  | 'storage:write';

/** Custom block type registered by a plugin. */
export interface PluginBlockType {
  type: string;
  label: string;
  icon: string;
}

/** Slash command registered by a plugin. */
export interface PluginSlashCommand {
  trigger: string;
  label: string;
  description: string;
}

/** Action (command palette / toolbar) registered by a plugin. */
export interface PluginAction {
  id: string;
  label: string;
  category: string;
  shortcut?: string;
}

/**
 * Plugin manifest -- the JSON descriptor bundled with every editor plugin.
 *
 * Required fields: name, version, displayName, description, author, entrypoint.
 * Optional arrays: permissions, blockTypes, slashCommands, actions.
 */
export interface PluginManifest {
  name: string;
  version: string;
  displayName: string;
  description: string;
  author: string;
  entrypoint: string;
  permissions: PluginPermission[];
  blockTypes?: PluginBlockType[];
  slashCommands?: PluginSlashCommand[];
  actions?: PluginAction[];
}

/** Runtime status of a plugin within a workspace. */
export type PluginStatus = 'enabled' | 'disabled';

/** Persisted workspace plugin record returned by the API. */
export interface WorkspacePlugin {
  id: string;
  workspaceId: string;
  name: string;
  version: string;
  displayName: string;
  description: string;
  author: string;
  status: PluginStatus;
  manifest: PluginManifest;
  storagePath: string;
  createdAt: string;
  updatedAt: string;
}
