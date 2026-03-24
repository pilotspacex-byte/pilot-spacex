/**
 * Plugin feature barrel exports.
 *
 * Re-exports the primary components, hooks, and types for the editor plugin
 * system (Phase 45). Consumers should import from this barrel rather than
 * reaching into subdirectories.
 */

// Components
export { PluginSandbox } from './sandbox/PluginSandbox';

// Hooks
export { usePluginLoader } from './hooks/usePluginLoader';
export { usePluginEditorBridge } from './integration/usePluginEditorBridge';

// Registry
export {
  registerPlugin,
  unregisterPlugin,
  getPlugin,
  getActivePlugins,
  getRegisteredBlockTypes,
  getRegisteredSlashCommands,
  clearAll,
} from './registry/PluginRegistry';

// Re-export registry types
export type {
  PluginManifest as RegistryPluginManifest,
  PluginInstance,
  RegisteredBlockType,
  RegisteredSlashCommand,
} from './registry/PluginRegistry';

// Types
export type { PluginManifest, WorkspacePlugin, PluginStatus } from './types';
