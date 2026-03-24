import { useState, useEffect, useRef, useCallback } from 'react';
import { parseMarkdownSymbols } from '../parsers/markdownSymbols';
import type { DocumentSymbol } from '../types';

/** Debounce delay in ms for markdown files. */
const MARKDOWN_DEBOUNCE = 500;
/** Debounce delay in ms for code files. */
const CODE_DEBOUNCE = 1000;

/**
 * Find the deepest symbol whose line is <= the given cursor line.
 * Searches depth-first through the symbol tree.
 */
function findActiveSymbol(symbols: DocumentSymbol[], cursorLine: number): string | null {
  let best: string | null = null;

  function walk(nodes: DocumentSymbol[]) {
    for (const node of nodes) {
      if (node.line <= cursorLine) {
        best = node.name;
        if (node.children.length > 0) {
          walk(node.children);
        }
      }
    }
  }

  walk(symbols);
  return best;
}

interface EditorLike {
  getPosition: () => { lineNumber: number } | null;
  onDidChangeCursorPosition: (cb: (e: unknown) => void) => { dispose: () => void };
}

interface SymbolOutlineState {
  symbols: DocumentSymbol[];
  isLoading: boolean;
}

/**
 * Hook that provides symbol extraction with debounce and active symbol tracking.
 *
 * For markdown files, uses `parseMarkdownSymbols`. For code files, returns empty
 * (Monaco OutlineModel integration deferred to Phase 43 LSP).
 *
 * Listens to editor cursor changes to determine the active symbol.
 */
export function useSymbolOutline(
  content: string,
  language: string,
  editor: EditorLike | null
): {
  symbols: DocumentSymbol[];
  activeSymbolId: string | null;
  isLoading: boolean;
} {
  const [state, setState] = useState<SymbolOutlineState>({
    symbols: [],
    isLoading: true,
  });
  const [activeSymbolId, setActiveSymbolId] = useState<string | null>(null);
  const symbolsRef = useRef<DocumentSymbol[]>([]);

  // Debounced symbol extraction
  useEffect(() => {
    const delay = language === 'markdown' ? MARKDOWN_DEBOUNCE : CODE_DEBOUNCE;

    const timer = setTimeout(() => {
      let parsed: DocumentSymbol[] = [];
      if (language === 'markdown' && content) {
        parsed = parseMarkdownSymbols(content);
      }
      symbolsRef.current = parsed;
      setState({ symbols: parsed, isLoading: false });

      // Compute initial active symbol from current cursor
      if (editor) {
        const pos = editor.getPosition();
        if (pos) {
          setActiveSymbolId(findActiveSymbol(parsed, pos.lineNumber));
        }
      }
    }, delay);

    return () => {
      // When content changes and effect re-runs, mark as loading again
      setState((prev) => (prev.isLoading ? prev : { ...prev, isLoading: true }));
      clearTimeout(timer);
    };
  }, [content, language, editor]);

  // Track cursor position changes
  const updateActiveSymbol = useCallback((lineNumber: number) => {
    setActiveSymbolId(findActiveSymbol(symbolsRef.current, lineNumber));
  }, []);

  useEffect(() => {
    if (!editor) return;

    const disposable = editor.onDidChangeCursorPosition((e: unknown) => {
      const event = e as { position?: { lineNumber: number } };
      if (event.position) {
        updateActiveSymbol(event.position.lineNumber);
      }
    });

    return () => disposable.dispose();
  }, [editor, updateActiveSymbol]);

  return { symbols: state.symbols, activeSymbolId, isLoading: state.isLoading };
}
