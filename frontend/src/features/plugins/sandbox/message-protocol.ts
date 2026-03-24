/**
 * Message Protocol
 *
 * Host-side postMessage handling for the plugin sandbox.
 * Validates origin, checks permissions, dispatches to handlers,
 * and ensures plugin errors never propagate to the host.
 */

import {
  type PluginPermission,
  type PluginResponse,
  type PluginSDKMethod,
  type PluginLifecycleEvent,
  METHOD_PERMISSIONS,
  isPluginMessage,
} from '../sdk/plugin-sdk-types';

// ---------------------------------------------------------------------------
// Permission check
// ---------------------------------------------------------------------------

/**
 * Returns true if the plugin's declared permissions satisfy all
 * permissions required by the given SDK method.
 */
export function checkPermission(
  method: PluginSDKMethod,
  manifestPermissions: PluginPermission[]
): boolean {
  const required = METHOD_PERMISSIONS[method];
  return required.every((perm) => manifestPermissions.includes(perm));
}

// ---------------------------------------------------------------------------
// Message handler factory
// ---------------------------------------------------------------------------

export type SDKHandlers = Record<
  PluginSDKMethod,
  (...args: unknown[]) => unknown | Promise<unknown>
>;

/**
 * Creates a `message` event handler for a specific plugin iframe.
 *
 * The returned handler:
 *  1. Validates the message shape via `isPluginMessage`.
 *  2. Checks that the plugin has permission for the called method.
 *  3. Invokes the corresponding handler from `handlers`.
 *  4. Posts a `PluginResponse` back to the iframe.
 *  5. Catches all errors and sends an error response (never throws).
 */
export function createMessageHandler(
  pluginName: string,
  permissions: PluginPermission[],
  handlers: SDKHandlers,
  iframe: HTMLIFrameElement
): (event: MessageEvent) => void {
  return (event: MessageEvent) => {
    // Only accept messages from the plugin iframe
    if (event.source !== iframe.contentWindow) return;

    const data = event.data;
    if (!isPluginMessage(data)) return;

    const { id, method, args } = data;

    // Permission check
    if (!checkPermission(method, permissions)) {
      const response: PluginResponse = {
        type: 'sdk-response',
        id,
        error: `Plugin "${pluginName}" lacks permission for "${method}". Required: ${METHOD_PERMISSIONS[method].join(', ')}`,
      };
      iframe.contentWindow?.postMessage(response, '*');
      return;
    }

    // Dispatch to handler
    const handler = handlers[method];
    if (!handler) {
      const response: PluginResponse = {
        type: 'sdk-response',
        id,
        error: `No handler registered for method "${method}"`,
      };
      iframe.contentWindow?.postMessage(response, '*');
      return;
    }

    // Execute handler (may be sync or async)
    void (async () => {
      try {
        const result = await handler(...args);
        const response: PluginResponse = {
          type: 'sdk-response',
          id,
          result,
        };
        iframe.contentWindow?.postMessage(response, '*');
      } catch (err) {
        const response: PluginResponse = {
          type: 'sdk-response',
          id,
          error: err instanceof Error ? err.message : `Unknown error in handler for "${method}"`,
        };
        iframe.contentWindow?.postMessage(response, '*');
      }
    })();
  };
}

// ---------------------------------------------------------------------------
// Lifecycle events
// ---------------------------------------------------------------------------

/**
 * Sends a lifecycle event to the plugin iframe.
 */
export function sendLifecycleEvent(
  iframe: HTMLIFrameElement,
  event: 'activate' | 'deactivate'
): void {
  const message: PluginLifecycleEvent = {
    type: 'lifecycle',
    event,
  };
  iframe.contentWindow?.postMessage(message, '*');
}
