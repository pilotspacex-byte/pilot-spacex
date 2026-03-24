'use client';

import { useEffect, useMemo, useState } from 'react';
import type * as monacoNs from 'monaco-editor';
import { ensurePythonLanguage } from '../language/python-worker';

/**
 * React hook that lazy-loads Python IntelliSense (Pyright WASM) when
 * the active file's language is 'python'.
 *
 * Returns `{ isLoading: true }` while Pyright initializes, then
 * `{ isLoading: false }` regardless of success or failure.
 *
 * The underlying worker persists across re-renders -- no cleanup needed.
 */
export function usePythonLanguage(
  monaco: typeof monacoNs | null,
  language: string
): { isLoading: boolean } {
  const isPython = language === 'python';

  // Derive loading state from whether we should load and whether loading has finished.
  // Avoids synchronous setState in effect body (React 19 react-hooks/set-state-in-effect).
  const [loadFinished, setLoadFinished] = useState(false);

  const isLoading = useMemo(
    () => isPython && !!monaco && !loadFinished,
    [isPython, monaco, loadFinished]
  );

  useEffect(() => {
    if (!monaco || !isPython) return;

    let cancelled = false;

    ensurePythonLanguage(monaco).then(() => {
      if (!cancelled) {
        setLoadFinished(true);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [monaco, isPython]);

  return { isLoading };
}
