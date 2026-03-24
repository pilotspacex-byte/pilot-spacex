'use client';

import { useEffect, useMemo, useState } from 'react';
import type * as monacoNs from 'monaco-editor';
import {
  type Diagnostic,
  type DiagnosticCounts,
  countDiagnostics,
  subscribeToDiagnostics,
} from '../language/diagnostics';

/**
 * Subscribes to Monaco's marker change events and returns normalized diagnostics.
 *
 * Uses `onDidChangeMarkers` (event-driven, not polling) for optimal performance.
 * Cleans up subscription on unmount or when `monaco` changes.
 *
 * @returns `diagnostics` — all active markers as `Diagnostic[]`
 * @returns `counts` — aggregate error/warning/info counts
 */
export function useDiagnostics(monaco: typeof monacoNs | null): {
  diagnostics: Diagnostic[];
  counts: DiagnosticCounts;
} {
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);

  useEffect(() => {
    if (!monaco) return;
    const disposable = subscribeToDiagnostics(monaco, setDiagnostics);
    return () => disposable.dispose();
  }, [monaco]);

  const counts = useMemo(() => countDiagnostics(diagnostics), [diagnostics]);

  return { diagnostics, counts };
}
