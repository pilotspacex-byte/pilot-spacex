/**
 * Plugin Registry
 *
 * Runtime registry of active plugin instances and their registrations
 * (blocks, commands, actions). Plain module-level Map -- not MobX.
 */

import type { PluginPermission } from '../sdk/plugin-sdk-types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PluginManifest {
  name: string;
  version: string;
  displayName: string;
  description: string;
  permissions: PluginPermission[];
  icon?: string;
  storagePath?: string;
}

export interface PluginInstance {
  name: string;
  iframe: HTMLIFrameElement;
  manifest: PluginManifest;
  registeredBlocks: string[];
  registeredCommands: string[];
  registeredActions: string[];
}

export interface RegisteredBlockType {
  pluginName: string;
  type: string;
  label: string;
  icon: string;
}

export interface RegisteredSlashCommand {
  pluginName: string;
  trigger: string;
  label: string;
  description: string;
}

// ---------------------------------------------------------------------------
// Registry state (module-level, not MobX)
// ---------------------------------------------------------------------------

let plugins = new Map<string, PluginInstance>();

/** Metadata for plugin-registered block types. */
let blockTypes = new Map<string, RegisteredBlockType>();

/** Metadata for plugin-registered slash commands. */
let slashCommands = new Map<string, RegisteredSlashCommand>();

// ---------------------------------------------------------------------------
// Plugin lifecycle
// ---------------------------------------------------------------------------

export function registerPlugin(instance: PluginInstance): void {
  plugins.set(instance.name, instance);
}

/**
 * Unregisters a plugin and cleans up all its registered blocks, commands,
 * and actions.
 */
export function unregisterPlugin(name: string): void {
  const instance = plugins.get(name);
  if (!instance) return;

  // Clean up block registrations
  for (const blockType of instance.registeredBlocks) {
    blockTypes.delete(`${name}:${blockType}`);
  }

  // Clean up command registrations
  for (const trigger of instance.registeredCommands) {
    slashCommands.delete(`${name}:${trigger}`);
  }

  // Clean up action registrations (handled externally via ActionRegistry)
  // The caller is responsible for unregistering from ActionRegistry

  plugins.delete(name);
}

export function getPlugin(name: string): PluginInstance | undefined {
  return plugins.get(name);
}

export function getActivePlugins(): PluginInstance[] {
  return Array.from(plugins.values());
}

// ---------------------------------------------------------------------------
// Block type registrations
// ---------------------------------------------------------------------------

export function addBlockRegistration(
  pluginName: string,
  type: string,
  label: string = type,
  icon: string = 'puzzle'
): void {
  const instance = plugins.get(pluginName);
  if (instance && !instance.registeredBlocks.includes(type)) {
    instance.registeredBlocks.push(type);
  }
  blockTypes.set(`${pluginName}:${type}`, { pluginName, type, label, icon });
}

export function getRegisteredBlockTypes(): RegisteredBlockType[] {
  return Array.from(blockTypes.values());
}

// ---------------------------------------------------------------------------
// Slash command registrations
// ---------------------------------------------------------------------------

export function addCommandRegistration(
  pluginName: string,
  trigger: string,
  label: string = trigger,
  description: string = ''
): void {
  const instance = plugins.get(pluginName);
  if (instance && !instance.registeredCommands.includes(trigger)) {
    instance.registeredCommands.push(trigger);
  }
  slashCommands.set(`${pluginName}:${trigger}`, {
    pluginName,
    trigger,
    label,
    description,
  });
}

export function getRegisteredSlashCommands(): RegisteredSlashCommand[] {
  return Array.from(slashCommands.values());
}

// ---------------------------------------------------------------------------
// Action registrations
// ---------------------------------------------------------------------------

export function addActionRegistration(pluginName: string, actionId: string): void {
  const instance = plugins.get(pluginName);
  if (instance && !instance.registeredActions.includes(actionId)) {
    instance.registeredActions.push(actionId);
  }
}

// ---------------------------------------------------------------------------
// Testing utility
// ---------------------------------------------------------------------------

export function clearAll(): void {
  plugins = new Map();
  blockTypes = new Map();
  slashCommands = new Map();
}
