'use client';

/**
 * usePluginEditorBridge
 *
 * Bridge hook that wires plugin DOM CustomEvents to Monaco editor operations.
 * Listens for events dispatched by PluginSandbox handlers and translates them
 * into Monaco editor API calls.
 *
 * All handlers are wrapped in try/catch -- errors are logged, never thrown.
 */

import { useEffect } from 'react';
import type * as monacoNs from 'monaco-editor';

/**
 * Hook that connects plugin DOM events to Monaco editor operations.
 *
 * @param editor - The Monaco editor instance (or null if not yet mounted)
 * @param monacoInstance - The Monaco namespace (or null if not yet loaded)
 */
export function usePluginEditorBridge(
  editor: monacoNs.editor.IStandaloneCodeEditor | null,
  monacoInstance: typeof monacoNs | null
): void {
  useEffect(() => {
    if (!editor || !monacoInstance) return;

    const handlers: Array<{ event: string; handler: EventListener }> = [];

    function listen(event: string, handler: (e: CustomEvent) => void): void {
      const wrappedHandler = ((e: Event) => {
        try {
          handler(e as CustomEvent);
        } catch (err) {
          console.warn(`[PluginEditorBridge] Error handling ${event}:`, err);
        }
      }) as EventListener;
      handlers.push({ event, handler: wrappedHandler });
      document.addEventListener(event, wrappedHandler);
    }

    // a. plugin:editor-get-content -- read editor value, respond via callback event
    listen('plugin:editor-get-content', () => {
      const content = editor.getValue();
      document.dispatchEvent(
        new CustomEvent('plugin:editor-content-response', { detail: content })
      );
    });

    // b. plugin:editor-insert-block -- insert PM block at cursor
    listen('plugin:editor-insert-block', (e) => {
      const { type, data } = e.detail as { type: string; data: unknown };
      const jsonStr = data ? JSON.stringify(data, null, 2) : '{\n  \n}';
      const blockText = `\`\`\`pm:${type}\n${jsonStr}\n\`\`\`\n`;

      const position = editor.getPosition();
      if (!position) return;

      editor.executeEdits('plugin-insert-block', [
        {
          range: new monacoInstance.Range(
            position.lineNumber,
            position.column,
            position.lineNumber,
            position.column
          ),
          text: blockText,
          forceMoveMarkers: true,
        },
      ]);
    });

    // c. plugin:editor-replace-selection -- replace current selection with text
    listen('plugin:editor-replace-selection', (e) => {
      const { text } = e.detail as { text: string };
      const selection = editor.getSelection();
      if (!selection) return;

      editor.executeEdits('plugin-replace-selection', [
        {
          range: selection,
          text,
          forceMoveMarkers: true,
        },
      ]);
    });

    // d. plugin:block-registered -- trigger re-parse by nudging editor content change
    listen('plugin:block-registered', () => {
      // Force Monaco to re-emit a content change so view zones refresh.
      // We do this by triggering a no-op edit (insert empty string at position 1,1).
      const model = editor.getModel();
      if (model) {
        model.applyEdits([
          {
            range: new monacoInstance.Range(1, 1, 1, 1),
            text: '',
          },
        ]);
      }
    });

    // e. plugin:command-registered -- no-op (slash command provider reads from registry)
    listen('plugin:command-registered', () => {
      // Intentionally empty. The CompletionItemProvider reads from PluginRegistry
      // on each invocation, so newly registered commands appear automatically.
    });

    return () => {
      for (const { event, handler } of handlers) {
        document.removeEventListener(event, handler);
      }
    };
  }, [editor, monacoInstance]);
}
