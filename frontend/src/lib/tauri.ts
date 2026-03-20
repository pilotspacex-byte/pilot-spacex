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

/**
 * Read the cached Supabase access token from Tauri Store (pilot-auth.json).
 * Returns null if not in Tauri mode or no token is stored.
 */
export async function getAuthToken(): Promise<string | null> {
  if (!isTauri()) return null;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<string | null>('get_auth_token');
}

/**
 * Write auth tokens to both OS keychain and Tauri Store via Rust IPC command.
 * Keychain is the secure source of truth for Rust-side access.
 * Tauri Store is kept in sync as a fallback for WebView reads.
 */
export async function setAuthToken(
  accessToken: string | null,
  refreshToken: string | null
): Promise<void> {
  if (!isTauri()) return;
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('set_auth_token', {
    accessToken,
    refreshToken,
  });
}

/**
 * Migrate tokens from Tauri Store to OS keychain (one-time, on app startup).
 *
 * Handles the upgrade path from Plan 31-01 (Store-only) to Plan 31-02
 * (keychain as primary secure storage). Safe to call on every startup —
 * it is a no-op if tokens are already in the keychain.
 *
 * Returns true if migration was performed, false if already migrated or
 * no tokens exist.
 */
export async function migrateTokensToKeychain(): Promise<boolean> {
  if (!isTauri()) return false;
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<boolean>('migrate_tokens_to_keychain');
}
