/**
 * Tauri platform detection and typed IPC wrappers.
 *
 * ALL @tauri-apps/api imports MUST be lazy (dynamic import) or gated
 * by isTauri() to prevent SSG build errors. NEVER import @tauri-apps/api
 * at the top level of any file.
 *
 * Components and stores must NEVER call invoke() directly — always use
 * the typed wrappers exported from this module.
 */

/**
 * Detect if running inside a Tauri desktop shell.
 * Returns false during SSG/SSR (no window) and in browser context.
 */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

// Phase 31+ will add typed invoke() wrappers here.
// NEVER call invoke() directly in components — always go through this module.
