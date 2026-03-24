'use client';

/**
 * PluginSandbox
 *
 * Renders a hidden iframe for a single plugin. The iframe uses
 * `sandbox="allow-scripts"` (no allow-same-origin, no allow-forms)
 * so the plugin has zero DOM access to the host. Communication happens
 * exclusively via the typed postMessage protocol.
 *
 * Plain React component -- NOT observer (React 19 flushSync constraint).
 */

import { useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';

import { registerAction } from '@/features/command-palette/registry/ActionRegistry';

import type { PluginSDKMethod } from '../sdk/plugin-sdk-types';
import { createMessageHandler, sendLifecycleEvent, type SDKHandlers } from './message-protocol';
import {
  type PluginManifest,
  registerPlugin,
  unregisterPlugin,
  addBlockRegistration,
  addCommandRegistration,
  addActionRegistration,
} from '../registry/PluginRegistry';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PluginSandboxProps {
  manifest: PluginManifest;
  jsContent: string;
  onError?: (error: string) => void;
}

// ---------------------------------------------------------------------------
// srcdoc template
// ---------------------------------------------------------------------------

function buildSrcdoc(jsContent: string): string {
  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<script>
// SDK proxy -- translates method calls into postMessage SDK calls.
(function() {
  var _pending = {};

  function call(method, args) {
    return new Promise(function(resolve, reject) {
      var id = Math.random().toString(36).slice(2) + Date.now().toString(36);
      _pending[id] = { resolve: resolve, reject: reject };
      parent.postMessage({ type: 'sdk-call', id: id, method: method, args: args || [] }, '*');
    });
  }

  window.addEventListener('message', function(e) {
    var d = e.data;
    if (d && d.type === 'sdk-response' && _pending[d.id]) {
      if (d.error) {
        _pending[d.id].reject(new Error(d.error));
      } else {
        _pending[d.id].resolve(d.result);
      }
      delete _pending[d.id];
    }
    if (d && d.type === 'lifecycle' && d.event === 'deactivate' && typeof onDeactivate === 'function') {
      try { onDeactivate(); } catch(e) { /* swallow */ }
    }
  });

  window.PilotPluginSDK = {
    editor: {
      getContent: function() { return call('editor.getContent'); },
      insertBlock: function(type, data) { return call('editor.insertBlock', [type, data]); },
      replaceSelection: function(text) { return call('editor.replaceSelection', [text]); },
      registerBlockRenderer: function(type, opts) { return call('editor.registerBlockRenderer', [type, opts]); }
    },
    commands: {
      register: function(trigger, opts) { return call('commands.register', [trigger, opts]); }
    },
    actions: {
      register: function(actionId, opts) { return call('actions.register', [actionId, opts]); }
    },
    ui: {
      showToast: function(message, opts) { return call('ui.showToast', [message, opts]); }
    },
    storage: {
      get: function(key) { return call('storage.get', [key]); },
      set: function(key, value) { return call('storage.set', [key, value]); }
    }
  };
})();
<\/script>
<script>
try {
  ${jsContent}
  if (typeof onActivate === 'function') { onActivate(window.PilotPluginSDK); }
} catch(e) {
  parent.postMessage({ type: 'sdk-call', id: '__error__', method: 'ui.showToast', args: ['Plugin error: ' + e.message] }, '*');
}
<\/script>
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PluginSandbox({ manifest, jsContent, onError }: PluginSandboxProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const actionUnregisters = useRef<Array<() => void>>([]);

  // Build SDK handlers that bridge postMessage calls to host functionality
  const buildHandlers = useCallback((): SDKHandlers => {
    const pluginName = manifest.name;

    const handlers: Record<PluginSDKMethod, (...args: unknown[]) => unknown | Promise<unknown>> = {
      'editor.getContent': () => {
        return new Promise((resolve) => {
          const handler = (e: Event) => {
            resolve((e as CustomEvent).detail);
          };
          document.addEventListener('plugin:editor-content-response', handler, { once: true });
          document.dispatchEvent(new CustomEvent('plugin:editor-get-content'));
        });
      },
      'editor.insertBlock': (type: unknown, data: unknown) => {
        document.dispatchEvent(
          new CustomEvent('plugin:editor-insert-block', { detail: { type, data } })
        );
      },
      'editor.replaceSelection': (text: unknown) => {
        document.dispatchEvent(
          new CustomEvent('plugin:editor-replace-selection', { detail: { text } })
        );
      },
      'editor.registerBlockRenderer': (type: unknown, opts: unknown) => {
        if (typeof type === 'string') {
          const options = (opts as Record<string, string>) ?? {};
          addBlockRegistration(pluginName, type, options.label, options.icon);
          document.dispatchEvent(
            new CustomEvent('plugin:block-registered', {
              detail: { pluginName, type, ...options },
            })
          );
        }
      },
      'commands.register': (trigger: unknown, opts: unknown) => {
        if (typeof trigger === 'string') {
          const options = (opts as Record<string, string>) ?? {};
          addCommandRegistration(pluginName, trigger, options.label, options.description);
          document.dispatchEvent(
            new CustomEvent('plugin:command-registered', {
              detail: { pluginName, trigger, ...options },
            })
          );
        }
      },
      'actions.register': (actionId: unknown, opts: unknown) => {
        if (typeof actionId === 'string') {
          const options = (opts as Record<string, unknown>) ?? {};
          const prefixedId = `plugin:${pluginName}:${actionId}`;
          addActionRegistration(pluginName, prefixedId);
          const unregister = registerAction({
            id: prefixedId,
            label: (options.label as string) ?? actionId,
            category: 'edit',
            icon: () => null,
            execute: () => {
              // Dispatch event so plugin can handle it
              document.dispatchEvent(
                new CustomEvent('plugin:action-executed', {
                  detail: { pluginName, actionId },
                })
              );
            },
          });
          actionUnregisters.current.push(unregister);
        }
      },
      'ui.showToast': (message: unknown, opts: unknown) => {
        const options = (opts as Record<string, string>) ?? {};
        const variant = options.variant;
        if (variant === 'error') {
          toast.error(String(message));
        } else if (variant === 'success') {
          toast.success(String(message));
        } else {
          toast(String(message));
        }
      },
      'storage.get': (key: unknown) => {
        try {
          const raw = localStorage.getItem(`plugin:${pluginName}:${String(key)}`);
          return raw ? JSON.parse(raw) : null;
        } catch {
          return null;
        }
      },
      'storage.set': (key: unknown, value: unknown) => {
        try {
          localStorage.setItem(`plugin:${pluginName}:${String(key)}`, JSON.stringify(value));
        } catch {
          // Storage full or unavailable -- swallow
        }
      },
    };

    return handlers;
  }, [manifest.name]);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    try {
      // Register plugin instance
      registerPlugin({
        name: manifest.name,
        iframe,
        manifest,
        registeredBlocks: [],
        registeredCommands: [],
        registeredActions: [],
      });

      // Set up message handler
      const handlers = buildHandlers();
      const messageHandler = createMessageHandler(
        manifest.name,
        manifest.permissions,
        handlers,
        iframe
      );
      window.addEventListener('message', messageHandler);

      // Send activate lifecycle event after iframe loads
      iframe.addEventListener(
        'load',
        () => {
          sendLifecycleEvent(iframe, 'activate');
        },
        { once: true }
      );

      return () => {
        // Cleanup: deactivate, unregister, remove listener
        sendLifecycleEvent(iframe, 'deactivate');
        window.removeEventListener('message', messageHandler);
        unregisterPlugin(manifest.name);

        // Clean up registered actions from ActionRegistry
        for (const unregister of actionUnregisters.current) {
          unregister();
        }
        actionUnregisters.current = [];
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown plugin error';
      onError?.(msg);
    }
  }, [manifest, buildHandlers, onError]);

  return (
    <iframe
      ref={iframeRef}
      sandbox="allow-scripts"
      srcDoc={buildSrcdoc(jsContent)}
      style={{ display: 'none' }}
      title={`Plugin: ${manifest.displayName}`}
    />
  );
}
