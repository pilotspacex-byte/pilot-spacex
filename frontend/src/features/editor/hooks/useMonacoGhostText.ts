'use client';

/**
 * useMonacoGhostText — Monaco InlineCompletionsProvider for AI ghost text suggestions.
 *
 * Registers a provider for 'markdown' language that calls fetchCompletion
 * with the text context around the cursor. Ghost text appears as inline
 * completions (Tab to accept, Escape to dismiss — handled natively by Monaco).
 *
 * Ghost text color is set in the Monaco theme: editorGhostText.foreground: #6b8fad
 */
import { useEffect, useRef } from 'react';
import type * as monacoNs from 'monaco-editor';
import type { GhostTextContext } from '../types';

export type GhostTextFetcher = (context: GhostTextContext) => Promise<string>;

/**
 * Hook that registers a Monaco InlineCompletionsProvider for AI ghost text.
 *
 * @param monacoInstance - The monaco namespace (from @monaco-editor/react loader)
 * @param editor - The Monaco editor instance
 * @param fetchCompletion - Async function that returns a suggestion string
 * @param noteId - Current note ID for context
 */
export function useMonacoGhostText(
  monacoInstance: typeof monacoNs | null,
  editor: monacoNs.editor.IStandaloneCodeEditor | null,
  fetchCompletion: GhostTextFetcher,
  noteId: string
): void {
  const disposableRef = useRef<monacoNs.IDisposable | null>(null);
  const fetchRef = useRef(fetchCompletion);
  const noteIdRef = useRef(noteId);

  // Keep refs current via effect (React 19 rule: no ref writes during render)
  useEffect(() => {
    fetchRef.current = fetchCompletion;
  }, [fetchCompletion]);

  useEffect(() => {
    noteIdRef.current = noteId;
  }, [noteId]);

  useEffect(() => {
    if (!monacoInstance || !editor) return;

    disposableRef.current = monacoInstance.languages.registerInlineCompletionsProvider('markdown', {
      provideInlineCompletions: async (model, position, _context, token) => {
        const textBeforeCursor = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        });

        const textAfterCursor = model.getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: position.column,
          endLineNumber: model.getLineCount(),
          endColumn: model.getLineMaxColumn(model.getLineCount()),
        });

        const cursorPosition = model.getOffsetAt(position);

        let suggestion: string;
        try {
          suggestion = await fetchRef.current({
            textBeforeCursor,
            textAfterCursor,
            cursorPosition,
            noteId: noteIdRef.current,
          });
        } catch {
          return { items: [] };
        }

        if (token.isCancellationRequested || !suggestion) {
          return { items: [] };
        }

        return {
          items: [
            {
              insertText: suggestion,
              range: new monacoInstance.Range(
                position.lineNumber,
                position.column,
                position.lineNumber,
                position.column
              ),
            },
          ],
        };
      },

      disposeInlineCompletions: () => {
        // No-op — Monaco manages lifecycle of inline completion items
      },
    });

    return () => {
      disposableRef.current?.dispose();
      disposableRef.current = null;
    };
  }, [monacoInstance, editor]);
}
