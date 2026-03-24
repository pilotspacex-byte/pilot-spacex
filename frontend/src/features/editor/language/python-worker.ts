import type * as monacoNs from 'monaco-editor';

/**
 * Lazy-loads Pyright WASM for Python code intelligence.
 *
 * Pyright WASM is ~5-8MB and must never be imported eagerly.
 * This module ensures it is loaded at most once, with a graceful
 * fallback to syntax-only highlighting if loading fails.
 *
 * The MonacoPyrightProvider registers hover, completion, signature help,
 * definition, and rename providers for the 'python' language on init().
 */

let pyrightLoaded = false;
let pyrightLoading: Promise<boolean> | null = null;

/**
 * Ensures the Pyright WASM language service is initialized for Python files.
 *
 * - Returns `true` if Pyright was successfully loaded (or was already loaded).
 * - Returns `false` if loading is in progress or failed.
 * - On failure, logs a warning and falls back to syntax highlighting only.
 *
 * Safe to call multiple times -- subsequent calls return immediately or
 * join the existing loading promise.
 */
export async function ensurePythonLanguage(monaco: typeof monacoNs): Promise<boolean> {
  if (pyrightLoaded) return true;

  // If already loading, join the existing promise
  if (pyrightLoading) return pyrightLoading;

  pyrightLoading = (async () => {
    try {
      const { MonacoPyrightProvider } = await import('monaco-pyright-lsp');
      const provider = new MonacoPyrightProvider();
      // monaco-pyright-lsp types target monaco-editor 0.52; runtime API is compatible
      // with 0.55.1 but the TypeScript types diverge. Cast to satisfy the compiler.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await provider.init(monaco as any);
      pyrightLoaded = true;
      return true;
    } catch (err) {
      console.warn('Failed to load Pyright WASM, falling back to syntax highlighting:', err);
      return false;
    } finally {
      pyrightLoading = null;
    }
  })();

  return pyrightLoading;
}
