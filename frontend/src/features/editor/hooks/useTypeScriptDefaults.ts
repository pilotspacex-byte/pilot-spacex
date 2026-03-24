'use client';

import { useEffect } from 'react';
import type * as monacoNs from 'monaco-editor';
import { configureTypeScriptDefaults } from '../language/typescript-config';

/**
 * Module-level flag ensuring TypeScript defaults are configured exactly once.
 * TS/JS defaults are global singletons in Monaco — calling setCompilerOptions
 * multiple times is harmless but wasteful.
 */
let configured = false;

/**
 * Configures Monaco's TypeScript and JavaScript language defaults on mount.
 *
 * Must be called before Editor renders so TS defaults are set before any
 * model creation (Pitfall 1 from research).
 *
 * Only touches TypeScript and JavaScript defaults — JSON, CSS, and HTML
 * language services remain on Monaco's built-in defaults (LSP-03).
 */
export function useTypeScriptDefaults(monaco: typeof monacoNs | null): void {
  useEffect(() => {
    if (!monaco || configured) return;
    configureTypeScriptDefaults(monaco);
    configured = true;
  }, [monaco]);
}
