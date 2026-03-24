/**
 * Plugin SDK Types
 *
 * Defines the typed postMessage communication contract between the host editor
 * and sandboxed plugin iframes. Every SDK method is mapped to required permissions
 * so the host can enforce access control on each call.
 */

// ---------------------------------------------------------------------------
// Permissions (declared in plugin manifest)
// ---------------------------------------------------------------------------

export type PluginPermission = 'editor:read' | 'editor:write' | 'storage:read' | 'storage:write';

// ---------------------------------------------------------------------------
// SDK Methods
// ---------------------------------------------------------------------------

export type PluginSDKMethod =
  | 'editor.getContent'
  | 'editor.insertBlock'
  | 'editor.replaceSelection'
  | 'editor.registerBlockRenderer'
  | 'commands.register'
  | 'actions.register'
  | 'ui.showToast'
  | 'storage.get'
  | 'storage.set';

/**
 * Maps every SDK method to the permissions it requires.
 * An empty array means the method is available to all plugins.
 */
export const METHOD_PERMISSIONS: Record<PluginSDKMethod, PluginPermission[]> = {
  'editor.getContent': ['editor:read'],
  'editor.insertBlock': ['editor:write'],
  'editor.replaceSelection': ['editor:write'],
  'editor.registerBlockRenderer': ['editor:write'],
  'commands.register': ['editor:write'],
  'actions.register': ['editor:write'],
  'ui.showToast': [],
  'storage.get': ['storage:read'],
  'storage.set': ['storage:write'],
};

// ---------------------------------------------------------------------------
// Message Protocol
// ---------------------------------------------------------------------------

/** Sent from plugin iframe to host via postMessage. */
export interface PluginMessage {
  type: 'sdk-call';
  id: string;
  method: PluginSDKMethod;
  args: unknown[];
}

/** Sent from host back to plugin iframe via postMessage. */
export interface PluginResponse {
  type: 'sdk-response';
  id: string;
  result?: unknown;
  error?: string;
}

/** Sent from host to plugin iframe for lifecycle transitions. */
export interface PluginLifecycleEvent {
  type: 'lifecycle';
  event: 'activate' | 'deactivate';
}

// ---------------------------------------------------------------------------
// Type guards
// ---------------------------------------------------------------------------

export function isPluginMessage(data: unknown): data is PluginMessage {
  if (typeof data !== 'object' || data === null) return false;
  const msg = data as Record<string, unknown>;
  return (
    msg.type === 'sdk-call' &&
    typeof msg.id === 'string' &&
    typeof msg.method === 'string' &&
    Array.isArray(msg.args)
  );
}
